"""Upload: grava o arquivo enviado com nome aleatório e para no meio se passar do limite (RN2)."""

import uuid
from pathlib import Path

from fastapi import UploadFile

from api.errors import FILE_TOO_LARGE_MESSAGE, ApiError

CHUNK_BYTES = 1024 * 1024  # lê 1 MB por vez: o arquivo nunca fica inteiro na memória


def save_upload_limited(upload: UploadFile, folder: Path, max_bytes: int) -> Path:
    """Grava o upload em pedaços com nome UUID (nunca o original); se passar de max_bytes, para e devolve 413."""
    path = folder / uuid.uuid4().hex  # sem extensão: o tipo é decidido pelo conteúdo (RN3)
    written = 0
    with path.open("wb") as out:
        while chunk := upload.file.read(CHUNK_BYTES):
            written += len(chunk)
            if written > max_bytes:
                raise ApiError(413, "FILE_TOO_LARGE", FILE_TOO_LARGE_MESSAGE.format(mb=max_bytes // (1024 * 1024)))
            out.write(chunk)
    if written == 0:
        raise ApiError(400, "INVALID_REQUEST", "O arquivo enviado está vazio.")
    return path
