"""O coração do projeto: do áudio à legenda conferida e marcada. A API (B4) só chama make_captions."""

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.captions import Cue, build_cues
from core.confidence import flag_cues
from core.legibility import check_cues
from core.metrics import rtf
from core.transcribers.base import Transcriber
from core.vtt import to_vtt

CAPTION_NOTICE = "Legenda automática: trechos destacados podem estar errados."  # RN12
NO_SPEECH_WARNING = {"code": "NO_SPEECH_DETECTED", "message": "Nenhuma fala foi detectada no vídeo."}


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


def _json_safe(value: Any) -> Any:
    """Troca números infinitos (CPS de um bloco sem duração) por None, porque JSON não aceita infinito."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def result_to_dict(result: CaptionResult, model: str) -> dict[str, Any]:
    """Converte o resultado no JSON que a página exibe; a API e a demo estática usam este mesmo formato."""
    speed = rtf(result.processing_time_s, result.audio_duration_s) if result.audio_duration_s > 0 else None
    return _json_safe({
        "model": model,
        "audio_duration_s": round(result.audio_duration_s, 2),
        "processing_time_s": round(result.processing_time_s, 2),
        "rtf": None if speed is None else round(speed, 3),
        "cues": [asdict(cue) for cue in result.cues],
        "vtt": result.vtt,
        "legibility": {
            "violations": [asdict(issue) for issue in result.legibility["violations"]],
            "warnings": [asdict(issue) for issue in result.legibility["warnings"]],
            "summary": result.legibility["summary"],
        },
        "low_confidence_cues": result.low_confidence_cues,
        "notice": result.notice,
        "warning": None if result.cues else NO_SPEECH_WARNING,  # sem fala: 200 com aviso, não erro
    })
