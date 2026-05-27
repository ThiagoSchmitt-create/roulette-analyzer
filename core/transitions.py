"""
Matriz de transicao (lag-1): para cada numero, seus ANTECESSORES e SUCESSORES,
com probabilidades condicionais P(proximo|atual) e P(anterior|atual).

HONESTIDADE (regra da casa): em roda justa os giros sao i.i.d., entao
P(proximo|atual) ~ 1/N para TODO `atual` -- a matriz fica "plana". Nesse caso os
"top sucessores" de um numero sao apenas RUIDO de amostra, nao padrao. So ha
estrutura sequencial real se um teste de independencia rejeitar (aqui via o teste
de permutacao do motor, robusto a celulas esparsas). Importante: vies MARGINAL
(alguns numeros saem mais no total) NAO e o mesmo que dependencia SERIAL (o
anterior prever o proximo) -- a matriz separa os dois. Nada aqui preve o proximo giro.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .predictability_engine import serial_dependence
from .wheel import Wheel


def transition_counts(spins: Sequence[str], wheel: Wheel) -> np.ndarray:
    """Matriz NxN de contagens lag-1: linha = numero atual, coluna = proximo."""
    pos = wheel.position
    idx = np.array([pos[s] for s in spins], dtype=int)
    n = wheel.pockets
    m = np.zeros((n, n), dtype=int)
    if idx.size >= 2:
        np.add.at(m, (idx[:-1], idx[1:]), 1)
    return m


def cond_prob_next(m: np.ndarray) -> np.ndarray:
    """P(proximo|atual): normaliza cada LINHA (linha sem dados -> zeros)."""
    row = m.sum(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(row > 0, m / row, 0.0)


def successors(
    spins: Sequence[str], wheel: Wheel, number: str, k: int = 5, m: np.ndarray | None = None,
) -> dict:
    """Top-k numeros que mais saem DEPOIS de `number`, com P(proximo|number)."""
    if m is None:
        m = transition_counts(spins, wheel)
    row = m[wheel.position[number]]
    total = int(row.sum())
    top = []
    if total > 0:
        for j in np.argsort(row)[::-1][:k]:
            if row[j] > 0:
                top.append({"numero": wheel.order[j], "count": int(row[j]),
                            "p_cond": round(float(row[j] / total), 4)})
    return {"number": number, "n_depois": total,
            "p_uniforme": round(1 / wheel.pockets, 4), "top": top}


def predecessors(
    spins: Sequence[str], wheel: Wheel, number: str, k: int = 5, m: np.ndarray | None = None,
) -> dict:
    """Top-k numeros que mais saem ANTES de `number`, com P(anterior|number)."""
    if m is None:
        m = transition_counts(spins, wheel)
    col = m[:, wheel.position[number]]
    total = int(col.sum())
    top = []
    if total > 0:
        for i in np.argsort(col)[::-1][:k]:
            if col[i] > 0:
                top.append({"numero": wheel.order[i], "count": int(col[i]),
                            "p_cond": round(float(col[i] / total), 4)})
    return {"number": number, "n_antes": total,
            "p_uniforme": round(1 / wheel.pockets, 4), "top": top}


def transition_summary(
    spins: Sequence[str], wheel: Wheel, seed: int = 42, n_perm: int = 200,
) -> dict:
    """
    Veredito honesto sobre a matriz: existe dependencia serial (o anterior informa
    o proximo)? Usa o teste de permutacao (robusto a matriz esparsa), nao o
    qui-quadrado direto (que e nao-confiavel com poucas contagens por celula).
    """
    m = transition_counts(spins, wheel)
    test = serial_dependence(spins, wheel, seed, n_perm)
    if test.get("skipped"):
        has, verdict = False, "Amostra insuficiente para avaliar a matriz de transicao."
    elif test.get("detected"):
        has = True
        verdict = (f"Dependencia serial DETECTADA (z={test['z']}, MI={test['mi_bits']} bits): "
                   "o numero anterior carrega informacao sobre o proximo.")
    else:
        has = False
        verdict = (f"SEM dependencia serial (z={test['z']}, p={test['p_value']}): o anterior NAO "
                   "informa o proximo. P(proximo|atual) ~ 1/N para todo atual; qualquer "
                   "'top sucessor' e ruido de amostra. (Vies marginal, se houver, e outra coisa.)")
    return {"n_transitions": int(m.sum()), "has_serial_structure": has,
            "independence_test": test, "verdict": verdict}
