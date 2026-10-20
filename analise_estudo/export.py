"""Etapa 7 — Exportação dos resultados.

Saída organizada em:
- ``indicadores_por_execucao.csv`` — uma linha por execução (para análise/estatística);
- ``por_sistema/<sistema>.json`` — detalhe por sistema (limites, Z* e execuções);
- ``resumo.json`` — configuração usada e contagens.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

from . import config
from .models import SystemResult


def _clean(value):
    """Converte tipos numpy para Python e NaN/Inf para ``None`` (JSON válido)."""
    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _clean_matrix(matrix: np.ndarray) -> list[list]:
    return [[_clean(v) for v in row] for row in matrix]


CSV_COLUMNS = [
    "persona", "config", "sistema", "repeticao", "n_pontos",
    "hv", "igd_plus", "ed_media", "ed_min", "spacing",
]


def write_csv(results: dict[str, SystemResult], out_path: Path) -> None:
    """Escreve a tabela por execução (CSV)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for system in sorted(results):
            for execution in results[system].executions:
                record = execution.record
                writer.writerow([
                    record.persona,
                    record.config,
                    record.system,
                    record.repetition,
                    execution.n_points,
                    _clean(execution.hv),
                    _clean(execution.igd_plus),
                    _clean(execution.ed_mean),
                    _clean(execution.ed_min),
                    _clean(execution.spacing),
                ])


def _system_payload(system_result: SystemResult) -> dict:
    """Monta o dicionário JSON de um sistema."""
    executions = []
    for execution in system_result.executions:
        record = execution.record
        executions.append({
            "persona": record.persona,
            "config": record.config,
            "repetition": record.repetition,
            "source_zip": record.source_zip,
            "n_pontos": execution.n_points,
            "hv": _clean(execution.hv),
            "igd_plus": _clean(execution.igd_plus),
            "ed_media": _clean(execution.ed_mean),
            "ed_min": _clean(execution.ed_min),
            "spacing": _clean(execution.spacing),
        })
    return {
        "sistema": system_result.system,
        "metric_names": list(system_result.metric_names),
        "limites_normalizacao": {
            "min": [_clean(v) for v in system_result.bounds_min],
            "max": [_clean(v) for v in system_result.bounds_max],
        },
        "tamanho_referencia": system_result.reference_size,
        "fronteira_referencia": _clean_matrix(system_result.reference_front),
        "execucoes": executions,
    }


def write_json(results: dict[str, SystemResult], out_dir: Path) -> None:
    """Escreve o JSON por sistema e o resumo geral."""
    out_dir = Path(out_dir)
    per_system_dir = out_dir / "por_sistema"
    per_system_dir.mkdir(parents=True, exist_ok=True)

    for system in sorted(results):
        payload = _system_payload(results[system])
        with open(per_system_dir / f"{system}.json", "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    summary = {
        "configuracao": {
            "hv_reference": config.HV_REFERENCE,
            "ed_ideal_value": config.ED_IDEAL_VALUE,
            "penalty_threshold": config.PENALTY_THRESHOLD,
            "hv_samples": config.HV_SAMPLES,
            "hv_seed": config.HV_SEED,
            "num_objetivos": config.NUM_OBJECTIVES,
        },
        "sistemas": {
            system: {
                "n_execucoes": len(results[system].executions),
                "tamanho_referencia": results[system].reference_size,
            }
            for system in sorted(results)
        },
    }
    with open(out_dir / "resumo.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
