"""
Gerenciamento de autenticação com persistência via query param.
"""
import streamlit as st


def require_login() -> dict:
    """
    Verifica sessão. Se não há usuário na session_state,
    tenta restaurar pelo token ?s= na URL.
    Retorna o dict do usuário ou para a execução (stop).
    """
    from utils.database import validar_sessao

    # Já autenticado nesta sessão
    if st.session_state.get("usuario"):
        return st.session_state.usuario

    # Tenta restaurar pelo token na URL
    token = st.query_params.get("s", "")
    if token:
        user = validar_sessao(token)
        if user:
            st.session_state.usuario = user
            st.session_state.session_token = token
            return user

    # Não autenticado — redireciona para login
    st.warning("⚠️ Sessão expirada. Faça login novamente.")
    if st.button("🔑 Ir para o login"):
        st.query_params.clear()
        st.switch_page("app.py")
    st.stop()


def logout():
    """Encerra a sessão e redireciona para o login."""
    from utils.database import deletar_sessao
    token = st.session_state.get("session_token", "")
    deletar_sessao(token)
    st.session_state.usuario = None
    st.session_state.session_token = None
    st.query_params.clear()
    st.switch_page("app.py")
