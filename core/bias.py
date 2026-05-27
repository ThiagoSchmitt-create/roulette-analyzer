"""Logica de decisao de vies a partir da bateria de testes."""
from __future__ import annotations
from math import ceil
from typing import Dict, Sequence

from scipy import stats

from .wheel import Wheel
from .stats import run_all_tests


def required_sample_size(wheel, effect_size=0.02, alpha=0.05, power=0.80):
    df = wheel.pockets - 1
    crit = stats.chi2.ppf(1 - alpha, df)
    ncp_needed = stats.ncx2.ppf(1 - power, df, 0) + crit
    w2 = (effect_size ** 2) / wheel.expected_prob
    n = ncp_needed / w2 if w2 > 0 else 1e9
    return max(int(ceil(n)), 1000)


def detect_bias(spins, wheel):
    results = run_all_tests(spins, wheel)
    tests = results["tests"]
    flags = []
    if tests["numbers"]["reject_h0_at_5pct"]:
        flags.append(("numbers_uniform_rejected", tests["numbers"]["p_value"]))
    if tests["sectors"]["reject_h0_at_5pct"]:
        flags.append(("sector_uniform_rejected", tests["sectors"]["p_value"]))
    if tests["color"]["reject_h0_at_5pct"]:
        flags.append(("color_balance_rejected", tests["color"]["p_value"]))
    if tests["runs"].get("reject_h0_at_5pct"):
        flags.append(("runs_independence_rejected", tests["runs"]["p_value"]))
    if tests["autocorr"].get("reject_h0_at_5pct"):
        flags.append(("autocorrelation_detected", tests["autocorr"]["p_value"]))

    n = len(spins)
    needed = required_sample_size(wheel)
    strong_evidence = any(p < 0.001 for _, p in flags)

    if n < 1000:
        confidence = "muito_baixa"
        verdict = "amostra_insuficiente"
    elif strong_evidence and n >= 3000:
        confidence = "alta"
        verdict = "vies_provavel"
    elif n < needed:
        confidence = "moderada"
        verdict = "inconclusivo" if not flags else "indicio_fraco"
    else:
        confidence = "alta"
        verdict = "sem_vies_detectado" if not flags else "vies_provavel"

    return {
        "n_spins": n,
        "sample_size_recommended": needed,
        "confidence": confidence,
        "verdict": verdict,
        "flags": flags,
        "honest_summary": _summarize(verdict, flags, n, needed),
        "full_tests": results,
    }


def _summarize(verdict, flags, n, needed):
    if verdict == "amostra_insuficiente":
        return f"Voce tem {n} giros. Recomendado: pelo menos {needed} para conclusao. Continue coletando."
    if verdict == "sem_vies_detectado":
        return f"Com {n} giros, nenhum teste rejeitou aleatoriedade. EV de qualquer aposta = -2.7%/-5.26%. NAO JOGUE."
    if verdict == "inconclusivo":
        return f"Com {n} giros, sem rejeicao. Coletar ate {needed} para confianca alta."
    if verdict == "indicio_fraco":
        return f"Com {n} giros, {len(flags)} sinal(is) de vies mas amostra abaixo de {needed}. Pode ser variancia."
    if verdict == "vies_provavel":
        return (f"Com {n} giros, {len(flags)} teste(s) rejeitaram aleatoriedade com p<0.001. "
                f"Veja top_hot e hot_sectors. AVISO: cassinos monitoram e corrigem vies.")
    return verdict
