"""
Página 2 — Dashboard Principal
KPIs reais, volume por cliente, acerto × receita, drill-down mês a mês.
Acerto = Qtde Dev/Acert / Qtde Remessa × 100
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

st.set_page_config(page_title="Dashboard · Consignação", page_icon="📊", layout="wide")
init_db()

if "usuario" not in st.session_state or not st.session_state.usuario:
    st.warning("⚠️ Faça login para acessar esta página.")
    st.stop()

usuario = st.session_state.usuario
is_admin = usuario["papel"] == "admin"
cod_gcon_user = usuario.get("cod_gcon")  # código Gcon do vendedor logado
gcon_filter = None if is_admin else cod_gcon_user

DARK = dict(plot_bgcolor="#1e293b", paper_bgcolor="#1e293b",
            font_color="#e2e8f0", title_font_color="#f1f5f9")
GRID = dict(gridcolor="#334155")

st.markdown("""
<style>
.stApp { background: #0f172a; color: #e2e8f0; }
section[data-testid="stSidebar"] { background: #1e293b !important; }
.kpi { background:#1e293b; border:1px solid rgba(255,255,255,.08);
       border-radius:12px; padding:18px 20px; text-align:center; }
.kv  { font-size:28px; font-weight:700; }
.kl  { font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:#64748b; margin-top:3px; }
.ks  { font-size:12px; color:#94a3b8; margin-top:2px; }
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**👤 {usuario['nome']}**")
    st.markdown(f"`{usuario['papel'].upper()}`")
    if cod_gcon_user:
        st.caption(f"Gcon: `{cod_gcon_user}`")
    st.divider()

    # Admin pode filtrar por vendedor (Gcon)
    if is_admin:
        vendedores = [u for u in get_all_users() if u["papel"] == "vendedor" and u["ativo"]]
        opts_gcon = ["Todos os vendedores"] + [
            f"{v['nome']} ({v['cod_gcon'] or '—'})" for v in vendedores
        ]
        sel_vend = st.selectbox("Vendedor / Gcon", opts_gcon)
        if sel_vend != "Todos os vendedores":
            gcon_filter = next(
                (v["cod_gcon"] for v in vendedores
                 if f"{v['nome']} ({v['cod_gcon'] or '—'})" == sel_vend),
                None
            )

    # Filtro de cliente
    clientes = get_clientes(gcon_filter)
    opts_cli = ["Todos os clientes"] + [
        f"{c['razao_social'][:35]} [{c['codigo_cliente']}]" for c in clientes
    ]
    sel_cli = st.selectbox("Cliente (drill-down)", opts_cli)
    cliente_sel = None
    if sel_cli != "Todos os clientes":
        cliente_sel = sel_cli.split("[")[-1].rstrip("]")

    st.divider()
    if st.button("🚪 Sair"):
        st.session_state.usuario = None
        st.rerun()


# ─── DADOS ────────────────────────────────────────────────────────────────────
with st.spinner("Carregando dados..."):
    kpis    = get_kpis(gcon_filter)
    df_full = get_analise_consignacao(gcon_filter)
    df_rank = get_ranking_clientes(gcon_filter)
    df_fat_mes = get_faturamento_por_mes(gcon_filter)


# ─── HEADER ───────────────────────────────────────────────────────────────────
st.title("📊 Dashboard de Consignação")
st.caption(f"Visão geral · {usuario['nome']} · Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")


# ─── KPIs ────────────────────────────────────────────────────────────────────
def kpi(col, value, label, sub="", color="#f1f5f9"):
    col.markdown(f"""
    <div class="kpi">
      <div class="kv" style="color:{color}">{value}</div>
      <div class="kl">{label}</div>
      <div class="ks">{sub}</div>
    </div>""", unsafe_allow_html=True)

k = st.columns(7)
kpi(k[0], f"{kpis['total_clientes']:,}", "Clientes", "com saldo ativo")
kpi(k[1], f"{kpis['total_titulos']:,}", "Títulos", "em consignação")
kpi(k[2], f"{kpis['qtde_remessa_total']:,}", "Qtde Remessa", "total enviado")
kpi(k[3], f"{kpis['qtde_saldo_total']:,}", "Qtde em Saldo", "ainda no cliente")
kpi(k[4], f"{kpis['qtde_acerto_total']:,}", "Dev/Acerto", "retornou ou faturou")
kpi(k[5],
    f"{kpis['pct_acerto_medio']:.1f}%",
    "% Acerto Global",
    "Dev+Acert / Remessa",
    color="#34d399" if kpis["pct_acerto_medio"] >= 40 else "#f59e0b" if kpis["pct_acerto_medio"] >= 20 else "#f87171"
)
kpi(k[6],
    f"{kpis['titulos_sem_giro']:,}",
    "Títulos s/ Giro",
    "0 devol. ou acerto",
    color="#f59e0b" if kpis["titulos_sem_giro"] > 0 else "#34d399"
)

st.divider()


# ─── DRILL-DOWN POR CLIENTE ──────────────────────────────────────────────────
if cliente_sel and not df_full.empty:
    df_cli = df_full[df_full["codigo_cliente"] == cliente_sel].copy()
    if not df_cli.empty:
        razao = df_cli["razao_social"].iloc[0]
        st.subheader(f"📌 {razao}")

        m1, m2, m3, m4 = st.columns(4)
        qtde_rem = int(df_cli["qtde_remessa"].sum())
        qtde_dev = int(df_cli["qtde_dev_acert"].sum())
        qtde_sal = int(df_cli["qtde_saldo"].sum())
        pct = round(qtde_dev / qtde_rem * 100, 1) if qtde_rem > 0 else 0
        m1.metric("Qtde Remessa", f"{qtde_rem:,}")
        m2.metric("Dev/Acerto", f"{qtde_dev:,}")
        m3.metric("Saldo Atual", f"{qtde_sal:,}")
        m4.metric("% Acerto", f"{pct:.1f}%")

        # Faturamento mês a mês deste cliente (apenas Venda + Acerto Consignação)
        df_fat_cli = get_faturamento_df(gcon_filter, tipos_tes=["Venda", "Acerto Consignação"])
        if not df_fat_cli.empty:
            df_fat_cli = df_fat_cli[df_fat_cli["codigo_cliente"] == cliente_sel].copy()
            date_col_cli = "data_nota" if "data_nota" in df_fat_cli.columns else "data_emissao"
            df_fat_cli[date_col_cli] = pd.to_datetime(df_fat_cli[date_col_cli], errors="coerce")
            df_fat_cli = df_fat_cli.dropna(subset=[date_col_cli])

        col_ga, col_gb = st.columns(2)

        if not df_fat_cli.empty:
            df_fat_cli["mes"] = df_fat_cli[date_col_cli].dt.to_period("M").astype(str)

            # Agrupa por mês e tipo_tes para stacked bar
            df_mes_tipo = df_fat_cli.groupby(["mes", "tipo_tes"]).agg(
                receita=("valor_atendido", "sum"),
                qtde=("qtd_atendida", "sum")
            ).reset_index().sort_values("mes")

            df_mes = df_fat_cli.groupby("mes").agg(
                receita=("valor_atendido", "sum"),
                qtde=("qtd_atendida", "sum")
            ).reset_index().sort_values("mes")

            with col_ga:
                fig = px.bar(
                    df_mes_tipo, x="mes", y="receita", color="tipo_tes",
                    title="Receita por mês (Venda + Acerto Consignação)",
                    labels={"mes": "Mês", "receita": "R$", "tipo_tes": "Tipo"},
                    color_discrete_map={"Venda": "#3b82f6", "Acerto Consignação": "#10b981"}
                )
                fig.update_layout(**DARK, xaxis=dict(tickangle=-30, **GRID), yaxis=GRID, height=320)
                st.plotly_chart(fig, use_container_width=True)

            with col_gb:
                fig2 = px.line(df_mes, x="mes", y="qtde",
                               title="Qtde faturada por mês",
                               labels={"mes": "Mês", "qtde": "Qtde"},
                               markers=True, color_discrete_sequence=["#a78bfa"])
                fig2.update_layout(**DARK, xaxis=dict(tickangle=-30, **GRID), yaxis=GRID, height=320)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            with col_ga:
                st.info("Sem dados de faturamento para este cliente. Importe o arquivo de Faturamento e a Tabela TES.")

        # Tabela de títulos do cliente
        st.markdown("**Títulos em consignação:**")
        cols_show = ["isbn", "titulo", "qtde_remessa", "qtde_dev_acert",
                     "qtde_saldo", "pct_acerto", "valor_liquido", "dias_em_saldo"]
        cols_exist = [c for c in cols_show if c in df_cli.columns]
        df_show = df_cli[cols_exist].copy()
        df_show.columns = [
            {"isbn": "ISBN", "titulo": "Título", "qtde_remessa": "Remessa",
             "qtde_dev_acert": "Dev/Acert", "qtde_saldo": "Saldo",
             "pct_acerto": "% Acerto", "valor_liquido": "Valor Líq. (R$)",
             "dias_em_saldo": "Dias em Saldo"}.get(c, c)
            for c in cols_exist
        ]
        if "% Acerto" in df_show.columns:
            df_show["% Acerto"] = df_show["% Acerto"].map("{:.1f}%".format)
        if "Valor Líq. (R$)" in df_show.columns:
            df_show["Valor Líq. (R$)"] = df_show["Valor Líq. (R$)"].map("R$ {:,.2f}".format)
        if "Dias em Saldo" in df_show.columns:
            df_show["Dias em Saldo"] = df_show["Dias em Saldo"].fillna(0).astype(int)
        st.dataframe(df_show, use_container_width=True, hide_index=True, height=360)

        st.divider()


# ─── GRÁFICOS PRINCIPAIS ─────────────────────────────────────────────────────
if df_full.empty:
    st.info("Sem dados. Acesse **Upload** para importar os arquivos.")
    st.stop()

col1, col2 = st.columns(2)

# Gráfico 1: Volume Saldo por Cliente (top 20)
with col1:
    if not df_rank.empty:
        top20 = df_rank.head(20).copy()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Remessa", x=top20["razao_social"].str[:22],
            y=top20["qtde_remessa"], marker_color="#334155"
        ))
        fig.add_trace(go.Bar(
            name="Saldo Atual", x=top20["razao_social"].str[:22],
            y=top20["qtde_saldo"], marker_color="#3b82f6"
        ))
        fig.add_trace(go.Bar(
            name="Dev/Acerto", x=top20["razao_social"].str[:22],
            y=top20["qtde_dev_acert"], marker_color="#34d399"
        ))
        fig.update_layout(
            title="Volume Consignação por Cliente (top 20)",
            barmode="group",
            **DARK,
            xaxis=dict(tickangle=-35, tickfont=dict(size=9), **GRID),
            yaxis=GRID,
            legend=dict(bgcolor="#1e293b", orientation="h", y=1.08),
            height=420
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("💡 Selecione um cliente no filtro lateral para ver o detalhe mês a mês.")

# Gráfico 2: % Acerto por Cliente
with col2:
    if not df_rank.empty:
        df_ack = df_rank.sort_values("pct_acerto", ascending=True).tail(20)
        fig2 = px.bar(
            df_ack, x="pct_acerto", y="razao_social",
            orientation="h",
            title="% Acerto por Cliente (Dev/Acert ÷ Remessa)",
            labels={"pct_acerto": "% Acerto", "razao_social": ""},
            color="pct_acerto",
            color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
            range_color=[0, 100],
            text="pct_acerto"
        )
        fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig2.update_layout(
            **DARK,
            coloraxis_showscale=False,
            yaxis=dict(tickfont=dict(size=9)),
            xaxis=dict(**GRID),
            height=420
        )
        st.plotly_chart(fig2, use_container_width=True)

col3, col4 = st.columns(2)

# Gráfico 3: Títulos sem giro (top 15 por volume parado)
with col3:
    df_sg = df_full[df_full["sem_giro"]].copy() if not df_full.empty else pd.DataFrame()
    if not df_sg.empty:
        df_sg_grp = (
            df_sg.groupby("titulo")
            .agg(clientes_afetados=("codigo_cliente", "nunique"), qtde_parada=("qtde_saldo", "sum"))
            .reset_index()
            .sort_values("qtde_parada", ascending=False)
            .head(15)
        )
        fig3 = px.bar(
            df_sg_grp, x="qtde_parada", y="titulo",
            orientation="h",
            title=f"Top 15 Títulos sem Giro ({kpis['titulos_sem_giro']} total)",
            labels={"qtde_parada": "Qtde parada", "titulo": ""},
            color_discrete_sequence=["#f59e0b"],
            text="qtde_parada"
        )
        fig3.update_traces(textposition="outside")
        fig3.update_layout(**DARK, yaxis=dict(tickfont=dict(size=9)), xaxis=GRID, height=400)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.success("✅ Todos os títulos têm ao menos um acerto registrado!")

# Gráfico 4: Faturamento mensal (se disponível) ou Dias em Saldo
with col4:
    if not df_fat_mes.empty:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            name="Venda direta", x=df_fat_mes["mes"],
            y=df_fat_mes.get("receita_venda", df_fat_mes.get("receita_total", [])),
            marker_color="#3b82f6", yaxis="y"
        ))
        if "receita_acerto_csg" in df_fat_mes.columns:
            fig4.add_trace(go.Bar(
                name="Acerto Consignação", x=df_fat_mes["mes"],
                y=df_fat_mes["receita_acerto_csg"], marker_color="#10b981", yaxis="y"
            ))
        fig4.add_trace(go.Scatter(
            name="Clientes", x=df_fat_mes["mes"],
            y=df_fat_mes["clientes"], mode="lines+markers",
            marker_color="#a78bfa", yaxis="y2"
        ))
        fig4.update_layout(
            title="Faturamento Mensal (Venda + Acerto Consignação)",
            barmode="stack",
            **DARK,
            xaxis=dict(tickangle=-30, **GRID),
            yaxis=dict(title="Receita (R$)", **GRID),
            yaxis2=dict(title="Clientes", overlaying="y", side="right"),
            legend=dict(bgcolor="#1e293b", orientation="h", y=1.05),
            height=400
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        # Curva ABC dos títulos em saldo (se tiver base de produtos)
        if "curva" in df_full.columns:
            df_curva = (
                df_full.groupby("curva")
                .agg(qtde_saldo=("qtde_saldo", "sum"), titulos=("isbn", "nunique"))
                .reset_index()
                .dropna(subset=["curva"])
            )
            fig4 = px.pie(
                df_curva, names="curva", values="qtde_saldo",
                title="Distribuição Saldo por Curva ABC",
                color_discrete_map={"A": "#34d399", "B": "#f59e0b", "C": "#ef4444"}
            )
            fig4.update_layout(**DARK, height=400)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Importe o Faturamento para ver a evolução mensal.")


# ─── TABELA DE RANKING ───────────────────────────────────────────────────────
with st.expander("📋 Ranking completo de clientes"):
    if not df_rank.empty:
        df_show = df_rank.copy()
        df_show["pct_acerto"] = df_show["pct_acerto"].map("{:.1f}%".format)
        df_show["valor_liquido"] = df_show["valor_liquido"].map("R$ {:,.2f}".format)
        df_show.columns = [
            "Cód. Cliente", "Razão Social", "UF",
            "Qtde Remessa", "Dev/Acerto", "Saldo Atual",
            "Valor Líquido", "Títulos", "% Acerto"
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)
        csv = df_show.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇ Exportar CSV", csv, "ranking_clientes.csv", "text/csv")


# ─── ANÁLISE DETALHADA ────────────────────────────────────────────────────────
with st.expander("🔍 Análise detalhada — por título e cliente"):
    if not df_full.empty:
        cols_sel = ["codigo_cliente", "razao_social", "uf", "isbn", "titulo",
                    "qtde_remessa", "qtde_dev_acert", "qtde_saldo",
                    "pct_acerto", "valor_liquido", "dias_em_saldo", "status_titulo"]
        cols_exist = [c for c in cols_sel if c in df_full.columns]
        df_det = df_full[cols_exist].copy()

        if "curva" in df_full.columns:
            df_det["curva"] = df_full["curva"]

        # Filtros inline
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            f_sg = st.checkbox("Somente sem giro", False)
        with col_f2:
            f_curva = st.multiselect("Curva", ["A", "B", "C"], default=[])
        with col_f3:
            f_min_dias = st.number_input("Dias em saldo ≥", min_value=0, value=0)

        if f_sg:
            df_det = df_det[df_det.get("sem_giro", False) == True] if "sem_giro" in df_full.columns else df_det
        if f_curva and "curva" in df_det.columns:
            df_det = df_det[df_det["curva"].isin(f_curva)]
        if f_min_dias > 0 and "dias_em_saldo" in df_det.columns:
            df_det = df_det[pd.to_numeric(df_det["dias_em_saldo"], errors="coerce").fillna(0) >= f_min_dias]

        if "pct_acerto" in df_det.columns:
            df_det["pct_acerto"] = df_det["pct_acerto"].map("{:.1f}%".format)
        if "valor_liquido" in df_det.columns:
            df_det["valor_liquido"] = pd.to_numeric(df_det["valor_liquido"], errors="coerce").map("R$ {:,.2f}".format)
        if "dias_em_saldo" in df_det.columns:
            df_det["dias_em_saldo"] = pd.to_numeric(df_det["dias_em_saldo"], errors="coerce").fillna(0).astype(int)

        st.dataframe(df_det, use_container_width=True, hide_index=True, height=400)
        csv2 = df_det.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇ Exportar detalhe CSV", csv2, "analise_detalhada.csv", "text/csv")
