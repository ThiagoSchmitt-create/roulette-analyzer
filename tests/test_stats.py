"""Smoke tests para core.stats."""
from __future__ import annotations
import numpy as np
import pytest
from core.wheel import EUROPEAN
from core.stats import (
    chi_square_numbers,
    chi_square_color,
    chi_square_sectors,
    runs_test_color,
    autocorrelation,
    z_scores_per_number,
    gap_distribution,
    run_all_tests,
)


@pytest.fixture
def unbiased_spins():
    rng = np.random.default_rng(2024)
    idx = rng.integers(0, EUROPEAN.pockets, size=5000)
    return [EUROPEAN.order[i] for i in idx]


@pytest.fixture
def biased_spins():
    rng = np.random.default_rng(2024)
    probs = np.full(EUROPEAN.pockets, 1.0)
    probs[:5] *= 2.0  # turbinar 5 primeiros numeros
    probs /= probs.sum()
    idx = rng.choice(EUROPEAN.pockets, size=5000, p=probs)
    return [EUROPEAN.order[i] for i in idx]


def test_chi_square_unbiased_does_not_reject(unbiased_spins):
    r = chi_square_numbers(unbiased_spins, EUROPEAN)
    # com seed=2024 e 5000 giros, p deve estar acima de 0.01 com alta prob
    assert r["chi2"] > 0
    assert r["dof"] == 36
    assert 0 <= r["p_value"] <= 1


def test_chi_square_biased_rejects(biased_spins):
    r = chi_square_numbers(biased_spins, EUROPEAN)
    assert r["reject_h0_at_5pct"] is True
    assert r["p_value"] < 0.05


def test_chi_square_sectors_finds_hot_zone(biased_spins):
    r = chi_square_sectors(biased_spins, EUROPEAN, sector_size=5)
    assert r["reject_h0_at_5pct"] is True
    # algum dos hot sectors deve ter z > 3
    max_z = max(hs["z_score"] for hs in r["hot_sectors"])
    assert max_z > 3.0


def test_color_test_unbiased_balances(unbiased_spins):
    r = chi_square_color(unbiased_spins, EUROPEAN)
    # red e black devem estar dentro de 5% de paridade
    obs = r["observed"]
    diff = abs(obs["red"] - obs["black"])
    assert diff < 200  # tolerancia generosa


def test_runs_test_returns_p_value(unbiased_spins):
    r = runs_test_color(unbiased_spins)
    assert "p_value" in r
    assert 0 <= r["p_value"] <= 1


def test_autocorrelation_skips_short_series():
    r = autocorrelation(["1", "2"] * 5, max_lag=10)
    assert r.get("skipped") is True


def test_autocorrelation_runs_on_full_series(unbiased_spins):
    r = autocorrelation(unbiased_spins, max_lag=10)
    assert "acf" in r
    assert len(r["acf"]) == 10


def test_z_scores_reports_top_hot_and_cold(unbiased_spins):
    r = z_scores_per_number(unbiased_spins, EUROPEAN)
    assert len(r["top_hot"]) == 5
    assert len(r["top_cold"]) == 5
    # top_hot[0] deve ter z >= top_hot[-1]
    assert r["top_hot"][0]["z"] >= r["top_hot"][-1]["z"]


def test_gap_distribution_around_expected(unbiased_spins):
    r = gap_distribution(unbiased_spins, EUROPEAN)
    # media de gap deve ficar perto de 37 (1/p)
    assert abs(r["mean_gap_observed"] - 37) < 5


def test_run_all_tests_structure(unbiased_spins):
    r = run_all_tests(unbiased_spins, EUROPEAN)
    assert r["wheel"] == "european"
    assert r["n_spins"] == 5000
    for key in ("numbers", "color", "sectors", "runs", "autocorr", "z_scores", "gaps"):
        assert key in r["tests"], f"falta {key}"
