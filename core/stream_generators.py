"""
Geradores de streams sinteticos de roleta com TIPOS de padrao conhecidos.

Usados para (a) testar o motor de previsibilidade com ground-truth, e (b)
alimentar o sandbox n8n multi-padrao. Cada gerador retorna list[str] de numeros
no padrao da roda (europeu por default). Seeds fixos (reprodutibilidade).

Tipos:
  fair     -> uniforme i.i.d. (sem padrao; previsibilidade ~0)
  biased   -> alguns bolsos super-representados (vies marginal, estacionario)
  markov   -> dependencia serial lag-1 (proximo depende do atual)
  periodic -> estrutura periodica (copia o valor de `period` giros atras)
  drift    -> mudanca de regime (1a parte justa, 2a parte enviesada)
"""
from __future__ import annotations

import numpy as np

from .wheel import Wheel, get_wheel


def _wheel(wheel: Wheel | None) -> Wheel:
    return wheel or get_wheel("european")


def _to_numbers(idx: np.ndarray, wheel: Wheel) -> list[str]:
    return [wheel.order[i] for i in idx]


def gen_fair(n: int, wheel: Wheel | None = None, seed: int = 42) -> list[str]:
    """Uniforme i.i.d.: nenhum padrao para aprender."""
    wheel = _wheel(wheel)
    rng = np.random.default_rng(seed)
    return _to_numbers(rng.integers(0, wheel.pockets, size=n), wheel)


def gen_biased(
    n: int,
    wheel: Wheel | None = None,
    hot: tuple[str, ...] = ("19", "4", "21", "2", "25"),
    strength: float = 0.25,
    seed: int = 42,
) -> list[str]:
    """Vies marginal: com prob `strength` o giro cai num bolso quente."""
    wheel = _wheel(wheel)
    rng = np.random.default_rng(seed)
    out = rng.integers(0, wheel.pockets, size=n)
    mask = rng.random(n) < strength
    hot_idx = np.array([wheel.position[h] for h in hot])
    out[mask] = hot_idx[rng.integers(0, len(hot_idx), size=int(mask.sum()))]
    return _to_numbers(out, wheel)


def gen_markov(
    n: int, wheel: Wheel | None = None, dependence: float = 0.6, seed: int = 42,
) -> list[str]:
    """Dependencia serial lag-1 CATEGORICA: com prob `dependence`, proximo = sigma(atual).

    sigma e uma permutacao fixa dos bolsos. Isso cria dependencia detectavel por
    informacao mutua (categorica), mas a marginal segue ~uniforme e NAO ha
    correlacao numerica (ACF), separando 'markov' de 'periodicidade'.
    """
    wheel = _wheel(wheel)
    rng = np.random.default_rng(seed)
    p = wheel.pockets
    sigma = rng.permutation(p)
    out = np.empty(n, dtype=int)
    out[0] = int(rng.integers(0, p))
    rnd = rng.random(n)
    unif = rng.integers(0, p, size=n)
    for t in range(1, n):
        out[t] = sigma[out[t - 1]] if rnd[t] < dependence else unif[t]
    return _to_numbers(out, wheel)


def gen_periodic(
    n: int, wheel: Wheel | None = None, period: int = 5, strength: float = 0.6, seed: int = 42,
) -> list[str]:
    """Periodicidade: com prob `strength`, copia o valor de `period` giros atras.

    Cria autocorrelacao no lag `period` SEM mexer na marginal (continua ~uniforme),
    distinguindo periodicidade de vies marginal.
    """
    wheel = _wheel(wheel)
    rng = np.random.default_rng(seed)
    out = rng.integers(0, wheel.pockets, size=n)
    rnd = rng.random(n)
    for t in range(period, n):
        if rnd[t] < strength:
            out[t] = out[t - period]
    return _to_numbers(out, wheel)


def gen_drift(
    n: int, wheel: Wheel | None = None, switch_at: float = 0.5, strength: float = 0.3, seed: int = 42,
) -> list[str]:
    """Mudanca de regime: 1a parte justa, 2a parte enviesada."""
    wheel = _wheel(wheel)
    k = int(n * switch_at)
    first = gen_fair(k, wheel, seed=seed)
    second = gen_biased(n - k, wheel, strength=strength, seed=seed + 1)
    return first + second


GENERATORS = {
    "fair": gen_fair,
    "biased": gen_biased,
    "markov": gen_markov,
    "periodic": gen_periodic,
    "drift": gen_drift,
}
