"""
Página 6 — Pipeline B2B
Evolutivo de faturamento por carteira e canal · Comparativo YTD · Pipeline do mês
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import datetime as _dt

from utils.database import (
    get_pipeline_mensal, get_pipeline_resumo,
    get_pipeline_carteiras, get_pipeline_metas, init_db
)
from utils.style import apply_theme, sidebar_header, sidebar_footer, COR_TEAL
from utils.auth import require_login

st.set_page_config(page_title="Pipeline B2B · Artmed", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")
init_db()
apply_theme()

usuario  = require_login()
is_admin = usuario["papel"] == "admin"

sidebar_header(usuario)
sidebar_footer(usuario)

# ── Cores ──────────────────────────────────────────────────────────────────────
CHART = dict(
    plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    font_color="#374151",
    title_font_color="#111827", title_font_size=14,
    title_x=0, title_pad=dict(l=4),
)
GRID = dict(gridcolor="#F3F4F6", zerolinecolor="#E5E7EB")

COR_2023  = "#E5E7EB"
COR_2024  = "#9CA3AF"
COR_2025  = "#3B82F6"
COR_26    = COR_TEAL
COR_25YTD = "rgba(0,169,157,0.25)"
COR_PIPE  = "rgba(59,130,246,0.7)"

MESES_PT = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
            7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}


def fmt_br(v, dec=0) -> str:
    try:
        s = f"{float(v):,.{dec}f}"
        return s.replace(",","X").replace(".","," ).replace("X",".")
    except Exception:
        return "—"

def fmt_m(v) -> str:
    """Formata como R$ 1,2M ou R$ 850k"""
    try:
        v = float(v)
        if v >= 1e6:  return f"R$ {v/1e6:.1f}M"
        if v >= 1e3:  return f"R$ {v/1e3:.0f}k"
        return f"R$ {v:.0f}"
    except Exception:
        return "—"

def var_badge(pct) -> str:
    try:
        pct = float(pct) * 100
        cor = "#D1FAE5" if pct >= 0 else "#FEE2E2"
        txt = "#065F46" if pct >= 0 else "#991B1B"
        sinal = "▲" if pct >= 0 else "▼"
        return f'<span style="background:{cor};color:{txt};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">{sinal} {abs(pct):.1f}%</span>'
    except Exception:
        return ""

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
col_title, col_filt = st.columns([3, 1.5])
with col_title:
    st.markdown("""
    <div style="padding:8px 0 0 0;">
      <div class="page-title">📈 Pipeline B2B</div>
      <div class="page-subtitle">Faturamento por carteira · Evolutivo 2023-2026 · YTD vs ano anterior</div>
    </div>
    """, unsafe_allow_html=True)

# ── Filtro de Carteira ─────────────────────────────────────────────────────────
carteiras_disp = get_pipeline_carteiras()

# Vendedor não-admin só vê sua carteira
if not is_admin and usuario.get("cod_gcon"):
    carteira_fixada = usuario.get("cod_gcon")
else:
    carteira_fixada = None

with col_filt:
    if is_admin and carteiras_disp:
        opts = ["Todas as carteiras"] + carteiras_disp
        sel_cart = st.selectbox("Carteira / Vendedor", opts, key="sel_cart_pipe")
        carteira_fil = None if sel_cart == "Todas as carteiras" else sel_cart
    elif carteira_fixada:
        carteira_fil = carteira_fixada
        st.info(f"Carteira: **{carteira_fixada}**")
    else:
        carteira_fil = None

# ── Carrega dados ──────────────────────────────────────────────────────────────
df_mes    = get_pipeline_mensal(carteira_fil)
df_resumo = get_pipeline_resumo(carteira_fil)

if df_resumo.empty:
    st.warning("Nenhum dado de Pipeline B2B encontrado. Importe o arquivo na página **Upload de Arquivos**.")
    st.stop()

st.markdown("<hr style='margin:10px 0 16px 0;border-color:#E5E7EB;'>", unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
tot_ytd26    = df_resumo["ytd_2026"].sum()
tot_ytd25    = df_resumo["ytd_2025"].sum()
tot_pipe     = df_resumo["pipeline_jul"].sum()
tot_tt25     = df_resumo["tt_2025"].sum()
tot_tt24     = df_resumo["tt_2024"].sum()
var_ytd      = (tot_ytd26 / tot_ytd25 - 1) if tot_ytd25 > 0 else 0
gap_ytd      = tot_ytd26 - tot_ytd25
proj_jul     = tot_ytd26 + tot_pipe

k = st.columns(5)
k[0].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Faturamento YTD 2026</div>
  <div class="kpi-value" style="color:{COR_TEAL};">{fmt_m(tot_ytd26)}</div>
  <div class="kpi-sub">Acumulado Jan–Jun 2026</div>
</div>""", unsafe_allow_html=True)

k[1].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">YTD 2025 (mesmo período)</div>
  <div class="kpi-value">{fmt_m(tot_ytd25)}</div>
  <div class="kpi-sub">Jan–Jun 2025</div>
</div>""", unsafe_allow_html=True)

cor_var = "#10B981" if var_ytd >= 0 else "#EF4444"
k[2].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Variação YTD</div>
  <div class="kpi-value" style="color:{cor_var};">{var_ytd*100:+.1f}%</div>
  <div class="kpi-sub">Gap: {fmt_m(gap_ytd)}</div>
</div>""", unsafe_allow_html=True)

k[3].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Pipeline Jul/2026</div>
  <div class="kpi-value" style="color:#3B82F6;">{fmt_m(tot_pipe)}</div>
  <div class="kpi-sub">Oportunidades mapeadas</div>
</div>""", unsafe_allow_html=True)

k[4].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Projeção Jul c/ Pipeline</div>
  <div class="kpi-value">{fmt_m(proj_jul)}</div>
  <div class="kpi-sub">YTD Jul = acum. + pipeline</div>
</div>""", unsafe_allow_html=True)

st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

# ── GRÁFICO 1: Evolutivo anual por Carteira ────────────────────────────────────
def _bar_evolutivo(df_r, grupo_col, titulo):
    agg = df_r.groupby(grupo_col).agg(
        tt_2023=("tt_2023","sum"), tt_2024=("tt_2024","sum"),
        tt_2025=("tt_2025","sum"), ytd_2026=("ytd_2026","sum"),
        ytd_2025=("ytd_2025","sum"),
    ).reset_index().sort_values("ytd_2026", ascending=False)

    fig = go.Figure()
    for label, col, cor in [
        ("2023",     "tt_2023",  COR_2023),
        ("2024",     "tt_2024",  COR_2024),
        ("2025",     "tt_2025",  COR_2025),
        ("YTD 2026", "ytd_2026", COR_26),
        ("YTD 2025", "ytd_2025", COR_25YTD),
    ]:
        cor_border = COR_TEAL if label == "YTD 2025" else cor
        fig.add_trace(go.Bar(
            name=label,
            x=agg[grupo_col],
            y=agg[col],
            marker_color=cor,
            marker_line_color=cor_border,
            marker_line_width=1 if label == "YTD 2025" else 0,
        ))

    fig.update_layout(
        **CHART, title=titulo, barmode="group", height=300,
        xaxis=dict(tickfont=dict(size=11), **GRID),
        yaxis=dict(tickformat=".2s", **GRID),
        legend=dict(orientation="h", y=-0.25, font=dict(size=10)),
        margin=dict(t=40, b=10, l=10, r=10),
    )
    return fig


col1, col2 = st.columns(2)
with col1:
    fig1 = _bar_evolutivo(df_resumo, "carteira", "Faturamento Anual por Carteira (R$)")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = _bar_evolutivo(df_resumo, "canal", "Faturamento Anual por Canal (R$)")
    st.plotly_chart(fig2, use_container_width=True)

# ── GRÁFICO 2: Budget / Forecast / Real / Pipeline por Canal (mês atual) ──────
_mes_hoje  = _dt.date.today().strftime("%Y-%m")
_mes_label = _dt.date.today().strftime("%b/%Y")
_MESES_ABREV = {"01":"Jan","02":"Fev","03":"Mar","04":"Abr","05":"Mai","06":"Jun",
                "07":"Jul","08":"Ago","09":"Set","10":"Out","11":"Nov","12":"Dez"}
_num_mes = _mes_hoje.split("-")[1]
_mes_pt  = _MESES_ABREV.get(_num_mes, _mes_label)

df_metas = get_pipeline_metas(mes=_mes_hoje)

# Cores do gráfico de metas
COR_BUDGET   = "#F59E0B"    # âmbar
COR_FORECAST = "#8B5CF6"    # violeta
COR_REAL     = COR_TEAL     # verde-azulado
COR_PIPELINE = "#3B82F6"    # azul

if not df_metas.empty:
    # Remove linhas de total e limpeza
    df_metas = df_metas[
        ~df_metas["canal"].astype(str).str.strip().str.startswith("Total")
    ].copy()

    metas_grp = df_metas.groupby("canal").agg(
        budget=("budget",     "sum"),
        forecast=("forecast",   "sum"),
        real_value=("real_value", "sum"),
    ).reset_index()

    # Pipeline por carteira (os nomes podem coincidir com os canais da aba Metas)
    pipe_by_cart = df_resumo.groupby("carteira").agg(
        pipeline_jul=("pipeline_jul","sum")
    ).reset_index().rename(columns={"carteira": "canal"})

    chart_df = metas_grp.merge(pipe_by_cart, on="canal", how="left")
    chart_df["pipeline_jul"] = chart_df["pipeline_jul"].fillna(0)
    # Mantém apenas linhas com pelo menos um valor > 0
    chart_df = chart_df[
        chart_df[["budget","forecast","real_value","pipeline_jul"]].sum(axis=1) > 0
    ].sort_values("budget", ascending=False)

    st.markdown(
        f'<div class="card-title">{_mes_pt}/{_mes_hoje[:4]} — Budget · Forecast · Real · Pipeline por Canal</div>',
        unsafe_allow_html=True
    )
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        name="Budget (Meta)", x=chart_df["canal"], y=chart_df["budget"],
        marker_color=COR_BUDGET,
        text=chart_df["budget"].apply(fmt_m),
        textposition="outside", textfont=dict(size=9),
    ))
    fig3.add_trace(go.Bar(
        name="Forecast", x=chart_df["canal"], y=chart_df["forecast"],
        marker_color=COR_FORECAST,
        text=chart_df["forecast"].apply(fmt_m),
        textposition="outside", textfont=dict(size=9),
    ))
    fig3.add_trace(go.Bar(
        name="Real", x=chart_df["canal"], y=chart_df["real_value"],
        marker_color=COR_REAL,
        text=chart_df["real_value"].apply(fmt_m),
        textposition="outside", textfont=dict(size=9),
    ))
    fig3.add_trace(go.Bar(
        name="Pipeline", x=chart_df["canal"], y=chart_df["pipeline_jul"],
        marker_color=COR_PIPELINE,
        text=chart_df["pipeline_jul"].apply(lambda v: fmt_m(v) if v > 0 else ""),
        textposition="outside", textfont=dict(size=9),
    ))
    fig3.update_layout(
        **CHART, title="", barmode="group", height=360,
        xaxis=dict(tickfont=dict(size=11), **GRID),
        yaxis=dict(tickformat=".2s", **GRID),
        legend=dict(orientation="h", y=-0.2, font=dict(size=11)),
        margin=dict(t=10, b=10, l=10, r=10),
        uniformtext_minsize=8, uniformtext_mode="hide",
    )
    st.plotly_chart(fig3, use_container_width=True)

else:
    # Sem metas importadas → exibe gráfico original (Pipeline + YTD empilhado)
    st.markdown(
        '<div class="card-title">Pipeline Jul/2026 vs Faturamento YTD — por Carteira</div>',
        unsafe_allow_html=True
    )
    st.caption("ℹ️ Importe a aba **Metas** para ver Budget · Forecast · Real por canal.")

    pipe_cart = df_resumo.groupby("carteira").agg(
        ytd_2026=("ytd_2026","sum"),
        ytd_2025=("ytd_2025","sum"),
        pipeline_jul=("pipeline_jul","sum"),
    ).reset_index().sort_values("ytd_2026", ascending=False)

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        name="Faturado YTD 2026 (Jan–Jun)",
        x=pipe_cart["carteira"], y=pipe_cart["ytd_2026"],
        marker_color=COR_TEAL,
        text=pipe_cart["ytd_2026"].apply(fmt_m),
        textposition="inside", textfont=dict(color="white", size=11),
        insidetextanchor="middle",
    ))
    fig3.add_trace(go.Bar(
        name="Pipeline Jul/2026",
        x=pipe_cart["carteira"], y=pipe_cart["pipeline_jul"],
        marker_color=COR_PIPE,
        text=pipe_cart["pipeline_jul"].apply(fmt_m),
        textposition="inside", textfont=dict(color="white", size=11),
        insidetextanchor="middle",
    ))
    fig3.add_trace(go.Scatter(
        name="YTD 2025 (referência)",
        x=pipe_cart["carteira"], y=pipe_cart["ytd_2025"],
        mode="markers+lines",
        marker=dict(size=10, color="#9CA3AF"),
        line=dict(color="#9CA3AF", dash="dot", width=2),
    ))
    fig3.update_layout(
        **CHART, barmode="stack", height=260,
        xaxis=dict(tickfont=dict(size=12), **GRID),
        yaxis=dict(tickformat=".2s", **GRID),
        legend=dict(orientation="h", y=-0.25, font=dict(size=10)),
        margin=dict(t=10, b=10, l=10, r=10),
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── GRÁFICO 3: Evolutivo mensal 2023-2026 (linha) ─────────────────────────────
if not df_mes.empty:
    st.markdown('<div class="card-title">Evolução Mensal · Faturamento por Mês (R$)</div>',
                unsafe_allow_html=True)

    df_mes["valor"] = pd.to_numeric(df_mes["valor"], errors="coerce").fillna(0)
    df_mes["mes_label"] = df_mes["mes"].map(lambda m: MESES_PT.get(m, str(m)))

    evol = df_mes.groupby(["ano","mes","mes_label"])["valor"].sum().reset_index()
    evol = evol.sort_values(["ano","mes"])

    fig4 = go.Figure()
    cores_ano = {2023: COR_2023, 2024: COR_2024, 2025: COR_2025, 2026: COR_TEAL}
    for ano in [2023, 2024, 2025, 2026]:
        sub = evol[evol["ano"] == ano]
        if sub.empty or sub["valor"].sum() == 0:
            continue
        fig4.add_trace(go.Scatter(
            name=str(ano),
            x=sub["mes_label"], y=sub["valor"],
            mode="lines+markers",
            line=dict(color=cores_ano.get(ano, "#6B7280"), width=2.5 if ano == 2026 else 1.5),
            marker=dict(size=6),
        ))
    fig4.update_layout(
        **CHART, height=260,
        xaxis=dict(tickfont=dict(size=11), **GRID),
        yaxis=dict(tickformat=".2s", **GRID),
        legend=dict(orientation="h", y=-0.25, font=dict(size=10)),
        margin=dict(t=10, b=10, l=10, r=10),
    )
    st.plotly_chart(fig4, use_container_width=True)

# ── TABELA DE CLIENTES ─────────────────────────────────────────────────────────
st.markdown('<div class="card-title">Lista de Clientes · Comparativo Detalhado</div>',
            unsafe_allow_html=True)

# Filtro extra por canal
canais_disp = sorted(df_resumo["canal"].dropna().unique().tolist())
col_f1, col_f2, _ = st.columns([1.5, 1.5, 4])
with col_f1:
    sel_canal = st.selectbox("Canal", ["Todos"] + canais_disp, key="sel_canal_pipe")
with col_f2:
    busca = st.text_input("Buscar cliente", placeholder="Nome...", key="busca_cli_pipe")

df_tab = df_resumo.copy()
if sel_canal != "Todos":
    df_tab = df_tab[df_tab["canal"] == sel_canal]
if busca:
    df_tab = df_tab[df_tab["nome_cliente"].str.upper().str.contains(busca.upper(), na=False)]

df_tab = df_tab.sort_values("ytd_2026", ascending=False).reset_index(drop=True)

# Formata tabela
CORES_CART = {
    "Large Account": "#1D4ED8", "Raquel": "#007A73",
    "Filial PR": "#B45309", "Distribuidor IES": "#6D28D9", "Tatiana": "#374151",
}

def _tag(carteira):
    cor = CORES_CART.get(carteira, "#374151")
    return (f'<span style="background:rgba(0,0,0,0.06);color:{cor};'
            f'padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">'
            f'{carteira}</span>')

rows_html = ""
for _, r in df_tab.iterrows():
    pct = r["pct_ytd"]
    cor_pct = "#10B981" if pct >= 0 else "#EF4444"
    sinal   = "▲" if pct >= 0 else "▼"
    pipe    = fmt_m(r["pipeline_jul"]) if r["pipeline_jul"] > 0 else "—"
    rows_html += f"""
    <tr>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
          title="{r['nome_cliente']}">{r['nome_cliente']}</td>
      <td>{_tag(r['carteira'])}</td>
      <td style="color:#6B7280;font-size:11px;">{r['canal'] or '—'}</td>
      <td class="text-right">{fmt_m(r['tt_2023'])}</td>
      <td class="text-right">{fmt_m(r['tt_2024'])}</td>
      <td class="text-right">{fmt_m(r['tt_2025'])}</td>
      <td class="text-right" style="font-weight:700;color:{COR_TEAL};">{fmt_m(r['ytd_2026'])}</td>
      <td class="text-right">{fmt_m(r['ytd_2025'])}</td>
      <td class="text-right" style="color:{cor_pct};font-weight:600;">{sinal} {abs(pct*100):.1f}%</td>
      <td class="text-right" style="color:#3B82F6;font-weight:600;">{pipe}</td>
    </tr>"""

st.markdown(f"""
<style>
.pipe-table {{ width:100%;border-collapse:collapse;font-size:12px; }}
.pipe-table thead th {{
  background:#F9FAFB;padding:10px 12px;text-align:left;
  font-size:10px;font-weight:700;color:#6B7280;text-transform:uppercase;
  letter-spacing:.06em;border-bottom:1px solid #E5E7EB;
}}
.pipe-table tbody td {{ padding:9px 12px;border-bottom:1px solid #F9FAFB;color:#374151; }}
.pipe-table tbody tr:hover {{ background:#F9FAFB; }}
.text-right {{ text-align:right; }}
</style>
<div style="overflow-x:auto;">
<table class="pipe-table">
  <thead>
    <tr>
      <th>Cliente</th><th>Carteira</th><th>Canal</th>
      <th class="text-right">TT 2023</th><th class="text-right">TT 2024</th>
      <th class="text-right">TT 2025</th>
      <th class="text-right">YTD 2026</th><th class="text-right">YTD 2025</th>
      <th class="text-right">Var %</th><th class="text-right">Pipeline Jul</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<div style='font-size:11px;color:#9CA3AF;margin-top:8px;'>"
            f"Exibindo {len(df_tab):,} clientes</div>", unsafe_allow_html=True)

# Download CSV
csv = df_tab.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ Baixar CSV", csv, "pipeline_b2b.csv", "text/csv", key="dl_pipe")
