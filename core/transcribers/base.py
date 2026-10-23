"""Tipos de dados da transcrição e o contrato que todo transcritor segue."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Word:
    """Uma palavra reconhecida, com o tempo (em segundos) e a segurança do modelo."""

    text: str
    start: float
    end: float
    probability: float


@dataclass(frozen=True)
class Segment:
    """Um trecho de fala com suas palavras e os sinais de confiança do modelo."""

    text: str
    start: float
    end: float
    words: list[Word]
    avg_logprob: float
    no_speech_prob: float
    compression_ratio: float


@dataclass(frozen=True)
class Transcription:
    """Resultado completo: trechos, duração do áudio e tempo gasto para transcrever."""

    segments: list[Segment]
    audio_duration_s: float
    processing_time_s: float


class Transcriber(ABC):
    """Contrato de todo transcritor: o resto do sistema só conhece esta interface."""

    name: str

    @abstractmethod
    def transcribe(self, audio_path: Path) -> Transcription:
        """Transcreve o áudio do caminho dado e devolve uma Transcription."""
