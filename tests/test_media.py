"""Testes da mídia: tipo pelo conteúdo, regras de duração e de áudio, extração em mono 16 kHz e chamada sem shell."""

import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from core import media
from core.media import MediaError, MediaInfo, extract_audio, probe, validate_media


def test_probe_reads_duration_and_audio(media_dir: Path) -> None:
    """O ffprobe descobre a duração, a trilha de áudio e o formato real."""
    info = probe(media_dir / "tone.wav")
    assert info.has_audio
    assert info.duration_s == pytest.approx(2.0, abs=0.1)
    assert "wav" in info.format_name


def test_type_comes_from_content_not_extension(media_dir: Path, tmp_path: Path) -> None:
    """Áudio com extensão .txt é aceito; texto com extensão .mp4 é recusado (RN3)."""
    disguised = shutil.copy(media_dir / "tone.wav", tmp_path / "audio.txt")
    assert probe(Path(disguised)).has_audio
    with pytest.raises(MediaError) as error:
        probe(media_dir / "text.mp4")
    assert error.value.code == "UNSUPPORTED_MEDIA"


def test_corrupt_file_is_unsupported(media_dir: Path) -> None:
    """Arquivo corrompido vira UNSUPPORTED_MEDIA."""
    with pytest.raises(MediaError) as error:
        probe(media_dir / "corrupt.mp4")
    assert error.value.code == "UNSUPPORTED_MEDIA"


def test_video_without_audio_is_detected(media_dir: Path) -> None:
    """Vídeo sem trilha de áudio: o probe funciona, mas has_audio é falso."""
    assert probe(media_dir / "no_audio.mp4").has_audio is False


@pytest.mark.parametrize(("duration", "ok"), [(60.0, True), (60.1, False)])
def test_duration_boundary(duration: float, ok: bool) -> None:
    """Exatamente 60 s passa; 60,1 s é recusado (RN1)."""
    info = MediaInfo(duration_s=duration, has_audio=True, format_name="wav")
    if ok:
        validate_media(info)
    else:
        with pytest.raises(MediaError) as error:
            validate_media(info)
        assert error.value.code == "DURATION_EXCEEDED"


def test_no_audio_track_is_rejected() -> None:
    """Sem trilha de áudio não há o que legendar (RN5)."""
    with pytest.raises(MediaError) as error:
        validate_media(MediaInfo(duration_s=10.0, has_audio=False, format_name="mp4"))
    assert error.value.code == "NO_AUDIO_TRACK"


def test_extract_audio_is_mono_16k(media_dir: Path, tmp_path: Path) -> None:
    """O áudio extraído de um som estéreo de 44,1 kHz sai mono e com 16 kHz."""
    output = tmp_path / "audio.wav"
    extract_audio(media_dir / "tone.wav", output)
    with wave.open(str(output), "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getframerate() == 16000


def test_ffprobe_is_called_without_shell_and_with_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """O ffprobe recebe uma lista de argumentos, sem shell e com timeout."""
    calls = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        """Finge ser o subprocess.run: anota como foi chamado e devolve uma falha."""
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, returncode=1, stdout=b"", stderr=b"")

    monkeypatch.setattr(media.subprocess, "run", fake_run)
    with pytest.raises(MediaError):
        probe(Path("qualquer; rm -rf ~"))
    command, kwargs = calls[0]
    assert isinstance(command, list)
    assert command[-1] == "qualquer; rm -rf ~"  # vira um argumento só, nunca um comando
    assert kwargs.get("shell") is not True
    assert "timeout" in kwargs
