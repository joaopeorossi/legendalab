"""Benchmark: mede o WER e a velocidade de cada modelo no conjunto de teste e grava em results/.

Uso: python -m bench.run_benchmark --models base small --n 427 --seed 42
"""

import argparse
import csv
import json
import os
import platform
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from core import config
from core.metrics import ErrorCounts, corpus_wer, count_errors, rtf, wer
from core.transcribers.base import Transcriber, Transcription
from core.transcribers.whisper_local import WhisperTranscriber

DEFAULT_TSV = Path("data/pt-BR/test.tsv")
DEFAULT_OUT = Path("results")


@dataclass(frozen=True)
class Sample:
    """Uma frase do dataset: o arquivo de áudio e a frase correta (nada sobre quem falou)."""

    audio_path: Path
    sentence: str


def load_samples(tsv_path: Path, n: int, seed: int) -> list[Sample]:
    """Lê o TSV do Common Voice e sorteia n frases com a seed: mesma seed, mesmas frases (RN10)."""
    with tsv_path.open(encoding="utf-8", newline="") as f:
        # Modo de aspas padrão: uma frase com aspas vem como "Ele disse ""oi""".
        rows = list(csv.DictReader(f, delimiter="\t"))
    clips_dir = tsv_path.parent / "clips"
    # Só as colunas path e sentence: nunca client_id, age, gender ou accents.
    samples = [Sample(clips_dir / row["path"], row["sentence"]) for row in rows]
    if n >= len(samples):
        return samples
    return random.Random(seed).sample(samples, n)


def _confidence_signals(transcription: Transcription) -> dict[str, float | None]:
    """Resume os sinais de confiança da frase pelo pior valor de cada um, para o B3 calibrar sem rodar o modelo."""
    segments = transcription.segments
    probabilities = [word.probability for segment in segments for word in segment.words]
    return {
        "min_avg_logprob": min((s.avg_logprob for s in segments), default=None),
        "max_no_speech_prob": max((s.no_speech_prob for s in segments), default=None),
        "max_compression_ratio": max((s.compression_ratio for s in segments), default=None),
        "min_word_probability": min(probabilities, default=None),
    }


def run_model(transcriber: Transcriber, samples: list[Sample]) -> list[dict[str, Any]]:
    """Transcreve cada frase, conta os erros e guarda tempos e sinais de confiança (uma linha por frase)."""
    results = []
    for i, sample in enumerate(samples, start=1):
        transcription = transcriber.transcribe(sample.audio_path)
        hypothesis = " ".join(segment.text for segment in transcription.segments)
        counts = count_errors(sample.sentence, hypothesis)
        results.append({
            "model": transcriber.name,
            "audio_file": sample.audio_path.name,  # só o nome: o caminho completo tem o usuário do Windows
            "reference": sample.sentence,
            "hypothesis": hypothesis,
            "substitutions": counts.substitutions,
            "deletions": counts.deletions,
            "insertions": counts.insertions,
            "reference_words": counts.reference_words,
            "wer": round(wer(counts), 4),
            "audio_duration_s": round(transcription.audio_duration_s, 3),
            "processing_time_s": round(transcription.processing_time_s, 3),
            **_confidence_signals(transcription),
        })
        if i % 50 == 0:
            print(f"  {transcriber.name}: {i}/{len(samples)} frases", flush=True)  # aparece na hora, mesmo em arquivo
    return results


def summarize(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Junta as frases por modelo: número de frases, WER de corpus (RN9) e RTF do conjunto."""
    summaries = []
    for model in dict.fromkeys(r["model"] for r in results):  # cada modelo uma vez, na ordem em que rodou
        rows = [r for r in results if r["model"] == model]
        counts = [
            ErrorCounts(r["substitutions"], r["deletions"], r["insertions"], r["reference_words"]) for r in rows
        ]
        # RTF do conjunto: soma dos tempos ÷ soma das durações (a mesma lógica do WER de corpus).
        total_time = sum(r["processing_time_s"] for r in rows)
        total_audio = sum(r["audio_duration_s"] for r in rows)
        summaries.append({
            "model": model,
            "n_samples": len(rows),
            "corpus_wer": round(corpus_wer(counts), 4),
            "rtf": round(rtf(total_time, total_audio), 4),
        })
    return summaries


def write_results(
    run_dir: Path, run_info: dict[str, Any], results: list[dict[str, Any]], summaries: list[dict[str, Any]]
) -> None:
    """Grava run.json, samples.csv e summary.csv na pasta da execução; nunca copia áudio."""
    run_dir.mkdir(parents=True, exist_ok=False)  # nunca sobrescreve uma execução anterior
    with (run_dir / "run.json").open("w", encoding="utf-8") as f:
        json.dump(run_info, f, ensure_ascii=False, indent=2)
    for file_name, rows in (("samples.csv", results), ("summary.csv", summaries)):
        with (run_dir / file_name).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    """Comando do benchmark: sorteia as frases, roda cada modelo e grava os resultados."""
    parser = argparse.ArgumentParser(description="Mede o WER e o RTF de cada modelo no conjunto de teste.")
    parser.add_argument("--models", nargs="+", default=list(config.MODEL_SIZES), help="tamanhos do Whisper")
    parser.add_argument("--n", type=int, required=True, help="quantas frases usar (todas, se passar do total)")
    parser.add_argument("--seed", type=int, default=config.SEED, help="semente do sorteio (RN10)")
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV, help="arquivo TSV do Common Voice")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="pasta onde gravar os resultados")
    args = parser.parse_args()

    total = len(load_samples(args.tsv, sys.maxsize, args.seed))
    samples = load_samples(args.tsv, args.n, args.seed)
    print(f"{total} frases no {args.tsv.name}; usando {len(samples)} (seed {args.seed})")

    started_at = datetime.now()
    results: list[dict[str, Any]] = []
    wall_time_s: dict[str, float] = {}
    for size in args.models:
        load_start = time.perf_counter()
        transcriber = WhisperTranscriber(size)  # carregado uma vez, fora da medição de tempo
        print(f"{transcriber.name} carregado em {time.perf_counter() - load_start:.1f} s")
        model_start = time.perf_counter()
        results += run_model(transcriber, samples)
        wall_time_s[transcriber.name] = round(time.perf_counter() - model_start, 1)
        print(f"{transcriber.name}: {len(samples)} frases em {wall_time_s[transcriber.name]:.0f} s")

    run_info = {
        "date": started_at.isoformat(timespec="seconds"),
        "dataset": {"name": "Common Voice pt-BR (Mozilla Data Collective)", "file": args.tsv.name, "total": total},
        "seed": args.seed,
        "n_samples": len(samples),
        "models": list(wall_time_s),
        "wall_time_s": wall_time_s,
        "settings": {
            "language": config.LANGUAGE,
            "device": config.DEVICE,
            "compute_type": config.COMPUTE_TYPE,
            "cpu_threads": config.CPU_THREADS,
        },
        "normalization_version": config.NORMALIZATION_VERSION,
        "machine": {"processor": platform.processor(), "cpu_count": os.cpu_count(), "system": platform.platform()},
        "versions": {"python": platform.python_version()}
        | {lib: version(lib) for lib in ("faster-whisper", "ctranslate2", "av", "jiwer")},
    }
    run_dir = args.out / started_at.strftime("%Y-%m-%d_%H%M%S")
    write_results(run_dir, run_info, results, summarize(results))
    print(f"Resultados gravados em {run_dir}")


if __name__ == "__main__":
    main()
