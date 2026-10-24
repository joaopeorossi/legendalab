"""Legibilidade: confere cada bloco contra os limites do Guia (RN7). Aponta, não reescreve (RN13)."""

from dataclasses import dataclass
from typing import Any

from core import config
from core.captions import Cue


@dataclass(frozen=True)
class Issue:
    """Um problema de legibilidade: bloco, regra, gravidade ("violation" ou "warning"), valor medido e limite."""

    cue_index: int
    rule: str
    severity: str
    value: float
    limit: float


def check_cue(cue: Cue) -> list[Issue]:
    """Confere um bloco: linhas, caracteres por linha, velocidade de leitura (CPS) e duração."""
    issues = []
    if len(cue.lines) > config.MAX_LINES:
        issues.append(Issue(cue.index, "max_lines", "violation", len(cue.lines), config.MAX_LINES))
    longest = max((len(line) for line in cue.lines), default=0)
    if longest > config.MAX_CHARS_PER_LINE:
        issues.append(Issue(cue.index, "max_chars_per_line", "violation", longest, config.MAX_CHARS_PER_LINE))
    if cue.cps > config.CPS_VIOLATION:
        issues.append(Issue(cue.index, "cps", "violation", round(cue.cps, 1), config.CPS_VIOLATION))
    elif cue.cps > config.CPS_WARNING:
        issues.append(Issue(cue.index, "cps", "warning", round(cue.cps, 1), config.CPS_WARNING))
    duration = round(cue.end - cue.start, 3)
    if duration < config.MIN_CUE_S:
        issues.append(Issue(cue.index, "min_duration", "violation", duration, config.MIN_CUE_S))
    elif duration > config.MAX_CUE_S:
        issues.append(Issue(cue.index, "max_duration", "violation", duration, config.MAX_CUE_S))
    return issues


def check_cues(cues: list[Cue]) -> dict[str, Any]:
    """Confere todos os blocos e devolve as violações, os avisos e um resumo com as contagens."""
    issues = [issue for cue in cues for issue in check_cue(cue)]
    violations = [i for i in issues if i.severity == "violation"]
    warnings = [i for i in issues if i.severity == "warning"]
    summary = {"cues": len(cues), "violations": len(violations), "warnings": len(warnings)}
    return {"violations": violations, "warnings": warnings, "summary": summary}
