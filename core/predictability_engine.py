"""
Motor de previsibilidade: mede QUAO previsivel um stream de giros e e de que
TIPO e a estrutura (se houver). Honesto por construcao:

  - stream aleatorio  -> score ~0, dominante 'sem_padrao' (e isso e o acerto)
  - estrutura real    -> detecta e quantifica o tipo

NAO preve o proximo numero. Mede previsibilidade; nao a inventa. Cada detector
usa um teste com hipotese nula propria (analitica ou por permutacao), entao
"detectado" significa significancia estatistica, nao ruido.

Detectores:
  vies_uniforme      -> qui-quadrado GoF vs uniforme (Cramer V)
  dependencia_serial -> informacao mutua lag-1 + teste de permutacao (z-score)
  periodicidade      -> pico de autocorrelacao (lags 2..L) + permutacao (z-score)
  drift              -> qui-quadrado 2-amostras (1a vs 2a metade) p/ mudanca de regime

predictability_score: max dos efeitos normalizados (cada um ~0 sob a nula), em [0,1].
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy import stats

from .wheel import Wheel

P_STRICT = 0.001  # limiar de significancia (testes analiticos)
Z_STRICT = 3.0    # limiar de z-score (testes de permutacao ~ p<0.001 unilateral)


def _to_idx(spins: Sequence[str], wheel: Wheel) -> np.ndarray:
    pos = wheel.position
    return np.array([pos[s] for s in spins], dtype=int)


def _entropy_bits(counts: np.ndarray) -> float:
    c = np.asarray(counts, dtype=float)
    tot = c.sum()
    if tot == 0:
        return 0.0
    p = c[c > 0] / tot
    return float(-np.sum(p * np.log2(p)))


def _mi_lag1_bits(idx: np.ndarray, pockets: int) -> float:
    """Informacao mutua entre giro e o anterior (categorica)."""
    a, b = idx[:-1], idx[1:]
    joint = np.zeros((pockets, pockets))
    np.add.at(joint, (a, b), 1.0)
    tot = joint.sum()
    if tot == 0:
        return 0.0
    joint /= tot
    pa = joint.sum(1)
    pb = joint.sum(0)
    nz = joint > 0
    outer = np.outer(pa, pb)
    return float(np.sum(joint[nz] * np.log2(joint[nz] / outer[nz])))


def _max_abs_acf(idx: np.ndarray, lags: list[int]) -> tuple[float, int]:
    x = idx.astype(float)
    x = x - x.mean()
    denom = float(np.dot(x, x))
    if denom == 0:
        return 0.0, 0
    best, best_lag = 0.0, 0
    for k in lags:
        r = float(np.dot(x[:-k], x[k:])) / denom
        if abs(r) > abs(best):
            best, best_lag = r, k
    return best, best_lag


# ----------------------------------------------------------------------
# Detectores
# ----------------------------------------------------------------------

def uniform_bias(spins: Sequence[str], wheel: Wheel) -> dict:
    """Vies marginal: alguns numeros saem mais que o esperado (qui-quadrado GoF)."""
    n = len(spins)
    p_pockets = wheel.pockets
    counts = np.bincount(_to_idx(spins, wheel), minlength=p_pockets)
    chi2, p = stats.chisquare(counts)
    v = float(np.sqrt(chi2 / (n * (p_pockets - 1)))) if n > 0 else 0.0
    effect = max(0.0, v - (1.0 / np.sqrt(n) if n > 0 else 0.0))
    return {
        "test": "vies_uniforme",
        "chi2": round(float(chi2), 3),
        "dof": p_pockets - 1,
        "p_value": round(float(p), 6),
        "cramers_v": round(v, 4),
        "effect": round(min(effect, 1.0), 4),
        "detected": bool(p < P_STRICT),
    }


def serial_dependence(
    spins: Sequence[str], wheel: Wheel, seed: int = 42, n_perm: int = 200,
) -> dict:
    """Dependencia serial lag-1 via informacao mutua + teste de permutacao."""
    idx = _to_idx(spins, wheel)
    n = len(idx)
    if n < 200:
        return {"test": "dependencia_serial", "skipped": True, "reason": "amostra <200"}
    obs = _mi_lag1_bits(idx, wheel.pockets)
    rng = np.random.default_rng(seed)
    null = np.array([_mi_lag1_bits(rng.permutation(idx), wheel.pockets) for _ in range(n_perm)])
    mu = float(null.mean())
    sd = float(null.std(ddof=1)) or 1e-12
    z = (obs - mu) / sd
    emp_p = (int(np.sum(null >= obs)) + 1) / (n_perm + 1)
    h = _entropy_bits(np.bincount(idx, minlength=wheel.pockets))
    effect = max(0.0, obs - mu) / h if h > 0 else 0.0
    return {
        "test": "dependencia_serial",
        "mi_bits": round(obs, 4),
        "mi_null_mean": round(mu, 4),
        "z": round(float(z), 2),
        "p_value": round(float(emp_p), 4),
        "effect": round(min(effect, 1.0), 4),
        "detected": bool(z > Z_STRICT),
    }


def periodicity(
    spins: Sequence[str], wheel: Wheel, seed: int = 42, n_perm: int = 200, max_lag: int = 20,
) -> dict:
    """Periodicidade: pico de autocorrelacao em lags 2..L + teste de permutacao."""
    idx = _to_idx(spins, wheel)
    n = len(idx)
    lags = list(range(2, min(max_lag, n // 4) + 1))
    if n < 200 or len(lags) < 2:
        return {"test": "periodicidade", "skipped": True, "reason": "amostra pequena"}
    obs, best_lag = _max_abs_acf(idx, lags)
    obs_abs = abs(obs)
    rng = np.random.default_rng(seed + 1)
    null = np.array([abs(_max_abs_acf(rng.permutation(idx), lags)[0]) for _ in range(n_perm)])
    mu = float(null.mean())
    sd = float(null.std(ddof=1)) or 1e-12
    z = (obs_abs - mu) / sd
    emp_p = (int(np.sum(null >= obs_abs)) + 1) / (n_perm + 1)
    effect = max(0.0, obs_abs - mu)
    return {
        "test": "periodicidade",
        "best_lag": best_lag,
        "acf_peak": round(obs, 4),
        "acf_null_mean": round(mu, 4),
        "z": round(float(z), 2),
        "p_value": round(float(emp_p), 4),
        "effect": round(min(effect, 1.0), 4),
        "detected": bool(z > Z_STRICT),
    }


def drift_change(spins: Sequence[str], wheel: Wheel) -> dict:
    """Mudanca de regime: distribuicao da 1a metade difere da 2a (qui-quadrado 2-amostras)."""
    idx = _to_idx(spins, wheel)
    n = len(idx)
    if n < 200:
        return {"test": "drift", "skipped": True, "reason": "amostra <200"}
    h = n // 2
    c1 = np.bincount(idx[:h], minlength=wheel.pockets)
    c2 = np.bincount(idx[h:], minlength=wheel.pockets)
    table = np.vstack([c1, c2]).astype(float)
    table = table[:, table.sum(0) > 0]
    chi2, p, dof, _ = stats.chi2_contingency(table)
    v = float(np.sqrt(chi2 / n))
    effect = max(0.0, v - np.sqrt((wheel.pockets - 1) / n))
    return {
        "test": "drift",
        "chi2": round(float(chi2), 3),
        "dof": int(dof),
        "p_value": round(float(p), 6),
        "cramers_v": round(v, 4),
        "effect": round(min(effect, 1.0), 4),
        "detected": bool(p < P_STRICT),
    }


# ----------------------------------------------------------------------
# Orquestrador
# ----------------------------------------------------------------------

def _verdict(dominant: str, score: float, detected: list[str], n: int) -> str:
    if dominant == "sem_padrao":
        return (
            f"Com {n} giros, nenhuma estrutura significativa (score {score:.3f}). "
            "Stream parece aleatorio: nada a prever. Mais dados so confirmam isso."
        )
    return (
        f"Estrutura detectada com {n} giros: {', '.join(detected)} "
        f"(dominante: {dominant}, score {score:.3f}). Isto mede a previsibilidade da "
        "estrutura - NAO garante adivinhar o proximo giro."
    )


def analyze_predictability(
    spins: Sequence[str], wheel: Wheel, seed: int = 42, n_perm: int = 200,
) -> dict:
    """Orquestra os detectores, compoe o score e classifica o padrao dominante."""
    tests = {
        "vies_uniforme": uniform_bias(spins, wheel),
        "dependencia_serial": serial_dependence(spins, wheel, seed, n_perm),
        "periodicidade": periodicity(spins, wheel, seed, n_perm),
        "drift": drift_change(spins, wheel),
    }
    effects = {k: float(t.get("effect", 0.0)) for k, t in tests.items()}
    detected = {k: effects[k] for k, t in tests.items() if t.get("detected")}
    score = float(min(max(effects.values(), default=0.0), 1.0))
    dominant = max(detected, key=detected.get) if detected else "sem_padrao"
    return {
        "n_spins": len(spins),
        "wheel": wheel.name,
        "predictability_score": round(score, 4),
        "dominant_pattern": dominant,
        "patterns_detected": list(detected.keys()),
        "tests": tests,
        "verdict": _verdict(dominant, score, list(detected.keys()), len(spins)),
    }


def rolling_structure(
    spins: Sequence[str], wheel: Wheel, window: int = 1000, step: int = 250,
) -> list[dict]:
    """
    Indicador RAPIDO de estrutura em janela deslizante (sem permutacao), para a
    visao temporal/dinamica. Por janela devolve vies (Cramer V debiasado) e
    dependencia serial (informacao mutua lag-1 debiasada). Uma subida ao longo do
    tempo evidencia drift/estrutura emergindo.
    """
    idx = _to_idx(spins, wheel)
    n = len(idx)
    pockets = wheel.pockets
    window = min(window, n)
    if window < 100:
        return []
    h_uniform = float(np.log2(pockets))
    mi_null = (pockets - 1) ** 2 / (2 * window * np.log(2))  # vies do estimador sob independencia
    rows: list[dict] = []
    for end in range(window, n + 1, step):
        w = idx[end - window:end]
        counts = np.bincount(w, minlength=pockets)
        chi2, _ = stats.chisquare(counts)
        v = float(np.sqrt(chi2 / (window * (pockets - 1))))
        bias = max(0.0, v - 1.0 / np.sqrt(window))
        mi = _mi_lag1_bits(w, pockets)
        serial = max(0.0, mi - mi_null) / h_uniform if h_uniform > 0 else 0.0
        rows.append({"end_index": int(end), "bias": round(bias, 4), "serial": round(serial, 4)})
    return rows
