"""Testes de regressão dos indicadores (valores conhecidos)."""

from __future__ import annotations

import numpy as np
import pytest

from analise_estudo import indicators as ind


def test_hv_2d_single_point():
    hv = ind.hypervolume(np.array([[0.5, 0.5]]), np.array([1.0, 1.0]))
    assert hv == pytest.approx(0.25)


def test_hv_2d_staircase_two_points():
    # (0.25,0.75) e (0.5,0.5), ref (1,1) -> 0.25*0.25 + 0.5*0.5 = 0.3125
    hv = ind.hypervolume(np.array([[0.25, 0.75], [0.5, 0.5]]), np.array([1.0, 1.0]))
    assert hv == pytest.approx(0.3125)


def test_hv_3d_single_point():
    hv = ind.hypervolume(np.array([[0.5, 0.5, 0.5]]), np.array([1.0, 1.0, 1.0]))
    assert hv == pytest.approx(0.125)


def test_hv_ignores_points_not_dominating_reference():
    # O segundo ponto (1.2, 0.1) não domina a referência (1.1, 1.1) -> ignorado.
    # Só (0.5, 0.5): (1.1 - 0.5) * (1.1 - 0.5) = 0.36.
    hv = ind.hypervolume(np.array([[0.5, 0.5], [1.2, 0.1]]), np.array([1.1, 1.1]))
    assert hv == pytest.approx(0.36)


def test_hv_qmc_deterministic_for_5_objectives():
    points = np.array([[0.5, 0.5, 0.5, 0.5, 0.5],
                       [0.6, 0.4, 0.5, 0.5, 0.5]])
    reference = np.array([1.1] * 5)
    assert ind.hypervolume(points, reference) == ind.hypervolume(points, reference)


def test_hv_empty_is_zero():
    assert ind.hypervolume(np.empty((0, 5)), np.array([1.1] * 5)) == 0.0


def test_igd_plus_known_value():
    value = ind.igd_plus(np.array([[0.1, 0.1]]), np.array([[0.0, 0.0]]))
    assert value == pytest.approx(np.sqrt(0.02))


def test_igd_plus_takes_minimum_over_points():
    points = np.array([[0.2, 0.2], [0.1, 0.1]])
    value = ind.igd_plus(points, np.array([[0.0, 0.0]]))
    assert value == pytest.approx(np.sqrt(0.02))


def test_ed_to_ideal_mean_and_min():
    mean, minimum = ind.ed_to_ideal(np.array([[3.0, 4.0], [0.0, 0.0]]), np.array([0.0, 0.0]))
    assert mean == pytest.approx(2.5)
    assert minimum == pytest.approx(0.0)


def test_spacing_collinear_is_zero():
    points = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    assert ind.spacing(points) == pytest.approx(0.0)


def test_spacing_fewer_than_two_points_is_zero():
    assert ind.spacing(np.array([[0.5, 0.5]])) == 0.0
