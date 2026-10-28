"""Teste da exportação da demo estática: o ffmpeg é chamado sem shell, com timeout e apagando os metadados."""

import subprocess
from pathlib import Path

import pytest

from bench import export_demo


def test_compress_video_strips_metadata_without_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    """O vídeo publicado perde os metadados (GPS, aparelho), e o nome do arquivo vira um argumento só."""
    calls = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        """Finge ser o subprocess.run: anota como foi chamado e devolve sucesso."""
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(export_demo.subprocess, "run", fake_run)
    export_demo._compress_video(Path("entrada; rm -rf ~.mp4"), Path("saida.mp4"))
    command, kwargs = calls[0]
    assert isinstance(command, list)
    assert command[command.index("-map_metadata") + 1] == "-1"
    assert "entrada; rm -rf ~.mp4" in command  # um argumento só, nunca um comando
    assert kwargs.get("shell") is not True
    assert "timeout" in kwargs
