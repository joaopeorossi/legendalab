"""Transcritor de mentira, determinístico, para testar o resto do código sem a IA."""

from pathlib import Path

from core.transcribers.base import Segment, Transcriber, Transcription, Word


class FakeTranscriber(Transcriber):
    """Devolve sempre as mesmas palavras, sem abrir o áudio: rápido e sempre igual."""

    name = "fake"

    def __init__(self, words: list[Word]) -> None:
        """Guarda as palavras que serão devolvidas em toda transcrição."""
        self._words = list(words)

    def transcribe(self, audio_path: Path) -> Transcription:
        """Monta um único trecho com as palavras guardadas e sinais de confiança fixos."""
        start = self._words[0].start if self._words else 0.0
        end = self._words[-1].end if self._words else 0.0
        segment = Segment(
            text=" ".join(w.text for w in self._words),
            start=start,
            end=end,
            words=self._words,
            avg_logprob=0.0,
            no_speech_prob=0.0,
            compression_ratio=1.0,
        )
        return Transcription(segments=[segment], audio_duration_s=end, processing_time_s=0.0)
