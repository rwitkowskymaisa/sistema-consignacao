"""
Gerenciamento de autenticação com persistência via query param + idle timeout.
"""
import time
import streamlit as st

IDLE_TIMEOUT = 10 * 60  # 10 minutos em segundos


def require_login() -> dict:
    """
    Verifica sessão. Ordem de checagem:
      1. session_state.usuario presente e não expirado por inatividade → OK
      2. token ?s= na URL → valida no banco → restaura sessão
      3. Nenhum dos dois → mostra tela de expirada

    Garante que o token SEMPRE esteja na URL para que F5 funcione.
    """
    from utils.database import validar_sessao

    agora = time.time()

    # ── 1. Sessão ativa na memória ────────────────────────────────────────────
    if st.session_state.get("usuario"):
        ultimo = st.session_state.get("last_activity", agora)

        # Verifica idle timeout
        if agora - ultimo > IDLE_TIMEOUT:
            _encerrar_por_inatividade()
            # _encerrar_por_inatividade chama st.stop(), não retorna

        # Atualiza timestamp de atividade
        st.session_state.last_activity = agora

        # Garante que o token esteja na URL (para F5 funcionar)
        token = st.session_state.get("session_token", "")
        if token and st.query_params.get("s") != token:
            st.query_params["s"] = token

        return st.session_state.usuario

    # ── 2. Tenta restaurar pelo token na URL ──────────────────────────────────
    token = st.query_params.get("s", "")
    if token:
        user = validar_sessao(token)
        if user:
            st.session_state.usuario      = user
            st.session_state.session_token = token
            st.session_state.last_activity = agora
            # Token já está na URL, não precisa setar novamente
            return user

    # ── 3. Não autenticado ────────────────────────────────────────────────────
    st.warning("⚠️ Sessão expirada. Faça login novamente.")
    if st.button("🔑 Ir para o login"):
        st.query_params.clear()
        st.switch_page("app.py")
    st.stop()


def _encerrar_por_inatividade():
    """Limpa sessão por inatividade e redireciona."""
    from utils.database import deletar_sessao
    token = st.session_state.get("session_token", "")
    if token:
        try:
            deletar_sessao(token)
        except Exception:
            pass
    st.session_state.usuario       = None
    st.session_state.session_token = None
    st.session_state.last_activity = None
    st.query_params.clear()
    st.warning("⏱️ Sessão encerrada por inatividade. Faça login novamente.")
    if st.button("🔑 Ir para o login", key="btn_idle_login"):
        st.switch_page("app.py")
    st.stop()


def logout():
    """Encerra a sessão manualmente e redireciona para o login."""
    from utils.database import deletar_sessao
    token = st.session_state.get("session_token", "")
    if token:
        try:
            deletar_sessao(token)
        except Exception:
            pass
    st.session_state.usuario       = None
    st.session_state.session_token = None
    st.session_state.last_activity = None
    st.query_params.clear()
    st.switch_page("app.py")
