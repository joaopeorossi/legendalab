"""Comando de teste: transcreve um áudio e, se houver referência, mostra o WER.

Uso: python -m bench.transcribe_one <áudio> --model base --reference "frase correta"
"""

import argparse
import time
from pathlib import Path

from core import config
from core.metrics import count_errors, rtf, wer
from core.transcribers.whisper_local import WhisperTranscriber


def main() -> None:
    """Transcreve um áudio pelo terminal, imprime cada palavra com o tempo e, se houver referência, o WER."""
    parser = argparse.ArgumentParser(description="Transcreve um áudio e mostra cada palavra com o tempo.")
    parser.add_argument("audio", type=Path, help="caminho do arquivo de áudio")
    parser.add_argument("--model", default=config.MODEL_SIZES[0], help=f"tamanho do Whisper (padrão: {config.MODEL_SIZES[0]})")
    parser.add_argument("--reference", help="frase correta, para calcular o WER")
    args = parser.parse_args()
    if not args.audio.is_file():
        parser.error(f"arquivo de áudio não encontrado: {args.audio}")

    load_start = time.perf_counter()
    transcriber = WhisperTranscriber(args.model)
    print(f"Modelo {transcriber.name} carregado em {time.perf_counter() - load_start:.1f} s")

    result = transcriber.transcribe(args.audio)
    for segment in result.segments:
        for word in segment.words:
            print(f"[{word.start:6.2f} -> {word.end:6.2f}] {word.text:<20} p={word.probability:.2f}")
    speed = rtf(result.processing_time_s, result.audio_duration_s)
    print(f"Áudio: {result.audio_duration_s:.2f} s | processamento: {result.processing_time_s:.2f} s | RTF: {speed:.2f}")

    if args.reference:
        hypothesis = " ".join(segment.text for segment in result.segments)
        counts = count_errors(args.reference, hypothesis)
        print(f"Referência:  {args.reference}")
        print(f"Transcrição: {hypothesis}")
        print(
            f"S={counts.substitutions} D={counts.deletions} I={counts.insertions} "
            f"N={counts.reference_words} | WER: {wer(counts):.1%}"
        )


if __name__ == "__main__":
    main()
