"""
Sistema de Análise de Consignação — Artmed Editora
Ponto de entrada principal — tela de login
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.database import init_db, authenticate
from utils.style import COR_TEAL

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

/* ── Card branco = o próprio elemento form do Streamlit ── */
[data-testid="stForm"] {{
    background: #FFFFFF !important;
    border-radius: 16px !important;
    padding: 36px 40px 28px 40px !important;
    box-shadow: 0 20px 50px rgba(0,0,0,0.5) !important;
    border: none !important;
}}

/* Inputs dentro do card */
[data-testid="stForm"] .stTextInput > label {{
    color: #374151 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}}
[data-testid="stForm"] .stTextInput > div > div > input {{
    background: #F9FAFB !important;
    border: 1px solid #D1D5DB !important;
    color: #111827 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
}}
[data-testid="stForm"] .stTextInput > div > div > input:focus {{
    border-color: {COR_TEAL} !important;
    box-shadow: 0 0 0 3px rgba(0,169,157,0.15) !important;
    outline: none !important;
}}

/* Botão dentro do form */
[data-testid="stForm"] .stButton > button,
[data-testid="stForm"] [data-testid="stFormSubmitButton"] > button {{
    background: {COR_TEAL} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 11px 24px !important;
    font-weight: 700 !important;
    width: 100% !important;
    font-size: 14px !important;
    letter-spacing: 0.03em !important;
    transition: all 0.2s !important;
    margin-top: 6px !important;
}}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] > button:hover {{
    background: #009589 !important;
    box-shadow: 0 4px 12px rgba(0,169,157,0.35) !important;
}}

.footer-login {{
    text-align: center;
    font-size: 11px;
    color: #6B7280;
    margin-top: 14px;
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

# ── Tela de login ─────────────────────────────────────────────────────────────
# Logo centralizado acima do card
st.markdown(f"""
<div style="text-align:center;padding:52px 0 24px 0;">
    <svg width="180" height="60" viewBox="0 0 180 60" xmlns="http://www.w3.org/2000/svg">
        <text x="4" y="42" font-family="Georgia,serif" font-size="36" font-weight="700"
              fill="#FFFFFF" letter-spacing="-1">artmed</text>
        <text x="4" y="57" font-family="Arial,sans-serif" font-size="11" font-weight="400"
              fill="#9CA3AF" letter-spacing="5">EDITORA</text>
        <text x="154" y="20" font-family="Arial,sans-serif" font-size="24" font-weight="700"
              fill="{COR_TEAL}">+</text>
    </svg>
</div>
""", unsafe_allow_html=True)

# Colunas estreitas para o formulário
_, col_form, _ = st.columns([3, 2, 3])
with col_form:
    with st.form("login_form"):
        st.markdown("""
        <div style="font-size:20px;font-weight:700;color:#111827;margin-bottom:2px;">
            Acesso ao Sistema
        </div>
        <div style="font-size:13px;color:#6B7280;margin-bottom:20px;
                    padding-bottom:16px;border-bottom:1px solid #E5E7EB;">
            Análise de Consignação · Acesso restrito
        </div>
        """, unsafe_allow_html=True)

        username  = st.text_input("Usuário", placeholder="seu.usuario")
        password  = st.text_input("Senha", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar →")

    if submitted:
        if username and password:
            do_login(username, password)
        else:
            st.warning("Preencha usuário e senha.")

    st.markdown("""
    <div class="footer-login">Artmed Editora · Sistema de Consignação</div>
    """, unsafe_allow_html=True)
