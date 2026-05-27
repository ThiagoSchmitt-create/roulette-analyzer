"""
Constroi relatorio textual humano-legivel a partir dos resultados.
"""
from __future__ import annotations
from typing import Dict


def build_report(bias_result: Dict, sim_result: Dict | None = None) -> str:
    """Recebe saida de detect_bias() (e opcional compare_all_strategies)."""
    t = bias_result["full_tests"]["tests"]
    lines = []
    lines.append("=" * 72)
    lines.append(" RELATORIO DE ANALISE DE ROLETA")
    lines.append("=" * 72)
    lines.append(f"Roda          : {bias_result['full_tests']['wheel']}")
    lines.append(f"Giros         : {bias_result['n_spins']}")
    lines.append(f"Recomendado   : {bias_result['sample_size_recommended']}")
    lines.append(f"Confianca     : {bias_result['confidence']}")
    lines.append(f"Veredito      : {bias_result['verdict']}")
    lines.append("")
    lines.append("RESUMO HONESTO:")
    lines.append("  " + bias_result["honest_summary"])
    lines.append("")
    lines.append("-" * 72)
    lines.append(" TESTES ESTATISTICOS")
    lines.append("-" * 72)

    n = t["numbers"]
    lines.append(
        f"Chi-square por numero    : chi2={n['chi2']}  dof={n['dof']}  "
        f"p={n['p_value']}  reject_5%={n['reject_h0_at_5pct']}"
    )
    c = t["color"]
    lines.append(
        f"Chi-square por cor       : chi2={c['chi2']}  p={c['p_value']}  "
        f"reject_5%={c['reject_h0_at_5pct']}"
    )
    lines.append(f"  observado: {c['observed']}  esperado: {c['expected']}")

    s = t["sectors"]
    lines.append(
        f"Chi-square setores (k={s['sector_size']}): chi2={s['chi2']}  p={s['p_value']}  "
        f"reject_5%={s['reject_h0_at_5pct']}"
    )
    for hs in s.get("hot_sectors", []):
        lines.append(
            f"  HOT SECTOR centrado em {hs['center']:>3} | z={hs['z_score']:+.2f} | "
            f"count={hs['count']} (esperado {hs['expected']}) | {hs['members']}"
        )

    r = t["runs"]
    if not r.get("skipped"):
        lines.append(
            f"Runs test (cores)        : z={r['z_score']}  p={r['p_value']}  "
            f"reject_5%={r['reject_h0_at_5pct']}"
        )
    a = t["autocorr"]
    if not a.get("skipped"):
        lines.append(
            f"Autocorrelacao (lag<=10) : Q={a['ljung_box_Q']}  p={a['p_value']}  "
            f"reject_5%={a['reject_h0_at_5pct']}"
        )

    z = t["z_scores"]
    lines.append("")
    lines.append(f"Numeros mais QUENTES (z mais alto):")
    for row in z["top_hot"]:
        lines.append(
            f"  {row['number']:>3}  count={row['count']}  esperado={row['expected']}  "
            f"z={row['z']:+.2f}"
        )
    lines.append(f"Numeros mais FRIOS (z mais baixo):")
    for row in z["top_cold"]:
        lines.append(
            f"  {row['number']:>3}  count={row['count']}  esperado={row['expected']}  "
            f"z={row['z']:+.2f}"
        )
    lines.append("")
    lines.append("AVISO: " + z["warning_multiple_testing"])

    g = t["gaps"]
    if not g.get("skipped"):
        lines.append("")
        lines.append(
            f"Gaps: media obs={g['mean_gap_observed']}  esperada={g['mean_gap_expected']}  "
            f"desvio={g['deviation_pct']}%"
        )

    if sim_result:
        lines.append("")
        lines.append("-" * 72)
        lines.append(" SIMULACAO DE ESTRATEGIAS (Monte Carlo)")
        lines.append("-" * 72)
        lines.append(f"{'estrategia':<14}{'media':>10}{'mediana':>10}{'p(ruina)':>12}{'p(lucro)':>12}")
        for name, r in sim_result.items():
            lines.append(
                f"{name:<14}{r['mean_final']:>10.2f}{r['median_final']:>10.2f}"
                f"{r['p_ruin']:>12.3f}{r['p_profit']:>12.3f}"
            )
        lines.append("")
        lines.append(
            "Observe: todas as medias convergem para o mesmo valor (house edge x volume). "
            "Estrategias apenas reformatam a distribuicao — nao geram edge."
        )

    lines.append("=" * 72)
    return "\n".join(lines)
