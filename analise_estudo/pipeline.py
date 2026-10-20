"""Etapas 3–6 — Orquestração da análise.

Fluxo (por SISTEMA):
  1. alinhar as colunas dos objetivos por nome (ordem canônica);
  2. descartar linhas penalizadas em cada execução;
  3. calcular os limites conjuntos (pooled) de todas as execuções;
  4. normalizar cada execução com ESSES MESMOS limites;
  5. construir Z* = união não-dominada de todos os pontos normalizados;
  6. calcular HV / IGD+ / ED / spacing de CADA execução.

Normalização e Z* são únicos por sistema, para permitir comparar configurações.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from . import config
from . import indicators as ind
from . import objective_space as ops
from .models import ExecutionRecord, ExecutionResult, SystemResult


def group_by_system(records: list[ExecutionRecord]) -> dict[str, list[ExecutionRecord]]:
    """Agrupa as execuções por sistema (``run.sourceId``)."""
    groups: dict[str, list[ExecutionRecord]] = defaultdict(list)
    for record in records:
        groups[record.system].append(record)
    return dict(groups)


def analyze_system(system: str, records: list[ExecutionRecord]) -> SystemResult:
    """Executa o fluxo completo para um único sistema."""
    # 1) Ordem canônica dos objetivos = a da primeira execução do sistema.
    canonical = records[0].metric_names

    # 2) Alinhar colunas por nome (evita pareamento errado por posição).
    aligned = [ops.align_metric_columns(r.frontier, r.metric_names, canonical)
               for r in records]

    # 3) Descartar penalizadas e calcular os limites conjuntos (pooled).
    cleaned = [ops.drop_penalized(p, config.PENALTY_THRESHOLD) for p in aligned]
    mins, maxs = ops.compute_bounds(cleaned)

    # 4) Normalizar cada execução com os MESMOS limites.
    normalized = [ops.normalize_with_bounds(p, mins, maxs) for p in cleaned]

    # 5) Frente de referência Z* = união não-dominada de tudo do sistema.
    reference_front = ops.union_non_dominated(normalized)

    # Pontos fixos no espaço normalizado.
    reference_point = np.full(len(canonical), config.HV_REFERENCE, dtype=float)
    ideal = np.full(len(canonical), config.ED_IDEAL_VALUE, dtype=float)

    # 6) Indicadores por execução.
    results: list[ExecutionResult] = []
    for record, points in zip(records, normalized):
        hv = ind.hypervolume(points, reference_point)
        igd = ind.igd_plus(points, reference_front)
        ed_mean, ed_min = ind.ed_to_ideal(points, ideal)
        sp = ind.spacing(points)
        results.append(ExecutionResult(
            record=record,
            n_points=int(len(points)),
            hv=hv,
            igd_plus=igd,
            ed_mean=ed_mean,
            ed_min=ed_min,
            spacing=sp,
        ))

    return SystemResult(
        system=system,
        metric_names=canonical,
        bounds_min=mins,
        bounds_max=maxs,
        reference_size=int(len(reference_front)),
        reference_front=reference_front,
        executions=results,
    )


def run_analysis(records: list[ExecutionRecord]) -> dict[str, SystemResult]:
    """Roda a análise para todos os sistemas presentes nos registros."""
    if not records:
        raise ValueError("nenhum registro válido para analisar")
    groups = group_by_system(records)
    return {system: analyze_system(system, recs)
            for system, recs in sorted(groups.items())}
