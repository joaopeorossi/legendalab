"""Teste do pipeline completo com o FakeTranscriber: rápido, sem IA e sempre igual."""

import json
from pathlib import Path

from core import config
from core.pipeline import CAPTION_NOTICE, make_captions, result_to_dict
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


def test_result_to_dict_has_the_page_format() -> None:
    """O JSON tem os campos que a página lê (na API e na demo estática), sem nome de arquivo."""
    words = [Word(t, i * 0.35, (i + 1) * 0.35, 0.9) for i, t in enumerate(TEXT.split())]
    body = result_to_dict(make_captions(Path("nao_existe.wav"), FakeTranscriber(words)), "fake")
    assert set(body) == {
        "model", "audio_duration_s", "processing_time_s", "rtf", "cues", "vtt",
        "legibility", "low_confidence_cues", "notice", "warning",
    }
    assert set(body["cues"][0]) == {"index", "start", "end", "text", "lines", "cps", "low_confidence", "reason"}
    assert body["warning"] is None
    assert "nao_existe" not in json.dumps(body)


def test_result_to_dict_replaces_infinity_with_none() -> None:
    """Bloco sem duração tem CPS infinito; no JSON ele vira None, porque JSON não aceita infinito."""
    body = result_to_dict(make_captions(Path("x.wav"), FakeTranscriber([Word("oi", 1.0, 1.0, 0.9)])), "fake")
    assert body["cues"][0]["cps"] is None
    json.dumps(body, allow_nan=False)  # quebraria se sobrasse algum infinito


def test_result_to_dict_without_speech_warns() -> None:
    """Sem fala detectada: nenhum bloco e o aviso NO_SPEECH_DETECTED (não é erro)."""
    body = result_to_dict(make_captions(Path("x.wav"), FakeTranscriber([])), "fake")
    assert body["cues"] == []
    assert body["warning"]["code"] == "NO_SPEECH_DETECTED"
