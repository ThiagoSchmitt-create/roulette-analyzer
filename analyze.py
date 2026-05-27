#!/usr/bin/env python3
"""
CLI: analise uma sequencia de giros de roleta e produza um relatorio honesto.

Uso:
  python analyze.py --input spins.csv --wheel european
  python analyze.py --input spins.csv --wheel american --json out.json
  python analyze.py --demo unbiased
  python analyze.py --demo biased

CSV deve ter uma coluna 'number' (0-36, '00' permitido para americana).
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

from core.wheel import get_wheel
from core.bias import detect_bias
from core.strategies import compare_all_strategies
from core.report import build_report


def load_csv(path: Path) -> list[str]:
    spins: list[str] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        if "number" not in (reader.fieldnames or []):
            raise SystemExit("CSV deve ter coluna 'number'")
        for row in reader:
            spins.append(str(row["number"]).strip())
    return spins


def generate_demo(kind: str, wheel_name: str, n: int = 5000) -> list[str]:
    """Gera amostra sintetica para testar o pipeline."""
    import numpy as np
    from core.wheel import get_wheel
    wheel = get_wheel(wheel_name)
    rng = np.random.default_rng(2024)
    if kind == "unbiased":
        idx = rng.integers(0, wheel.pockets, size=n)
        return [wheel.order[i] for i in idx]
    elif kind == "biased":
        # injeta vies leve em um setor (5 numeros adjacentes na roda)
        probs = np.full(wheel.pockets, 1.0)
        bias_center = wheel.position[wheel.order[5]]
        for k in range(-2, 3):
            probs[(bias_center + k) % wheel.pockets] *= 1.35
        probs /= probs.sum()
        idx = rng.choice(wheel.pockets, size=n, p=probs)
        return [wheel.order[i] for i in idx]
    else:
        raise SystemExit(f"demo desconhecido: {kind}")


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--input", type=Path, help="CSV com coluna 'number'")
    g.add_argument("--demo", choices=["unbiased", "biased"], help="usar dados sinteticos")
    p.add_argument("--wheel", default="european", choices=["european", "american"])
    p.add_argument("--demo-n", type=int, default=5000)
    p.add_argument("--json", type=Path, help="salvar resultado completo em JSON")
    p.add_argument("--no-sim", action="store_true", help="pular simulacao de estrategias")
    args = p.parse_args()

    wheel = get_wheel(args.wheel)
    if args.demo:
        spins = generate_demo(args.demo, args.wheel, n=args.demo_n)
        print(f"[demo] gerados {len(spins)} giros sinteticos ({args.demo})\n", file=sys.stderr)
    else:
        spins = load_csv(args.input)

    wheel.validate_spins(spins)
    bias_result = detect_bias(spins, wheel)

    sim_result = None
    if not args.no_sim:
        sim_result = compare_all_strategies(
            wheel,
            starting_bankroll=1000,
            base_bet=10,
            n_spins=100,
            n_sessions=1000,
        )

    print(build_report(bias_result, sim_result))

    if args.json:
        out = {"bias_analysis": bias_result, "strategies": sim_result}
        args.json.write_text(json.dumps(out, indent=2, default=str))
        print(f"\n[ok] resultado completo salvo em {args.json}", file=sys.stderr)


if __name__ == "__main__":
    main()
