"""
Bateria de testes de aleatoriedade para sequencias de giros de roleta.

Inclui:
  - Chi-square goodness-of-fit (por numero, cor, duzia, coluna, alto/baixo, setor)
  - Runs test (Wald-Wolfowitz)  — testa independencia em sequencia binarizada
  - Autocorrelacao em lag 1..k  — detecta dependencia serial
  - Z-score por numero          — destaca outliers individuais
  - Frequencia de gaps           — distancia entre repeticoes

Todas as funcoes retornam dict serializavel (para JSON / relatorio).

Referencias:
  - NIST SP 800-22 (Statistical Test Suite for RNGs)
  - Wald & Wolfowitz (1940), "On a test whether two samples are from the same population"
  - Pearson chi-square (1900)
"""
from __future__ import annotations
from collections import Counter
from math import sqrt
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy import stats

from .wheel import Wheel, color_of


# ----------------------------------------------------------------------
# Chi-square goodness-of-fit
# ----------------------------------------------------------------------

def chi_square_numbers(spins: Sequence[str], wheel: Wheel) -> Dict:
    """H0: cada numero tem probabilidade 1/N. Rejeita -> roda enviesada."""
    n = len(spins)
    observed = Counter(spins)
    expected = n / wheel.pockets
    obs_arr = np.array([observed.get(num, 0) for num in wheel.order])
    exp_arr = np.full(wheel.pockets, expected)
    chi2, p = stats.chisquare(f_obs=obs_arr, f_exp=exp_arr)
    dof = wheel.pockets - 1
    return {
        "test": "chi_square_numbers",
        "h0": f"distribuicao uniforme sobre {wheel.pockets} numeros",
        "n_spins": n,
        "expected_per_number": round(expected, 3),
        "chi2": round(float(chi2), 3),
        "dof": dof,
        "p_value": round(float(p), 6),
        "reject_h0_at_5pct": bool(p < 0.05),
        "reject_h0_at_1pct": bool(p < 0.01),
    }


def chi_square_color(spins: Sequence[str], wheel: Wheel) -> Dict:
    """H0: P(red) = P(black) = 18/N, P(green) = (1 ou 2)/N."""
    n = len(spins)
    obs = Counter(color_of(s) for s in spins)
    # probabilidades teoricas
    p_red = 18 / wheel.pockets
    p_black = 18 / wheel.pockets
    p_green = 1 - p_red - p_black
    obs_arr = np.array([obs.get("red", 0), obs.get("black", 0), obs.get("green", 0)])
    exp_arr = np.array([n * p_red, n * p_black, n * p_green])
    chi2, p = stats.chisquare(f_obs=obs_arr, f_exp=exp_arr)
    return {
        "test": "chi_square_color",
        "h0": "probabilidades teoricas de vermelho/preto/verde",
        "observed": {"red": int(obs_arr[0]), "black": int(obs_arr[1]), "green": int(obs_arr[2])},
        "expected": {"red": round(exp_arr[0], 1), "black": round(exp_arr[1], 1), "green": round(exp_arr[2], 1)},
        "chi2": round(float(chi2), 3),
        "p_value": round(float(p), 6),
        "reject_h0_at_5pct": bool(p < 0.05),
    }


def chi_square_sectors(spins: Sequence[str], wheel: Wheel, sector_size: int = 5) -> Dict:
    """
    Vies por SETOR: agrupa numeros vizinhos na roda fisica.
    Sensivel a deformacoes localizadas (ex.: um lado da roda desgastado).
    """
    if sector_size % 2 == 0:
        raise ValueError("sector_size deve ser impar para centralizar")
    n = len(spins)
    # Para cada giro, em quantos setores ele cai? Em `sector_size` setores
    # (ja que cada numero pertence a `sector_size` janelas centradas em diferentes pos).
    # Atribuimos cada giro a UM unico setor: o centrado nele.
    # Mais simples e didatico: contamos quantos giros caem na vizinhanca de cada centro.
    sector_counts = np.zeros(wheel.pockets)
    pos = wheel.position
    half = sector_size // 2
    for s in spins:
        # incrementa em cada centro cuja janela contem `s`
        idx = pos[s]
        for k in range(-half, half + 1):
            sector_counts[(idx + k) % wheel.pockets] += 1
    expected_per_sector = (n * sector_size) / wheel.pockets
    chi2, p = stats.chisquare(
        f_obs=sector_counts,
        f_exp=np.full(wheel.pockets, expected_per_sector),
    )
    # destaca top 3 setores acima do esperado
    z_scores = (sector_counts - expected_per_sector) / sqrt(
        expected_per_sector * (1 - 1 / wheel.pockets)
    )
    top_indices = np.argsort(z_scores)[-3:][::-1]
    hot_sectors = [
        {
            "center": wheel.order[i],
            "members": wheel.sector(wheel.order[i], sector_size),
            "count": int(sector_counts[i]),
            "expected": round(expected_per_sector, 1),
            "z_score": round(float(z_scores[i]), 3),
        }
        for i in top_indices
    ]
    return {
        "test": "chi_square_sectors",
        "h0": f"uniformidade sobre setores de {sector_size} numeros adjacentes na roda",
        "sector_size": sector_size,
        "chi2": round(float(chi2), 3),
        "p_value": round(float(p), 6),
        "reject_h0_at_5pct": bool(p < 0.05),
        "hot_sectors": hot_sectors,
    }


# ----------------------------------------------------------------------
# Runs test (Wald-Wolfowitz)
# ----------------------------------------------------------------------

def runs_test_color(spins: Sequence[str]) -> Dict:
    """
    Binariza em vermelho=1 / preto=0 (ignora verdes) e testa se o numero de runs
    e compativel com uma sequencia independente.
    """
    binary = [1 if color_of(s) == "red" else 0 for s in spins if color_of(s) != "green"]
    n = len(binary)
    if n < 30:
        return {
            "test": "runs_test_color",
            "skipped": True,
            "reason": "amostra binaria menor que 30 apos remover verdes",
        }
    n1 = sum(binary)
    n0 = n - n1
    # numero observado de runs
    runs = 1 + sum(1 for i in range(1, n) if binary[i] != binary[i - 1])
    # media e variancia teorica sob H0 (independencia)
    mu = 1 + (2 * n1 * n0) / n
    var = (2 * n1 * n0 * (2 * n1 * n0 - n)) / (n * n * (n - 1))
    z = (runs - mu) / sqrt(var) if var > 0 else 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {
        "test": "runs_test_color",
        "h0": "sequencia de cores e independente (sem clusters/alternancia anormal)",
        "n_binary": n,
        "runs_observed": runs,
        "runs_expected": round(mu, 2),
        "z_score": round(z, 3),
        "p_value": round(p, 6),
        "reject_h0_at_5pct": bool(p < 0.05),
    }


# ----------------------------------------------------------------------
# Autocorrelacao (Ljung-Box / serial dependence)
# ----------------------------------------------------------------------

def autocorrelation(spins: Sequence[str], max_lag: int = 10) -> Dict:
    """
    Calcula autocorrelacao da serie de numeros (tratados como inteiros) em
    varios lags. Sob H0 (independencia), todos devem ser ~0.

    Faz o teste de Ljung-Box: H0 = nao ha autocorrelacao ate `max_lag`.
    """
    # converte 00 -> -1 para facilitar
    series = np.array([(-1 if s == "00" else int(s)) for s in spins], dtype=float)
    n = len(series)
    if n < max_lag * 4:
        return {
            "test": "autocorrelation",
            "skipped": True,
            "reason": f"amostra muito pequena para lag {max_lag}",
        }
    series = series - series.mean()
    denom = float(np.sum(series ** 2))
    if denom == 0:
        return {"test": "autocorrelation", "skipped": True, "reason": "serie constante"}
    acf = []
    for lag in range(1, max_lag + 1):
        num = float(np.sum(series[:-lag] * series[lag:]))
        acf.append(num / denom)
    # Ljung-Box Q
    q = n * (n + 2) * sum((r ** 2) / (n - k - 1) for k, r in enumerate(acf))
    p = 1 - stats.chi2.cdf(q, df=max_lag)
    return {
        "test": "autocorrelation_ljung_box",
        "h0": f"sem autocorrelacao serial ate lag {max_lag}",
        "max_lag": max_lag,
        "acf": [round(x, 4) for x in acf],
        "ljung_box_Q": round(float(q), 3),
        "p_value": round(float(p), 6),
        "reject_h0_at_5pct": bool(p < 0.05),
    }


# ----------------------------------------------------------------------
# Z-score por numero
# ----------------------------------------------------------------------

def z_scores_per_number(spins: Sequence[str], wheel: Wheel) -> Dict:
    """Z-score binomial para cada numero individualmente."""
    n = len(spins)
    p = wheel.expected_prob
    expected = n * p
    sd = sqrt(n * p * (1 - p))
    observed = Counter(spins)
    rows = []
    for num in wheel.order:
        obs = observed.get(num, 0)
        z = (obs - expected) / sd if sd > 0 else 0.0
        rows.append({"number": num, "count": obs, "expected": round(expected, 2), "z": round(z, 3)})
    # ordena por z decrescente, retorna os 5 mais altos e 5 mais baixos
    rows.sort(key=lambda r: r["z"], reverse=True)
    return {
        "test": "z_scores_per_number",
        "h0": "frequencia ~ Binomial(N, 1/{pockets})".format(pockets=wheel.pockets),
        "top_hot": rows[:5],
        "top_cold": rows[-5:][::-1],
        "max_abs_z": round(max(abs(r["z"]) for r in rows), 3),
        # com 37/38 numeros, esperamos ~|z| > 2.7 em ~1 numero por puro acaso (multiple testing)
        "warning_multiple_testing": (
            "Com {n} numeros, esperamos |z|>2 em ~5% deles ({k:.1f}) por puro acaso. "
            "Para vies real, exigir |z|>3 ou usar Bonferroni."
        ).format(n=wheel.pockets, k=wheel.pockets * 0.05),
    }


# ----------------------------------------------------------------------
# Gaps (distancia entre repeticoes do mesmo numero)
# ----------------------------------------------------------------------

def gap_distribution(spins: Sequence[str], wheel: Wheel) -> Dict:
    """
    Distribuicao de gaps. Sob aleatoriedade, gap segue Geometric(p=1/N),
    media = N. Desvio sistematico sugere dependencia ou vies.
    """
    last_seen: Dict[str, int] = {}
    gaps: List[int] = []
    for i, s in enumerate(spins):
        if s in last_seen:
            gaps.append(i - last_seen[s])
        last_seen[s] = i
    if not gaps:
        return {"test": "gap_distribution", "skipped": True}
    mean_gap = float(np.mean(gaps))
    return {
        "test": "gap_distribution",
        "mean_gap_observed": round(mean_gap, 2),
        "mean_gap_expected": wheel.pockets,
        "min_gap": int(np.min(gaps)),
        "max_gap": int(np.max(gaps)),
        "deviation_pct": round(100 * (mean_gap - wheel.pockets) / wheel.pockets, 2),
    }


# ----------------------------------------------------------------------
# Orquestrador
# ----------------------------------------------------------------------

def run_all_tests(spins: Sequence[str], wheel: Wheel, sector_size: int = 5) -> Dict:
    """Roda toda a bateria e devolve dict consolidado."""
    return {
        "n_spins": len(spins),
        "wheel": wheel.name,
        "tests": {
            "numbers": chi_square_numbers(spins, wheel),
            "color": chi_square_color(spins, wheel),
            "sectors": chi_square_sectors(spins, wheel, sector_size),
            "runs": runs_test_color(spins),
            "autocorr": autocorrelation(spins, max_lag=10),
            "z_scores": z_scores_per_number(spins, wheel),
            "gaps": gap_distribution(spins, wheel),
        },
    }
