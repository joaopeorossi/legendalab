"""Prévia local: legenda o seu vídeo e gera um HTML com o player em data/preview/ (fora do Git).

Uso: python -m bench.make_preview data/meu_video.mp4 --model base
"""

import argparse
import html
import json
import os
from pathlib import Path

from core import config
from core.pipeline import make_captions
from core.transcribers.whisper_local import WhisperTranscriber

PREVIEW_DIR = Path("data/preview")

HTML_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Prévia da legenda</title></head>
<body>
<p><strong>{notice}</strong></p>
<video id="player" src="{video_src}" controls width="720"></video>
<script>
  // O Chrome não carrega <track> aberto direto do disco (file://), então a legenda vira um Blob URL.
  const vtt = {vtt_json};
  const track = document.createElement("track");
  track.kind = "subtitles";
  track.srclang = "pt";
  track.label = "Português";
  track.default = true;
  track.src = URL.createObjectURL(new Blob([vtt], {{ type: "text/vtt" }}));
  document.getElementById("player").appendChild(track);
</script>
</body>
</html>
"""


def main() -> None:
    """Legenda o vídeo com o pipeline completo e grava o .vtt e o preview.html em data/preview/."""
    parser = argparse.ArgumentParser(description="Gera a legenda do seu vídeo e uma página para assistir.")
    parser.add_argument("video", type=Path, nargs="?", default=Path("data/meu_video.mp4"), help="vídeo a legendar")
    parser.add_argument("--model", default=config.MODEL_SIZES[0], help="tamanho do Whisper")
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error(f"vídeo não encontrado: {args.video}")

    result = make_captions(args.video, WhisperTranscriber(args.model))

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    (PREVIEW_DIR / f"{args.video.stem}.vtt").write_text(result.vtt, encoding="utf-8")
    video_src = Path(os.path.relpath(args.video, PREVIEW_DIR)).as_posix()
    page = HTML_TEMPLATE.format(
        notice=html.escape(result.notice),
        video_src=html.escape(video_src),
        vtt_json=json.dumps(result.vtt).replace("</", "<\\/"),  # impede o texto de fechar o <script>
    )
    (PREVIEW_DIR / "preview.html").write_text(page, encoding="utf-8")

    summary = result.legibility["summary"]
    print(f"{summary['cues']} blocos | {summary['violations']} violações | {summary['warnings']} avisos")
    for cue in result.cues:
        if cue.low_confidence:
            print(f"  Bloco {cue.index} duvidoso ({cue.reason}): {cue.text}")
    print(f"Abra {PREVIEW_DIR / 'preview.html'} no navegador.")


if __name__ == "__main__":
    main()
