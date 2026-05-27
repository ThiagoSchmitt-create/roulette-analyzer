"""
Simulacao Monte Carlo de estrategias classicas de roleta.

OBJETIVO: mostrar empiricamente que estrategias tipo Martingale/Fibonacci
NAO superam o house edge — apenas reformatam a distribuicao de retornos
(menos perdas pequenas, raras perdas catastroficas).

Estrategias:
  - flat: aposta fixa
  - martingale: dobra apos perda
  - fibonacci: avanca/recua na sequencia
  - dalembert: +1 apos perda, -1 apos ganho
  - paroli: dobra apos ganho (anti-martingale)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List

import numpy as np

from .wheel import Wheel, color_of


@dataclass
class SimResult:
    strategy: str
    n_sessions: int
    n_spins_per_session: int
    final_bankrolls: List[float]
    mean_final: float
    median_final: float
    p_ruin: float                 # prob de zerar o bankroll
    p_profit: float               # prob de terminar acima
    worst: float
    best: float


def _spin(wheel: Wheel, rng: np.random.Generator) -> str:
    return wheel.order[rng.integers(0, wheel.pockets)]


def _flat(bankroll: float, base: float, last_won: bool, state) -> float:
    return base


def _martingale(bankroll: float, base: float, last_won: bool, state) -> float:
    if last_won or state.get("current") is None:
        state["current"] = base
    else:
        state["current"] = min(state["current"] * 2, bankroll)
    return state["current"]


def _fibonacci(bankroll: float, base: float, last_won: bool, state) -> float:
    if "fib" not in state:
        state["fib"] = [base, base]
        state["idx"] = 0
    if last_won:
        state["idx"] = max(0, state["idx"] - 2)
    else:
        state["idx"] = state["idx"] + 1
        while state["idx"] >= len(state["fib"]):
            state["fib"].append(state["fib"][-1] + state["fib"][-2])
    return min(state["fib"][state["idx"]], bankroll)


def _dalembert(bankroll: float, base: float, last_won: bool, state) -> float:
    cur = state.get("current", base)
    if last_won:
        cur = max(base, cur - base)
    else:
        cur = cur + base
    state["current"] = min(cur, bankroll)
    return state["current"]


def _paroli(bankroll: float, base: float, last_won: bool, state) -> float:
    streak = state.get("streak", 0)
    if last_won:
        streak += 1
    else:
        streak = 0
    if streak >= 3:
        streak = 0  # reseta apos 3 vitorias
    state["streak"] = streak
    return min(base * (2 ** streak), bankroll)


STRATEGIES: Dict[str, Callable] = {
    "flat": _flat,
    "martingale": _martingale,
    "fibonacci": _fibonacci,
    "dalembert": _dalembert,
    "paroli": _paroli,
}


def simulate_strategy(
    wheel: Wheel,
    strategy: str = "flat",
    bet_type: str = "red",
    starting_bankroll: float = 1000,
    base_bet: float = 10,
    n_spins: int = 100,
    n_sessions: int = 1000,
    seed: int = 42,
) -> SimResult:
    """
    Roda Monte Carlo: `n_sessions` sessoes de `n_spins` cada.

    bet_type: 'red', 'black', 'odd', 'even', 'high', 'low' (todos pagam 1:1)
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"Estrategia desconhecida: {strategy}")
    stake_fn = STRATEGIES[strategy]
    rng = np.random.default_rng(seed)
    finals: List[float] = []
    ruins = 0
    profits = 0

    for _ in range(n_sessions):
        bankroll = starting_bankroll
        last_won = True
        state: Dict = {}
        for _ in range(n_spins):
            if bankroll <= 0:
                break
            stake = stake_fn(bankroll, base_bet, last_won, state)
            stake = min(stake, bankroll)
            result = _spin(wheel, rng)
            won = _is_winner(result, bet_type)
            bankroll += stake if won else -stake
            last_won = won
        finals.append(bankroll)
        if bankroll <= 0:
            ruins += 1
        if bankroll > starting_bankroll:
            profits += 1

    return SimResult(
        strategy=strategy,
        n_sessions=n_sessions,
        n_spins_per_session=n_spins,
        final_bankrolls=finals,
        mean_final=float(np.mean(finals)),
        median_final=float(np.median(finals)),
        p_ruin=ruins / n_sessions,
        p_profit=profits / n_sessions,
        worst=float(np.min(finals)),
        best=float(np.max(finals)),
    )


def _is_winner(num: str, bet_type: str) -> bool:
    c = color_of(num)
    if bet_type in ("red", "black"):
        return c == bet_type
    if num in ("0", "00"):
        return False
    n = int(num)
    if bet_type == "odd":
        return n % 2 == 1
    if bet_type == "even":
        return n % 2 == 0 and n != 0
    if bet_type == "high":
        return 19 <= n <= 36
    if bet_type == "low":
        return 1 <= n <= 18
    raise ValueError(f"bet_type desconhecido: {bet_type}")


def compare_all_strategies(
    wheel: Wheel,
    starting_bankroll: float = 1000,
    base_bet: float = 10,
    n_spins: int = 100,
    n_sessions: int = 1000,
) -> Dict:
    """Compara todas as estrategias com os mesmos parametros."""
    out = {}
    for s in STRATEGIES:
        r = simulate_strategy(
            wheel, strategy=s,
            starting_bankroll=starting_bankroll,
            base_bet=base_bet,
            n_spins=n_spins,
            n_sessions=n_sessions,
        )
        out[s] = {
            "mean_final": round(r.mean_final, 2),
            "median_final": round(r.median_final, 2),
            "p_ruin": round(r.p_ruin, 4),
            "p_profit": round(r.p_profit, 4),
            "expected_house_edge_loss": round(
                starting_bankroll
                + base_bet * n_spins * (-1 / wheel.pockets if wheel.pockets == 37 else -2 / wheel.pockets),
                2,
            ),
        }
    return out
