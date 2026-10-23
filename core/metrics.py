"""Métricas do benchmark: contagem de erros de palavra, WER e velocidade (RTF)."""

from dataclasses import dataclass

import jiwer

from core.normalize import normalize_text


@dataclass(frozen=True)
class ErrorCounts:
    """Contagens de uma frase: substituições (S), deleções (D), inserções (I) e palavras da referência (N)."""

    substitutions: int
    deletions: int
    insertions: int
    reference_words: int


def count_errors(reference: str, hypothesis: str) -> ErrorCounts:
    """Normaliza as duas frases e usa o jiwer para alinhar palavra por palavra e contar S, D e I."""
    ref = normalize_text(reference)
    hyp = normalize_text(hypothesis)
    if not ref:
        raise ValueError("A frase de referência ficou vazia depois da normalização.")
    # Hipótese vazia: o jiwer conta todas as palavras da referência como deleção.
    result = jiwer.process_words(ref, hyp)
    return ErrorCounts(
        substitutions=result.substitutions,
        deletions=result.deletions,
        insertions=result.insertions,
        reference_words=len(ref.split()),
    )


def wer(counts: ErrorCounts) -> float:
    """WER de uma frase: (S + D + I) ÷ N."""
    if counts.reference_words == 0:
        raise ValueError("Não dá para calcular o WER sem palavras na referência.")
    errors = counts.substitutions + counts.deletions + counts.insertions
    return errors / counts.reference_words


def corpus_wer(list_of_counts: list[ErrorCounts]) -> float:
    """WER do conjunto (RN9): soma de todos os erros ÷ soma de todas as palavras de referência."""
    total_words = sum(c.reference_words for c in list_of_counts)
    if total_words == 0:
        raise ValueError("Não dá para calcular o WER de corpus sem frases.")
    total_errors = sum(c.substitutions + c.deletions + c.insertions for c in list_of_counts)
    return total_errors / total_words


def rtf(processing_time_s: float, audio_duration_s: float) -> float:
    """Velocidade: tempo de processamento ÷ duração do áudio (abaixo de 1 = mais rápido que o tempo real)."""
    if audio_duration_s <= 0:
        raise ValueError("A duração do áudio precisa ser maior que zero.")
    return processing_time_s / audio_duration_s
