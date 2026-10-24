"""Teste do pipeline completo com o FakeTranscriber: rápido, sem IA e sempre igual."""

from pathlib import Path

from core import config
from core.pipeline import CAPTION_NOTICE, make_captions
from core.transcribers.base import Word
from core.transcribers.fake import FakeTranscriber

TEXT = "hoje vamos aprender como funciona a legenda automática para pessoas surdas no LegendaLab"


def test_pipeline_end_to_end() -> None:
    """Do "áudio" ao VTT: blocos dentro dos limites, aviso da RN12 e o bloco duvidoso marcado."""
    words = [Word(t, i * 0.35, (i + 1) * 0.35, 0.9) for i, t in enumerate(TEXT.split())]
    words[-1] = Word("LegendaLab", words[-1].start, words[-1].end, 0.2)  # palavra duvidosa no último bloco
    result = make_captions(Path("nao_existe.wav"), FakeTranscriber(words))

    assert result.vtt.startswith("WEBVTT")
    assert result.notice == CAPTION_NOTICE
    assert result.legibility["summary"]["cues"] == len(result.cues)
    assert " ".join(cue.text for cue in result.cues) == TEXT
    for cue in result.cues:
        assert len(cue.lines) <= config.MAX_LINES
        assert all(len(line) <= config.MAX_CHARS_PER_LINE for line in cue.lines)
    assert result.low_confidence_cues == [result.cues[-1].index]
    assert result.audio_duration_s == words[-1].end
