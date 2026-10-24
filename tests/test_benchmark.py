"""Testes do benchmark: sorteio reprodutível, leitura do TSV, RN6 e arquivos gravados sem dados proibidos."""

from dataclasses import fields
from pathlib import Path

import pytest

from bench.run_benchmark import Sample, load_samples, run_model, summarize, write_results
from core.metrics import choose_default_model
from core.transcribers.base import Word
from core.transcribers.fake import FakeTranscriber

FORBIDDEN_COLUMNS = {"client_id", "age", "gender", "accents"}


@pytest.fixture
def tsv_path(tmp_path: Path) -> Path:
    """Cria um TSV pequeno no formato do Common Voice, com as colunas proibidas e uma frase com aspas."""
    lines = ["client_id\tpath\tsentence\tage\tgender\taccents"]
    lines += [f"pessoa{i}\tclip_{i}.mp3\tfrase número {i}\tthirties\tfemale\tsul" for i in range(10)]
    lines.append('pessoa10\tclip_10.mp3\t"Ele disse ""oi"" e saiu"\tteens\tmale\tnordeste')
    path = tmp_path / "test.tsv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_same_seed_gives_same_samples(tsv_path: Path) -> None:
    """Mesma seed sorteia exatamente as mesmas frases, na mesma ordem (RN10)."""
    first = load_samples(tsv_path, n=5, seed=42)
    second = load_samples(tsv_path, n=5, seed=42)
    assert len(first) == 5
    assert first == second


def test_n_at_least_total_uses_all(tsv_path: Path) -> None:
    """Com n igual ou maior que o total (11 frases), usa todas, sem sortear."""
    assert len(load_samples(tsv_path, n=11, seed=42)) == 11
    assert len(load_samples(tsv_path, n=100, seed=42)) == 11


def test_quoted_sentence_is_read_correctly(tsv_path: Path) -> None:
    """Aspas duplicadas no formato CSV viram aspas normais na frase."""
    last = load_samples(tsv_path, n=100, seed=42)[-1]
    assert last.sentence == 'Ele disse "oi" e saiu'
    assert last.audio_path.name == "clip_10.mp3"


def test_sample_keeps_only_audio_and_sentence() -> None:
    """A frase carregada só guarda o áudio e o texto, nada sobre quem falou."""
    assert [f.name for f in fields(Sample)] == ["audio_path", "sentence"]


def test_rn6_both_fast_picks_lowest_wer() -> None:
    """RN6: se os dois modelos são rápidos o bastante, ganha o de menor WER."""
    summaries = [
        {"model": "base", "corpus_wer": 0.30, "rtf": 0.2},
        {"model": "small", "corpus_wer": 0.20, "rtf": 0.4},
    ]
    assert choose_default_model(summaries, rtf_limit=0.5) == "small"


def test_rn6_more_accurate_but_too_slow_is_excluded() -> None:
    """RN6: o modelo mais preciso fica de fora se passar do limite de velocidade."""
    summaries = [
        {"model": "base", "corpus_wer": 0.30, "rtf": 0.2},
        {"model": "small", "corpus_wer": 0.20, "rtf": 0.51},
    ]
    assert choose_default_model(summaries, rtf_limit=0.5) == "base"


def test_rn6_rtf_equal_to_limit_passes() -> None:
    """RN6: RTF exatamente igual ao limite ainda passa (a regra é "menor ou igual")."""
    summaries = [
        {"model": "base", "corpus_wer": 0.30, "rtf": 0.2},
        {"model": "small", "corpus_wer": 0.20, "rtf": 0.5},
    ]
    assert choose_default_model(summaries, rtf_limit=0.5) == "small"


def test_rn6_none_fast_enough_returns_none() -> None:
    """RN6: se nenhum modelo passa no limite, não há modelo padrão."""
    summaries = [
        {"model": "base", "corpus_wer": 0.30, "rtf": 0.7},
        {"model": "small", "corpus_wer": 0.20, "rtf": 1.2},
    ]
    assert choose_default_model(summaries, rtf_limit=0.5) is None


def test_rn6_accepts_values_read_from_csv() -> None:
    """RN6 funciona com os números em texto, como vêm do summary.csv."""
    summaries = [
        {"model": "base", "corpus_wer": "0.30", "rtf": "0.2"},
        {"model": "small", "corpus_wer": "0.20", "rtf": "0.4"},
    ]
    assert choose_default_model(summaries, rtf_limit=0.5) == "small"


def test_results_have_no_forbidden_columns_and_no_audio(tsv_path: Path, tmp_path: Path) -> None:
    """Os arquivos gravados não têm colunas proibidas e a pasta só tem JSON e CSV, nunca áudio."""
    fake = FakeTranscriber([Word("frase", 0.0, 0.5, 0.9), Word("número", 0.5, 1.0, 0.8)])
    results = run_model(fake, load_samples(tsv_path, n=100, seed=42))
    run_dir = tmp_path / "run"
    write_results(run_dir, {"seed": 42}, results, summarize(results))

    for file_name in ("samples.csv", "summary.csv"):
        header = (run_dir / file_name).read_text(encoding="utf-8").splitlines()[0].split(",")
        assert not FORBIDDEN_COLUMNS & set(header)
    assert {p.suffix for p in run_dir.iterdir()} == {".json", ".csv"}


def test_summarize_uses_corpus_wer(tsv_path: Path) -> None:
    """O resumo soma os erros e as palavras de todas as frases antes de dividir (RN9)."""
    fake = FakeTranscriber([Word("frase", 0.0, 0.5, 0.9), Word("número", 0.5, 1.0, 0.8)])
    summary = summarize(run_model(fake, load_samples(tsv_path, n=100, seed=42)))[0]
    # 10 frases "frase número i": 1 deleção em 3 palavras cada.
    # 'Ele disse "oi" e saiu': 2 substituições + 3 deleções em 5 palavras.
    assert summary["n_samples"] == 11
    assert summary["corpus_wer"] == round(15 / 35, 4)
