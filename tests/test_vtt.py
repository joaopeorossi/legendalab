"""Testes do WebVTT: formato do tempo e arquivo completo comparado com um arquivo esperado."""

from pathlib import Path

import pytest

from core.captions import Cue
from core.vtt import format_timestamp, to_vtt

EXPECTED_VTT = Path(__file__).parent / "fixtures" / "expected.vtt"


def test_format_timestamp() -> None:
    """75,5 s vira 00:01:15.500; zero e horas também saem no formato certo."""
    assert format_timestamp(75.5) == "00:01:15.500"
    assert format_timestamp(0) == "00:00:00.000"
    assert format_timestamp(3661.25) == "01:01:01.250"


def test_negative_timestamp_raises() -> None:
    """Tempo negativo não existe numa legenda."""
    with pytest.raises(ValueError):
        format_timestamp(-1)


def test_to_vtt_matches_expected_file() -> None:
    """O VTT gerado é igual, caractere por caractere, ao arquivo esperado."""
    cues = [
        Cue(index=1, start=0.0, end=2.5, text="Quero um misto quente", lines=["Quero um misto quente"]),
        Cue(
            index=2,
            start=2.6,
            end=75.5,
            text="e um suco de laranja, por favor",
            lines=["e um suco de laranja,", "por favor"],
        ),
    ]
    assert to_vtt(cues) == EXPECTED_VTT.read_text(encoding="utf-8")


def test_special_characters_are_escaped() -> None:
    """&, < e > viram entidades, para o texto não virar marcação no player."""
    cue = Cue(index=1, start=0.0, end=1.0, text="a < b & c", lines=["a < b & c"])
    assert "a &lt; b &amp; c" in to_vtt([cue])
