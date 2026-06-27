"""
Página 2 — Dashboard Principal · Layout Artmed
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.database import (
    get_kpis, get_analise_consignacao, get_ranking_clientes,
    get_faturamento_por_mes, get_faturamento_df,
    get_all_users, get_clientes, init_db
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

# Cores para gráficos (tema claro)
CHART = dict(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
             font_color="#374151", title_font_color="#111827",
             title_font_size=14)
GRID  = dict(gridcolor="#F3F4F6", zerolinecolor="#E5E7EB")

# ─── SIDEBAR — só logo e footer ───────────────────────────────────────────────
sidebar_header(usuario)
sidebar_footer(usuario)

# ─── DADOS ────────────────────────────────────────────────────────────────────
with st.spinner("Carregando dados..."):
    clientes   = get_clientes(gcon_filter)
    kpis       = get_kpis(gcon_filter)
    df_full    = get_analise_consignacao(gcon_filter)
    df_rank    = get_ranking_clientes(gcon_filter)
    df_fat_mes = get_faturamento_por_mes(gcon_filter)

# ─── CABEÇALHO COM FILTROS ─────────────────────────────────────────────────────
# Linha do cabeçalho: título à esquerda, filtros à direita
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
        vendedores = [u for u in get_all_users() if u["papel"] == "vendedor" and u["ativo"]]
        opts_gcon  = ["Todos os vendedores"] + [
            f"{v['nome']} ({v['cod_gcon'] or '—'})" for v in vendedores
        ]
        sel_vend = st.selectbox("Vendedor", opts_gcon, label_visibility="visible")
        if sel_vend != "Todos os vendedores":
            gcon_filter = next(
                (v["cod_gcon"] for v in vendedores
                 if f"{v['nome']} ({v['cod_gcon'] or '—'})" == sel_vend), None
            )
            clientes = get_clientes(gcon_filter)

opts_cli  = ["Todos os clientes"] + [
    f"{c['razao_social'][:28]} [{c['codigo_cliente']}]" for c in clientes
]
with col_cli:
    sel_cli = st.selectbox("Cliente (drill-down)", opts_cli, label_visibility="visible")

cliente_sel = None
if sel_cli != "Todos os clientes":
    cliente_sel = sel_cli.split("[")[-1].rstrip("]")

st.markdown("<hr style='margin:8px 0 16px 0;border-color:#E5E7EB;'>", unsafe_allow_html=True)

# ─── KPIs ─────────────────────────────────────────────────────────────────────
pct = kpis["pct_acerto_medio"]
pct_cor = "green" if pct >= 40 else "amber" if pct >= 20 else "red"
sg_cor  = "amber" if kpis["titulos_sem_giro"] > 0 else "green"

k = st.columns(4)
k[0].markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">Clientes Ativos</div>
  <div class="kpi-value teal">{kpis['total_clientes']:,}</div>
  <div class="kpi-sub">com saldo consignado</div>
</div>""", unsafe_allow_html=True)

k[1].markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">Saldo Consignado</div>
  <div class="kpi-value blue">{kpis['qtde_saldo_total']:,}</div>
  <div class="kpi-sub">itens no cliente · Rem: {kpis['qtde_remessa_total']:,}</div>
</div>""", unsafe_allow_html=True)

k[2].markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">% Acerto Global</div>
  <div class="kpi-value {pct_cor}">{pct:.1f}%</div>
  <div class="kpi-sub">Dev+Acert ÷ Remessa · {kpis['qtde_acerto_total']:,} unid.</div>
</div>""", unsafe_allow_html=True)

k[3].markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">Títulos sem Giro</div>
  <div class="kpi-value {sg_cor}">{kpis['titulos_sem_giro']:,}</div>
  <div class="kpi-sub">em {kpis['clientes_sem_giro']} clientes · 0 devolução</div>
</div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

k2 = st.columns(4)
k2[0].markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">Títulos em Consignação</div>
  <div class="kpi-value">{kpis['total_titulos']:,}</div>
  <div class="kpi-sub">ISBNs distintos</div>
</div>""", unsafe_allow_html=True)

k2[1].markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">Qtde Remessa Total</div>
  <div class="kpi-value">{kpis['qtde_remessa_total']:,}</div>
  <div class="kpi-sub">unidades enviadas</div>
</div>""", unsafe_allow_html=True)

k2[2].markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">Dev / Acerto</div>
  <div class="kpi-value">{kpis['qtde_acerto_total']:,}</div>
  <div class="kpi-sub">unidades retornadas ou faturadas</div>
</div>""", unsafe_allow_html=True)

vl = kpis.get("valor_liquido_total", 0)
k2[3].markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">Valor Líquido Total</div>
  <div class="kpi-value">R$ {vl:,.0f}</div>
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

        st.markdown(f"""
        <div class="content-card">
          <div class="card-title">📌 {razao}</div>
        </div>
        """, unsafe_allow_html=True)

        mc = st.columns(4)
        mc[0].metric("Qtde Remessa", f"{qtde_rem:,}")
        mc[1].metric("Dev/Acerto", f"{qtde_dev:,}")
        mc[2].metric("Saldo Atual", f"{qtde_sal:,}")
        mc[3].metric("% Acerto", f"{pct_cli:.1f}%")

        # Faturamento mês a mês
        df_fat_cli = get_faturamento_df(gcon_filter, tipos_tes=["Venda", "Acerto Consignação"])
        col_ga, col_gb = st.columns(2)

        if not df_fat_cli.empty:
            df_fat_cli = df_fat_cli[df_fat_cli["codigo_cliente"] == cliente_sel].copy()
            date_col   = "data_nota" if "data_nota" in df_fat_cli.columns else "data_emissao"
            df_fat_cli[date_col] = pd.to_datetime(df_fat_cli[date_col], errors="coerce")
            df_fat_cli = df_fat_cli.dropna(subset=[date_col])

        if not df_fat_cli.empty:
            df_fat_cli["mes"] = df_fat_cli[date_col].dt.to_period("M").astype(str)
            df_mes_tipo = df_fat_cli.groupby(["mes","tipo_tes"]).agg(
                receita=("valor_atendido","sum"), qtde=("qtd_atendida","sum")
            ).reset_index().sort_values("mes")
            df_mes = df_fat_cli.groupby("mes").agg(
                receita=("valor_atendido","sum"), qtde=("qtd_atendida","sum")
            ).reset_index().sort_values("mes")

            with col_ga:
                fig = px.bar(df_mes_tipo, x="mes", y="receita", color="tipo_tes",
                             title="Receita Mensal por Tipo",
                             labels={"mes":"Mês","receita":"R$","tipo_tes":"Tipo"},
                             color_discrete_map={"Venda":"#3B82F6","Acerto Consignação":COR_TEAL})
                fig.update_layout(**CHART, xaxis=dict(tickangle=-30,**GRID), yaxis=GRID, height=300,
                                  legend=dict(orientation="h",y=1.1))
                st.plotly_chart(fig, use_container_width=True)

            with col_gb:
                fig2 = px.line(df_mes, x="mes", y="qtde", markers=True,
                               title="Qtde Faturada por Mês",
                               labels={"mes":"Mês","qtde":"Qtde"},
                               color_discrete_sequence=[COR_TEAL])
                fig2.update_layout(**CHART, xaxis=dict(tickangle=-30,**GRID), yaxis=GRID, height=300)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            with col_ga:
                st.info("Sem dados de faturamento para este cliente.")

        # Tabela de títulos
        st.markdown('<div class="card-title" style="margin-top:8px;">Títulos em Consignação</div>',
                    unsafe_allow_html=True)
        cols_show  = ["isbn","titulo","qtde_remessa","qtde_dev_acert","qtde_saldo",
                      "pct_acerto","valor_liquido","dias_em_saldo"]
        cols_exist = [c for c in cols_show if c in df_cli.columns]
        df_show    = df_cli[cols_exist].copy()
        RENAME = {"isbn":"ISBN","titulo":"Título","qtde_remessa":"Remessa",
                  "qtde_dev_acert":"Dev/Acert","qtde_saldo":"Saldo",
                  "pct_acerto":"% Acerto","valor_liquido":"Vlr Líq (R$)","dias_em_saldo":"Dias"}
        df_show.columns = [RENAME.get(c,c) for c in cols_exist]
        if "% Acerto" in df_show.columns:
            df_show["% Acerto"] = df_show["% Acerto"].map("{:.1f}%".format)
        if "Vlr Líq (R$)" in df_show.columns:
            df_show["Vlr Líq (R$)"] = df_show["Vlr Líq (R$)"].map("R$ {:,.2f}".format)
        if "Dias" in df_show.columns:
            df_show["Dias"] = df_show["Dias"].fillna(0).astype(int)
        st.dataframe(df_show, use_container_width=True, hide_index=True, height=360)
        st.markdown("<hr>", unsafe_allow_html=True)

# ─── GRÁFICOS PRINCIPAIS ─────────────────────────────────────────────────────
if df_full.empty:
    st.info("Sem dados. Acesse **Upload** para importar os arquivos.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="content-card"><div class="card-title">Receita Mensal</div>', unsafe_allow_html=True)
    if not df_fat_mes.empty:
        fig_fat = go.Figure()
        fig_fat.add_trace(go.Bar(
            name="Venda", x=df_fat_mes["mes"],
            y=df_fat_mes.get("receita_venda", []), marker_color="#3B82F6"
        ))
        if "receita_acerto_csg" in df_fat_mes.columns:
            fig_fat.add_trace(go.Bar(
                name="Acerto Consignação", x=df_fat_mes["mes"],
                y=df_fat_mes["receita_acerto_csg"], marker_color=COR_TEAL
            ))
        fig_fat.update_layout(**CHART, barmode="stack",
                              xaxis=dict(tickangle=-30,**GRID), yaxis=GRID,
                              legend=dict(orientation="h",y=1.08), height=320,
                              yaxis_title="R$")
        st.plotly_chart(fig_fat, use_container_width=True)
    else:
        st.info("Sem dados de faturamento. Importe o arquivo de Faturamento.")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="content-card"><div class="card-title">Top 10 Clientes por Saldo</div>', unsafe_allow_html=True)
    if not df_rank.empty:
        top10 = df_rank.head(10).copy()
        fig_pie = px.pie(top10, names="razao_social", values="qtde_saldo",
                         hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Set2)
        fig_pie.update_traces(textposition="outside", textinfo="percent+label",
                               textfont_size=10)
        fig_pie.update_layout(**CHART, height=320, showlegend=False,
                               margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

col3, col4 = st.columns(2)

with col3:
    st.markdown('<div class="content-card"><div class="card-title">% Acerto por Cliente (top 20)</div>', unsafe_allow_html=True)
    if not df_rank.empty:
        df_ack = df_rank.sort_values("pct_acerto", ascending=True).tail(20)
        fig2 = px.bar(df_ack, x="pct_acerto", y="razao_social", orientation="h",
                      labels={"pct_acerto":"% Acerto","razao_social":""},
                      color="pct_acerto",
                      color_continuous_scale=["#EF4444","#F59E0B","#10B981"],
                      range_color=[0,100], text="pct_acerto")
        fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig2.update_layout(**CHART, coloraxis_showscale=False,
                           yaxis=dict(tickfont=dict(size=9)), xaxis=GRID, height=380)
        st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="content-card"><div class="card-title">Top 15 Títulos sem Giro</div>', unsafe_allow_html=True)
    df_sg = df_full[df_full["sem_giro"]].copy() if not df_full.empty else pd.DataFrame()
    if not df_sg.empty:
        df_sg_grp = (df_sg.groupby("titulo")
                     .agg(clientes_afetados=("codigo_cliente","nunique"),
                          qtde_parada=("qtde_saldo","sum"))
                     .reset_index().sort_values("qtde_parada",ascending=False).head(15))
        fig3 = px.bar(df_sg_grp, x="qtde_parada", y="titulo", orientation="h",
                      labels={"qtde_parada":"Qtde parada","titulo":""},
                      color_discrete_sequence=["#F59E0B"], text="qtde_parada")
        fig3.update_traces(textposition="outside")
        fig3.update_layout(**CHART, yaxis=dict(tickfont=dict(size=9)),
                           xaxis=GRID, height=380)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.success("✅ Todos os títulos têm ao menos um acerto!")
    st.markdown('</div>', unsafe_allow_html=True)

# ─── TABELA RANKING ──────────────────────────────────────────────────────────
st.markdown('<div class="content-card"><div class="card-title">Top Clientes por Receita de Consignação</div>', unsafe_allow_html=True)
if not df_rank.empty:
    df_show_rank = df_rank.head(30).copy()
    df_show_rank["pct_acerto"] = df_show_rank["pct_acerto"].map("{:.1f}%".format)
    df_show_rank["valor_liquido"] = df_show_rank["valor_liquido"].map("R$ {:,.2f}".format)
    df_show_rank.columns = [
        {"codigo_cliente":"Código","razao_social":"Cliente","uf":"UF",
         "qtde_remessa":"Remessa","qtde_dev_acert":"Dev/Acert",
         "qtde_saldo":"Saldo","valor_liquido":"Vlr Líquido","titulos":"Títulos",
         "pct_acerto":"% Acerto"}.get(c,c) for c in df_show_rank.columns
    ]
    st.dataframe(df_show_rank, use_container_width=True, hide_index=True, height=380)
    csv = df_rank.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇ Exportar CSV", csv, "ranking_clientes.csv", "text/csv")
st.markdown('</div>', unsafe_allow_html=True)
