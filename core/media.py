"""Mídia: descobre o que é o arquivo (ffprobe), aplica as regras e extrai o áudio (ffmpeg).

ffprobe e ffmpeg são chamados com lista de argumentos e timeout, nunca por shell.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from core import config

UNSUPPORTED_MESSAGE = "Formato não suportado ou arquivo corrompido. Envie um vídeo ou áudio comum (MP4, MOV, WebM, MP3, WAV)."


@dataclass(frozen=True)
class MediaInfo:
    """O que o ffprobe descobriu: duração, se tem trilha de áudio e o formato real do arquivo."""

    duration_s: float
    has_audio: bool
    format_name: str


class MediaError(Exception):
    """Erro de mídia com código e mensagem em português; não sabe nada de HTTP (quem traduz é a API)."""

    def __init__(self, code: str, message: str) -> None:
        """Guarda o código (por exemplo, NO_AUDIO_TRACK) e a mensagem para a pessoa."""
        super().__init__(message)
        self.code = code
        self.message = message


def probe(path: Path) -> MediaInfo:
    """Roda o ffprobe e decide o tipo pelo conteúdo do arquivo, nunca pela extensão (RN3)."""
    command = ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]
    try:
        completed = subprocess.run(command, capture_output=True, timeout=config.FFPROBE_TIMEOUT_S, check=False)
    except subprocess.TimeoutExpired as exc:
        raise MediaError("UNSUPPORTED_MEDIA", UNSUPPORTED_MESSAGE) from exc
    if completed.returncode != 0:
        raise MediaError("UNSUPPORTED_MEDIA", UNSUPPORTED_MESSAGE)

    data = json.loads(completed.stdout or b"{}")  # bytes em UTF-8: não depende da codificação do Windows
    fmt = data.get("format", {})
    if not set(fmt.get("format_name", "").split(",")) & config.ALLOWED_FORMATS:
        raise MediaError("UNSUPPORTED_MEDIA", UNSUPPORTED_MESSAGE)
    try:
        duration = float(fmt["duration"])
    except (KeyError, ValueError) as exc:
        raise MediaError("UNSUPPORTED_MEDIA", UNSUPPORTED_MESSAGE) from exc
    has_audio = any(stream.get("codec_type") == "audio" for stream in data.get("streams", []))
    return MediaInfo(duration_s=duration, has_audio=has_audio, format_name=fmt["format_name"])


def validate_media(info: MediaInfo) -> None:
    """Aplica a RN1 (duração máxima) e a RN5 (precisa ter áudio) cedo, antes de gastar processamento."""
    if info.duration_s > config.MAX_DURATION_S:
        duration = f"{info.duration_s:.1f}".replace(".", ",")
        raise MediaError(
            "DURATION_EXCEEDED",
            f"O vídeo tem {duration} s e o limite é {config.MAX_DURATION_S:.0f} s. Envie um trecho mais curto.",
        )
    if not info.has_audio:
        raise MediaError("NO_AUDIO_TRACK", "O arquivo não tem trilha de áudio, então não há fala para legendar.")


def extract_audio(src: Path, dst: Path) -> None:
    """Usa o ffmpeg para tirar o áudio em mono e 16 kHz, o formato com que o Whisper trabalha."""
    command = [
        "ffmpeg", "-nostdin", "-v", "error", "-y",
        "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", str(dst),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, timeout=config.FFMPEG_TIMEOUT_S, check=False)
    except subprocess.TimeoutExpired as exc:
        raise MediaError("UNSUPPORTED_MEDIA", "Não foi possível extrair o áudio a tempo.") from exc
    if completed.returncode != 0:
        raise MediaError("UNSUPPORTED_MEDIA", "Não foi possível extrair o áudio do arquivo.")
