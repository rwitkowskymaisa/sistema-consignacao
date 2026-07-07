"""
Página 2 — Dashboard Principal · Layout Artmed
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.database import (
    get_analise_consignacao, get_ranking_clientes,
    get_faturamento_df, get_gcon_vendedores, get_clientes, init_db
)
from utils.style import apply_theme, sidebar_header, sidebar_footer, COR_TEAL
from utils.auth import require_login

st.set_page_config(page_title="Dashboard · Artmed Consignação",
                   page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")
init_db()
apply_theme()

usuario = require_login()
is_admin    = usuario["papel"] == "admin"
cod_gcon_u  = usuario.get("cod_gcon")
gcon_filter = None if is_admin else cod_gcon_u

# Para admin: determina gcon_filter a partir do selectbox (session_state)
# ANTES de carregar dados, para que kpis/análise já venham filtrados.
_gcon_list: list = []
if is_admin:
    _gcon_list = get_gcon_vendedores()
    _sel_vend  = st.session_state.get("sel_vendedor", "Todos os vendedores")
    if _sel_vend != "Todos os vendedores":
        _m = next((v for v in _gcon_list if v["nome"] == _sel_vend), None)
        if _m:
            gcon_filter = _m["cod_gcon"]

# Tema base para todos os gráficos
CHART = dict(
    plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    font_color="#374151",
    title_font_color="#111827", title_font_size=14,
    title_x=0,           # título alinhado à esquerda
    title_pad=dict(l=4),
)
GRID = dict(gridcolor="#F3F4F6", zerolinecolor="#E5E7EB")

MESES_PT = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
            7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}


def fmt_br(n, dec=0) -> str:
    try:
        s = f"{float(n):,.{dec}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(n)


def to_mes_label(ts) -> str:
    """Timestamp → 'Jan/2026'  (string pura, Plotly não parseia como data)"""
    try:
        return f"{MESES_PT[ts.month]}/{ts.year}"
    except Exception:
        return str(ts)


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
sidebar_header(usuario)
sidebar_footer(usuario)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "fat_mes_sel" not in st.session_state:
    st.session_state.fat_mes_sel = None

# ─── DADOS ────────────────────────────────────────────────────────────────────
with st.spinner("Carregando dados..."):
    clientes   = get_clientes(gcon_filter)
    df_full    = get_analise_consignacao(gcon_filter)   # base única — kpis e ranking derivam daqui
    df_fat_raw = get_faturamento_df(gcon_filter, tipos_tes=("Venda", "Acerto Consignação"))

# ─── KPIs calculados a partir do df_full (sem nova query) ─────────────────────
def _calc_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"total_clientes": 0, "total_titulos": 0,
                "qtde_remessa_total": 0, "qtde_saldo_total": 0,
                "qtde_acerto_total": 0, "pct_acerto_medio": 0.0,
                "valor_liquido_total": 0.0, "valor_potencial": 0.0,
                "titulos_sem_giro": 0, "clientes_sem_giro": 0}
    return {
        "total_clientes": int(df["cod_loja"].nunique()) if "cod_loja" in df.columns else int(df["codigo_cliente"].nunique()),
        "total_titulos": int(df["isbn"].nunique()),
        "qtde_remessa_total": int(df["qtde_remessa"].sum()),
        "qtde_saldo_total": int(df["qtde_saldo"].sum()),
        "qtde_acerto_total": int(df["qtde_dev_acert"].sum()),
        "pct_acerto_medio": round(float(
            df["qtde_dev_acert"].sum() / df["qtde_remessa"].sum() * 100
        ) if df["qtde_remessa"].sum() > 0 else 0, 1),
        "valor_liquido_total": float(df["valor_liquido"].sum()),
        "valor_potencial": float(df.get("valor_potencial", pd.Series([0])).sum()),
        "titulos_sem_giro": int(df[df["sem_giro"]]["isbn"].nunique()),
        "clientes_sem_giro": int(df[df["sem_giro"]]["cod_loja"].nunique()) if "cod_loja" in df.columns else int(df[df["sem_giro"]]["codigo_cliente"].nunique()),
    }

def _calc_ranking(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    ranking = df.groupby(["codigo_cliente", "razao_social", "uf"]).agg(
        qtde_remessa=("qtde_remessa", "sum"),
        qtde_dev_acert=("qtde_dev_acert", "sum"),
        qtde_saldo=("qtde_saldo", "sum"),
        valor_liquido=("valor_liquido", "sum"),
        titulos=("isbn", "nunique"),
    ).reset_index()
    ranking["pct_acerto"] = (
        ranking["qtde_dev_acert"] / ranking["qtde_remessa"].replace(0, 1) * 100
    ).round(1)
    return ranking.sort_values("qtde_saldo", ascending=False)

kpis    = _calc_kpis(df_full)
df_rank = _calc_ranking(df_full)

DATE_COL = None
if not df_fat_raw.empty:
    DATE_COL = "data_nota" if "data_nota" in df_fat_raw.columns else "data_emissao"
    df_fat_raw[DATE_COL] = pd.to_datetime(df_fat_raw[DATE_COL], errors="coerce")
    df_fat_raw = df_fat_raw.dropna(subset=[DATE_COL])

dmin_def = df_fat_raw[DATE_COL].dt.date.min() if DATE_COL and not df_fat_raw.empty else date(2025, 1, 1)
dmax_def = df_fat_raw[DATE_COL].dt.date.max() if DATE_COL and not df_fat_raw.empty else date.today()

# ─── CABEÇALHO ────────────────────────────────────────────────────────────────
if is_admin:
    col_title, col_vend, col_cli = st.columns([3, 1.5, 2])
else:
    col_title, col_cli = st.columns([3.5, 2])

with col_title:
    st.markdown(f"""
    <div style="padding:8px 0 0 0;">
      <div class="page-title">Dashboard Geral</div>
      <div class="page-subtitle">
          {usuario['nome']} &nbsp;·&nbsp;
          Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}
      </div>
    </div>
    """, unsafe_allow_html=True)

if is_admin:
    with col_vend:
        opts_gcon = ["Todos os vendedores"] + [v["nome"] for v in _gcon_list]
        st.selectbox("Vendedor", opts_gcon, key="sel_vendedor")

opts_cli = ["Todos os clientes"] + [
    f"{c['razao_social'][:28]} [{c['codigo_cliente']}]" for c in clientes
]
with col_cli:
    sel_cli = st.selectbox("Clientes", opts_cli)

cliente_sel = None
if sel_cli != "Todos os clientes":
    cliente_sel = sel_cli.split("[")[-1].rstrip("]")

with st.expander("📅 Filtro de período — gráficos de faturamento", expanded=False):
    col_di, col_df, _ = st.columns([2, 2, 4])
    with col_di:
        data_ini = st.date_input("De", value=dmin_def, format="DD/MM/YYYY", key="filter_di")
    with col_df:
        data_fim = st.date_input("Até", value=dmax_def, format="DD/MM/YYYY", key="filter_df")

st.markdown("<hr style='margin:8px 0 16px 0;border-color:#E5E7EB;'>", unsafe_allow_html=True)

# ─── FILTRA POR DATA ──────────────────────────────────────────────────────────
if DATE_COL and not df_fat_raw.empty:
    df_fat_filt = df_fat_raw[
        (df_fat_raw[DATE_COL].dt.date >= data_ini) &
        (df_fat_raw[DATE_COL].dt.date <= data_fim)
    ].copy()
    df_fat_filt["mes_label"] = df_fat_filt[DATE_COL].apply(to_mes_label)
    df_fat_filt["mes_sort"]  = df_fat_filt[DATE_COL].dt.to_period("M").astype(str)
else:
    df_fat_filt = pd.DataFrame()

if not df_fat_filt.empty:
    df_v = (df_fat_filt[df_fat_filt["tipo_tes"] == "Venda"]
            .groupby(["mes_sort", "mes_label"])["valor_atendido"].sum()
            .reset_index().rename(columns={"valor_atendido": "receita_venda"}))
    df_a = (df_fat_filt[df_fat_filt["tipo_tes"] == "Acerto Consignação"]
            .groupby(["mes_sort", "mes_label"])["valor_atendido"].sum()
            .reset_index().rename(columns={"valor_atendido": "receita_acerto_csg"}))
    df_fat_mes_plot = (df_v.merge(df_a, on=["mes_sort", "mes_label"], how="outer")
                       .fillna(0).sort_values("mes_sort"))
else:
    df_fat_mes_plot = pd.DataFrame()

# ─── KPIs ─────────────────────────────────────────────────────────────────────
pct     = kpis["pct_acerto_medio"]
pct_cor = "green" if pct >= 40 else "amber" if pct >= 20 else "red"
sg_cor  = "amber" if kpis["titulos_sem_giro"] > 0 else "green"

k = st.columns(4)
k[0].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Clientes Ativos</div>
  <div class="kpi-value teal">{fmt_br(kpis['total_clientes'])}</div>
  <div class="kpi-sub">lojas/filiais com saldo consignado</div>
</div>""", unsafe_allow_html=True)

k[1].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Saldo Consignado</div>
  <div class="kpi-value blue">{fmt_br(kpis['qtde_saldo_total'])}</div>
  <div class="kpi-sub">itens no cliente · Rem: {fmt_br(kpis['qtde_remessa_total'])}</div>
</div>""", unsafe_allow_html=True)

k[2].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">% Acerto Global</div>
  <div class="kpi-value {pct_cor}">{pct:.1f}%</div>
  <div class="kpi-sub">Dev+Acert ÷ Remessa · {fmt_br(kpis['qtde_acerto_total'])} unid.</div>
</div>""", unsafe_allow_html=True)

k[3].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Títulos sem Giro</div>
  <div class="kpi-value {sg_cor}">{fmt_br(kpis['titulos_sem_giro'])}</div>
  <div class="kpi-sub">em {fmt_br(kpis['clientes_sem_giro'])} clientes · 0 devolução</div>
</div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

k2 = st.columns(4)
k2[0].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Qtda. SKU Consignados</div>
  <div class="kpi-value">{fmt_br(kpis['total_titulos'])}</div>
  <div class="kpi-sub">ISBNs distintos</div>
</div>""", unsafe_allow_html=True)

k2[1].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Qtde Remessa Total</div>
  <div class="kpi-value">{fmt_br(kpis['qtde_remessa_total'])}</div>
  <div class="kpi-sub">unidades enviadas</div>
</div>""", unsafe_allow_html=True)

k2[2].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Dev / Acerto</div>
  <div class="kpi-value">{fmt_br(kpis['qtde_acerto_total'])}</div>
  <div class="kpi-sub">unidades retornadas ou faturadas</div>
</div>""", unsafe_allow_html=True)

vl = kpis.get("valor_liquido_total", 0)
k2[3].markdown(f"""<div class="kpi-card">
  <div class="kpi-label">Valor Líquido Total</div>
  <div class="kpi-value">R$ {fmt_br(vl)}</div>
  <div class="kpi-sub">valor consignado em aberto</div>
</div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

# ─── DRILL-DOWN POR CLIENTE ──────────────────────────────────────────────────
if cliente_sel and not df_full.empty:
    df_cli = df_full[df_full["codigo_cliente"] == cliente_sel].copy()
    if not df_cli.empty:
        razao    = df_cli["razao_social"].iloc[0]
        qtde_rem = int(df_cli["qtde_remessa"].sum())
        qtde_dev = int(df_cli["qtde_dev_acert"].sum())
        qtde_sal = int(df_cli["qtde_saldo"].sum())
        pct_cli  = round(qtde_dev / qtde_rem * 100, 1) if qtde_rem > 0 else 0

        st.markdown(f'<div class="content-card"><div class="card-title">📌 {razao}</div></div>',
                    unsafe_allow_html=True)
        mc = st.columns(4)
        mc[0].metric("Qtde Remessa", fmt_br(qtde_rem))
        mc[1].metric("Dev/Acerto", fmt_br(qtde_dev))
        mc[2].metric("Saldo Atual", fmt_br(qtde_sal))
        mc[3].metric("% Acerto", f"{pct_cli:.1f}%")

        df_fat_cli = (df_fat_filt[df_fat_filt["codigo_cliente"] == cliente_sel].copy()
                      if not df_fat_filt.empty and "codigo_cliente" in df_fat_filt.columns
                      else pd.DataFrame())
        col_ga, col_gb = st.columns(2)

        if not df_fat_cli.empty:
            df_mes_tipo = (df_fat_cli.groupby(["mes_sort", "mes_label", "tipo_tes"])
                           .agg(receita=("valor_atendido", "sum"), qtde=("qtd_atendida", "sum"))
                           .reset_index().sort_values("mes_sort"))
            df_mes = (df_fat_cli.groupby(["mes_sort", "mes_label"])
                      .agg(receita=("valor_atendido", "sum"), qtde=("qtd_atendida", "sum"))
                      .reset_index().sort_values("mes_sort"))
            with col_ga:
                fig = px.bar(df_mes_tipo, x="mes_label", y="receita", color="tipo_tes",
                             title="Receita Mensal por Tipo",
                             labels={"mes_label": "Mês", "receita": "R$", "tipo_tes": "Tipo"},
                             color_discrete_map={"Venda": "#3B82F6", "Acerto Consignação": COR_TEAL})
                fig.update_layout(**CHART, xaxis=dict(tickangle=-30, type="category", **GRID),
                                  yaxis=GRID, height=300, legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig, use_container_width=True)
            with col_gb:
                fig2c = px.line(df_mes, x="mes_label", y="qtde", markers=True,
                                title="Qtde Faturada por Mês",
                                labels={"mes_label": "Mês", "qtde": "Qtde"},
                                color_discrete_sequence=[COR_TEAL])
                fig2c.update_layout(**CHART, xaxis=dict(tickangle=-30, type="category", **GRID),
                                    yaxis=GRID, height=300)
                st.plotly_chart(fig2c, use_container_width=True)
        else:
            col_ga.info("Sem dados de faturamento para este cliente no período.")

        cols_show  = ["isbn", "titulo", "qtde_remessa", "qtde_dev_acert",
                      "qtde_saldo", "pct_acerto", "valor_liquido", "dias_em_saldo"]
        cols_exist = [c for c in cols_show if c in df_cli.columns]
        df_show    = df_cli[cols_exist].copy()
        RENAME = {"isbn": "ISBN", "titulo": "Título", "qtde_remessa": "Remessa",
                  "qtde_dev_acert": "Dev/Acert", "qtde_saldo": "Saldo",
                  "pct_acerto": "% Acerto", "valor_liquido": "Vlr Líq (R$)",
                  "dias_em_saldo": "Dias"}
        df_show.columns = [RENAME.get(c, c) for c in cols_exist]
        if "% Acerto" in df_show.columns:
            df_show["% Acerto"] = df_show["% Acerto"].map("{:.1f}%".format)
        if "Vlr Líq (R$)" in df_show.columns:
            df_show["Vlr Líq (R$)"] = df_show["Vlr Líq (R$)"].map("R$ {:,.2f}".format)
        if "Dias" in df_show.columns:
            df_show["Dias"] = df_show["Dias"].fillna(0).astype(int)
        st.markdown('<div class="card-title" style="margin-top:8px;">Títulos em Consignação</div>',
                    unsafe_allow_html=True)
        st.dataframe(df_show, use_container_width=True, hide_index=True, height=360)
        st.markdown("<hr>", unsafe_allow_html=True)

if df_full.empty:
    st.info("Sem dados. Acesse **Upload** para importar os arquivos.")
    st.stop()

# ─── GRÁFICOS: FATURAMENTO + PARTICIPAÇÃO POR CLIENTE ────────────────────────
col1, col2 = st.columns(2)

with col1:
    mes_sel = st.session_state.fat_mes_sel

    # ── VISÃO DRILL-DOWN: dia a dia ───────────────────────────────────────────
    if mes_sel and not df_fat_filt.empty:
        df_dia = df_fat_filt[df_fat_filt["mes_label"] == mes_sel].copy()
        if not df_dia.empty:
            df_dia["data_str"]  = df_dia[DATE_COL].dt.strftime("%Y-%m-%d")
            df_dia["dia_label"] = df_dia[DATE_COL].dt.strftime("%d/%m")
            df_dia_grp = (df_dia.groupby(["data_str", "dia_label", "tipo_tes"])["valor_atendido"]
                          .sum().reset_index().sort_values("data_str"))
            tickvals = df_dia_grp["data_str"].unique().tolist()
            lbl_map  = df_dia_grp.drop_duplicates("data_str").set_index("data_str")["dia_label"]
            ticktext = [lbl_map.get(v, v) for v in tickvals]
            fig_dia = px.bar(df_dia_grp, x="data_str", y="valor_atendido", color="tipo_tes",
                             title=f"Faturamento dia a dia — {mes_sel}",
                             labels={"data_str": "Data", "valor_atendido": "R$", "tipo_tes": "Tipo"},
                             color_discrete_map={"Venda": "#3B82F6", "Acerto Consignação": COR_TEAL},
                             text_auto=".2s")
            fig_dia.update_layout(
                **CHART,
                barmode="stack",
                xaxis=dict(tickangle=-45, tickvals=tickvals, ticktext=ticktext,
                           type="category", **GRID),
                yaxis=dict(title="R$", **GRID),
                legend=dict(orientation="h", y=1.08),
                height=340,
                margin=dict(t=40, b=10, l=10, r=10),
            )
            st.plotly_chart(fig_dia, use_container_width=True)
            if st.button("← Voltar ao faturamento mensal", key="btn_close_dd"):
                st.session_state.fat_mes_sel = None
                st.rerun()
        else:
            st.session_state.fat_mes_sel = None
            st.rerun()

    # ── VISÃO MENSAL (padrão) ─────────────────────────────────────────────────
    else:
        if not df_fat_mes_plot.empty:
            # Lê seleção pendente do widget ANTES de renderizar
            # (o on_select="rerun" já popula st.session_state["fat_mes_chart"]
            #  no início do rerun, permitindo trocar de view sem st.rerun() extra)
            try:
                chart_state = st.session_state.get("fat_mes_chart")
                if chart_state is not None:
                    sel = (chart_state if isinstance(chart_state, dict)
                           else getattr(chart_state, "__dict__", {}))
                    s   = sel.get("selection", {})
                    pts = (s.get("points", []) if isinstance(s, dict)
                           else list(getattr(s, "points", [])))
                    if pts:
                        pt    = pts[0]
                        x_val = (pt.get("x") if isinstance(pt, dict)
                                 else getattr(pt, "x", None))
                        if x_val:
                            st.session_state.fat_mes_sel = str(x_val)
                            # Limpa seleção do widget para evitar loop
                            del st.session_state["fat_mes_chart"]
                            st.rerun()
            except Exception:
                pass

            fig_fat = go.Figure()
            if "receita_venda" in df_fat_mes_plot.columns:
                fig_fat.add_trace(go.Bar(
                    name="Venda",
                    x=df_fat_mes_plot["mes_label"],
                    y=df_fat_mes_plot["receita_venda"],
                    marker_color="#3B82F6",
                    text=df_fat_mes_plot["receita_venda"].apply(
                        lambda v: f"R$ {v/1e6:.1f}M" if v >= 1e6 else f"R$ {v/1e3:.0f}k" if v >= 1e3 else f"R$ {v:.0f}"
                    ),
                    textposition="inside",
                    textfont=dict(color="white", size=11),
                    insidetextanchor="middle",
                ))
            if "receita_acerto_csg" in df_fat_mes_plot.columns:
                fig_fat.add_trace(go.Bar(
                    name="Acerto Consignação",
                    x=df_fat_mes_plot["mes_label"],
                    y=df_fat_mes_plot["receita_acerto_csg"],
                    marker_color=COR_TEAL,
                    text=df_fat_mes_plot["receita_acerto_csg"].apply(
                        lambda v: f"R$ {v/1e6:.1f}M" if v >= 1e6 else f"R$ {v/1e3:.0f}k" if v >= 1e3 else (f"R$ {v:.0f}" if v > 0 else "")
                    ),
                    textposition="inside",
                    textfont=dict(color="white", size=11),
                    insidetextanchor="middle",
                ))
            fig_fat.update_layout(
                **CHART,
                title="Faturamento  ·  clique em um mês para ver dia a dia",
                barmode="stack",
                xaxis=dict(tickangle=-30, type="category", **GRID),
                yaxis=dict(title="R$", **GRID),
                legend=dict(orientation="h", y=1.08),
                height=340,
                margin=dict(t=40, b=10, l=10, r=10),
            )
            # on_select="rerun" dispara um único rerun quando o usuário clica
            # NÃO chamamos st.rerun() manualmente aqui para evitar duplo rerun
            st.plotly_chart(fig_fat, use_container_width=True,
                            on_select="rerun", selection_mode="points",
                            key="fat_mes_chart")
        else:
            st.info("Sem dados de faturamento. Importe o arquivo de Faturamento.")

# ─── GRÁFICO: PARTICIPAÇÃO POR CLIENTE ───────────────────────────────────────
with col2:
    if not df_rank.empty:
        top10 = df_rank.head(10).copy()
        fig_pie = px.pie(top10, names="razao_social", values="qtde_saldo",
                         hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Set2)
        fig_pie.update_traces(textposition="outside", textinfo="percent+label",
                               textfont_size=10)
        fig_pie.update_layout(
            **CHART,
            title="Partic. por Cliente",
            height=340,
            showlegend=False,
            margin=dict(t=40, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# ─── GRÁFICO: % ACERTO POR CLIENTE ───────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    if not df_rank.empty:
        df_ack = df_rank.sort_values("pct_acerto", ascending=True).tail(20)
        fig_ack = px.bar(df_ack, x="pct_acerto", y="razao_social", orientation="h",
                         title="% Acerto por Cliente (top 20)",
                         labels={"pct_acerto": "% Acerto", "razao_social": ""},
                         color="pct_acerto",
                         color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"],
                         range_color=[0, 100], text="pct_acerto")
        fig_ack.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_ack.update_layout(**CHART, coloraxis_showscale=False,
                              yaxis=dict(tickfont=dict(size=9)),
                              xaxis=GRID, height=400,
                              margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_ack, use_container_width=True)

# ─── GRÁFICO: TÍTULOS SEM GIRO ───────────────────────────────────────────────
with col4:
    try:
        df_sg = df_full[df_full["sem_giro"]].copy() if "sem_giro" in df_full.columns else pd.DataFrame()
    except Exception:
        df_sg = pd.DataFrame()

    if not df_sg.empty:
        df_sg_grp = (df_sg.groupby("titulo")
                     .agg(clientes_afetados=("codigo_cliente", "nunique"),
                          qtde_parada=("qtde_saldo", "sum"))
                     .reset_index().sort_values("qtde_parada", ascending=False).head(15))
        fig_sg = px.bar(df_sg_grp, x="qtde_parada", y="titulo", orientation="h",
                        title="Top 15 Títulos sem Giro",
                        labels={"qtde_parada": "Qtde parada", "titulo": ""},
                        color_discrete_sequence=["#F59E0B"], text="qtde_parada")
        fig_sg.update_traces(textposition="outside")
        fig_sg.update_layout(**CHART, yaxis=dict(tickfont=dict(size=9)),
                             xaxis=GRID, height=400,
                             margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_sg, use_container_width=True)
    else:
        st.success("✅ Todos os títulos têm ao menos um acerto!")

# ─── TABELA RANKING ───────────────────────────────────────────────────────────
st.markdown('<div class="card-title">Top Clientes por Receita de Consignação</div>',
            unsafe_allow_html=True)
if not df_rank.empty:
    df_show_rank = df_rank.head(30).copy()
    df_show_rank["pct_acerto"]    = df_show_rank["pct_acerto"].map("{:.1f}%".format)
    df_show_rank["valor_liquido"] = df_show_rank["valor_liquido"].map("R$ {:,.2f}".format)
    df_show_rank.columns = [
        {"codigo_cliente": "Código", "razao_social": "Cliente", "uf": "UF",
         "qtde_remessa": "Remessa", "qtde_dev_acert": "Dev/Acert",
         "qtde_saldo": "Saldo", "valor_liquido": "Vlr Líquido",
         "titulos": "Títulos", "pct_acerto": "% Acerto"}.get(c, c)
        for c in df_show_rank.columns
    ]
    st.dataframe(df_show_rank, use_container_width=True, hide_index=True, height=380)
    csv = df_rank.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇ Exportar CSV", csv, "ranking_clientes.csv", "text/csv")
