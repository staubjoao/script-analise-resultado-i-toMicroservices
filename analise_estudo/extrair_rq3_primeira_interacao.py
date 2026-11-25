"""RQ3 — coorte da primeira interação do DM.

Extrai, para cada run, as intenções estruturais criadas no PRIMEIRO prompt e a
satisfação em três pontos:
- +25 gerações (absorção);
- +100 gerações (consolidação; horizonte comum às três personas);
- g2-1, isto é, a geração imediatamente anterior ao segundo prompt
  (219 gerações em P1, 249 em P2, 149 em P3). O valor em g2 não é usado porque
  a amostragem da geração do prompt é pós-decisão.

Fonte: `intent_diffusion.json` de cada ZIP da v5.
Uso: `.venv/bin/python analise_estudo/extrair_rq3_primeira_interacao.py`
"""

from __future__ import annotations

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
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for path in sorted(glob.glob(os.path.join(V5, "**", "*.zip"), recursive=True)):
        relative = os.path.relpath(path, V5)
        meta = parse_path(relative)
        first, second = SCHEDULE[meta["persona_dir"]][:2]
        to_next = second - 1 - first
        with zipfile.ZipFile(path) as archive:
            diffusion = json.loads(archive.read("intent_diffusion.json"))
        for intent in diffusion.get("intents", []):
            if intent.get("source") != "STRUCTURAL":
                continue
            if intent.get("activeFrom") != first:
                continue
            series = {
                int(r[0]): (r[2], r[3])
                for r in intent.get("series") or []
                if len(r) >= 4
            }
            relation = intent.get("relation") or {}
            row = {
                **meta,
                "intent_id": intent.get("id"),
                "origin": first,
                "to_next_prompt": to_next,
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

    with open(os.path.join(OUT, "intents.csv"), "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} intenções da 1ª interação -> {OUT}")


if __name__ == "__main__":
    main()
