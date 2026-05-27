"""Smoke tests para core.bias, core.ev, core.strategies."""
from __future__ import annotations
import numpy as np
import pytest
from core.wheel import EUROPEAN, AMERICAN
from core.bias import detect_bias, required_sample_size
from core.ev import calibrated_ev, kelly_fraction, evaluate_all_numbers, house_edge
from core.strategies import simulate_strategy, compare_all_strategies


# ----------------- bias -----------------

def test_required_sample_size_within_garcia_pelayo_range():
    n = required_sample_size(EUROPEAN)
    # esperamos algo entre 3000 e 10000 com defaults
    assert 3000 <= n <= 10000


def test_detect_bias_on_unbiased_data():
    rng = np.random.default_rng(2024)
    idx = rng.integers(0, EUROPEAN.pockets, size=10000)
    spins = [EUROPEAN.order[i] for i in idx]
    r = detect_bias(spins, EUROPEAN)
    # nao deve dar vies_provavel num conjunto verdadeiramente uniforme
    assert r["verdict"] in ("sem_vies_detectado", "inconclusivo", "indicio_fraco")


def test_detect_bias_on_strong_bias():
    rng = np.random.default_rng(2024)
    probs = np.full(EUROPEAN.pockets, 1.0)
    probs[:5] *= 2.0
    probs /= probs.sum()
    idx = rng.choice(EUROPEAN.pockets, size=5000, p=probs)
    spins = [EUROPEAN.order[i] for i in idx]
    r = detect_bias(spins, EUROPEAN)
    # com vies forte e n=5000 deve detectar
    assert r["verdict"] == "vies_provavel"
    assert r["confidence"] == "alta"
    assert len(r["flags"]) >= 2


def test_detect_bias_small_sample_says_insufficient():
    r = detect_bias(["7"] * 50, EUROPEAN)
    assert r["verdict"] == "amostra_insuficiente"


# ----------------- ev -----------------

def test_house_edge_european():
    # europeia: -1/37 ~ -2.7%
    assert abs(house_edge(EUROPEAN) - (-1 / 37)) < 1e-9


def test_house_edge_american():
    # americana: -2/38 ~ -5.26%
    assert abs(house_edge(AMERICAN) - (-2 / 38)) < 1e-9


def test_calibrated_ev_returns_structure():
    spins = ["7"] * 100 + ["1"] * 100
    r = calibrated_ev(spins, EUROPEAN, "7")
    assert "ev_empirical" in r
    assert "ev_theoretical" in r
    assert r["target"] == "7"


def test_kelly_fraction_zero_for_negative_ev():
    assert kelly_fraction(-0.027) == 0.0


def test_kelly_fraction_capped_at_25pct():
    # mesmo com EV absurdamente positivo, Kelly cap em 0.25
    assert kelly_fraction(10.0) == 0.25


def test_evaluate_all_numbers_returns_sorted():
    spins = ["7"] * 200 + ["1"] * 100 + ["12"] * 50
    results = evaluate_all_numbers(spins, EUROPEAN)
    assert len(results) == EUROPEAN.pockets
    # ordenado por ev_empirical decrescente
    evs = [r["ev_empirical"] for r in results]
    assert evs == sorted(evs, reverse=True)


# ----------------- strategies -----------------

def test_simulate_flat_strategy():
    r = simulate_strategy(
        EUROPEAN, strategy="flat", n_spins=50, n_sessions=100, seed=42
    )
    assert r.n_sessions == 100
    assert len(r.final_bankrolls) == 100
    # media final deve estar abaixo do inicial (house edge)
    assert r.mean_final < 1000


def test_compare_all_strategies_returns_all():
    out = compare_all_strategies(EUROPEAN, n_spins=50, n_sessions=100)
    for name in ("flat", "martingale", "fibonacci", "dalembert", "paroli"):
        assert name in out
        assert "mean_final" in out[name]


def test_all_strategies_lose_in_expectation():
    """Pilar: nenhuma estrategia bate o house edge no longo prazo."""
    out = compare_all_strategies(EUROPEAN, n_spins=200, n_sessions=500)
    for name, r in out.items():
        assert r["mean_final"] < 1000, f"{name} deveria perder em media"
