"""Transcritor real: Whisper rodando localmente na CPU via faster-whisper."""

import time
from pathlib import Path

from faster_whisper import WhisperModel

from core import config
from core.transcribers.base import Segment, Transcriber, Transcription, Word


class WhisperTranscriber(Transcriber):
    """Transcreve com um tamanho do Whisper, carregando o modelo uma única vez."""

    def __init__(self, size: str) -> None:
        """Carrega o modelo agora (parte lenta), para não repetir a cada áudio."""
        self.name = f"whisper-{size}"
        self._model = WhisperModel(size, device=config.DEVICE, compute_type=config.COMPUTE_TYPE)

    def transcribe(self, audio_path: Path) -> Transcription:
        """Transcreve em português, com tempo por palavra e filtro de silêncio, medindo o tempo."""
        start = time.perf_counter()
        raw_segments, info = self._model.transcribe(
            str(audio_path),
            language=config.LANGUAGE,
            word_timestamps=True,
            vad_filter=True,  # pula trechos sem fala antes de transcrever
        )
        # O faster-whisper devolve um gerador: a transcrição só acontece ao percorrê-lo,
        # por isso a conversão precisa ficar dentro da medição de tempo.
        segments = [
            Segment(
                text=raw.text.strip(),
                start=raw.start,
                end=raw.end,
                words=[Word(w.word.strip(), w.start, w.end, w.probability) for w in raw.words or []],
                avg_logprob=raw.avg_logprob,
                no_speech_prob=raw.no_speech_prob,
                compression_ratio=raw.compression_ratio,
            )
            for raw in raw_segments
        ]
        elapsed = time.perf_counter() - start
        return Transcription(segments=segments, audio_duration_s=info.duration, processing_time_s=elapsed)
