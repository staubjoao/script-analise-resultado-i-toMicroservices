"""Recalcula o IGD+ contra uma fronteira de referência única por sistema.

Decisão metodológica (2026-11-20): o IGD+ usa **uma** referência por sistema —
a união não dominada das fronteiras finais normalizadas de todas as execuções
do sistema (8 configurações x 5 execuções x 3 personas = 120), no espaço
normalizado fixo da instância (``frontiers.json.normalizedFrontier``).

Com isso o IGD+ de cada execução é comparável entre personas e as duas bases
(5 e 15 execuções) reutilizam os mesmos valores, sem recomputar a referência.
Os demais indicadores (HV, ED, spacing) não são alterados por este script.

Uso:
    python analise_estudo/recalcular_igd_sistema.py --update

Saídas:
    analise_estudo/resultados_base1/igd_sistema.csv  (chaves + igd_plus_sistema)
    (--update) coluna ``igd_plus`` reescrita em base1.csv e base2.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from . import indicators as ind
from . import objective_space as ops

ROOT = Path(__file__).resolve().parent
DEFAULT_ROOT = Path(
    "/home/staubjoao/Documents/mestrado/toMicroservices/v2/"
    "controle_experimento_i-toMicroservices_v5"
)
KEYS = ["persona", "config_label", "sistema", "repeticao"]


def _read(zip_path: Path) -> tuple[dict, dict, dict]:
    with zipfile.ZipFile(zip_path) as zf:
        manifest = json.load(zf.open("manifest.json"))
        indicators = json.load(zf.open("indicators.json"))
        frontiers = json.load(zf.open("frontiers.json"))
    return manifest, indicators, frontiers


def collect(root: Path) -> pd.DataFrame:
    rows = []
    for zip_path in sorted(root.rglob("*.zip")):
        manifest, indicators, frontiers = _read(zip_path)
        study = manifest.get("study") or {}
        run = manifest.get("run") or {}
        points = frontiers.get("normalizedFrontier") or []
        if not points:
            continue
        rows.append({
            "persona": study.get("personaId"),
            "config_label": study.get("configLabel"),
            "sistema": run.get("sourceId"),
            "repeticao": study.get("repetition"),
            "points": np.asarray(points, dtype=float),
        })
    if not rows:
        raise SystemExit("nenhuma execução com normalizedFrontier")
    return pd.DataFrame(rows)


def references(df: pd.DataFrame) -> dict[str, np.ndarray]:
    refs = {}
    for system, group in df.groupby("sistema"):
        stacked = np.vstack(group.points.tolist())
        refs[system] = ops.non_dominated(ops.unique_rows(stacked))
        print(f"{system}: executacoes={len(group)} | |Z*|={len(refs[system])}")
    return refs


def compute(df: pd.DataFrame, refs: dict[str, np.ndarray]) -> pd.DataFrame:
    out = []
    for row in df.itertuples(index=False):
        out.append({
            "persona": row.persona,
            "config_label": row.config_label,
            "sistema": row.sistema,
            "repeticao": row.repeticao,
            "igd_plus_sistema": float(ind.igd_plus(row.points, refs[row.sistema])),
        })
    return pd.DataFrame(out)


def rewrite_csv(path: Path, values: dict[tuple, float]) -> int:
    """Reescreve apenas a coluna ``igd_plus``, preservando o restante do arquivo."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if "igd_plus" not in fieldnames:
        raise SystemExit(f"{path} sem coluna igd_plus")
    replaced = 0
    for row in rows:
        key = (row["persona"], row["config_label"], row["sistema"], int(row["repeticao"]))
        if key in values:
            row["igd_plus"] = f"{values[key]:.17g}"
            replaced += 1
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)
    return replaced


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--base1", default=str(ROOT / "resultados_base1" / "base1.csv"))
    parser.add_argument("--base2", default=str(ROOT / "resultados_base2" / "base2.csv"))
    parser.add_argument("--out", default=str(ROOT / "resultados_base1" / "igd_sistema.csv"))
    parser.add_argument("--update", action="store_true", help="reescreve igd_plus em base1/base2")
    args = parser.parse_args()

    df = collect(Path(args.root))
    refs = references(df)
    result = compute(df, refs)
    result.to_csv(args.out, index=False)
    print(f"IGD+ por execução: {len(result)} linhas -> {args.out}")

    if args.update:
        values = {
            (r.persona, r.config_label, r.sistema, int(r.repeticao)): r.igd_plus_sistema
            for r in result.itertuples(index=False)
        }
        for path in (Path(args.base1), Path(args.base2)):
            replaced = rewrite_csv(path, values)
            print(f"{path.name}: {replaced} valores atualizados")

    medians = (
        result.groupby(["sistema", "config_label"]).igd_plus_sistema.median().unstack()
    )
    print("\nmedianas por configuração:")
    print(medians.round(4).to_string())


if __name__ == "__main__":
    main()
