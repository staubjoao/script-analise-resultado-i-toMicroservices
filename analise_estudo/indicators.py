"""Etapa 5 — Indicadores de qualidade (reimplementados, sem depender de ``experiments/``).

Todos em convenção de MINIMIZAÇÃO e no espaço normalizado [0,1]^M:
- Hypervolume (HV): maior é melhor;
- IGD+: menor é melhor;
- ED ao ideal: menor é melhor (média e mínima);
- Spacing: menor é mais uniforme.

HV exato para M=2 e M=3; para M >= 4 usa Monte Carlo por amostragem QMC (Sobol)
com semente fixa (determinístico).
"""

from __future__ import annotations

import numpy as np
from scipy.stats.qmc import Sobol

from . import config


# ---------------------------------------------------------------------------
# Hypervolume
# ---------------------------------------------------------------------------
def hypervolume(points: np.ndarray, reference: np.ndarray,
                n_samples: int = config.HV_SAMPLES,
                seed: int = config.HV_SEED) -> float:
    """Hypervolume em relação a ``reference`` (ponto de referência fixo).

    Args:
        points: (n, M) objetivos (minimização), no espaço normalizado.
        reference: (M,) ponto de referência; só contam pontos que o dominam
            estritamente (``p < reference`` em todos os objetivos).
        n_samples: amostras do QMC quando M >= 4.
        seed: semente fixa do Sobol (reprodutibilidade).
    """
    if points.size == 0:
        return 0.0

    m = reference.shape[0]
    valid = points[np.all(points < reference, axis=1)]
    if valid.size == 0:
        return 0.0

    if m == 2:
        return _hv_2d(valid, reference)
    if m == 3:
        return _hv_3d(valid, reference)
    return _hv_qmc(valid, reference, n_samples, seed)


def _hv_2d(points: np.ndarray, ref: np.ndarray) -> float:
    """HV 2D exato via varredura da escada inferior-esquerda."""
    pts = points[np.all(points < ref, axis=1)]
    if len(pts) == 0:
        return 0.0
    pts = pts[np.argsort(pts[:, 0], kind="stable")]

    # Mantém apenas a escada: y estritamente decrescente à medida que x cresce.
    staircase: list[tuple[float, float]] = []
    best_y = np.inf
    for x, y in pts:
        if y < best_y:
            staircase.append((float(x), float(y)))
            best_y = y

    hv = 0.0
    for i, (x, y) in enumerate(staircase):
        x_next = staircase[i + 1][0] if i + 1 < len(staircase) else float(ref[0])
        hv += (x_next - x) * (float(ref[1]) - y)
    return hv


def _hv_3d(points: np.ndarray, ref: np.ndarray) -> float:
    """HV 3D exato por fatiamento em Z (cada fatia usa o HV 2D)."""
    pts = points[np.all(points < ref, axis=1)]
    if len(pts) == 0:
        return 0.0
    pts = pts[np.argsort(pts[:, 2], kind="stable")]

    hv = 0.0
    for i in range(len(pts)):
        z_low = float(pts[i, 2])
        z_high = float(pts[i + 1, 2]) if i + 1 < len(pts) else float(ref[2])
        if z_high <= z_low:
            continue
        area = _hv_2d(pts[: i + 1, :2], ref[:2])
        hv += (z_high - z_low) * area
    return hv


def _hv_qmc(points: np.ndarray, ref: np.ndarray, n_samples: int,
            seed: int) -> float:
    """HV em M >= 4 por Monte Carlo com amostragem QMC (Sobol) determinística."""
    m = ref.shape[0]
    lower = np.zeros(m)  # caixas vão de cada ponto até o reference (minimização)
    box_volume = float(np.prod(ref - lower))

    sampler = Sobol(d=m, scramble=True, seed=seed)
    samples = lower + sampler.random(n_samples) * (ref - lower)

    # Um ponto da amostra é "coberto" se algum ponto da fronteira o domina.
    covered = np.zeros(n_samples, dtype=bool)
    for p in points:
        covered |= np.all(samples >= p, axis=1)
    return box_volume * float(covered.mean())


# ---------------------------------------------------------------------------
# IGD+
# ---------------------------------------------------------------------------
def igd_plus(points: np.ndarray, reference_front: np.ndarray) -> float:
    """IGD+ da fronteira de referência Z* em relação à fronteira ``points``.

    Para cada ``r`` em Z*: ``d+(r) = min_p sqrt( sum_j max(0, p_j - r_j)^2 )``.
    O IGD+ é a média de ``d+(r)`` sobre a referência.

    Args:
        points: (np, M) fronteira da execução (normalizada, minimização).
        reference_front: (nr, M) a fronteira de referência Z*.
    """
    if points.size == 0 or reference_front.size == 0:
        return float("nan")

    diff = points[:, None, :] - reference_front[None, :, :]  # (np, nr, M)
    np.maximum(diff, 0.0, out=diff)
    distances = np.sqrt(np.sum(diff * diff, axis=2))           # (np, nr)
    best_per_reference = distances.min(axis=0)                 # (nr,)
    return float(best_per_reference.mean())


# ---------------------------------------------------------------------------
# ED (distância ao ideal)
# ---------------------------------------------------------------------------
def ed_to_ideal(points: np.ndarray, ideal: np.ndarray) -> tuple[float, float]:
    """Distância euclidiana ao ideal: retorna ``(média, mínima)``.

    O ideal padrão no espaço normalizado é ``(0, 0, 0, 0, 0)``.
    """
    if points.size == 0:
        return float("nan"), float("nan")
    distances = np.linalg.norm(points - ideal, axis=1)
    return float(distances.mean()), float(distances.min())


# ---------------------------------------------------------------------------
# Spacing
# ---------------------------------------------------------------------------
def spacing(points: np.ndarray) -> float:
    """Spacing (uniformidade da fronteira). Menor é mais uniforme.

    Para cada ponto, a distância de Manhattan ao vizinho mais próximo; depois
    ``sqrt( sum((d - média)^2) / (n - 1) )``. Retorna 0.0 com menos de 2 pontos.
    """
    n = len(points)
    if n < 2:
        return 0.0
    pairwise = np.abs(points[:, None, :] - points[None, :, :]).sum(axis=2)
    np.fill_diagonal(pairwise, np.inf)
    nearest = pairwise.min(axis=1)
    mean = float(nearest.mean())
    return float(np.sqrt(np.sum((nearest - mean) ** 2) / (n - 1)))
