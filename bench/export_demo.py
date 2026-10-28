"""Exporta a demo estática do GitHub Pages: um vídeo já legendado pelo LegendaLab, sem servidor.

Grava em site/: demo.mp4 (reduzido e sem metadados), demo.vtt e demo.json. Nenhum arquivo guarda o nome original.
Uso: python -m bench.export_demo data/meu_video.mp4
"""

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from core import config
from core.media import extract_audio, probe, validate_media
from core.pipeline import make_captions, result_to_dict
from core.transcribers.whisper_local import WhisperTranscriber

MB = 1024 * 1024


def _compress_video(src: Path, dst: Path) -> None:
    """Reduz o vídeo para a web com o ffmpeg (sem shell, com timeout) e apaga metadados como local e aparelho."""
    command = [
        "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src),
        "-map", "0:v:0", "-map", "0:a:0",  # só a 1ª trilha de vídeo e a 1ª de áudio
        "-map_metadata", "-1",  # privacidade: tira GPS, aparelho, título e qualquer outro metadado
        "-vf", f"scale=-2:'min({config.DEMO_VIDEO_MAX_HEIGHT},ih)'",  # no máximo 720p, sem aumentar vídeo menor
        "-c:v", "libx264", "-preset", "medium", "-crf", str(config.DEMO_VIDEO_CRF), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",  # o navegador começa a tocar antes de baixar o arquivo inteiro
        str(dst),
    ]
    subprocess.run(command, capture_output=True, timeout=config.FFMPEG_TIMEOUT_S, check=True)


def main() -> None:
    """Valida o vídeo, reduz para site/demo.mp4, gera a legenda com o modelo da demo e grava demo.vtt e demo.json."""
    parser = argparse.ArgumentParser(description="Gera a demo estática (site/) a partir de um vídeo seu.")
    parser.add_argument("video", type=Path, help="vídeo a legendar (só com você, porque fica público)")
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error(f"vídeo não encontrado: {args.video}")
    validate_media(probe(args.video))  # mesmas regras da demo: até 60 s e com trilha de áudio

    config.SITE_DIR.mkdir(exist_ok=True)
    demo_video = config.SITE_DIR / "demo.mp4"
    _compress_video(args.video, demo_video)
    size_mb = demo_video.stat().st_size / MB
    if size_mb > config.DEMO_VIDEO_MAX_MB:
        demo_video.unlink()
        parser.error(f"o vídeo reduzido ficou com {size_mb:.1f} MB (limite {config.DEMO_VIDEO_MAX_MB} MB); use um mais curto")

    transcriber = WhisperTranscriber(config.DEFAULT_MODEL)
    folder = Path(tempfile.mkdtemp(prefix="legendalab_demo_"))
    try:
        # A legenda sai do próprio demo.mp4, para os tempos baterem com o vídeo publicado.
        audio_path = folder / "audio.wav"
        extract_audio(demo_video, audio_path)
        result = make_captions(audio_path, transcriber)
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    (config.SITE_DIR / "demo.vtt").write_text(result.vtt, encoding="utf-8")
    with (config.SITE_DIR / "demo.json").open("w", encoding="utf-8") as f:
        json.dump(result_to_dict(result, transcriber.name), f, ensure_ascii=False, indent=2)

    summary = result.legibility["summary"]
    print(f"site/demo.mp4: {size_mb:.1f} MB · {summary['cues']} blocos · {len(result.low_confidence_cues)} duvidosos · "
          f"{summary['violations']} violações e {summary['warnings']} avisos de legibilidade ({transcriber.name})")
    print("Para conferir: .venv\\Scripts\\python -m http.server 8001 --directory site e abra http://127.0.0.1:8001")


if __name__ == "__main__":
    main()
