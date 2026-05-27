"""
Dashboard Streamlit para auditoria de aleatoriedade de roleta.

Le giros de:
  - upload de CSV (coluna 'number' por padrao, ou escolhida)
  - exemplos em examples/
  - memoria de uma instancia da FastAPI rodando (GET /history/{wheel_id})

Mostra:
  - veredito honesto (com n, p-value e sample-size recomendado SEMPRE visiveis)
  - heatmap do anel fisico da roda (z-score por bolso)
  - frequencias observado vs esperado
  - tabela da bateria de testes estatisticos
  - numeros quentes/frios + aviso de multiple testing
  - setores quentes (vizinhos no rotor)
  - EV calibrado, condicionado pela REGRA DA CASA

REGRA DA CASA: este painel AUDITA aleatoriedade. NAO preve numeros.
Roleta justa tem house edge fixo. Veja docs/HONEST_MATH.md.

Rodar:
  streamlit run dashboard.py
"""
from __future__ import annotations

import os
from collections import Counter
from collections.abc import Sequence
from math import sqrt
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.colors import TwoSlopeNorm

from core.bias import detect_bias
from core.ev import evaluate_all_numbers, house_edge
from core.patterns import frequency_ranking, prob_not_appearing
from core.predictability_engine import analyze_predictability, rolling_structure
from core.wheel import Wheel, color_of, get_wheel

EXAMPLES_DIR = Path(__file__).parent / "examples"

# cor do veredito -> (cor de fundo do banner, rotulo)
VERDICT_STYLE: dict[str, tuple[str, str]] = {
    "vies_provavel": ("#b00020", "VIES PROVAVEL"),
    "indicio_fraco": ("#d98300", "INDICIO FRACO"),
    "inconclusivo": ("#5c6bc0", "INCONCLUSIVO"),
    "amostra_insuficiente": ("#616161", "AMOSTRA INSUFICIENTE"),
    "sem_vies_detectado": ("#2e7d32", "SEM VIES DETECTADO"),
}

ROULETTE_HEX = {"red": "#c62828", "black": "#212121", "green": "#2e7d32"}


# ----------------------------------------------------------------------
# Funcoes puras (testaveis sem Streamlit)
# ----------------------------------------------------------------------

def parse_spins_from_df(df: pd.DataFrame, column: str) -> list[str]:
    """Extrai a coluna de giros como lista de strings normalizadas."""
    raw = df[column].dropna().astype(str).str.strip().tolist()
    out: list[str] = []
    for v in raw:
        if v.endswith(".0"):  # "20.0" -> "20" (CSV lido como float em algum momento)
            v = v[:-2]
        if v:
            out.append(v)
    return out


def z_per_number(spins: Sequence[str], wheel: Wheel) -> dict[str, float]:
    """Z-score binomial de cada bolso. Usado para colorir o anel."""
    n = len(spins)
    p = wheel.expected_prob
    expected = n * p
    sd = sqrt(n * p * (1 - p)) if n > 0 else 0.0
    counts = Counter(spins)
    return {
        num: ((counts.get(num, 0) - expected) / sd if sd > 0 else 0.0)
        for num in wheel.order
    }


def tests_dataframe(full_tests: dict) -> pd.DataFrame:
    """Tabela consolidada da bateria de testes."""
    t = full_tests["tests"]
    rows: list[list] = []

    nb = t["numbers"]
    rows.append(["Chi2 numeros", nb["chi2"], nb["p_value"], nb["reject_h0_at_5pct"], f"dof={nb['dof']}"])

    c = t["color"]
    obs = c["observed"]
    rows.append(["Chi2 cor", c["chi2"], c["p_value"], c["reject_h0_at_5pct"],
                 f"r={obs['red']} b={obs['black']} g={obs['green']}"])

    s = t["sectors"]
    rows.append([f"Chi2 setores (k={s['sector_size']})", s["chi2"], s["p_value"],
                 s["reject_h0_at_5pct"], f"{len(s['hot_sectors'])} setores quentes"])

    r = t["runs"]
    if r.get("skipped"):
        rows.append(["Runs (cores)", None, None, None, r.get("reason", "skipped")])
    else:
        rows.append(["Runs (cores)", r["z_score"], r["p_value"], r["reject_h0_at_5pct"],
                     f"runs={r['runs_observed']} (esp {r['runs_expected']})"])

    a = t["autocorr"]
    if a.get("skipped"):
        rows.append(["Ljung-Box autocorr", None, None, None, a.get("reason", "skipped")])
    else:
        rows.append(["Ljung-Box autocorr", a["ljung_box_Q"], a["p_value"], a["reject_h0_at_5pct"],
                     f"lag<={a['max_lag']}"])

    return pd.DataFrame(rows, columns=["teste", "estatistica", "p_value", "rejeita_h0_5pct", "nota"])


def ev_dataframe(spins: Sequence[str], wheel: Wheel, top_n: int = 12) -> pd.DataFrame:
    """Top-N numeros por EV calibrado (aposta straight)."""
    evs = evaluate_all_numbers(spins, wheel)[:top_n]
    return pd.DataFrame([
        {
            "numero": e["target"],
            "obs": e["observed_count"],
            "p_emp": e["p_empirical"],
            "p_teo": e["p_theoretical"],
            "ev_emp": e["ev_empirical"],
            "edge_pct": e["edge_pct"],
            "playable": e["playable"],
        }
        for e in evs
    ])


# ----------------------------------------------------------------------
# Figuras matplotlib
# ----------------------------------------------------------------------

def wheel_heatmap_fig(spins: Sequence[str], wheel: Wheel, center_text: str) -> plt.Figure:
    """Anel fisico da roda colorido por z-score de cada bolso."""
    z = z_per_number(spins, wheel)
    zvals = np.array([z[num] for num in wheel.order])
    maxabs = max(1.0, float(np.max(np.abs(zvals)))) if zvals.size else 1.0
    norm = TwoSlopeNorm(vmin=-maxabs, vcenter=0.0, vmax=maxabs)
    cmap = plt.get_cmap("coolwarm")

    n = wheel.pockets
    width = 2 * np.pi / n
    theta = np.array([i * width for i in range(n)])

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(7, 7))
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.bar(theta, height=0.45, width=width * 0.92, bottom=1.0,
           color=[cmap(norm(v)) for v in zvals], edgecolor="white", linewidth=0.6)

    for i, num in enumerate(wheel.order):
        ax.text(theta[i], 1.62, num, ha="center", va="center", fontsize=8,
                color=ROULETTE_HEX[color_of(num)])
        if abs(zvals[i]) >= 2.0:  # so anota outliers para nao poluir
            ax.text(theta[i], 1.22, f"{zvals[i]:+.1f}", ha="center", va="center",
                    fontsize=6.5, color="white", weight="bold")

    ax.set_axis_off()
    ax.set_ylim(0, 1.85)
    ax.text(0, 0, center_text, ha="center", va="center", fontsize=11, weight="bold")

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.045, pad=0.08)
    cbar.set_label("z-score (observado vs esperado)")
    fig.tight_layout()
    return fig


def frequency_fig(spins: Sequence[str], wheel: Wheel, order_by_wheel: bool) -> plt.Figure:
    """Barras de contagem por numero, com linha do esperado."""
    counts = Counter(spins)
    if order_by_wheel:
        nums = list(wheel.order)
    else:
        nums = sorted(wheel.order, key=lambda x: (-1 if x == "00" else int(x)))
    obs = [counts.get(num, 0) for num in nums]
    expected = len(spins) / wheel.pockets if wheel.pockets else 0.0

    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.bar(range(len(nums)), obs, color=[ROULETTE_HEX[color_of(num)] for num in nums],
           edgecolor="#444", linewidth=0.3)
    ax.axhline(expected, color="black", linestyle="--", linewidth=1.0,
               label=f"esperado = {expected:.1f}")
    ax.set_xticks(range(len(nums)))
    ax.set_xticklabels(nums, rotation=90, fontsize=7)
    ax.set_ylabel("contagem")
    ax.set_xlabel("numero" + (" (ordem fisica da roda)" if order_by_wheel else ""))
    ax.legend(loc="upper right")
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------
# Carregamento de dados
# ----------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def analyze_cached(spins_tuple: tuple, wheel_name: str) -> dict:
    """detect_bias com cache keyado pelos giros + roda."""
    wheel = get_wheel(wheel_name)
    return detect_bias(list(spins_tuple), wheel)


@st.cache_data(show_spinner=False)
def predictability_cached(spins_tuple: tuple, wheel_name: str, n_perm: int = 150) -> dict:
    """analyze_predictability com cache (testes de permutacao sao custosos)."""
    return analyze_predictability(list(spins_tuple), get_wheel(wheel_name), seed=42, n_perm=n_perm)


def load_from_api(base_url: str, wheel_id: str, limit: int) -> list[str]:
    """Busca os giros da memoria de uma FastAPI rodando (GET /history)."""
    import httpx

    url = base_url.rstrip("/") + f"/history/{wheel_id}"
    resp = httpx.get(url, params={"limit": limit}, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    return [str(s) for s in data.get("last", [])]


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------

def _read_csv(file_like, dtype=str) -> pd.DataFrame:
    return pd.read_csv(file_like, dtype=dtype)


def main() -> None:
    st.set_page_config(page_title="Roulette Analyzer", layout="wide")
    st.title("Roulette Analyzer - auditoria de aleatoriedade")
    st.caption(
        "Este painel AUDITA aleatoriedade. NAO preve numeros. "
        "Roleta justa tem house edge fixo (-2.7% europeia, -5.26% americana). "
        "Nenhuma estrategia muda isso. Detalhes em docs/HONEST_MATH.md."
    )

    # ---- Sidebar: fonte de dados + roda ----
    st.sidebar.header("Dados")
    source = st.sidebar.radio("Fonte dos giros", ["Upload CSV", "Exemplo", "Memoria da API"])
    wheel_name = st.sidebar.selectbox("Tipo de roda", ["european", "american"])
    order_by_wheel = st.sidebar.checkbox("Frequencias em ordem fisica da roda", value=False)

    spins: list[str] = []

    if source == "Upload CSV":
        up = st.sidebar.file_uploader("CSV de giros", type=["csv"])
        if up is not None:
            df = _read_csv(up)
            cols = list(df.columns)
            default_idx = cols.index("number") if "number" in cols else 0
            column = st.sidebar.selectbox("Coluna com os giros", cols, index=default_idx)
            spins = parse_spins_from_df(df, column)

    elif source == "Exemplo":
        examples = sorted(p.name for p in EXAMPLES_DIR.glob("*.csv")) if EXAMPLES_DIR.exists() else []
        if not examples:
            st.sidebar.warning("Nenhum CSV em examples/.")
        else:
            choice = st.sidebar.selectbox("Arquivo de exemplo", examples)
            df = _read_csv(EXAMPLES_DIR / choice)
            cols = list(df.columns)
            default_idx = cols.index("number") if "number" in cols else 0
            column = st.sidebar.selectbox("Coluna com os giros", cols, index=default_idx)
            spins = parse_spins_from_df(df, column)

    else:  # Memoria da API
        base_url = st.sidebar.text_input(
            "URL base da API", value=os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
        )
        wheel_id = st.sidebar.text_input("wheel_id", value="casino-x-mesa-3")
        limit = st.sidebar.number_input("limite de giros", min_value=100, max_value=100000,
                                        value=5000, step=500)
        if st.sidebar.button("Buscar da API"):
            try:
                spins = load_from_api(base_url, wheel_id, int(limit))
                st.session_state["api_spins"] = spins
            except Exception as exc:  # noqa: BLE001 - feedback amigavel ao usuario
                st.sidebar.error(f"Falha ao buscar da API: {exc}")
        spins = st.session_state.get("api_spins", spins)

    # ---- Sem dados ainda ----
    if not spins:
        st.info("Escolha uma fonte de giros na barra lateral para comecar.")
        st.stop()

    # ---- Validacao contra a roda escolhida ----
    wheel = get_wheel(wheel_name)
    valid = set(wheel.order)
    invalid = sorted({s for s in spins if s not in valid})
    if invalid:
        st.error(
            f"{len(invalid)} valor(es) invalido(s) para a roda '{wheel_name}': "
            f"{invalid[:8]}{'...' if len(invalid) > 8 else ''}. "
            "Confira o tipo de roda (00 so existe na americana) ou a coluna escolhida."
        )
        st.stop()

    # ---- Analise ----
    bias = analyze_cached(tuple(spins), wheel_name)
    verdict = bias["verdict"]
    bg, label = VERDICT_STYLE.get(verdict, ("#616161", verdict.upper()))

    # ---- Banner de veredito ----
    st.markdown(
        f"<div style='background:{bg};color:white;padding:16px;border-radius:8px'>"
        f"<h2 style='margin:0;color:white'>{label}</h2>"
        f"<p style='margin:6px 0 0 0;color:white'>{bias['honest_summary']}</p></div>",
        unsafe_allow_html=True,
    )

    # numeros que a REGRA DA CASA exige sempre visiveis
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Giros", bias["n_spins"])
    m2.metric("Sample size recomendado", bias["sample_size_recommended"])
    m3.metric("Confianca", bias["confidence"])
    p_numbers = bias["full_tests"]["tests"]["numbers"]["p_value"]
    m4.metric("p-value (chi2 numeros)", f"{p_numbers:.4g}")

    st.divider()

    # ---- Heatmap + frequencias ----
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Anel fisico da roda")
        fig = wheel_heatmap_fig(spins, wheel, label)
        st.pyplot(fig)
        plt.close(fig)
        st.caption("Cor = z-score do bolso. Anotacoes so em |z|>=2. Vizinhanca quente sugere vies de setor.")
    with right:
        st.subheader("Frequencias: observado vs esperado")
        fig = frequency_fig(spins, wheel, order_by_wheel)
        st.pyplot(fig)
        plt.close(fig)

    st.divider()

    # ---- Tabela de testes ----
    st.subheader("Bateria de testes estatisticos")
    st.dataframe(tests_dataframe(bias["full_tests"]), use_container_width=True, hide_index=True)

    # ---- Quentes / frios ----
    zt = bias["full_tests"]["tests"]["z_scores"]
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Numeros mais quentes")
        st.dataframe(pd.DataFrame(zt["top_hot"]), use_container_width=True, hide_index=True)
    with c2:
        st.subheader("Numeros mais frios")
        st.dataframe(pd.DataFrame(zt["top_cold"]), use_container_width=True, hide_index=True)
    st.warning(zt["warning_multiple_testing"])

    # ---- Frequencia e probabilidade de NAO sair ----
    st.divider()
    st.subheader("Frequencia e probabilidade de NAO sair")
    st.caption(
        "Estatistica descritiva da amostra + probabilidade da distribuicao sob "
        "independencia. NAO e previsao: em roda justa o proximo giro independe do "
        "passado (anti-feature #1 do CLAUDE.md)."
    )
    freq = frequency_ranking(spins, wheel)
    fc1, fc2 = st.columns(2)
    with fc1:
        st.markdown("**Mais frequentes (mais saem)**")
        st.dataframe(pd.DataFrame(freq["most_frequent"]), use_container_width=True, hide_index=True)
    with fc2:
        st.markdown("**Menos frequentes (menos saem)**")
        st.dataframe(pd.DataFrame(freq["least_frequent"]), use_container_width=True, hide_index=True)

    horizon = st.slider("Horizonte N (giros futuros) para P(NAO sair)", 1, 50, 1)
    base_theo = (1 - wheel.expected_prob) ** horizon
    st.caption(
        f"Baseline teorico (roda justa): P(NAO sair em {horizon} giro(s)) = "
        f"{base_theo:.4f} para QUALQUER numero."
    )
    pna = prob_not_appearing(spins, wheel, horizons=(1, horizon))
    pmap = {x["number"]: x for x in pna["numbers"]}
    rows = []
    for r in freq["ranking"]:
        num = r["number"]
        pn = pmap[num]["p_not_appear"]
        rows.append({
            "numero": num,
            "count": r["count"],
            "freq_obs": r["freq_observed"],
            "p_sair_calibrada": r["p_calibrated"],
            "P_nao_sair_proximo": pn["1"]["calibrated"],
            f"P_nao_sair_{horizon}giros": pn[str(horizon)]["calibrated"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ---- Setores quentes ----
    hot = bias["full_tests"]["tests"]["sectors"].get("hot_sectors", [])
    if hot:
        st.subheader("Setores quentes (vizinhos no rotor)")
        st.dataframe(
            pd.DataFrame([
                {
                    "centro": h["center"],
                    "membros": ", ".join(h["members"]),
                    "count": h["count"],
                    "esperado": h["expected"],
                    "z_score": h["z_score"],
                }
                for h in hot
            ]),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # ---- EV calibrado (condicionado pela regra da casa) ----
    st.subheader("EV calibrado por numero (aposta straight)")
    edge = house_edge(wheel)
    if verdict == "vies_provavel":
        st.warning(
            "Veredito = vies_provavel. Numeros com playable=True PODEM ter EV+ real. "
            "AINDA ASSIM: cassinos monitoram e corrigem vies; exija 3000+ giros e trate com ceticismo."
        )
    else:
        st.info(
            f"Veredito != vies_provavel. Qualquer playable=True abaixo e RUIDO, nao edge. "
            f"EV real de qualquer aposta = house edge ({edge:.4f}). NAO aposte com base nisto."
        )
    st.dataframe(ev_dataframe(spins, wheel), use_container_width=True, hide_index=True)

    # ---- Motor de previsibilidade (dinamico) ----
    st.divider()
    st.subheader("Motor de previsibilidade (dinamico)")
    st.caption(
        "Mede QUAO previsivel e o stream e de que TIPO e a estrutura. Aleatorio -> "
        "score ~0 e 'sem_padrao'. NAO preve o proximo numero: mede previsibilidade."
    )
    pred = predictability_cached(tuple(spins), wheel_name)
    g1, g2, g3 = st.columns(3)
    g1.metric("Score (0-1)", f"{pred['predictability_score']:.3f}")
    g2.metric("Padrao dominante", pred["dominant_pattern"])
    g3.metric("Padroes detectados", len(pred["patterns_detected"]))
    if pred["dominant_pattern"] == "sem_padrao":
        st.success(pred["verdict"])
    else:
        st.warning(pred["verdict"])
    det_rows = [
        {
            "detector": key,
            "detectado": bool(t.get("detected", False)),
            "effect": t.get("effect", 0.0),
            "p_value": t.get("p_value"),
            "z": t.get("z"),
        }
        for key, t in pred["tests"].items()
    ]
    st.dataframe(pd.DataFrame(det_rows), use_container_width=True, hide_index=True)

    if len(spins) >= 1500:
        st.markdown("**Evolucao dinamica (janela deslizante)**")
        roll = rolling_structure(
            spins, wheel, window=min(1000, len(spins) // 3), step=max(100, len(spins) // 40)
        )
        if roll:
            df_roll = pd.DataFrame(roll).set_index("end_index")
            st.line_chart(df_roll[["bias", "serial"]])
            st.caption(
                "Subida ao longo do tempo = estrutura emergindo (ex.: drift/vies). "
                "Plano e baixo = aleatorio estavel."
            )
    else:
        st.caption("Forneca >= 1500 giros para a visao dinamica em janela deslizante.")

    with st.expander("Como interpretar (regra da casa)"):
        st.markdown(
            "- Um teste rejeitar H0 a 5% NAO prova vies: com varios testes, falsos positivos sao esperados.\n"
            "- Veredito `vies_provavel` exige sinal forte (p<0.001) E amostra >= 3000 giros.\n"
            "- `sem_vies_detectado` e um resultado VALIDO e util: confirma roda limpa. EV = house edge.\n"
            "- z-score individual alto pode ser variancia (ver aviso de multiple testing).\n"
            "- Nada aqui preve o proximo numero. Veja docs/HONEST_MATH.md."
        )


if __name__ == "__main__":
    main()
