"""Testes da analise de matriz de transicao (antecessores/sucessores)."""
from __future__ import annotations

from core.stream_generators import gen_fair, gen_markov
from core.transitions import (
    cond_prob_next,
    predecessors,
    successors,
    transition_counts,
    transition_summary,
)
from core.wheel import get_wheel

WHEEL = get_wheel("european")


def test_fair_no_serial_structure() -> None:
    s = transition_summary(gen_fair(4000, WHEEL, seed=1), WHEEL, n_perm=120)
    assert s["has_serial_structure"] is False


def test_markov_has_serial_structure() -> None:
    s = transition_summary(gen_markov(4000, WHEEL, dependence=0.6, seed=2), WHEEL, n_perm=120)
    assert s["has_serial_structure"] is True


def test_markov_successor_dominant() -> None:
    spins = gen_markov(4000, WHEEL, dependence=0.7, seed=3)
    m = transition_counts(spins, WHEEL)
    mx = max(
        (successors(spins, WHEEL, num, k=1, m=m)["top"] or [{"p_cond": 0.0}])[0]["p_cond"]
        for num in WHEEL.order
    )
    assert mx > 0.4  # com dependence 0.7, o sucessor dominante tem p_cond ~0.7


def test_fair_successor_near_uniform() -> None:
    spins = gen_fair(8000, WHEEL, seed=5)
    m = transition_counts(spins, WHEEL)
    mx = max(
        (successors(spins, WHEEL, num, k=1, m=m)["top"] or [{"p_cond": 0.0}])[0]["p_cond"]
        for num in WHEEL.order
    )
    assert mx < 0.25  # em fair nenhum sucessor domina: top ~ ruido, bem abaixo de estrutura


def test_predecessors_shape() -> None:
    spins = gen_fair(2000, WHEEL, seed=4)
    p = predecessors(spins, WHEEL, "17", k=5)
    assert p["number"] == "17" and "top" in p and p["n_antes"] >= 0


def test_cond_prob_rows_sum_to_one_or_zero() -> None:
    pnext = cond_prob_next(transition_counts(gen_fair(2000, WHEEL, seed=7), WHEEL))
    for sm in pnext.sum(1):
        assert abs(sm - 1.0) < 1e-9 or sm == 0.0
