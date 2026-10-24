"""Mídias de teste geradas na hora com o ffmpeg (sem shell), para não guardar áudio ou vídeo no repositório."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _make(path: Path, *ffmpeg_args: str) -> Path:
    """Roda o ffmpeg com lista de argumentos para criar um arquivo pequeno."""
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *ffmpeg_args, str(path)], check=True, timeout=60)
    return path


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Cria, uma vez por rodada de testes: um som de 2 s, um vídeo sem som e um arquivo corrompido."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe não instalados")
    folder = tmp_path_factory.mktemp("media")
    _make(folder / "tone.wav", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-ac", "2", "-ar", "44100")
    _make(folder / "no_audio.mp4", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=2", "-c:v", "mpeg4")
    (folder / "corrupt.mp4").write_bytes(os.urandom(4096))
    (folder / "text.mp4").write_text("isto não é um vídeo, só tem a extensão de um", encoding="utf-8")
    return folder
