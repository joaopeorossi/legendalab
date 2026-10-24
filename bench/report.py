"""Relatórios do benchmark: a tabela em Markdown para o README e o errors.md ("Onde o modelo erra").

Uso: python -m bench.report results/<data_hora>
"""

import argparse
import csv
import json
from pathlib import Path

from core import config
from core.metrics import choose_default_model


def make_results_table(run_dir: Path) -> str:
    """Monta, a partir do summary.csv, a tabela em Markdown com a escolha da RN6, pronta para o README."""
    with (run_dir / "summary.csv").open(encoding="utf-8", newline="") as f:
        summaries = list(csv.DictReader(f))
    with (run_dir / "run.json").open(encoding="utf-8") as f:
        run_info = json.load(f)

    lines = ["| Modelo | WER (corpus) | RTF | Frases |", "|---|---|---|---|"]
    for s in summaries:
        wer_text = f"{float(s['corpus_wer']):.1%}".replace(".", ",")
        rtf_text = f"{float(s['rtf']):.2f}".replace(".", ",")
        lines.append(f"| {s['model']} | {wer_text} | {rtf_text} | {s['n_samples']} |")

    limit_text = f"{config.RTF_LIMIT}".replace(".", ",")
    chosen = choose_default_model(summaries, config.RTF_LIMIT)
    if chosen:
        lines.append(f"\n**Modelo padrão da demo (RN6: menor WER entre os modelos com RTF até {limit_text}):** {chosen}")
    else:
        lines.append(f"\n**RN6:** nenhum modelo teve RTF até {limit_text}; nenhum modelo padrão escolhido.")
    lines.append(
        f"\nMedido em {run_info['date'][:10]}: {run_info['n_samples']} frases do {run_info['dataset']['name']}, "
        f"seed {run_info['seed']}, {run_info['settings']['cpu_threads']} threads de CPU, normalização "
        f"{run_info['normalization_version']}."
    )
    return "\n".join(lines)


def make_errors_report(run_dir: Path) -> Path:
    """Grava o errors.md com as frases de mais erros do modelo escolhido, referência ao lado da transcrição."""
    with (run_dir / "summary.csv").open(encoding="utf-8", newline="") as f:
        summaries = list(csv.DictReader(f))
    with (run_dir / "samples.csv").open(encoding="utf-8", newline="") as f:
        samples = list(csv.DictReader(f))

    chosen = choose_default_model(summaries, config.RTF_LIMIT)
    note = ""
    if chosen is None:
        chosen = min(summaries, key=lambda s: float(s["corpus_wer"]))["model"]
        note = "> Nenhum modelo passou no limite de velocidade da RN6; abaixo está o de menor WER.\n\n"

    rows = [r for r in samples if r["model"] == chosen]
    # Mais erros (S + D + I) primeiro; no empate, maior WER.
    worst = sorted(
        rows,
        key=lambda r: (int(r["substitutions"]) + int(r["deletions"]) + int(r["insertions"]), float(r["wer"])),
        reverse=True,
    )[: config.ERRORS_REPORT_SIZE]

    lines = [
        f"# Onde o modelo erra: {chosen}",
        "",
        f"{note}As {len(worst)} frases com mais erros de palavra, entre {len(rows)} frases medidas. "
        "S = palavra trocada, D = palavra que faltou, I = palavra que sobrou.",
        "",
        "| # | Frase correta | Transcrição | S/D/I | WER |",
        "|---|---|---|---|---|",
    ]
    for i, r in enumerate(worst, start=1):
        reference = r["reference"].replace("|", "\\|")  # "|" quebraria a tabela em Markdown
        hypothesis = r["hypothesis"].replace("|", "\\|")
        sdi = f"{r['substitutions']}/{r['deletions']}/{r['insertions']}"
        lines.append(f"| {i} | {reference} | {hypothesis} | {sdi} | {float(r['wer']):.0%} |")

    path = run_dir / "errors.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    """Imprime a tabela de resultados com a RN6 e grava o errors.md da execução indicada."""
    parser = argparse.ArgumentParser(description="Gera a tabela de resultados e o errors.md de uma execução.")
    parser.add_argument("run_dir", type=Path, help="pasta da execução, por exemplo results/2026-10-24_101500")
    args = parser.parse_args()
    print(make_results_table(args.run_dir))
    print(f"\nRelatório de erros gravado em {make_errors_report(args.run_dir)}")


if __name__ == "__main__":
    main()
