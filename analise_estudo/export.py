"""Etapa 7 — Exportação dos resultados.

Saída organizada em:
- ``por_sistema/<sistema>.csv`` — uma linha por execução (UM CSV POR SISTEMA);
- ``por_sistema/<grupo>.json`` — detalhe por grupo (limites, Z* e execuções);
- ``resumo.json`` — configuração usada, contagens e grupos ignorados.
"""

from __future__ import annotations

import csv
import json
import math
import re
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


def _safe_filename(name: str) -> str:
    """Sanitiza o nome do grupo para uso como nome de arquivo."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "grupo").strip("_")
    return safe or "grupo"


CSV_COLUMNS = [
    "persona", "participante", "config", "sistema", "repeticao",
    "geracao", "completo", "n_pontos", "n_duplicados",
    "hv", "igd_plus", "ed_media", "ed_min", "spacing", "source_zip",
]


def write_csv(results: dict[str, SystemResult], out_dir: Path) -> list[Path]:
    """Escreve **um CSV por sistema** em ``<out_dir>/por_sistema/<sistema>.csv``.

    Retorna a lista de arquivos escritos. Cada CSV contém apenas as execuções
    daquele sistema (a coluna ``sistema`` permanece para rastreabilidade).
    """
    out_dir = Path(out_dir)
    per_system_dir = out_dir / "por_sistema"
    per_system_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for key in sorted(results):
        path = per_system_dir / f"{_safe_filename(key)}.csv"
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(CSV_COLUMNS)
            for execution in results[key].executions:
                record = execution.record
                writer.writerow([
                    record.persona,
                    record.participant,
                    record.config,
                    record.system,
                    record.repetition,
                    record.generation,
                    record.completo,
                    execution.n_points,
                    execution.n_duplicates,
                    _clean(execution.hv),
                    _clean(execution.igd_plus),
                    _clean(execution.ed_mean),
                    _clean(execution.ed_min),
                    _clean(execution.spacing),
                    record.source_zip,
                ])
        written.append(path)
    return written


def _system_payload(system_result: SystemResult) -> dict:
    """Monta o dicionário JSON de um grupo."""
    executions = []
    for execution in system_result.executions:
        record = execution.record
        executions.append({
            "persona": record.persona,
            "participante": record.participant,
            "config": record.config,
            "repetition": record.repetition,
            "generation": record.generation,
            "completo": record.completo,
            "stop_reason": record.stop_reason,
            "source_zip": record.source_zip,
            "n_pontos": execution.n_points,
            "n_duplicados": execution.n_duplicates,
            "hv": _clean(execution.hv),
            "igd_plus": _clean(execution.igd_plus),
            "ed_media": _clean(execution.ed_mean),
            "ed_min": _clean(execution.ed_min),
            "spacing": _clean(execution.spacing),
        })
    return {
        "grupo": system_result.system,
        "agrupamento": system_result.group_by,
        "normalizacao": system_result.normalization,
        "origem_dos_limites": system_result.bounds_source,
        "zstar": system_result.zstar,
        "metric_names": list(system_result.metric_names),
        "limites_normalizacao": {
            "min": [_clean(v) for v in system_result.bounds_min],
            "max": [_clean(v) for v in system_result.bounds_max],
        },
        "tamanho_referencia": system_result.reference_size,
        "fronteira_referencia": _clean_matrix(system_result.reference_front),
        "execucoes": executions,
    }


def write_json(results: dict[str, SystemResult], out_dir: Path,
               skipped: dict[str, str] | None = None,
               meta: dict | None = None) -> None:
    """Escreve o JSON por grupo e o resumo geral."""
    out_dir = Path(out_dir)
    skipped = skipped or {}
    meta = meta or {}
    per_system_dir = out_dir / "por_sistema"
    per_system_dir.mkdir(parents=True, exist_ok=True)

    for key in sorted(results):
        payload = _system_payload(results[key])
        with open(per_system_dir / f"{_safe_filename(key)}.json", "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    summary = {
        "configuracao": {
            "agrupamento": meta.get("group_by", "system"),
            "normalizacao": meta.get("normalization", "pooled"),
            "zstar": meta.get("zstar", "full"),
            "hv_reference": config.HV_REFERENCE,
            "ed_ideal_value": config.ED_IDEAL_VALUE,
            "penalty_threshold": config.PENALTY_THRESHOLD,
            "hv_samples": config.HV_SAMPLES,
            "hv_seed": config.HV_SEED,
            "num_objetivos": config.NUM_OBJECTIVES,
        },
        "grupos": {
            key: {
                "n_execucoes": len(results[key].executions),
                "n_incompletos": sum(1 for e in results[key].executions
                                     if not e.record.completo),
                "tamanho_referencia": results[key].reference_size,
            }
            for key in sorted(results)
        },
        "grupos_ignorados": skipped,
        "descartes_de_zip": meta.get("skipped_zips", []),
    }
    with open(out_dir / "resumo.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
