"""Testes da normalização: pontuação e maiúsculas não contam como erro; acentos contam."""

from core.metrics import count_errors
from core.normalize import normalize_text


def test_lowercase_and_punctuation_removed() -> None:
    """Maiúsculas viram minúsculas e a pontuação some."""
    assert normalize_text("Olá, Mundo! Tudo bem?") == "olá mundo tudo bem"


def test_multiple_spaces_become_one() -> None:
    """Espaços repetidos, tabs e espaços nas pontas viram um espaço só."""
    assert normalize_text("  quero   um\tmisto  ") == "quero um misto"


def test_hyphen_becomes_space() -> None:
    """O hífen vira espaço, para não juntar as palavras."""
    assert normalize_text("Lembre-se!") == "lembre se"


def test_accents_are_kept() -> None:
    """Acentos não são removidos: "e" e "é" são palavras diferentes."""
    assert normalize_text("É") == "é"
    assert normalize_text("é") != normalize_text("e")


def test_composed_and_decomposed_accents_are_equal() -> None:
    """O mesmo "é" escrito de dois jeitos internos vira o mesmo texto."""
    assert normalize_text("é") == normalize_text("é")


def test_numbers_are_not_converted() -> None:
    """Números em algarismo ficam como estão (a v1 não converte números)."""
    assert normalize_text("3 gatos") == "3 gatos"


def test_punctuation_and_case_are_not_errors() -> None:
    """Diferença só de pontuação e maiúsculas dá zero erros."""
    counts = count_errors("Quero um misto quente.", "quero, UM misto quente")
    assert (counts.substitutions, counts.deletions, counts.insertions) == (0, 0, 0)


def test_missing_accent_is_an_error() -> None:
    """Faltar um acento conta como uma substituição."""
    counts = count_errors("ele é bom", "ele e bom")
    assert counts.substitutions == 1
