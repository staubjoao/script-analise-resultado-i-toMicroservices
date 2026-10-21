"""Etapas 2/3/4 — Espaço de objetivos: filtro, alinhamento, limites,
normalização e frente de referência (Z*).

Todas as funções trabalham em convenção de MINIMIZAÇÃO.
"""

from __future__ import annotations

import numpy as np


def align_metric_columns(points: np.ndarray, names: tuple[str, ...],
                         canonical: tuple[str, ...]) -> np.ndarray:
    """Reordena as colunas de ``points`` para a ordem canônica (por NOME).

    Protege contra ordens de ``metricNames`` diferentes: o pareamento é feito
    pelo nome do objetivo, nunca pela posição.
    """
    if tuple(names) == tuple(canonical):
        return points
    if set(names) != set(canonical):
        raise ValueError(
            f"objetivos divergentes entre execuções do mesmo grupo: "
            f"{sorted(names)} != {sorted(canonical)}"
        )
    index = [names.index(metric) for metric in canonical]
    return points[:, index]


def drop_penalized(points: np.ndarray, threshold: float) -> np.ndarray:
    """Remove linhas penalizadas (qualquer objetivo >= threshold) ou não finitas."""
    if points.size == 0:
        return points
    finite = np.isfinite(points).all(axis=1)
    under_threshold = (points < threshold).all(axis=1)
    return points[finite & under_threshold]


def unique_rows(points: np.ndarray) -> np.ndarray:
    """Remove linhas duplicadas exatas (preserva a ordem? não — ordena como ``np.unique``).

    Duplicatas distorcem IGD+/ED (médias) e spacing (distância 0 ao vizinho).
    Aplicar antes de calcular os indicadores e em Z*.
    """
    if points.size == 0:
        return points
    return np.unique(points, axis=0)


def compute_bounds(populations: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Mínimos e máximos conjuntos (pooled) por objetivo, a partir de várias fronteiras.

    É a base da "normalização única por grupo": os limites são calculados uma
    única vez e aplicados a TODAS as execuções do grupo.
    """
    non_empty = [p for p in populations if p.size > 0]
    if not non_empty:
        raise ValueError("não há pontos para calcular os limites de normalização")
    pooled = np.vstack(non_empty)
    return pooled.min(axis=0), pooled.max(axis=0)


def normalize_with_bounds(points: np.ndarray, mins: np.ndarray,
                          maxs: np.ndarray) -> np.ndarray:
    """Normaliza por min-max: ``(x - min) / (max - min)``.

    Quando o intervalo é degenerado (praticamente zero), usa 1.0 no denominador
    para evitar divisão por zero.
    """
    ranges = maxs - mins
    ranges = np.where(np.abs(ranges) > 1e-10, ranges, 1.0)
    return (points - mins) / ranges


def non_dominated(points: np.ndarray) -> np.ndarray:
    """Mantém apenas as linhas não-dominadas (todos os objetivos minimizados).

    ``a`` domina ``b`` quando ``a <= b`` em todos os objetivos e ``a < b`` em
    pelo menos um. A deduplicação é responsabilidade de ``unique_rows``.
    """
    n = len(points)
    if n == 0:
        return points

    dominated = np.zeros(n, dtype=bool)
    for i in range(n):
        weakly_better = np.all(points <= points[i], axis=1)   # a <= b em todos
        strictly_better = np.any(points < points[i], axis=1)  # a < b em algum
        mask = weakly_better & strictly_better
        mask[i] = False  # um ponto não domina a si mesmo
        if mask.any():
            dominated[i] = True
    return points[~dominated]


def union_non_dominated(populations: list[np.ndarray]) -> np.ndarray:
    """União não-dominada de várias populações — usada para construir Z*.

    Deduplica antes de filtrar, para que Z* não carregue pontos repetidos.
    """
    non_empty = [p for p in populations if p.size > 0]
    if not non_empty:
        return np.empty((0, 0))
    stacked = unique_rows(np.vstack(non_empty))
    return non_dominated(stacked)
