"""Baixa confiança: marca os trechos em que o próprio modelo está inseguro (F10).

A mesma regra (is_low_confidence + has_repetition) é usada na demo e na calibração,
por isso o número da calibração vale para o que a demo marca.
"""

from dataclasses import dataclass, replace

from core import config
from core.captions import Cue
from core.normalize import normalize_text
from core.transcribers.base import Transcription

REPETITION_REASON = "trecho repetido"


@dataclass(frozen=True)
class Signals:
    """Sinais do modelo para um trecho: log-probabilidade média, chance de não haver fala, compressão e a pior palavra."""

    avg_logprob: float
    no_speech_prob: float
    compression_ratio: float
    min_word_probability: float


def is_low_confidence(signals: Signals) -> tuple[bool, str]:
    """A regra: se algum sinal passar do corte, o trecho é duvidoso; devolve a decisão e o motivo."""
    reasons = []
    if signals.no_speech_prob > config.LOW_CONF_MAX_NO_SPEECH_PROB:
        reasons.append("provável trecho sem fala")
    if signals.avg_logprob < config.LOW_CONF_MIN_AVG_LOGPROB:
        reasons.append("modelo inseguro no trecho")
    if signals.compression_ratio > config.LOW_CONF_MAX_COMPRESSION_RATIO:
        reasons.append("texto repetitivo demais")
    if signals.min_word_probability < config.LOW_CONF_MIN_WORD_PROBABILITY:
        reasons.append("palavra com baixa probabilidade")
    return bool(reasons), "; ".join(reasons)


def has_repetition(words: list[str]) -> bool:
    """Detecta o mesmo trecho repetido várias vezes seguidas, um erro conhecido do Whisper."""
    tokens = normalize_text(" ".join(words)).split()
    for size in range(1, config.REPETITION_MAX_NGRAM + 1):
        needed = size * config.REPETITION_MIN_REPEATS
        for start in range(len(tokens) - needed + 1):
            window = tokens[start : start + needed]
            # Ex.: size 2 e 3 repetições -> a janela é igual aos 2 primeiros tokens copiados 3 vezes.
            if window == window[:size] * config.REPETITION_MIN_REPEATS:
                return True
    return False


def flag_cues(cues: list[Cue], transcription: Transcription) -> list[Cue]:
    """Marca cada bloco como duvidoso ou não, com o pior sinal dos trechos e das palavras que ele contém."""
    flagged = []
    for cue in cues:
        segments = [s for s in transcription.segments if s.start < cue.end and s.end > cue.start]
        # Uma palavra pertence ao bloco se o meio dela cai dentro do tempo do bloco.
        words = [w for s in segments for w in s.words if cue.start <= (w.start + w.end) / 2 <= cue.end]
        if not words:
            flagged.append(cue)
            continue
        signals = Signals(
            avg_logprob=min(s.avg_logprob for s in segments),
            no_speech_prob=max(s.no_speech_prob for s in segments),
            compression_ratio=max(s.compression_ratio for s in segments),
            min_word_probability=min(w.probability for w in words),
        )
        low, reason = is_low_confidence(signals)
        reasons = [reason] if low else []
        if has_repetition([w.text for w in words]):
            reasons.append(REPETITION_REASON)
        flagged.append(replace(cue, low_confidence=bool(reasons), reason="; ".join(reasons)))
    return flagged
