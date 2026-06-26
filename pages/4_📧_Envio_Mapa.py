"""
Página 4 — Envio do Mapa de Consignação
Seleciona clientes, gera mapa Excel, envia por email (Outlook/M365).
"""
import streamlit as st
import pandas as pd
import io
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.database import (
    get_clientes, get_status_envio_mes, get_saldo_df,
    registrar_envio, init_db, get_all_users, get_envios_df
)
from utils.email_service import build_mapa_email_html, send_email_graph
from utils.mapa_generator import gerar_mapa_excel
from utils.style import apply_theme, sidebar_header, sidebar_footer

st.set_page_config(page_title="Envio Mapa · Consignação", page_icon="📧", layout="wide",
                   initial_sidebar_state="expanded")
init_db()
apply_theme()

if "usuario" not in st.session_state or not st.session_state.usuario:
    st.warning("⚠️ Faça login para acessar esta página.")
    st.stop()

usuario = st.session_state.usuario
is_admin = usuario["papel"] == "admin"
gcon_filter = None if is_admin else usuario.get("cod_gcon")

sidebar_header(usuario)
with st.sidebar:
    st.markdown('<div class="sidebar-section">Envio</div>', unsafe_allow_html=True)
sidebar_footer(usuario)

st.markdown("""
<div class="page-header">
  <div>
    <div class="page-title">📧 Envio do Mapa de Consignação</div>
    <div class="page-subtitle">Gere e envie o mapa mensal para cada cliente</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── CONFIGURAÇÃO DE EMAIL ────────────────────────────────────────────────────
with st.expander("⚙️ Configuração de Email (Outlook/M365)", expanded=False):
    st.markdown("""
    As credenciais são lidas do arquivo `.streamlit/secrets.toml`.
    Se ainda não configurou, veja as instruções na página **Configurações**.
    """)
    try:
        client_id = st.secrets.get("AZURE_CLIENT_ID", "")
        client_secret = st.secrets.get("AZURE_CLIENT_SECRET", "")
        tenant_id = st.secrets.get("AZURE_TENANT_ID", "")
        email_configured = all([client_id, client_secret, tenant_id])
    except Exception:
        email_configured = False

    if email_configured:
        st.success("✅ Credenciais Azure configuradas.")
    else:
        st.warning("⚠️ Credenciais Azure não configuradas. O envio por email estará desativado.")
        st.code("""
# .streamlit/secrets.toml
AZURE_CLIENT_ID     = "seu-client-id"
AZURE_CLIENT_SECRET = "seu-client-secret"
AZURE_TENANT_ID     = "seu-tenant-id"
""", language="toml")


# ─── SELEÇÃO DE MÊS E REMETENTE ──────────────────────────────────────────────
col_conf1, col_conf2 = st.columns([1, 2])

with col_conf1:
    mes_sel = st.selectbox(
        "Mês de referência",
        pd.date_range(end=datetime.now(), periods=12, freq="MS").strftime("%Y-%m").tolist()[::-1],
        key="mes_envio"
    )

with col_conf2:
    from_email = usuario.get("email_envio") or usuario.get("email") or ""
    from_email_input = st.text_input("Email do remetente (seu email Outlook)", value=from_email)
    from_nome = st.text_input("Nome que aparece no email", value=usuario["nome"])

st.divider()

# ─── LISTA DE CLIENTES ────────────────────────────────────────────────────────
df_status = get_status_envio_mes(gcon_filter)
df_saldo = get_saldo_df(gcon_filter)

if df_status.empty:
    st.info("Nenhum cliente. Importe o **Saldo Consignado** na página Upload.")
    st.stop()

st.subheader("Selecione os clientes para envio")

filtro_rapido = st.radio(
    "Mostrar",
    ["Todos", "Ainda não enviados este mês", "Enviados — para reenvio"],
    horizontal=True
)

df_view = df_status.copy()
if filtro_rapido == "Ainda não enviados este mês":
    df_view = df_view[~df_view["mapa_enviado"]]
elif filtro_rapido == "Enviados — para reenvio":
    df_view = df_view[df_view["mapa_enviado"]]

st.markdown(f"**{len(df_view)} clientes disponíveis:**")

selecionar_todos = st.checkbox("Selecionar todos visíveis")

selecionados = []
for _, row in df_view.iterrows():
    cod = row["codigo_cliente"]
    razao = row["razao_social"] or cod
    email_cli = row.get("email") or ""
    enviado = row["mapa_enviado"]

    badge = "🟢" if enviado else "🔴"
    label = f"{badge} **{razao}** · `{cod}` · {email_cli or '⚠️ sem email'}"

    checked = st.checkbox(label, value=selecionar_todos, key=f"sel_{cod}")
    if checked:
        selecionados.append(row)

st.divider()

# ─── PREVIEW E ENVIO ─────────────────────────────────────────────────────────
if selecionados:
    st.markdown(f"**{len(selecionados)} cliente(s) selecionado(s)**")

    # Preview do primeiro selecionado
    primeiro = selecionados[0]
    cod_prev = primeiro["codigo_cliente"]
    cnpj_prev = primeiro.get("cnpj") or ""

    df_saldo_prev = df_saldo[df_saldo["codigo_cliente"] == cod_prev]

    with st.expander(f"👁 Preview do mapa — {primeiro['razao_social']}", expanded=True):
        if not df_saldo_prev.empty:
            cols_show = ["isbn", "titulo", "qtde_saldo", "qtde_remessa", "qtde_dev_acert", "valor_liquido"]
            cols_show = [c for c in cols_show if c in df_saldo_prev.columns]
            preview_df = df_saldo_prev[cols_show].copy()
            preview_df.columns = [c.replace("qtde_", "Qtde ").replace("valor_liquido", "Vlr Líquido")
                                   .replace("isbn", "ISBN").replace("titulo", "Título")
                                   for c in cols_show]
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
        else:
            st.warning("Sem dados de consignação para este cliente.")

    # ─── BOTÕES ──────────────────────────────────────────────────────────────
    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        if not df_saldo_prev.empty:
            excel_prev = gerar_mapa_excel(
                df_saldo=df_saldo_prev,
                codigo_cliente=cod_prev,
                razao_social=primeiro["razao_social"],
                cnpj=cnpj_prev,
                mes_referencia=mes_sel,
                codigo_rastreio="PREVIEW",
                vendedor_nome=from_nome,
            )
            st.download_button(
                "⬇ Baixar mapa do primeiro selecionado (Excel)",
                data=excel_prev,
                file_name=f"mapa_consignacao_{cod_prev}_{mes_sel}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with col_btn2:
        enviar_btn = st.button(
            f"📨 Enviar mapa para {len(selecionados)} cliente(s)",
            type="primary",
            disabled=not email_configured
        )

    if not email_configured:
        st.caption("⚠️ Configure as credenciais Azure para habilitar o envio.")

    if enviar_btn and email_configured:
        progress_bar = st.progress(0, text="Iniciando envios...")
        resultados = []

        for i, row in enumerate(selecionados):
            cod = row["codigo_cliente"]
            razao = row["razao_social"] or cod
            email_cli = row.get("email") or ""
            cnpj_cli = row.get("cnpj") or ""
            eh_reenvio = row.get("mapa_enviado", False)

            if not email_cli:
                resultados.append({"cliente": razao, "status": "❌ Sem email cadastrado"})
                continue

            df_cli_saldo = df_saldo[df_saldo["codigo_cliente"] == cod]

            if df_cli_saldo.empty:
                resultados.append({"cliente": razao, "status": "❌ Sem saldo consignado"})
                continue

            # Registra envio para obter código de rastreio
            cod_rastreio = registrar_envio(
                codigo_cliente=cod,
                razao_social=razao,
                email_cliente=email_cli,
                cod_gcon=gcon_filter or usuario.get("cod_gcon") or "",
                mes_referencia=mes_sel,
                status="enviado",
                reenviado=eh_reenvio
            )

            # Gera o Excel em memória
            excel_bytes = gerar_mapa_excel(
                df_saldo=df_cli_saldo,
                codigo_cliente=cod,
                razao_social=razao,
                cnpj=cnpj_cli,
                mes_referencia=mes_sel,
                codigo_rastreio=cod_rastreio,
                vendedor_nome=from_nome,
            )

            # Itens para corpo do email (resumo)
            itens = df_cli_saldo[["isbn", "titulo", "qtde_saldo", "valor_liquido"]].rename(
                columns={"isbn": "codigo", "titulo": "titulo",
                         "qtde_saldo": "quantidade", "valor_liquido": "preco_unitario"}
            ).to_dict("records") if not df_cli_saldo.empty else []

            # Monta corpo HTML
            body_html = build_mapa_email_html(
                razao_social=razao, vendedor_nome=from_nome,
                mes_referencia=mes_sel, codigo_rastreio=cod_rastreio,
                itens_mapa=itens
            )

            # Envia via Graph API
            ok, msg = send_email_graph(
                from_email=from_email_input,
                to_email=email_cli,
                subject=f"Mapa de Consignação — {razao} — {mes_sel}",
                body_html=body_html,
                client_id=client_id,
                client_secret=client_secret,
                tenant_id=tenant_id,
                attachment_bytes=excel_bytes,
                attachment_filename=f"mapa_consignacao_{cod}_{mes_sel}.xlsx"
            )

            status_label = "✅ Enviado" if ok else f"❌ Erro: {msg}"
            resultados.append({"cliente": razao, "email": email_cli, "status": status_label})
            progress_bar.progress((i + 1) / len(selecionados), text=f"{i+1}/{len(selecionados)} processados")

        enviados_ok = sum(1 for r in resultados if "✅" in r["status"])
        st.success(f"Processo concluído! {enviados_ok}/{len(selecionados)} enviados.")
        st.dataframe(pd.DataFrame(resultados), use_container_width=True, hide_index=True)

# ─── HISTÓRICO DE ENVIOS ─────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Histórico de envios")

df_hist = get_envios_df(gcon_filter, mes_referencia=mes_sel)

if not df_hist.empty:
    df_hist_show = df_hist[["data_envio", "razao_social", "email_cliente",
                             "status", "codigo_rastreio", "reenviado"]].copy()
    df_hist_show["data_envio"] = pd.to_datetime(df_hist_show["data_envio"]).dt.strftime("%d/%m/%Y %H:%M")
    df_hist_show["reenviado"] = df_hist_show["reenviado"].map({0: "Não", 1: "Sim"})
    df_hist_show.columns = ["Data Envio", "Cliente", "Email", "Status", "Rastreio", "Reenvio"]
    st.dataframe(df_hist_show, use_container_width=True, hide_index=True)

    csv = df_hist_show.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇ Exportar histórico CSV", csv, "historico_envios.csv", "text/csv")
else:
    st.info("Nenhum envio registrado para este mês.")
