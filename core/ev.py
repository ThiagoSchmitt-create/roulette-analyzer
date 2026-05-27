"""
Calculo de EV (Expected Value) e Kelly criterion.

A logica honesta:
  - Sem vies detectado: EV = -house_edge para QUALQUER aposta. Kelly = 0.
  - Com vies detectado: estima a probabilidade real de um numero e calcula EV+ se houver.

Apostas padrao da roleta e seus payouts:
  straight (numero exato): paga 35:1
  split: 17:1
  street: 11:1
  corner: 8:1
  six-line: 5:1
  dozen/column: 2:1
  red/black/odd/even/high/low: 1:1
"""
from __future__ import annotations
from typing import Dict, List, Sequence

from .wheel import Wheel


PAYOUTS = {
    "straight": 35,
    "split": 17,
    "street": 11,
    "corner": 8,
    "six_line": 5,
    "dozen": 2,
    "column": 2,
    "red": 1, "black": 1, "odd": 1, "even": 1, "high": 1, "low": 1,
}


def house_edge(wheel: Wheel) -> float:
    """House edge teorico: -2.7% europeia, -5.26% americana."""
    return - (wheel.pockets - 36) / wheel.pockets if wheel.pockets > 36 else -1 / wheel.pockets


def calibrated_ev(
    spins: Sequence[str], wheel: Wheel, target_number: str,
) -> Dict:
    """
    EV calibrado para uma aposta STRAIGHT em `target_number` baseado na
    frequencia empirica observada (com correcao de Laplace).
    """
    n = len(spins)
    if n == 0:
        return {"target": target_number, "ev": house_edge(wheel), "note": "sem dados"}
    obs = sum(1 for s in spins if s == target_number)
    # Laplace smoothing: (obs+1) / (n + pockets)
    p_empirical = (obs + 1) / (n + wheel.pockets)
    p_theoretical = wheel.expected_prob
    # EV de aposta straight: p * 35 + (1-p) * (-1) = 36p - 1
    ev_empirical = 36 * p_empirical - 1
    ev_theoretical = 36 * p_theoretical - 1
    return {
        "target": target_number,
        "observed_count": obs,
        "n_spins": n,
        "p_empirical": round(p_empirical, 5),
        "p_theoretical": round(p_theoretical, 5),
        "ev_empirical": round(ev_empirical, 4),
        "ev_theoretical": round(ev_theoretical, 4),
        "edge_pct": round(100 * (ev_empirical - ev_theoretical), 3),
        "playable": bool(ev_empirical > 0),
    }


def kelly_fraction(ev: float, bet_odds: int = 35) -> float:
    """
    Kelly fraction para aposta com payout `bet_odds:1` e EV positivo.
    f* = (b*p - q) / b, onde b = odds, p = prob de vitoria, q = 1-p.
    Retorna 0 se EV <= 0. Limitado a 25% por seguranca (fractional Kelly).
    """
    if ev <= 0:
        return 0.0
    # p tal que EV = (bet_odds+1)*p - 1
    p = (ev + 1) / (bet_odds + 1)
    q = 1 - p
    f = (bet_odds * p - q) / bet_odds
    return max(0.0, min(f, 0.25))  # cap em 25% por seguranca


def evaluate_all_numbers(spins: Sequence[str], wheel: Wheel) -> List[Dict]:
    """Avalia EV de aposta straight para cada numero. Util para descobrir +EV."""
    results = [calibrated_ev(spins, wheel, num) for num in wheel.order]
    return sorted(results, key=lambda r: r["ev_empirical"], reverse=True)
