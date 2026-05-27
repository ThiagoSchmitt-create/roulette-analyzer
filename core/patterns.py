"""
Analise de frequencia e probabilidade de ausencia (NAO sair) por numero.

HONESTIDADE (regra da casa): estas sao estatisticas DESCRITIVAS da amostra e
probabilidades da DISTRIBUICAO. Em roda justa cada giro e i.i.d.: a frequencia
passada NAO torna nenhum numero mais (nem menos) provavel no proximo giro.
Nada aqui preve o proximo numero (ver anti-feature #1 em CLAUDE.md).

Funcoes:
  frequency_ranking  -> quais numeros mais/menos saem (ranking por contagem)
  prob_not_appearing -> P(NAO sair) no proximo giro e no horizonte de N giros
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from math import sqrt

from .wheel import Wheel


def _calibrated_p(obs: int, n: int, pockets: int) -> float:
    """Probabilidade empirica com smoothing de Laplace (igual a core/ev.py)."""
    return (obs + 1) / (n + pockets)


def frequency_ranking(spins: Sequence[str], wheel: Wheel) -> dict:
    """
    Ranking de todos os numeros por frequencia observada (mais -> menos saem).

    Cada linha traz count, esperado, frequencia observada, p calibrada (Laplace)
    e z-score binomial. NAO e ordem de probabilidade do proximo giro.
    """
    n = len(spins)
    counts = Counter(spins)
    p_theoretical = wheel.expected_prob
    expected = n * p_theoretical
    sd = sqrt(n * p_theoretical * (1 - p_theoretical)) if n > 0 else 0.0

    rows: list[dict] = []
    for num in wheel.order:
        obs = counts.get(num, 0)
        rows.append({
            "number": num,
            "count": obs,
            "expected": round(expected, 2),
            "freq_observed": round(obs / n, 5) if n > 0 else 0.0,
            "p_calibrated": round(_calibrated_p(obs, n, wheel.pockets), 5),
            "z": round((obs - expected) / sd, 3) if sd > 0 else 0.0,
        })
    rows.sort(key=lambda r: r["count"], reverse=True)

    return {
        "n_spins": n,
        "wheel": wheel.name,
        "p_theoretical": round(p_theoretical, 5),
        "ranking": rows,
        "most_frequent": rows[:5],
        "least_frequent": rows[-5:][::-1],
    }


def prob_not_appearing(
    spins: Sequence[str], wheel: Wheel, horizons: Sequence[int] = (1, 5, 10, 37),
) -> dict:
    """
    Para cada numero, P(NAO sair) em cada horizonte N de giros futuros.

    Sob independencia (H0): P(nao sair em N giros) = (1 - p)^N.
      - theoretical: p = 1/pockets
      - calibrated : p = p_empirical com Laplace (reflete a amostra, mas NAO
                     implica que o passado preve o futuro em roda justa)
    """
    n = len(spins)
    counts = Counter(spins)
    p_theo = wheel.expected_prob

    numbers: list[dict] = []
    for num in wheel.order:
        obs = counts.get(num, 0)
        p_cal = _calibrated_p(obs, n, wheel.pockets)
        per_horizon = {
            str(h): {
                "theoretical": round((1 - p_theo) ** h, 6),
                "calibrated": round((1 - p_cal) ** h, 6),
            }
            for h in horizons
        }
        numbers.append({
            "number": num,
            "count": obs,
            "p_appear_theoretical": round(p_theo, 5),
            "p_appear_calibrated": round(p_cal, 5),
            "p_not_appear": per_horizon,
        })

    return {
        "n_spins": n,
        "wheel": wheel.name,
        "horizons": list(horizons),
        "numbers": numbers,
        "note": (
            "P(nao sair em N giros) = (1-p)^N sob independencia. "
            "Frequencia passada NAO altera o proximo giro em roda justa."
        ),
    }
