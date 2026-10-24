"""O coração do projeto: do áudio à legenda conferida e marcada. A API (B4) só chama make_captions."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.captions import Cue, build_cues
from core.confidence import flag_cues
from core.legibility import check_cues
from core.transcribers.base import Transcriber
from core.vtt import to_vtt

CAPTION_NOTICE = "Legenda automática: trechos destacados podem estar errados."  # RN12


@dataclass(frozen=True)
class CaptionResult:
    """Tudo o que a demo devolve: blocos, VTT, legibilidade, blocos duvidosos, tempos e o aviso da RN12."""

    cues: list[Cue]
    vtt: str
    legibility: dict[str, Any]
    low_confidence_cues: list[int]
    audio_duration_s: float
    processing_time_s: float
    notice: str = CAPTION_NOTICE


def make_captions(audio_path: Path, transcriber: Transcriber) -> CaptionResult:
    """Transcreve, monta os blocos, confere a legibilidade, marca a baixa confiança e gera o VTT."""
    transcription = transcriber.transcribe(audio_path)
    words = [word for segment in transcription.segments for word in segment.words]
    cues = build_cues(words)
    legibility = check_cues(cues)
    cues = flag_cues(cues, transcription)
    return CaptionResult(
        cues=cues,
        vtt=to_vtt(cues),
        legibility=legibility,
        low_confidence_cues=[cue.index for cue in cues if cue.low_confidence],
        audio_duration_s=transcription.audio_duration_s,
        processing_time_s=transcription.processing_time_s,
    )
