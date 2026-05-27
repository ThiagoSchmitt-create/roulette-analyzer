"""
Validacao cruzada dos testes estatisticos hand-rolled em core/stats.py contra
as implementacoes de referencia do statsmodels.

Garante que o Ljung-Box e o runs test feitos a mao produzem os mesmos numeros
que a biblioteca de referencia. Pulado automaticamente se statsmodels nao
estiver instalado (instalacao sem o extra [dev]).
"""
from __future__ import annotations

import numpy as np
import pytest

from core.stats import autocorrelation, runs_test_color
from core.wheel import color_of

pytest.importorskip("statsmodels")


def _european_spins(n: int, seed: int) -> list[str]:
    rng = np.random.default_rng(seed)
    return [str(int(x)) for x in rng.integers(0, 37, size=n)]


def test_ljung_box_matches_statsmodels() -> None:
    """O Q e o p-value do Ljung-Box hand-rolled batem com statsmodels."""
    from statsmodels.stats.diagnostic import acorr_ljungbox

    spins = _european_spins(2000, seed=42)
    core_res = autocorrelation(spins, max_lag=10)
    assert not core_res.get("skipped"), core_res

    # mesma serie que core usa internamente (00 -> -1; aqui nao ha 00)
    series = np.array([(-1 if s == "00" else int(s)) for s in spins], dtype=float)
    ref = acorr_ljungbox(series, lags=[10])
    q_ref = float(ref["lb_stat"].iloc[-1])
    p_ref = float(ref["lb_pvalue"].iloc[-1])

    assert core_res["ljung_box_Q"] == pytest.approx(q_ref, rel=1e-4)
    assert core_res["p_value"] == pytest.approx(p_ref, rel=1e-4, abs=1e-9)


def test_runs_test_matches_statsmodels() -> None:
    """O z e o p-value do runs test (Wald-Wolfowitz) hand-rolled batem com statsmodels."""
    from statsmodels.sandbox.stats.runs import runstest_1samp

    spins = _european_spins(3000, seed=7)
    core_res = runs_test_color(spins)
    assert not core_res.get("skipped"), core_res

    # mesma binarizacao que core usa: vermelho=1, preto=0, descarta verdes
    binary = np.array(
        [1.0 if color_of(s) == "red" else 0.0 for s in spins if color_of(s) != "green"]
    )
    # correction=False para casar com a formula sem correcao de continuidade do core
    z_ref, p_ref = runstest_1samp(binary, cutoff=0.5, correction=False)

    # core arredonda o z para 3 casas (round(z, 3)), entao a tolerancia e ~1e-3;
    # abs() protege contra eventual diferenca de convencao de sinal
    assert abs(core_res["z_score"]) == pytest.approx(abs(float(z_ref)), abs=1e-3)
    # core arredonda o p para 6 casas
    assert core_res["p_value"] == pytest.approx(float(p_ref), abs=1e-6)
