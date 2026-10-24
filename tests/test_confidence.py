"""Testes da baixa confiança: sinais acima e abaixo do corte, repetição e marcação dos blocos."""

from dataclasses import replace

import pytest

from core.captions import Cue
from core.confidence import Signals, flag_cues, has_repetition, is_low_confidence
from core.transcribers.base import Segment, Transcription, Word

CONFIDENT = Signals(avg_logprob=-0.3, no_speech_prob=0.01, compression_ratio=1.2, min_word_probability=0.9)


def test_confident_signals_are_not_flagged() -> None:
    """Sinais bons: o trecho não é marcado e não há motivo."""
    assert is_low_confidence(CONFIDENT) == (False, "")


@pytest.mark.parametrize(
    ("field", "at_cutoff", "beyond", "reason"),
    [
        ("no_speech_prob", 0.6, 0.61, "provável trecho sem fala"),
        ("avg_logprob", -1.0, -1.01, "modelo inseguro no trecho"),
        ("compression_ratio", 2.4, 2.41, "texto repetitivo demais"),
        ("min_word_probability", 0.5, 0.49, "palavra com baixa probabilidade"),
    ],
)
def test_each_signal_cutoff(field: str, at_cutoff: float, beyond: float, reason: str) -> None:
    """Exatamente no corte não marca; passando do corte marca, com o motivo certo."""
    assert is_low_confidence(replace(CONFIDENT, **{field: at_cutoff}))[0] is False
    assert is_low_confidence(replace(CONFIDENT, **{field: beyond})) == (True, reason)


def test_repetition_is_detected() -> None:
    """Mesma palavra ou mesmo trecho 3 vezes seguidas é repetição, ignorando pontuação e maiúsculas."""
    assert has_repetition("obrigado obrigado obrigado".split())
    assert has_repetition("eu vou eu vou eu vou".split())
    assert has_repetition("Obrigado, obrigado. OBRIGADO!".split())


def test_normal_speech_is_not_repetition() -> None:
    """Fala normal e uma repetição dupla ("não, não") não contam."""
    assert not has_repetition("não não".split())
    assert not has_repetition("quero um misto quente e um suco".split())


def test_flag_cues_marks_only_the_doubtful_cue() -> None:
    """Só o bloco com a palavra de baixa probabilidade fica marcado."""
    words = [Word("bom", 0.0, 0.4, 0.9), Word("dia", 0.4, 1.0, 0.95), Word("pessoal", 1.0, 2.0, 0.2)]
    segment = Segment("bom dia pessoal", 0.0, 2.0, words, avg_logprob=-0.2, no_speech_prob=0.01, compression_ratio=1.1)
    transcription = Transcription(segments=[segment], audio_duration_s=2.0, processing_time_s=0.1)
    cues = [
        Cue(index=1, start=0.0, end=1.0, text="bom dia", lines=["bom dia"]),
        Cue(index=2, start=1.0, end=2.0, text="pessoal", lines=["pessoal"]),
    ]
    first, second = flag_cues(cues, transcription)
    assert not first.low_confidence
    assert second.low_confidence
    assert second.reason == "palavra com baixa probabilidade"
