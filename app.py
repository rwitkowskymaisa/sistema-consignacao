"""
Sistema de Análise de Consignação
Ponto de entrada principal — tela de login
"""
import streamlit as st
import sys
from pathlib import Path

# Adiciona raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.database import init_db, authenticate

# ─── CONFIGURAÇÃO DA PÁGINA ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Consignação · Login",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Inicializa banco ao iniciar
init_db()

# ─── ESTILOS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none; }
.stApp { background: #0f172a; }

.login-card {
    background: #1e293b;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 40px 48px;
    max-width: 420px;
    margin: 60px auto 0;
}
.login-title {
    font-size: 26px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 4px;
}
.login-sub {
    font-size: 14px;
    color: #64748b;
    margin-bottom: 32px;
}
.login-icon { font-size: 40px; margin-bottom: 16px; }

div[data-testid="stForm"] {
    background: transparent !important;
}

.stTextInput > label { color: #94a3b8 !important; font-size: 13px !important; }
.stTextInput > div > div > input {
    background: #0f172a !important;
    border: 1px solid #334155 !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,.2) !important;
}

.stButton > button {
    background: #3b82f6 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    width: 100% !important;
    font-size: 14px !important;
}
.stButton > button:hover { background: #2563eb !important; }

.footer-login {
    text-align: center;
    font-size: 12px;
    color: #334155;
    margin-top: 48px;
}
</style>
""", unsafe_allow_html=True)

# ─── ESTADO DE SESSÃO ─────────────────────────────────────────────────────────
if "usuario" not in st.session_state:
    st.session_state.usuario = None


def do_login(username: str, password: str):
    user = authenticate(username.strip(), password)
    if user:
        st.session_state.usuario = user
        st.rerun()
    else:
        st.error("Usuário ou senha incorretos.")


# ─── SE JÁ LOGADO, REDIRECIONA ───────────────────────────────────────────────
if st.session_state.usuario:
    st.markdown("""
    <div style="text-align:center;padding:60px 0;color:#94a3b8;font-size:16px">
        ✅ Você está autenticado!<br><br>
        Use o menu lateral para navegar pelo sistema.
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚪 Sair"):
            st.session_state.usuario = None
            st.rerun()
    st.stop()

# ─── TELA DE LOGIN ────────────────────────────────────────────────────────────
st.markdown("""
<div class="login-card">
  <div class="login-icon">📚</div>
  <div class="login-title">Consignação</div>
  <div class="login-sub">Sistema de Análise · Acesso restrito</div>
</div>
""", unsafe_allow_html=True)

# Centraliza o formulário
col_a, col_b, col_c = st.columns([1, 2, 1])
with col_b:
    with st.form("login_form"):
        username = st.text_input("Usuário", placeholder="seu.usuario")
        password = st.text_input("Senha", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        if username and password:
            do_login(username, password)
        else:
            st.warning("Preencha usuário e senha.")

st.markdown("""
<div class="footer-login">
    Sistema de Análise de Consignação<br>
    Login padrão inicial: <strong>admin</strong> / <strong>admin123</strong>
</div>
""", unsafe_allow_html=True)
