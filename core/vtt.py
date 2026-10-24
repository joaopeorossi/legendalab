"""Exportação em WebVTT, o formato de legenda que o player do navegador entende sem biblioteca."""

from core.captions import Cue


def format_timestamp(seconds: float) -> str:
    """Converte segundos para o formato do WebVTT: 75,5 s vira 00:01:15.500."""
    if seconds < 0:
        raise ValueError("O tempo da legenda não pode ser negativo.")
    total_ms = round(seconds * 1000)
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def to_vtt(cues: list[Cue]) -> str:
    """Escreve o texto WebVTT: cabeçalho WEBVTT e, para cada bloco, o número, "início --> fim" e as linhas."""
    parts = ["WEBVTT", ""]
    for cue in cues:
        # &, < e > têm significado especial no WebVTT: sem escapar, o texto vira marcação ou o arquivo fica inválido.
        lines = [line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for line in cue.lines]
        parts += [str(cue.index), f"{format_timestamp(cue.start)} --> {format_timestamp(cue.end)}", *lines, ""]
    return "\n".join(parts)
