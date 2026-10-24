"""Testes da quebra em blocos: nenhum bloco passa de 2 linhas x 37 caracteres nem de 6 segundos."""

import math

from core import config
from core.captions import Cue, build_cues, chars_per_second, wrap_lines
from core.transcribers.base import Word

TEXT = (
    "a legenda automática precisa caber na tela sem cortar palavras e sem passar do tempo que a "
    "pessoa surda leva para ler cada bloco com calma enquanto o vídeo continua tocando normalmente"
)


def make_words(text: str, word_s: float = 0.3) -> list[Word]:
    """Cria palavras seguidas, cada uma durando word_s segundos."""
    return [Word(t, i * word_s, (i + 1) * word_s, 0.9) for i, t in enumerate(text.split())]


def test_wrap_lines_does_not_cut_words() -> None:
    """A quebra respeita 37 caracteres por linha e não perde nem corta palavras."""
    lines = wrap_lines("a legenda precisa caber em duas linhas de trinta e sete", 37, 2)
    assert lines is not None
    assert all(len(line) <= 37 for line in lines)
    assert " ".join(lines) == "a legenda precisa caber em duas linhas de trinta e sete"


def test_wrap_lines_returns_none_when_more_than_max_lines() -> None:
    """Texto que precisaria de 3 linhas não cabe em 2."""
    assert wrap_lines(TEXT, 37, 2) is None


def test_long_word_stays_alone_on_its_line() -> None:
    """Uma palavra maior que a linha fica sozinha nela, inteira."""
    assert wrap_lines("x" * 40, 37, 2) == ["x" * 40]


def test_no_cue_exceeds_two_lines_of_37_chars() -> None:
    """Nenhum bloco passa de 2 linhas nem de 37 caracteres por linha."""
    cues = build_cues(make_words(TEXT))
    assert len(cues) > 1
    for cue in cues:
        assert len(cue.lines) <= config.MAX_LINES
        assert all(len(line) <= config.MAX_CHARS_PER_LINE for line in cue.lines)


def test_cues_keep_every_word_in_order() -> None:
    """Juntando os blocos, o texto é exatamente o original, na mesma ordem."""
    cues = build_cues(make_words(TEXT))
    assert " ".join(cue.text for cue in cues) == TEXT
    assert [cue.index for cue in cues] == list(range(1, len(cues) + 1))


def test_cue_times_come_from_first_and_last_word() -> None:
    """O bloco começa no início da primeira palavra e termina no fim da última."""
    words = make_words(TEXT)
    first = build_cues(words)[0]
    n_words = len(first.text.split())
    assert first.start == words[0].start
    assert first.end == words[n_words - 1].end


def test_cue_is_closed_before_six_seconds() -> None:
    """Fala lenta: o bloco fecha antes de passar de 6 s, mesmo cabendo mais texto."""
    cues = build_cues(make_words("um dois três quatro cinco seis sete oito nove dez", word_s=1.0))
    assert len(cues) == 2
    assert all(cue.end - cue.start <= config.MAX_CUE_S for cue in cues)


def test_chars_per_second() -> None:
    """CPS = caracteres ÷ duração: 30 caracteres em 2 s dão 15."""
    cue = Cue(index=1, start=0.0, end=2.0, text="x" * 30, lines=["x" * 30])
    assert chars_per_second(cue) == 15.0


def test_chars_per_second_without_duration_is_infinite() -> None:
    """Bloco sem duração é impossível de ler: CPS infinito (vira violação)."""
    cue = Cue(index=1, start=1.0, end=1.0, text="oi", lines=["oi"])
    assert math.isinf(chars_per_second(cue))
