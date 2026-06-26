"""
Página 3 — Gestão de Clientes
Listagem, edição de email, status de envio do mapa.
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.database import (
    get_clientes, update_cliente_email,
    get_status_envio_mes, init_db
)

st.set_page_config(page_title="Clientes · Consignação", page_icon="👥", layout="wide")
init_db()

if "usuario" not in st.session_state or not st.session_state.usuario:
    st.warning("⚠️ Faça login para acessar esta página.")
    st.stop()

usuario = st.session_state.usuario
is_admin = usuario["papel"] == "admin"
vend_filter = None if is_admin else usuario["username"]

st.markdown("""
<style>
.stApp { background: #0f172a; color: #e2e8f0; }
section[data-testid="stSidebar"] { background: #1e293b !important; }
.status-ok    { color: #34d399; font-weight: 600; }
.status-pend  { color: #f59e0b; font-weight: 600; }
.status-wait  { color: #60a5fa; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"**👤 {usuario['nome']}**")
    st.markdown(f"`{usuario['papel'].upper()}`")
    st.divider()

    mes_sel = st.selectbox(
        "Mês de referência",
        pd.date_range(end=datetime.now(), periods=12, freq="MS").strftime("%Y-%m").tolist()[::-1]
    )

    filtro_status = st.multiselect(
        "Filtrar por status",
        ["Não enviado", "Enviado", "Aguardando retorno"],
        default=[]
    )

    st.divider()
    if st.button("🚪 Sair"):
        st.session_state.usuario = None
        st.rerun()

st.title("👥 Clientes")
st.caption(f"Referência: **{mes_sel}** · {usuario['nome']}")

# ─── STATUS DE ENVIO DO MÊS ──────────────────────────────────────────────────
df_status = get_status_envio_mes(vend_filter)

if df_status.empty:
    st.info("Nenhum cliente encontrado. Importe o Saldo Consignado na página **Upload**.")
    st.stop()

# Métricas rápidas
total = len(df_status)
enviados = df_status["mapa_enviado"].sum()
nao_enviados = total - enviados
aguard = (df_status["ultimo_status"] == "aguardando_retorno").sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total de Clientes", total)
m2.metric("Mapa Enviado", int(enviados), delta=f"{int(enviados/total*100)}% do total" if total else None)
m3.metric("Ainda não enviado", int(nao_enviados))
m4.metric("Aguardando retorno", int(aguard))

st.divider()

# ─── TABELA DE CLIENTES ───────────────────────────────────────────────────────
# Aplica filtros de status
df_view = df_status.copy()
if filtro_status:
    conds = []
    if "Não enviado" in filtro_status:
        conds.append(~df_view["mapa_enviado"])
    if "Enviado" in filtro_status:
        conds.append(df_view["mapa_enviado"] & (df_view["ultimo_status"] != "aguardando_retorno"))
    if "Aguardando retorno" in filtro_status:
        conds.append(df_view["ultimo_status"] == "aguardando_retorno")
    if conds:
        import functools, operator
        df_view = df_view[functools.reduce(operator.or_, conds)]

# Busca textual
busca = st.text_input("🔍 Buscar cliente (nome, CNPJ ou código)...", key="busca_cli")
if busca:
    mask = (
        df_view["razao_social"].str.contains(busca, case=False, na=False) |
        df_view["codigo_cliente"].str.contains(busca, case=False, na=False) |
        df_view["cnpj"].fillna("").str.contains(busca, na=False)
    )
    df_view = df_view[mask]

st.markdown(f"**{len(df_view)} clientes** encontrados")

# Renderiza como cards interativos
for _, row in df_view.iterrows():
    cod = row["codigo_cliente"]
    razao = row["razao_social"] or cod
    cnpj = row.get("cnpj") or "—"
    email = row.get("email") or ""
    enviado = row["mapa_enviado"]
    ultimo_envio = row.get("ultimo_envio")
    status_txt = row.get("ultimo_status") or "não enviado"

    # Badge de status
    if not enviado:
        badge = "🔴 Não enviado"
        badge_class = "status-pend"
    elif status_txt == "aguardando_retorno":
        badge = "🔵 Aguardando retorno"
        badge_class = "status-wait"
    else:
        badge = "🟢 Enviado"
        badge_class = "status-ok"

    with st.expander(f"**{razao}** — {badge}", expanded=False):
        c1, c2 = st.columns([2, 1])

        with c1:
            st.markdown(f"**Código:** `{cod}` · **CNPJ:** {cnpj}")
            if ultimo_envio:
                st.markdown(f"**Último envio:** {pd.Timestamp(ultimo_envio).strftime('%d/%m/%Y %H:%M')}")
            else:
                st.markdown("**Último envio:** —")

        with c2:
            novo_email = st.text_input(
                "Email do cliente",
                value=email,
                key=f"email_{cod}",
                placeholder="cliente@email.com"
            )
            if st.button("💾 Salvar email", key=f"save_email_{cod}"):
                update_cliente_email(cod, novo_email)
                st.success("Email salvo!")
                st.rerun()

        # Ações de status
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if status_txt not in ["aguardando_retorno", "retorno_recebido"]:
                if st.button("🔵 Marcar: Aguardando retorno", key=f"wait_{cod}"):
                    from utils.database import get_envios_df, update_status_envio
                    env = get_envios_df(vend_filter, mes_referencia=mes_sel)
                    env_cli = env[env["codigo_cliente"] == cod]
                    if not env_cli.empty:
                        update_status_envio(int(env_cli.iloc[0]["id"]), "aguardando_retorno")
                        st.success("Status atualizado!")
                        st.rerun()

        with col_a2:
            if status_txt == "aguardando_retorno":
                if st.button("✅ Marcar: Retorno recebido", key=f"recv_{cod}"):
                    from utils.database import get_envios_df, update_status_envio
                    env = get_envios_df(vend_filter, mes_referencia=mes_sel)
                    env_cli = env[env["codigo_cliente"] == cod]
                    if not env_cli.empty:
                        update_status_envio(int(env_cli.iloc[0]["id"]), "retorno_recebido")
                        st.success("Retorno registrado!")
                        st.rerun()
