"""Calibração da baixa confiança: as frases marcadas como duvidosas erram mais que as outras?

Lê o samples.csv do B2 (sem rodar os modelos de novo) e aplica a mesma regra da demo a cada frase.
Uso: python -m bench.calibrate results/<data_hora>
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from core import config
from core.confidence import REPETITION_REASON, Signals, has_repetition, is_low_confidence
from core.metrics import ErrorCounts, corpus_wer


def _calibrate_model(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Separa as frases de um modelo em marcadas e não marcadas e calcula o WER de corpus de cada grupo."""
    flagged: list[ErrorCounts] = []
    unflagged: list[ErrorCounts] = []
    reasons: Counter[str] = Counter()
    without_transcription = 0
    for r in rows:
        if not r["min_word_probability"]:  # nenhuma palavra reconhecida: não há sinais para avaliar
            without_transcription += 1
            continue
        signals = Signals(
            avg_logprob=float(r["min_avg_logprob"]),
            no_speech_prob=float(r["max_no_speech_prob"]),
            compression_ratio=float(r["max_compression_ratio"]),
            min_word_probability=float(r["min_word_probability"]),
        )
        low, reason = is_low_confidence(signals)
        found = reason.split("; ") if low else []
        if has_repetition(r["hypothesis"].split()):
            found.append(REPETITION_REASON)
        counts = ErrorCounts(
            int(r["substitutions"]), int(r["deletions"]), int(r["insertions"]), int(r["reference_words"])
        )
        (flagged if found else unflagged).append(counts)
        reasons.update(found)
    flagged_errors = sum(c.substitutions + c.deletions + c.insertions for c in flagged)
    total_errors = flagged_errors + sum(c.substitutions + c.deletions + c.insertions for c in unflagged)
    return {
        "flagged": len(flagged),
        "unflagged": len(unflagged),
        "without_transcription": without_transcription,
        "wer_flagged": round(corpus_wer(flagged), 4) if flagged else None,
        "wer_unflagged": round(corpus_wer(unflagged), 4) if unflagged else None,
        # Que parte de todos os erros caiu em frases marcadas: quanto do erro a pessoa foi avisada.
        "errors_in_flagged": round(flagged_errors / total_errors, 4) if total_errors else None,
        "reasons": dict(reasons),
    }


def main() -> None:
    """Compara, por modelo, o WER das frases marcadas com o das não marcadas e grava calibration.json."""
    parser = argparse.ArgumentParser(description="Calibra a marcação de baixa confiança com o samples.csv do B2.")
    parser.add_argument("run_dir", type=Path, help="pasta da execução, por exemplo results/2026-10-24_101500")
    args = parser.parse_args()
    with (args.run_dir / "samples.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    cutoffs = {
        "max_no_speech_prob": config.LOW_CONF_MAX_NO_SPEECH_PROB,
        "min_avg_logprob": config.LOW_CONF_MIN_AVG_LOGPROB,
        "max_compression_ratio": config.LOW_CONF_MAX_COMPRESSION_RATIO,
        "min_word_probability": config.LOW_CONF_MIN_WORD_PROBABILITY,
        "repetition": f"{config.REPETITION_MIN_REPEATS}x seguidas, trechos de até {config.REPETITION_MAX_NGRAM} palavras",
    }
    report: dict[str, Any] = {"cutoffs": cutoffs, "models": {}}
    for model in dict.fromkeys(r["model"] for r in rows):
        result = _calibrate_model([r for r in rows if r["model"] == model])
        report["models"][model] = result
        flagged_wer = "-" if result["wer_flagged"] is None else f"{result['wer_flagged']:.1%}"
        unflagged_wer = "-" if result["wer_unflagged"] is None else f"{result['wer_unflagged']:.1%}"
        print(
            f"{model}: {result['flagged']} frases marcadas tiveram WER de {flagged_wer}, "
            f"contra {unflagged_wer} nas {result['unflagged']} demais, e concentraram "
            f"{result['errors_in_flagged']:.0%} dos erros ({result['without_transcription']} sem transcrição, "
            f"fora da conta). Motivos: {result['reasons']}"
        )

    with (args.run_dir / "calibration.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Calibração gravada em {args.run_dir / 'calibration.json'}")


if __name__ == "__main__":
    main()
