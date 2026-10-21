"""Etapas 3–6 — Orquestração da análise.

Fluxo (por GRUPO — sistema ou persona × sistema):
  1. alinhar as colunas dos objetivos por nome (ordem canônica);
  2. descartar linhas penalizadas e DEDUPLICAR cada execução;
  3. obter os limites de normalização:
       - ``pooled``: mín/máx de todas as execuções do grupo;
       - ``embedded``: bounds fixos de referência trazidos pelo ``frontiers.json``;
  4. normalizar cada execução com ESSES MESMOS limites;
  5. construir Z* = união não-dominada de todos os pontos normalizados
     (ou, em ``--zstar loo``, uma Z* por execução, sem a própria execução);
  6. calcular HV / IGD+ / ED / spacing de CADA execução.

Um grupo sem pontos válidos não derruba a análise: é registrado como ignorado.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from . import config
from . import indicators as ind
from . import objective_space as ops
from .models import ExecutionRecord, ExecutionResult, SystemResult


def group_key(record: ExecutionRecord, group_by: str) -> str:
    """Chave de agrupamento: ``system`` ou ``persona`` (persona × sistema)."""
    if group_by == "persona":
        return f"{record.persona}||{record.system}"
    return record.system


def group_records(records: list[ExecutionRecord], group_by: str) -> dict[str, list[ExecutionRecord]]:
    groups: dict[str, list[ExecutionRecord]] = defaultdict(list)
    for record in records:
        groups[group_key(record, group_by)].append(record)
    return dict(groups)


def _resolve_bounds(records: list[ExecutionRecord], cleaned: list[np.ndarray],
                    normalization: str) -> tuple[np.ndarray, np.ndarray, str]:
    """Resolve os limites de normalização (pooled ou embedded)."""
    if normalization == "embedded":
        pairs = [(r.embedded_min, r.embedded_max) for r in records]
        if any(lo is None or hi is None for lo, hi in pairs):
            raise ValueError(
                "normalização 'embedded' indisponível: algum ZIP não traz "
                "frontiers.json.normalization.bounds"
            )
        mins, maxs = pairs[0]
        for lo, hi in pairs[1:]:
            if not (np.allclose(lo, mins) and np.allclose(hi, maxs)):
                raise ValueError(
                    "normalização 'embedded' inconsistente: bounds diferentes entre execuções"
                )
        return mins, maxs, "embedded"

    mins, maxs = ops.compute_bounds(cleaned)
    return mins, maxs, "pooled"


def analyze_group(key: str, records: list[ExecutionRecord],
                  normalization: str = "pooled", zstar: str = "full",
                  group_by: str = "system") -> SystemResult:
    """Executa o fluxo completo para um grupo."""
    canonical = records[0].metric_names

    # 1) Alinhar colunas por nome.
    aligned = [ops.align_metric_columns(r.frontier, r.metric_names, canonical)
               for r in records]

    # 2) Descartar penalizadas e deduplicar (guarda a contagem antes da dedup).
    cleaned_before = [ops.drop_penalized(p, config.PENALTY_THRESHOLD) for p in aligned]
    cleaned = [ops.unique_rows(p) for p in cleaned_before]

    # 3) Limites de normalização.
    mins, maxs, bounds_source = _resolve_bounds(records, cleaned, normalization)

    # 4) Normalizar cada execução com os MESMOS limites.
    normalized = [ops.normalize_with_bounds(p, mins, maxs) for p in cleaned]

    # 5) Frente de referência completa do grupo.
    reference_front = ops.union_non_dominated(normalized)

    reference_point = np.full(len(canonical), config.HV_REFERENCE, dtype=float)
    ideal = np.full(len(canonical), config.ED_IDEAL_VALUE, dtype=float)

    # 6) Indicadores por execução.
    results: list[ExecutionResult] = []
    for index, (record, points) in enumerate(zip(records, normalized)):
        if zstar == "loo":
            others = [normalized[j] for j in range(len(normalized)) if j != index]
            reference = ops.union_non_dominated(others)
        else:
            reference = reference_front

        hv = ind.hypervolume(points, reference_point)
        igd = ind.igd_plus(points, reference)
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
            n_duplicates=int(len(cleaned_before[index]) - len(points)),
        ))

    return SystemResult(
        system=key,
        metric_names=canonical,
        bounds_min=mins,
        bounds_max=maxs,
        reference_size=int(len(reference_front)),
        reference_front=reference_front,
        executions=results,
        group_by=group_by,
        normalization=normalization,
        zstar=zstar,
        bounds_source=bounds_source,
    )


def run_analysis(records: list[ExecutionRecord], normalization: str = "pooled",
                 zstar: str = "full", group_by: str = "system"
                 ) -> tuple[dict[str, SystemResult], dict[str, str]]:
    """Roda a análise para todos os grupos.

    Retorna ``(resultados, grupos_ignorados)``. Um grupo com erro (ex.: todos os
    pontos penalizados) é registrado em ``grupos_ignorados`` e não impede os
    demais de serem analisados.
    """
    if not records:
        raise ValueError("nenhum registro válido para analisar")

    results: dict[str, SystemResult] = {}
    skipped: dict[str, str] = {}
    for key, group in sorted(group_records(records, group_by).items()):
        try:
            results[key] = analyze_group(
                key, group, normalization=normalization,
                zstar=zstar, group_by=group_by,
            )
        except Exception as exc:  # noqa: BLE001 — um grupo ruim não derruba os outros
            skipped[key] = f"{type(exc).__name__}: {exc}"
    return results, skipped
