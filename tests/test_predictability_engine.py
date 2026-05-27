"""
Testes do motor de previsibilidade.

Prova o ponto central: dado aleatorio -> 'sem_padrao' (honesto), e cada tipo de
estrutura conhecida e corretamente detectado e classificado. Geramos streams com
ground-truth via core.stream_generators.
"""
from __future__ import annotations

from core.predictability_engine import analyze_predictability
from core.stream_generators import (
    gen_biased,
    gen_drift,
    gen_fair,
    gen_markov,
    gen_periodic,
)
from core.wheel import get_wheel

WHEEL = get_wheel("european")
N = 4000
NPERM = 120
SEED = 7


def _analyze(spins) -> dict:
    return analyze_predictability(spins, WHEEL, seed=SEED, n_perm=NPERM)


def test_fair_stream_is_unpredictable() -> None:
    res = _analyze(gen_fair(N, WHEEL, seed=1))
    assert res["dominant_pattern"] == "sem_padrao", res["patterns_detected"]
    assert res["predictability_score"] < 0.15


def test_biased_detects_uniform_bias() -> None:
    res = _analyze(gen_biased(N, WHEEL, strength=0.25, seed=2))
    assert res["tests"]["vies_uniforme"]["detected"]
    assert res["dominant_pattern"] == "vies_uniforme"


def test_markov_detects_serial_dependence() -> None:
    res = _analyze(gen_markov(N, WHEEL, dependence=0.6, seed=3))
    assert res["tests"]["dependencia_serial"]["detected"]
    assert res["dominant_pattern"] == "dependencia_serial"


def test_periodic_detects_periodicity() -> None:
    res = _analyze(gen_periodic(N, WHEEL, period=5, strength=0.6, seed=4))
    assert res["tests"]["periodicidade"]["detected"]
    assert res["tests"]["periodicidade"]["best_lag"] % 5 == 0
    assert res["dominant_pattern"] == "periodicidade"


def test_drift_detects_change_point() -> None:
    res = _analyze(gen_drift(N, WHEEL, switch_at=0.5, strength=0.35, seed=5))
    assert res["tests"]["drift"]["detected"]


def test_structured_scores_higher_than_fair() -> None:
    fair = _analyze(gen_fair(N, WHEEL, seed=6))["predictability_score"]
    biased = _analyze(gen_biased(N, WHEEL, strength=0.3, seed=6))["predictability_score"]
    assert biased > fair
