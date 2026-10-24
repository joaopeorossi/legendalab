"""Testes da legibilidade (RN7), com as fronteiras de velocidade e de duração."""

import pytest

from core.captions import Cue
from core.legibility import check_cue, check_cues


def make_cue(cps: float = 10.0, start: float = 0.0, end: float = 2.0, lines: list[str] | None = None) -> Cue:
    """Cria um bloco com a velocidade, a duração e as linhas pedidas."""
    lines = lines or ["texto"]
    return Cue(index=1, start=start, end=end, text=" ".join(lines), lines=lines, cps=cps)


def rules(cue: Cue) -> list[tuple[str, str]]:
    """Lista (regra, gravidade) dos problemas encontrados no bloco."""
    return [(issue.rule, issue.severity) for issue in check_cue(cue)]


@pytest.mark.parametrize(
    ("cps", "expected"),
    [
        (14.9, []),
        (15.0, []),
        (15.1, [("cps", "warning")]),
        (18.0, [("cps", "warning")]),
        (18.1, [("cps", "violation")]),
    ],
)
def test_cps_boundaries(cps: float, expected: list[tuple[str, str]]) -> None:
    """Até 15 está ok; acima de 15 até 18 é aviso; acima de 18 é violação."""
    assert rules(make_cue(cps=cps)) == expected


@pytest.mark.parametrize(
    ("end", "expected"),
    [
        (0.9, [("min_duration", "violation")]),
        (1.0, []),
        (6.0, []),
        (6.1, [("max_duration", "violation")]),
    ],
)
def test_duration_boundaries(end: float, expected: list[tuple[str, str]]) -> None:
    """O bloco precisa durar de 1 s a 6 s, incluindo os dois limites."""
    assert rules(make_cue(start=0.0, end=end)) == expected


def test_three_lines_is_a_violation() -> None:
    """Mais de 2 linhas é violação."""
    assert rules(make_cue(lines=["um", "dois", "três"])) == [("max_lines", "violation")]


def test_line_length_boundary() -> None:
    """Linha de 37 caracteres está ok; de 38 é violação."""
    assert rules(make_cue(lines=["x" * 37])) == []
    assert rules(make_cue(lines=["x" * 38])) == [("max_chars_per_line", "violation")]


def test_check_cues_summary() -> None:
    """O resumo conta blocos, violações e avisos de todos os blocos."""
    report = check_cues([make_cue(cps=10.0), make_cue(cps=16.0), make_cue(cps=20.0)])
    assert report["summary"] == {"cues": 3, "violations": 1, "warnings": 1}
