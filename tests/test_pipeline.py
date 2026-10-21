"""Testes do pipeline (dedup, grupos, normalização embedded e leave-one-out)."""

from __future__ import annotations

import numpy as np
import pytest

from analise_estudo import pipeline
from analise_estudo.models import ExecutionRecord

METRICS = ("Coupling", "Cohesion", "Overhead", "Functionality", "ReusePerMS")


def make_record(frontier, *, persona="P1", config="c1", system="sys", rep=1, **extra):
    return ExecutionRecord(
        persona=persona,
        config=config,
        system=system,
        repetition=rep,
        metric_names=METRICS,
        frontier=np.asarray(frontier, dtype=float),
        **extra,
    )


def test_deduplicates_and_reports_duplicate_count():
    frontier = [[0.1, 0.2, 0.3, 0.4, 0.5], [0.1, 0.2, 0.3, 0.4, 0.5], [0.2, 0.2, 0.2, 0.2, 0.2]]
    group = [make_record(frontier)]
    result = pipeline.analyze_group("sys", group)
    execution = result.executions[0]
    assert execution.n_points == 2
    assert execution.n_duplicates == 1


def test_all_penalized_group_is_skipped_without_aborting_others():
    penalized = make_record([[1e6] * 5, [1e6] * 5], system="bad")
    valid = make_record([[0.1, 0.2, 0.3, 0.4, 0.5], [0.2, 0.1, 0.3, 0.4, 0.5]], system="good")
    results, skipped = pipeline.run_analysis([penalized, valid])
    assert "good" in results
    assert "bad" in skipped
    assert len(results["good"].executions) == 1


def test_embedded_normalization_uses_fixed_bounds():
    record = make_record(
        [[1.0, 1.0, 1.0, 1.0, 1.0], [2.0, 2.0, 2.0, 2.0, 2.0]],
        embedded_min=np.zeros(5),
        embedded_max=np.full(5, 10.0),
    )
    result = pipeline.analyze_group("sys", [record], normalization="embedded")
    assert result.bounds_source == "embedded"
    assert np.allclose(result.bounds_max, 10.0)


def test_embedded_normalization_requires_bounds():
    record = make_record([[0.1] * 5])
    with pytest.raises(ValueError):
        pipeline.analyze_group("sys", [record], normalization="embedded")


def test_embedded_normalization_rejects_inconsistent_bounds():
    a = make_record([[0.1] * 5], embedded_min=np.zeros(5), embedded_max=np.full(5, 10.0))
    b = make_record([[0.1] * 5], embedded_min=np.zeros(5), embedded_max=np.full(5, 20.0))
    with pytest.raises(ValueError):
        pipeline.analyze_group("sys", [a, b], normalization="embedded")


def test_leave_one_out_zstar_runs():
    a = make_record([[0.1, 0.2, 0.3, 0.4, 0.5]])
    b = make_record([[0.2, 0.1, 0.3, 0.4, 0.5]])
    result = pipeline.analyze_group("sys", [a, b], zstar="loo")
    assert all(np.isfinite(e.igd_plus) for e in result.executions)


def test_group_by_persona_uses_composite_key():
    a = make_record([[0.1] * 5], persona="P1", system="sys")
    b = make_record([[0.2] * 5], persona="P2", system="sys")
    results, _ = pipeline.run_analysis([a, b], group_by="persona")
    assert set(results) == {"P1||sys", "P2||sys"}


def test_run_analysis_empty_raises():
    with pytest.raises(ValueError):
        pipeline.run_analysis([])
