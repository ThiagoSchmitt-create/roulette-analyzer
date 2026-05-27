"""Testes do modulo de frequencia e probabilidade de ausencia (core/patterns)."""
from __future__ import annotations

import pytest

from core.patterns import frequency_ranking, prob_not_appearing
from core.wheel import get_wheel


def test_prob_not_appearing_theoretical_next_spin() -> None:
    """P(NAO sair no proximo giro) teorica = 1 - 1/37 = 36/37 (europeia)."""
    wheel = get_wheel("european")
    spins = ["0"] * 100  # conteudo nao afeta a parte teorica
    res = prob_not_appearing(spins, wheel, horizons=(1,))
    for row in res["numbers"]:
        assert row["p_not_appear"]["1"]["theoretical"] == pytest.approx(36 / 37, abs=1e-6)


def test_prob_not_appearing_horizon_compounds() -> None:
    """P(NAO sair em 10 giros) teorica = (36/37)^10."""
    wheel = get_wheel("european")
    spins = ["7"] * 50
    res = prob_not_appearing(spins, wheel, horizons=(10,))
    expected = (1 - 1 / 37) ** 10
    for row in res["numbers"]:
        assert row["p_not_appear"]["10"]["theoretical"] == pytest.approx(expected, abs=1e-6)


def test_theoretical_appear_probs_sum_to_one() -> None:
    """Soma das p teoricas de aparecer ~ 1 (38 bolsos na americana)."""
    wheel = get_wheel("american")
    spins = ["00"] * 10
    res = prob_not_appearing(spins, wheel, horizons=(1,))
    total = sum(r["p_appear_theoretical"] for r in res["numbers"])
    assert total == pytest.approx(1.0, abs=1e-3)


def test_calibrated_p_uses_laplace() -> None:
    """p calibrada = (obs+1)/(n+pockets): 10 ocorrencias de '5' em 10 giros -> 11/47."""
    wheel = get_wheel("european")
    spins = ["5"] * 10
    res = frequency_ranking(spins, wheel)
    row = next(r for r in res["ranking"] if r["number"] == "5")
    assert row["p_calibrated"] == pytest.approx(11 / 47, abs=1e-5)


def test_frequency_ranking_orders_by_count() -> None:
    """O numero injetado com mais ocorrencias lidera o ranking."""
    wheel = get_wheel("european")
    spins = ["17"] * 5 + [n for n in wheel.order if n != "17"]
    res = frequency_ranking(spins, wheel)
    assert res["ranking"][0]["number"] == "17"
    assert res["most_frequent"][0]["number"] == "17"
    assert res["most_frequent"][0]["count"] == 5
    assert res["least_frequent"][0]["count"] == 1


def test_calibrated_not_appear_reflects_sample() -> None:
    """Numero que nunca saiu tem P(NAO sair) calibrada maior que um que saiu muito."""
    wheel = get_wheel("european")
    spins = ["17"] * 200 + ["5"] * 50  # "0" nunca sai
    res = prob_not_appearing(spins, wheel, horizons=(1,))
    by_num = {r["number"]: r for r in res["numbers"]}
    p_not_hot = by_num["17"]["p_not_appear"]["1"]["calibrated"]
    p_not_absent = by_num["0"]["p_not_appear"]["1"]["calibrated"]
    assert p_not_absent > p_not_hot
