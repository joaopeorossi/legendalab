"""Blocos de legenda: transforma palavras com tempo em blocos que respeitam os limites do Guia."""

import math
from dataclasses import dataclass

from core import config
from core.transcribers.base import Word


@dataclass
class Cue:
    """Um bloco de legenda: número, tempos, texto, linhas, velocidade de leitura e marcação de dúvida."""

    index: int
    start: float
    end: float
    text: str
    lines: list[str]
    cps: float = 0.0
    low_confidence: bool = False
    reason: str = ""


def wrap_lines(text: str, max_chars: int, max_lines: int) -> list[str] | None:
    """Quebra o texto em linhas de até max_chars sem cortar palavras; devolve None se precisar de mais de max_lines."""
    lines: list[str] = []
    for word in text.split():
        if lines and len(lines[-1]) + 1 + len(word) <= max_chars:
            lines[-1] += " " + word
        else:
            lines.append(word)  # uma palavra maior que a linha fica sozinha nela: nunca cortamos palavras
    return lines if len(lines) <= max_lines else None


def chars_per_second(cue: Cue) -> float:
    """Velocidade de leitura do bloco: número de caracteres ÷ duração em segundos."""
    duration = cue.end - cue.start
    if duration <= 0:
        return math.inf  # bloco sem duração é impossível de ler
    return len(cue.text) / duration


def _make_cue(index: int, words: list[Word]) -> Cue:
    """Fecha um bloco: começa no início da primeira palavra, termina no fim da última e calcula o CPS."""
    text = " ".join(w.text for w in words)
    lines = wrap_lines(text, config.MAX_CHARS_PER_LINE, config.MAX_LINES) or [text]
    cue = Cue(index=index, start=words[0].start, end=words[-1].end, text=text, lines=lines)
    cue.cps = chars_per_second(cue)
    return cue


def build_cues(words: list[Word]) -> list[Cue]:
    """Algoritmo guloso: põe palavras no bloco enquanto cabe; quando não cabe, fecha o bloco e abre outro."""
    cues: list[Cue] = []
    current: list[Word] = []
    for word in words:
        candidate = current + [word]
        lines = wrap_lines(" ".join(w.text for w in candidate), config.MAX_CHARS_PER_LINE, config.MAX_LINES)
        fits = (
            lines is not None
            and max(len(line) for line in lines) <= config.MAX_CHARS_PER_LINE
            and candidate[-1].end - candidate[0].start <= config.MAX_CUE_S
        )
        if fits or not current:  # uma palavra sozinha sempre entra, mesmo que não caiba
            current = candidate
        else:
            cues.append(_make_cue(len(cues) + 1, current))
            current = [word]
    if current:
        cues.append(_make_cue(len(cues) + 1, current))
    return cues
