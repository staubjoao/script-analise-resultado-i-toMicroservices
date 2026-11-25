"""RQ3 — análise da coorte da primeira interação.

Desfechos por run (média das intenções da 1ª interação):
- A: parcial em +25 (absorção);
- C: parcial em +100 (consolidação; primário);
- N: parcial em g2-1 (antes do segundo prompt; robustez).
Estrita em +100 como secundária.

Configuração entra como exploratória: fatores marginais (algoritmo, elitismo)
com n~20 por nível; ranking por configuração apenas descritivo (n=5).

Uso: `.venv/bin/python analise_estudo/analise_rq3_primeira_interacao.py`
"""

from __future__ import annotations

import itertools
import os

import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados_rq3", "primeira_interacao")
FIG = os.path.join(ROOT, "figuras")
ALGORITHM = {f"config_{k}": ("R-NSGA-III" if k in (3, 4, 7, 8) else "NSGA-III") for k in range(1, 9)}
ELITISM = {f"config_{k}": ("on" if k in (1, 3, 5, 7) else "off") for k in range(1, 9)}
OUTCOMES = ("A", "C", "N")
COLORS = {"NSGA-III": "#4C72B0", "R-NSGA-III": "#DD8452"}


def a12(a, b) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    diff = a[:, None] - b[None, :]
    return (np.sum(diff > 0) + 0.5 * np.sum(diff == 0)) / (len(a) * len(b))


def bh(pvalues) -> np.ndarray:
    pvalues = np.asarray(pvalues, float)
    order = np.argsort(pvalues)
    m = len(pvalues)
    ranked = pvalues[order] * m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty_like(pvalues)
    out[order] = np.clip(ranked, 0, 1)
    return out


def magnitude(value: float) -> str:
    if pd.isna(value):
        return ""
    delta = abs(value - 0.5)
    if delta <= 0.06:
        return "Desprezível"
    if delta <= 0.14:
        return "Pequena"
    if delta <= 0.21:
        return "Média"
    return "Grande"


def run_table(intents: pd.DataFrame) -> pd.DataFrame:
    intents = intents.copy()
    intents["run"] = intents[["persona_dir", "config", "sistema", "participant", "rep"]].astype(str).agg("|".join, axis=1)
    runs = intents.groupby("run").agg(
        n_int=("type", "size"),
        cocl=("type", lambda s: (s == "CO_LOCATE").mean()),
        A=("partial_A", "mean"),
        C=("partial_C", "mean"),
        N=("partial_N", "mean"),
        S_C=("strict_C", "mean"),
    ).reset_index()
    meta = intents.drop_duplicates("run").set_index("run")[
        ["persona_dir", "persona", "sistema", "config", "participant", "rep"]
    ]
    runs = runs.set_index("run").join(meta).reset_index()
    runs["algoritmo"] = runs.config.map(ALGORITHM)
    runs["elitismo"] = runs.config.map(ELITISM)
    return runs


def descriptives(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (persona, system), group in runs.groupby(["persona", "sistema"]):
        row = {
            "persona": persona, "sistema": system, "runs": len(group),
            "intencoes_mediana": group.n_int.median(),
        }
        for outcome in OUTCOMES:
            row[f"{outcome}_mediana"] = group[outcome].median()
            row[f"{outcome}_media"] = group[outcome].mean()
            row[f"{outcome}_q1"] = group[outcome].quantile(0.25)
            row[f"{outcome}_q3"] = group[outcome].quantile(0.75)
        row["S_C_mediana"] = group.S_C.median()
        rows.append(row)
    return pd.DataFrame(rows)


def factor_table(runs: pd.DataFrame, factor: str) -> pd.DataFrame:
    rows = []
    for outcome in OUTCOMES:
        for (persona, system), group in runs.groupby(["persona", "sistema"]):
            levels = sorted(group[factor].unique())
            if len(levels) != 2:
                continue
            x = group[group[factor] == levels[0]][outcome].dropna()
            y = group[group[factor] == levels[1]][outcome].dropna()
            if len(x) < 2 or len(y) < 2:
                continue
            rows.append({
                "desfecho": outcome, "persona": persona, "sistema": system,
                "nivel_a": levels[0], "nivel_b": levels[1],
                "n_a": len(x), "n_b": len(y),
                "mediana_a": x.median(), "mediana_b": y.median(),
                "delta": y.median() - x.median(),
                "A12": a12(x, y),
                "p": mannwhitneyu(x, y, alternative="two-sided").pvalue,
                "melhor": levels[1] if y.median() > x.median() else levels[0] if x.median() > y.median() else "empate",
            })
    out = pd.DataFrame(rows)
    for outcome in OUTCOMES:
        idx = out.index[out.desfecho == outcome]
        if len(idx):
            out.loc[idx, "p_adj"] = bh(out.loc[idx, "p"].values)
    out["magnitude"] = out["A12"].map(magnitude)
    return out


def plot(runs: pd.DataFrame, factors: pd.DataFrame) -> None:
    os.makedirs(FIG, exist_ok=True)
    fig, axes = plt.subplots(3, 2, figsize=(8.6, 8.6), sharey=True)
    rng = np.random.default_rng(42)
    for row, persona in enumerate(("P1", "P2", "P3")):
        for column, system in enumerate(("spring-petclinic", "jpetstore")):
            ax = axes[row, column]
            cell = runs[(runs.sistema == system) & (runs.persona == persona)]
            data = [cell[cell.algoritmo == algorithm].C.dropna().values
                    for algorithm in ("NSGA-III", "R-NSGA-III")]
            boxes = ax.boxplot(data, patch_artist=True, widths=0.55, showfliers=False,
                               medianprops={"color": "#222", "linewidth": 1.1})
            for patch, algorithm in zip(boxes["boxes"], ("NSGA-III", "R-NSGA-III")):
                patch.set_facecolor(COLORS[algorithm])
                patch.set_alpha(0.65)
                patch.set_edgecolor("#333")
            for position, values in zip((1, 2), data):
                ax.scatter(rng.normal(position, 0.05, len(values)), values,
                           s=12, color="#222", alpha=0.45, linewidths=0)
            line = factors[(factors.persona == persona) & (factors.sistema == system)
                           & (factors.desfecho == "C")].iloc[0]
            ax.set_xticks((1, 2))
            ax.set_xticklabels(("NSGA-III", "R-NSGA-III"), fontsize=8)
            ax.set_title(f"{persona} · {'Spring PetClinic' if system == 'spring-petclinic' else 'JPetStore'}",
                         fontsize=10)
            ax.text(0.5, 0.04, f"$\\hat{{A}}_{{12}}$ = {line.A12:.2f}; $p_{{adj}}$ = {line.p_adj:.3f}",
                    transform=ax.transAxes, ha="center", fontsize=8)
            ax.set_ylim(0, 1)
            ax.grid(axis="y", alpha=0.25)
    fig.supylabel("Consolidação a +100 gerações (média do run)", fontsize=9)
    fig.tight_layout(rect=(0.03, 0, 1, 1))
    fig.savefig(os.path.join(FIG, "rq3_primeira_interacao.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_lines(runs: pd.DataFrame, factors: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(8.6, 8.2), sharey=True, sharex=True)
    for row, persona in enumerate(("P1", "P2", "P3")):
        for column, system in enumerate(("spring-petclinic", "jpetstore")):
            ax = axes[row, column]
            for algorithm in ("NSGA-III", "R-NSGA-III"):
                cell = runs[(runs.sistema == system) & (runs.persona == persona) & (runs.algoritmo == algorithm)]
                medians = [cell[outcome].median() for outcome in OUTCOMES]
                ax.plot((1, 2, 3), medians, marker="o", color=COLORS[algorithm],
                        label=algorithm, linewidth=1.5, markersize=5)
            line = factors[(factors.persona == persona) & (factors.sistema == system)
                           & (factors.desfecho == "N")].iloc[0]
            ax.set_xticks((1, 2, 3))
            ax.set_xticklabels(("+25", "+100", "próxima\ninteração"), fontsize=8)
            ax.set_title(f"{persona} · {'Spring PetClinic' if system == 'spring-petclinic' else 'JPetStore'}",
                         fontsize=10)
            ax.text(0.5, 0.04, f"$p_{{adj}}$ (2ª interação) = {line.p_adj:.3f}",
                    transform=ax.transAxes, ha="center", fontsize=8)
            ax.set_ylim(0.5, 1.0)
            ax.grid(axis="y", alpha=0.25)
    fig.supylabel("Satisfação parcial (mediana do run)", fontsize=9)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0.03, 0.05, 1, 1))
    fig.savefig(os.path.join(FIG, "rq3_primeira_interacao_linhas.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    intents = pd.read_csv(os.path.join(ROOT, "intents.csv"), dtype={"participant": str})
    runs = run_table(intents)
    runs.to_csv(os.path.join(ROOT, "runs.csv"), index=False)

    desc = descriptives(runs)
    desc.to_csv(os.path.join(ROOT, "descritivas.csv"), index=False)

    by_algorithm = factor_table(runs, "algoritmo")
    by_algorithm.to_csv(os.path.join(ROOT, "fatores_algoritmo.csv"), index=False)

    by_elitism = factor_table(runs, "elitismo")
    by_elitism.to_csv(os.path.join(ROOT, "fatores_elitismo.csv"), index=False)

    configs = runs.groupby(["persona", "sistema", "config"]).agg(
        runs=("C", "size"), A=("A", "median"), C=("C", "median"), N=("N", "median")
    ).reset_index()
    configs.to_csv(os.path.join(ROOT, "configs.csv"), index=False)

    two_by_two = runs.groupby(["algoritmo", "elitismo"]).agg(
        runs=("C", "size"), A=("A", "median"), C=("C", "median"), N=("N", "median")
    ).reset_index()
    two_by_two.to_csv(os.path.join(ROOT, "2x2.csv"), index=False)

    plot(runs, by_algorithm)
    plot_lines(runs, by_algorithm)

    print(f"intenções: {len(intents)} | runs: {len(runs)}")
    print("\n== descritivas ==")
    print(desc.round(3).to_string(index=False))
    print("\n== algoritmo ==")
    print(by_algorithm.round(3).to_string(index=False))
    print("\n== elitismo ==")
    print(by_elitism.round(3).to_string(index=False))
    print("\n== 2x2 ==")
    print(two_by_two.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
