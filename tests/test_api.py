"""Testes da API com TestClient e FakeTranscriber: cada erro da tabela, o caminho feliz e a limpeza dos arquivos."""

import csv
import io
import json
import logging
import tempfile
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

import api.main as main
from api.errors import ApiError
from api.uploads import save_upload_limited
from core import config
from core.metrics import choose_default_model
from core.transcribers.base import Word
from core.transcribers.fake import FakeTranscriber

WORDS = [Word("bom", 0.0, 0.4, 0.9), Word("dia", 0.4, 0.9, 0.9), Word("pessoal", 0.9, 1.6, 0.2)]
ODD_NAME = "; rm -rf ~ vídeo da Ana.mp4"  # nome original estranho: nunca pode ser usado nem ir para o log


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente de teste com o FakeTranscriber no lugar do modelo (sem lifespan, então o Whisper não carrega)."""
    main.app.state.transcriber = FakeTranscriber(WORDS)
    yield TestClient(main.app)
    main.app.state.transcriber = None


def post_file(client: TestClient, path: Path) -> httpx.Response:
    """Envia o arquivo como a página envia: FormData com o campo 'file'."""
    with path.open("rb") as f:
        return client.post("/api/captions", files={"file": (ODD_NAME, f, "video/mp4")})


def assert_error(response: httpx.Response, status: int, code: str) -> None:
    """Confere o status e o formato único de erro {error_code, message, request_id}."""
    assert response.status_code == status
    body = response.json()
    assert body["error_code"] == code
    assert body["message"]
    assert body["request_id"]


def test_happy_path(client: TestClient, media_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Vídeo válido: 200 com blocos, VTT, aviso da RN12 e o bloco duvidoso; o log não tem texto nem nome."""
    caplog.set_level(logging.INFO, logger="legendalab")
    response = post_file(client, media_dir / "tone.wav")
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "fake"
    assert body["vtt"].startswith("WEBVTT")
    assert body["notice"] == "Legenda automática: trechos destacados podem estar errados."
    assert body["low_confidence_cues"] == [1]
    assert body["warning"] is None
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["request_id"] in caplog.text
    assert "pessoal" not in caplog.text and "rm -rf" not in caplog.text


def test_no_file_is_400(client: TestClient) -> None:
    """Nenhum arquivo enviado: 400 INVALID_REQUEST."""
    assert_error(client.post("/api/captions"), 400, "INVALID_REQUEST")


def test_wrong_field_is_400(client: TestClient, media_dir: Path) -> None:
    """Arquivo no campo errado conta como nenhum arquivo: 400."""
    with (media_dir / "tone.wav").open("rb") as f:
        assert_error(client.post("/api/captions", files={"video": ("a.wav", f)}), 400, "INVALID_REQUEST")


def test_too_large_is_rejected_by_content_length(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Com limite de 1 MB, um envio de 3 MB é recusado pelo tamanho declarado, antes de ler o corpo (413)."""
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 1)
    response = client.post("/api/captions", files={"file": ("grande.mp4", b"x" * 3 * 1024 * 1024)})
    assert_error(response, 413, "FILE_TOO_LARGE")


def test_save_upload_stops_at_the_limit(tmp_path: Path) -> None:
    """Sem tamanho declarado, a cópia em pedaços para assim que passa do limite (413)."""
    upload = UploadFile(file=io.BytesIO(b"x" * 3000), filename="a.mp4")
    with pytest.raises(ApiError) as error:
        save_upload_limited(upload, tmp_path, max_bytes=1000)
    assert error.value.status == 413


def test_saved_file_never_uses_the_original_name(tmp_path: Path) -> None:
    """O arquivo salvo tem nome aleatório (UUID), nunca o nome enviado."""
    path = save_upload_limited(UploadFile(file=io.BytesIO(b"abc"), filename=ODD_NAME), tmp_path, max_bytes=1000)
    assert path.name != ODD_NAME and len(path.name) == 32


def test_empty_file_is_400(client: TestClient, tmp_path: Path) -> None:
    """Arquivo vazio: 400."""
    empty = tmp_path / "vazio.mp4"
    empty.write_bytes(b"")
    assert_error(post_file(client, empty), 400, "INVALID_REQUEST")


@pytest.mark.parametrize("name", ["corrupt.mp4", "text.mp4"])
def test_unsupported_or_corrupt_is_415(client: TestClient, media_dir: Path, name: str) -> None:
    """Arquivo corrompido ou que não é mídia: 415 UNSUPPORTED_MEDIA."""
    assert_error(post_file(client, media_dir / name), 415, "UNSUPPORTED_MEDIA")


def test_too_long_is_422(client: TestClient, media_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Com o limite em 1 s, o som de 2 s passa da duração máxima: 422 DURATION_EXCEEDED."""
    monkeypatch.setattr(config, "MAX_DURATION_S", 1.0)
    assert_error(post_file(client, media_dir / "tone.wav"), 422, "DURATION_EXCEEDED")


def test_no_audio_track_is_422(client: TestClient, media_dir: Path) -> None:
    """Vídeo sem trilha de áudio: 422 NO_AUDIO_TRACK."""
    assert_error(post_file(client, media_dir / "no_audio.mp4"), 422, "NO_AUDIO_TRACK")


def test_no_speech_is_200_with_warning(client: TestClient, media_dir: Path) -> None:
    """Sem fala detectada não é erro do usuário: 200, sem blocos, com o aviso NO_SPEECH_DETECTED."""
    main.app.state.transcriber = FakeTranscriber([])
    response = post_file(client, media_dir / "tone.wav")
    assert response.status_code == 200
    assert response.json()["cues"] == []
    assert response.json()["warning"]["code"] == "NO_SPEECH_DETECTED"


def test_model_unavailable_is_503(client: TestClient, media_dir: Path) -> None:
    """Modelo não carregado: 503 MODEL_UNAVAILABLE, no upload e no /health."""
    main.app.state.transcriber = None
    assert_error(post_file(client, media_dir / "tone.wav"), 503, "MODEL_UNAVAILABLE")
    assert_error(client.get("/health"), 503, "MODEL_UNAVAILABLE")


def test_temporary_files_are_deleted_even_on_error(
    client: TestClient, media_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pasta temporária some depois de um sucesso e depois de um erro (RN11)."""
    created: list[Path] = []
    real_mkdtemp = tempfile.mkdtemp

    def spy_mkdtemp(*args: str, **kwargs: str) -> str:
        """Cria a pasta temporária de verdade e anota o caminho para conferir depois."""
        folder = real_mkdtemp(*args, **kwargs)
        created.append(Path(folder))
        return folder

    monkeypatch.setattr(main.tempfile, "mkdtemp", spy_mkdtemp)
    assert post_file(client, media_dir / "tone.wav").status_code == 200
    assert post_file(client, media_dir / "corrupt.mp4").status_code == 415
    assert len(created) == 2
    assert not any(folder.exists() for folder in created)


def test_health(client: TestClient) -> None:
    """Servidor vivo e modelo carregado."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model": "fake"}


def test_benchmark_reads_latest_results(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """O /api/benchmark lê a execução mais recente e aplica a RN6 na hora, com o limite que estiver no config."""
    run_dir = tmp_path / "2026-01-01_120000"
    run_dir.mkdir()
    run_info = {"date": "2026-01-01T12:00:00", "dataset": {"name": "teste"}, "seed": 42, "n_samples": 3,
                "settings": {"cpu_threads": 2}}
    (run_dir / "run.json").write_text(json.dumps(run_info), encoding="utf-8")
    (run_dir / "summary.csv").write_text(
        "model,n_samples,corpus_wer,rtf\nwhisper-base,3,0.3,0.2\nwhisper-small,3,0.2,0.9\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(config, "RTF_LIMIT", 0.5)  # o teste fixa o próprio limite: não depende do valor do config
    body = client.get("/api/benchmark").json()
    assert body["rtf_limit"] == 0.5
    assert body["default_model"] == "whisper-base"  # com 0,5, o small (RTF 0,9) fica de fora
    assert [m["model"] for m in body["models"]] == ["whisper-base", "whisper-small"]


def test_benchmark_without_results_is_404(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem nenhum resultado, o /api/benchmark responde 404 no formato padrão."""
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    assert_error(client.get("/api/benchmark"), 404, "BENCHMARK_NOT_FOUND")


def test_index_page(client: TestClient) -> None:
    """A raiz entrega a página com o aviso fixo da RN12."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Legenda automática: trechos destacados podem estar errados." in response.text


def test_default_model_matches_rn6() -> None:
    """O modelo carregado pela demo é o que a RN6 escolhe no último benchmark de results/."""
    run_dir = main._latest_run_dir()
    if run_dir is None:
        pytest.skip("ainda não há resultados em results/")
    with (run_dir / "summary.csv").open(encoding="utf-8", newline="") as f:
        chosen = choose_default_model(list(csv.DictReader(f)), config.RTF_LIMIT)
    assert chosen == f"whisper-{config.DEFAULT_MODEL}"
