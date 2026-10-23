"""Normalização do texto antes de medir o erro (versão em config.NORMALIZATION_VERSION)."""

import unicodedata


def normalize_text(text: str) -> str:
    """Padroniza o texto para o WER: minúsculas, sem pontuação e espaços únicos (mantém acentos e números)."""
    # NFC junta "e" + acento solto num único "é"; o acento continua valendo.
    text = unicodedata.normalize("NFC", text).lower()
    # Pontuação (categoria Unicode "P...") vira espaço: "lembre-se!" -> "lembre se ".
    without_punct = "".join(" " if unicodedata.category(ch).startswith("P") else ch for ch in text)
    return " ".join(without_punct.split())
