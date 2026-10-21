"""Testes do espaço de objetivos (filtro, dedup, dominância, normalização)."""

from __future__ import annotations

import numpy as np
import pytest

from analise_estudo import objective_space as ops


def test_unique_rows_removes_duplicates():
    points = np.array([[0.1, 0.2], [0.1, 0.2], [0.3, 0.4]])
    unique = ops.unique_rows(points)
    assert len(unique) == 2


def test_drop_penalized_removes_threshold_and_non_finite():
    points = np.array([[0.1, 0.2], [1e6, 0.2], [np.nan, 0.3]])
    kept = ops.drop_penalized(points, 1e5)
    assert len(kept) == 1
    assert kept[0].tolist() == [0.1, 0.2]


def test_non_dominated_keeps_frontier():
    points = np.array([[0.1, 0.5], [0.5, 0.1], [0.6, 0.6]])
    front = ops.non_dominated(points)
    assert [row.tolist() for row in front] == [[0.1, 0.5], [0.5, 0.1]]


def test_union_non_dominated_deduplicates():
    populations = [
        np.array([[0.1, 0.5], [0.1, 0.5]]),
        np.array([[0.1, 0.5], [0.6, 0.6]]),
    ]
    union = ops.union_non_dominated(populations)
    assert len(union) == 1
    assert union[0].tolist() == [0.1, 0.5]


def test_compute_bounds_and_normalize():
    populations = [np.array([[1.0, 10.0]]), np.array([[3.0, 20.0]])]
    mins, maxs = ops.compute_bounds(populations)
    assert mins.tolist() == [1.0, 10.0]
    assert maxs.tolist() == [3.0, 20.0]
    normalized = ops.normalize_with_bounds(np.array([[2.0, 15.0]]), mins, maxs)
    assert normalized[0].tolist() == pytest.approx([0.5, 0.5])


def test_compute_bounds_empty_raises():
    with pytest.raises(ValueError):
        ops.compute_bounds([np.empty((0, 5))])


def test_normalize_degenerate_range_uses_one():
    normalized = ops.normalize_with_bounds(
        np.array([[5.0, 5.0]]), np.array([5.0, 5.0]), np.array([5.0, 5.0])
    )
    assert normalized[0].tolist() == [0.0, 0.0]


def test_align_metric_columns_reorders_by_name():
    points = np.array([[1.0, 2.0, 3.0]])
    aligned = ops.align_metric_columns(points, ("C", "A", "B"), ("A", "B", "C"))
    assert aligned[0].tolist() == [2.0, 3.0, 1.0]


def test_align_metric_columns_raises_on_divergent_names():
    with pytest.raises(ValueError):
        ops.align_metric_columns(np.array([[1.0]]), ("A",), ("B",))
