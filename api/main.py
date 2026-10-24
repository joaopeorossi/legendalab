"""Servidor da demo: valida o vídeo, chama o núcleo (make_captions) e responde. Nenhuma regra de negócio mora aqui.

Rodar: .venv\\Scripts\\python -m uvicorn api.main:app --reload
"""

import csv
import json
import logging
import math
import shutil
import tempfile
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Request, Response, UploadFile
from fastapi.responses import FileResponse

from api.errors import FILE_TOO_LARGE_MESSAGE, MEDIA_ERROR_STATUS, ApiError, error_response, register_error_handlers
from api.uploads import save_upload_limited
from core import config
from core.media import MediaError, extract_audio, probe, validate_media
from core.metrics import choose_default_model, rtf
from core.pipeline import CaptionResult, make_captions
from core.transcribers.base import Transcriber
from core.transcribers.whisper_local import WhisperTranscriber

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("legendalab")
INDEX_HTML = config.PROJECT_ROOT / "web" / "index.html"
MB = 1024 * 1024
MODEL_UNAVAILABLE = "O modelo de transcrição ainda não está disponível. Tente de novo em instantes."


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Carrega o modelo uma única vez ao iniciar o servidor; se falhar, as rotas respondem 503."""
    try:
        app.state.transcriber = WhisperTranscriber(config.DEFAULT_MODEL)
    except Exception:
        logger.exception("Não foi possível carregar o modelo %s", config.DEFAULT_MODEL)
        app.state.transcriber = None
    yield


app = FastAPI(title="LegendaLab", description="Legendas em português com aviso de baixa confiança.", lifespan=lifespan)
app.state.transcriber = None
register_error_handlers(app)


@app.middleware("http")
async def request_context(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Dá um request_id a cada requisição e recusa uploads grandes demais antes de ler o corpo (RN2)."""
    request.state.request_id = uuid.uuid4().hex
    try:
        declared_bytes = int(request.headers.get("content-length", "0"))
    except ValueError:
        declared_bytes = 0
    if declared_bytes > config.MAX_UPLOAD_MB * MB + config.UPLOAD_FORM_MARGIN_BYTES:
        return error_response(request, 413, "FILE_TOO_LARGE", FILE_TOO_LARGE_MESSAGE.format(mb=config.MAX_UPLOAD_MB))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.get("/health")
def health(request: Request) -> dict[str, str]:
    """Diz se o servidor está vivo e se o modelo carregou."""
    transcriber = request.app.state.transcriber
    if transcriber is None:
        raise ApiError(503, "MODEL_UNAVAILABLE", MODEL_UNAVAILABLE)
    return {"status": "ok", "model": transcriber.name}


def _latest_run_dir() -> Path | None:
    """Acha a execução mais recente em results/ (as pastas têm nome de data e hora, então a maior é a última)."""
    if not config.RESULTS_DIR.is_dir():
        return None
    return max((p for p in config.RESULTS_DIR.iterdir() if (p / "summary.csv").is_file()), default=None)


@app.get("/api/benchmark")
def benchmark() -> dict[str, Any]:
    """Devolve o resumo do último benchmark (os números da tabela do README) e a escolha da RN6."""
    run_dir = _latest_run_dir()
    if run_dir is None:
        raise ApiError(404, "BENCHMARK_NOT_FOUND", "Nenhum resultado de benchmark encontrado.")
    with (run_dir / "run.json").open(encoding="utf-8") as f:
        run_info = json.load(f)
    with (run_dir / "summary.csv").open(encoding="utf-8", newline="") as f:
        models = [
            {"model": r["model"], "n_samples": int(r["n_samples"]), "corpus_wer": float(r["corpus_wer"]), "rtf": float(r["rtf"])}
            for r in csv.DictReader(f)
        ]
    return {
        "date": run_info["date"],
        "dataset": run_info["dataset"],
        "seed": run_info["seed"],
        "n_samples": run_info["n_samples"],
        "cpu_threads": run_info["settings"]["cpu_threads"],
        "models": models,
        "rtf_limit": config.RTF_LIMIT,
        "default_model": choose_default_model(models, config.RTF_LIMIT),
    }


def _json_safe(value: Any) -> Any:
    """Troca números infinitos (CPS de um bloco sem duração) por None, porque JSON não aceita infinito."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _build_response(request_id: str, transcriber: Transcriber, result: CaptionResult) -> dict[str, Any]:
    """Monta o JSON de resposta; se não houve fala, devolve 200 com o aviso NO_SPEECH_DETECTED."""
    speed = rtf(result.processing_time_s, result.audio_duration_s) if result.audio_duration_s > 0 else None
    no_speech = {"code": "NO_SPEECH_DETECTED", "message": "Nenhuma fala foi detectada no vídeo."}
    return _json_safe({
        "request_id": request_id,
        "model": transcriber.name,
        "audio_duration_s": round(result.audio_duration_s, 2),
        "processing_time_s": round(result.processing_time_s, 2),
        "rtf": None if speed is None else round(speed, 3),
        "cues": [asdict(cue) for cue in result.cues],
        "vtt": result.vtt,
        "legibility": {
            "violations": [asdict(issue) for issue in result.legibility["violations"]],
            "warnings": [asdict(issue) for issue in result.legibility["warnings"]],
            "summary": result.legibility["summary"],
        },
        "low_confidence_cues": result.low_confidence_cues,
        "notice": result.notice,
        "warning": None if result.cues else no_speech,
    })


@app.post("/api/captions")
def create_captions(request: Request, file: UploadFile | None = File(None)) -> dict[str, Any]:
    """Endpoint principal: salva → probe → valida → extrai o áudio → make_captions → JSON; apaga tudo no fim (RN11)."""
    request_id = request.state.request_id
    log: dict[str, Any] = {"request_id": request_id, "route": "/api/captions", "status": 200, "error_code": None}
    folder = Path(tempfile.mkdtemp(prefix="legendalab_"))
    try:
        transcriber = request.app.state.transcriber
        if transcriber is None:  # erra cedo: nem salva o arquivo se não há modelo
            raise ApiError(503, "MODEL_UNAVAILABLE", MODEL_UNAVAILABLE)
        if file is None:
            raise ApiError(400, "INVALID_REQUEST", "Nenhum arquivo enviado. Escolha um vídeo e tente de novo.")
        upload_path = save_upload_limited(file, folder, config.MAX_UPLOAD_MB * MB)
        validate_media(probe(upload_path))
        audio_path = folder / "audio.wav"
        extract_audio(upload_path, audio_path)
        result = make_captions(audio_path, transcriber)
        body = _build_response(request_id, transcriber, result)
        summary = result.legibility["summary"]
        log.update(
            model=body["model"], audio_duration_s=body["audio_duration_s"], processing_time_s=body["processing_time_s"],
            rtf=body["rtf"], n_cues=summary["cues"], n_violations=summary["violations"],
            n_warnings=summary["warnings"], n_low_confidence=len(result.low_confidence_cues),
        )
        return body
    except MediaError as exc:
        error = ApiError(MEDIA_ERROR_STATUS[exc.code], exc.code, exc.message)
        log.update(status=error.status, error_code=error.code)
        raise error from exc
    except ApiError as exc:
        log.update(status=exc.status, error_code=exc.code)
        raise
    except Exception:
        log.update(status=500, error_code="INTERNAL_ERROR")
        raise
    finally:
        shutil.rmtree(folder, ignore_errors=True)  # RN11: apaga o upload e o áudio extraído, inclusive em erro
        logger.info(json.dumps(log))  # uma linha por requisição, sem o texto transcrito e sem o nome do arquivo


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Entrega a página da demo."""
    return FileResponse(INDEX_HTML)
