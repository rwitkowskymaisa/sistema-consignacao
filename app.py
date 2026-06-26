"""
Sistema de Análise de Consignação — Artmed Editora
Ponto de entrada principal — tela de login
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.database import init_db, authenticate
from utils.style import LOGO_SVG, COR_TEAL

st.set_page_config(
    page_title="Artmed · Consignação",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()

st.markdown(f"""
<style>
html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
}}
[data-testid="stSidebar"] {{ display: none; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}

.stApp {{
    background: linear-gradient(135deg, #1F2937 0%, #111827 100%);
    min-height: 100vh;
}}

.login-wrapper {{
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 40px 20px;
}}
.login-card {{
    background: #FFFFFF;
    border-radius: 20px;
    padding: 48px 52px;
    width: 100%;
    max-width: 420px;
    box-shadow: 0 25px 60px rgba(0,0,0,0.4);
}}
.login-logo {{
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 1px solid #E5E7EB;
}}
.login-title {{
    font-size: 22px;
    font-weight: 700;
    color: #111827;
    margin-bottom: 4px;
}}
.login-sub {{
    font-size: 13px;
    color: #6B7280;
    margin-bottom: 28px;
}}
.stTextInput > label {{
    color: #374151 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}}
.stTextInput > div > div > input {{
    background: #F9FAFB !important;
    border: 1px solid #D1D5DB !important;
    color: #111827 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
}}
.stTextInput > div > div > input:focus {{
    border-color: {COR_TEAL} !important;
    box-shadow: 0 0 0 3px rgba(0,169,157,0.15) !important;
}}
.stButton > button {{
    background: {COR_TEAL} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    font-weight: 700 !important;
    width: 100% !important;
    font-size: 14px !important;
    letter-spacing: 0.03em !important;
    transition: all 0.2s !important;
}}
.stButton > button:hover {{
    background: #009589 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,169,157,0.3) !important;
}}
.footer-login {{
    text-align: center;
    font-size: 11px;
    color: #9CA3AF;
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid #F3F4F6;
}}
</style>
""", unsafe_allow_html=True)

if "usuario" not in st.session_state:
    st.session_state.usuario = None


def do_login(username: str, password: str):
    user = authenticate(username.strip(), password)
    if user:
        st.session_state.usuario = user
        st.rerun()
    else:
        st.error("Usuário ou senha incorretos.")


# Se já logado
if st.session_state.usuario:
    u = st.session_state.usuario
    st.markdown(f"""
    <div style="text-align:center;padding:80px 0;">
        <div style="font-size:48px;margin-bottom:16px;">✅</div>
        <div style="font-size:20px;font-weight:700;color:#F9FAFB;">
            Bem-vindo, {u['nome']}!
        </div>
        <div style="font-size:14px;color:#9CA3AF;margin-top:8px;">
            Use o menu lateral para navegar pelo sistema.
        </div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("🚪 Sair"):
            st.session_state.usuario = None
            st.rerun()
    st.stop()

# Tela de login
col_a, col_b, col_c = st.columns([1, 1.2, 1])
with col_b:
    # Logo SVG em fundo escuro (renderizado inline)
    st.markdown(f"""
    <div style="text-align:center;margin-bottom:32px;">
        <svg width="200" height="64" viewBox="0 0 200 64" xmlns="http://www.w3.org/2000/svg">
            <text x="8" y="44" font-family="Georgia,serif" font-size="38" font-weight="700"
                  fill="#FFFFFF" letter-spacing="-1">artmed</text>
            <text x="8" y="60" font-family="Arial,sans-serif" font-size="12" font-weight="400"
                  fill="#9CA3AF" letter-spacing="5">EDITORA</text>
            <text x="170" y="22" font-family="Arial,sans-serif" font-size="26" font-weight="700"
                  fill="{COR_TEAL}">+</text>
        </svg>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="login-card">
        <div class="login-title">Acesso ao Sistema</div>
        <div class="login-sub">Análise de Consignação · Acesso restrito</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Usuário", placeholder="seu.usuario")
        password = st.text_input("Senha", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar →")

    if submitted:
        if username and password:
            do_login(username, password)
        else:
            st.warning("Preencha usuário e senha.")

    st.markdown("""
    <div class="footer-login">
        Artmed Editora · Sistema de Consignação
    </div>
    """, unsafe_allow_html=True)
