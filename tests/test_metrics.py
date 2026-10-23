"""Testes do WER por frase, do WER de corpus e do RTF, incluindo as fronteiras."""

import pytest

from core.metrics import ErrorCounts, corpus_wer, count_errors, rtf, wer


def test_identical_sentence_has_zero_wer() -> None:
    """Frase idêntica tem WER 0."""
    assert wer(count_errors("quero um misto quente", "quero um misto quente")) == 0.0


def test_one_substitution_in_four_words() -> None:
    """Uma troca em 4 palavras dá WER 0,25."""
    counts = count_errors("quero um misto quente", "quero um misto frio")
    assert counts == ErrorCounts(substitutions=1, deletions=0, insertions=0, reference_words=4)
    assert wer(counts) == 0.25


def test_insertions_can_exceed_one() -> None:
    """Inserções podem levar o WER acima de 1: "a" contra "a b c" dá 2,0."""
    counts = count_errors("a", "a b c")
    assert counts.insertions == 2
    assert wer(counts) == 2.0


def test_empty_hypothesis_is_all_deletions() -> None:
    """Hipótese vazia conta todas as palavras como deleção: WER 1,0."""
    counts = count_errors("quero um misto quente", "")
    assert counts == ErrorCounts(substitutions=0, deletions=4, insertions=0, reference_words=4)
    assert wer(counts) == 1.0


def test_empty_reference_raises() -> None:
    """Referência que fica vazia depois de normalizar é erro, porque não há N para dividir."""
    with pytest.raises(ValueError):
        count_errors("...", "qualquer coisa")


def test_corpus_wer_is_not_the_mean_of_sentences() -> None:
    """O WER de corpus soma antes de dividir, então não é a média das frases."""
    short = count_errors("sim", "não")  # 1 erro em 1 palavra: WER 1,0
    long = count_errors("um dois três quatro cinco seis sete oito nove", "um dois três quatro cinco seis sete oito nove")
    mean = (wer(short) + wer(long)) / 2
    assert mean == 0.5
    assert corpus_wer([short, long]) == pytest.approx(0.1)  # 1 erro ÷ 10 palavras


def test_corpus_wer_without_sentences_raises() -> None:
    """Lista vazia não tem WER de corpus."""
    with pytest.raises(ValueError):
        corpus_wer([])


def test_rtf() -> None:
    """10 s de áudio processados em 3 s dão RTF 0,3."""
    assert rtf(processing_time_s=3.0, audio_duration_s=10.0) == pytest.approx(0.3)


def test_rtf_with_zero_duration_raises() -> None:
    """Áudio com duração zero não tem RTF (seria divisão por zero)."""
    with pytest.raises(ValueError):
        rtf(processing_time_s=1.0, audio_duration_s=0.0)
