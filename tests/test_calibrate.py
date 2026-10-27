"""Testes da calibração: os "erros sem aviso" contam só as frases que a regra NÃO marcou."""

import pytest

from bench.calibrate import _calibrate_model


def make_row(min_word_probability: float, substitutions: int, reference_words: int) -> dict[str, str]:
    """Cria uma linha no formato do samples.csv, com sinais bons exceto a probabilidade de palavra."""
    return {
        "min_avg_logprob": "-0.2",
        "max_no_speech_prob": "0.01",
        "max_compression_ratio": "1.1",
        "min_word_probability": str(min_word_probability),
        "hypothesis": "uma frase qualquer sem repetição",
        "substitutions": str(substitutions),
        "deletions": "0",
        "insertions": "0",
        "reference_words": str(reference_words),
    }


def test_errors_without_warning_count_only_unflagged_sentences() -> None:
    """2 erros numa frase marcada e 1 numa não marcada: só 1 erro passa sem aviso, em 7 palavras."""
    result = _calibrate_model([make_row(0.2, substitutions=2, reference_words=3), make_row(0.9, 1, 4)])
    assert (result["flagged"], result["unflagged"]) == (1, 1)
    assert result["errors_without_warning"] == 1
    assert result["errors_without_warning_rate"] == pytest.approx(round(1 / 7, 4))


def test_sentence_at_the_cutoff_is_not_flagged() -> None:
    """Probabilidade exatamente no corte (0,5) não marca, então o erro dessa frase passa sem aviso."""
    result = _calibrate_model([make_row(0.5, substitutions=1, reference_words=5)])
    assert result["flagged"] == 0
    assert result["errors_without_warning"] == 1
    assert result["errors_without_warning_rate"] == 0.2
