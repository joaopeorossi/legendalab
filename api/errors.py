"""Erros da API: todo erro sai no mesmo formato {error_code, message, request_id}, com mensagem clara em português."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("legendalab")

# O núcleo (core/media.py) não conhece HTTP: a tradução do código de erro para o status fica aqui.
MEDIA_ERROR_STATUS = {"UNSUPPORTED_MEDIA": 415, "DURATION_EXCEEDED": 422, "NO_AUDIO_TRACK": 422}
FILE_TOO_LARGE_MESSAGE = "O arquivo passa do limite de {mb} MB. Envie um vídeo menor."


class ApiError(Exception):
    """Erro com status HTTP, código e mensagem em português, devolvido no formato padrão."""

    def __init__(self, status: int, code: str, message: str) -> None:
        """Guarda o status HTTP (por exemplo, 413), o código (FILE_TOO_LARGE) e a mensagem."""
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def error_response(request: Request, status: int, code: str, message: str) -> JSONResponse:
    """Monta a resposta de erro no formato único, com o request_id para achar a requisição no log."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(status_code=status, content={"error_code": code, "message": message, "request_id": request_id})


async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    """Transforma um ApiError na resposta padrão."""
    return error_response(request, exc.status, exc.code, exc.message)


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Campo errado no formulário vira 400 INVALID_REQUEST, no nosso formato (o FastAPI usaria 422)."""
    return error_response(request, 400, "INVALID_REQUEST", "Requisição inválida: envie o vídeo no campo 'file'.")


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Falha inesperada vira 500; o detalhe técnico vai só para o log, nunca para a pessoa."""
    logger.exception("Erro inesperado (request_id=%s)", getattr(request.state, "request_id", None))
    return error_response(request, 500, "INTERNAL_ERROR", "Algo deu errado do nosso lado. Tente de novo em instantes.")


def register_error_handlers(app: FastAPI) -> None:
    """Liga cada tipo de erro ao seu tratador."""
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
