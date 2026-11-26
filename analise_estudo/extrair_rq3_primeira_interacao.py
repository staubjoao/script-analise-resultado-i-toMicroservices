"""RQ3 — coorte da primeira interação do DM.

Extrai, para cada run, as intenções estruturais criadas na PRIMEIRA interação e a
satisfação em três pontos:
- +25 gerações (absorção);
- +100 gerações (consolidação; horizonte comum às três personas);
- g2-1, isto é, a geração imediatamente anterior à segunda interação
  (219 gerações em P1, 249 em P2, 149 em P3). O valor em g2 não é usado porque
  a amostragem da geração da interação é pós-decisão.

Fonte: `intent_diffusion.json` e `decisions.json` de cada ZIP da v5.
Uso: `.venv/bin/python analise_estudo/extrair_rq3_primeira_interacao.py [--zips DIR] [--out DIR]`
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import zipfile

V5 = "/home/staubjoao/Documents/mestrado/toMicroservices/v2/controle_experimento_i-toMicroservices_v5"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados_rq3", "primeira_interacao")
SCHEDULE = {
    "persona_1": [600, 820, 950],
    "persona_2": [300, 550, 800],
    "persona_3": [150, 300, 450],
}
HORIZONS = {"A": 25, "C": 100}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrai a coorte da primeira interação (RQ3).")
    parser.add_argument(
        "--zips",
        default=os.environ.get("ITOMICROSERVICES_V5", V5),
        help="diretório com os ZIPs da v5 (default: $ITOMICROSERVICES_V5 ou o caminho local)",
    )
    parser.add_argument("--out", default=OUT, help="diretório de saída")
    return parser.parse_args()


def parse_path(relative: str) -> dict:
    match = re.match(
        r"study_(.+?)__(.+?)__(config_\d+)__(.+?)__execution_(\d+)\.zip",
        os.path.basename(relative),
    )
    if not match:
        raise ValueError(f"nome fora do padrão: {relative}")
    parts = relative.split(os.sep)
    return {
        "persona_dir": parts[0],
        "persona": {"persona_1": "P1", "persona_2": "P2", "persona_3": "P3"}[parts[0]],
        "sistema": next(p for p in parts if p in ("spring-petclinic", "jpetstore")),
        "config": match.group(3),
        "participant": match.group(1),
        "rep": int(match.group(5)),
    }


def main() -> None:
    args = parse_args()
    zips_root = args.zips
    out = args.out
    if not os.path.isdir(zips_root):
        raise SystemExit(f"diretório de ZIPs não encontrado: {zips_root}")
    os.makedirs(out, exist_ok=True)
    rows = []
    for path in sorted(glob.glob(os.path.join(zips_root, "**", "*.zip"), recursive=True)):
        relative = os.path.relpath(path, zips_root)
        meta = parse_path(relative)
        with zipfile.ZipFile(path) as archive:
            diffusion = json.loads(archive.read("intent_diffusion.json"))
            try:
                decisions = json.loads(archive.read("decisions.json"))
            except KeyError:
                decisions = []
        generations = sorted({
            int(d["generation"]) for d in decisions if d.get("generation") is not None
        })
        if len(generations) >= 2:
            first, second = generations[0], generations[1]
        else:
            first, second = SCHEDULE[meta["persona_dir"]][:2]
        to_next = second - 1 - first
        columns = diffusion.get("seriesColumns") or []
        strict_index = columns.index("strictFraction") if "strictFraction" in columns else 2
        partial_index = columns.index("meanPartialSatisfaction") if "meanPartialSatisfaction" in columns else 3
        for intent in diffusion.get("intents", []):
            if intent.get("source") != "STRUCTURAL":
                continue
            if intent.get("activeFrom") != first:
                continue
            series = {
                int(r[0]): (r[strict_index], r[partial_index])
                for r in intent.get("series") or []
                if len(r) > max(strict_index, partial_index)
            }
            relation = intent.get("relation") or {}
            row = {
                **meta,
                "intent_id": intent.get("id"),
                "origin": first,
                "to_next_interaction": to_next,
                "type": intent.get("type"),
                "n_group": len(relation.get("groupIds") or []),
                "n_from": len(relation.get("fromIds") or []),
                "n_samples": len(series),
            }
            for label, horizon in HORIZONS.items():
                strict, partial = series.get(first + horizon, (None, None))
                row[f"partial_{label}"] = partial
                row[f"strict_{label}"] = strict
            strict, partial = series.get(first + to_next, (None, None))
            row["partial_N"] = partial
            row["strict_N"] = strict
            rows.append(row)

    if not rows:
        raise SystemExit("nenhuma intenção encontrada; verifique --zips")
    with open(os.path.join(out, "intents.csv"), "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} intenções da 1ª interação -> {out}")


if __name__ == "__main__":
    main()
