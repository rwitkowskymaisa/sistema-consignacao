"""
Página 5 — Configurações
Gestão de usuários/vendedores, configuração de email, instruções de deploy.
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.database import (
    get_all_users, create_user, update_user_password,
    toggle_user_active, init_db
)
from utils.style import apply_theme, sidebar_header, sidebar_footer

st.set_page_config(page_title="Configurações · Consignação", page_icon="⚙️", layout="wide")
init_db()
apply_theme()

if "usuario" not in st.session_state or not st.session_state.usuario:
    st.warning("⚠️ Faça login para acessar esta página.")
    st.stop()

usuario = st.session_state.usuario
is_admin = usuario["papel"] == "admin"

sidebar_header(usuario)
with st.sidebar:
    st.markdown('<div class="sidebar-section">Sistema</div>', unsafe_allow_html=True)
sidebar_footer(usuario)

st.markdown("""
<div class="page-header">
  <div>
    <div class="page-title">⚙️ Configurações</div>
    <div class="page-subtitle">Usuários, email, deploy e conta</div>
  </div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["👤 Usuários", "📧 Email / Azure", "🚀 Deploy", "🔒 Minha Conta"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — USUÁRIOS (somente admin)
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    if not is_admin:
        st.info("Somente administradores podem gerenciar usuários.")
    else:
        st.subheader("Usuários cadastrados")

        usuarios = get_all_users()
        for u in usuarios:
            ativo = u["ativo"] == 1
            with st.expander(
                f"{'🟢' if ativo else '🔴'} **{u['nome']}** · `{u['username']}` · {u['papel'].upper()}",
                expanded=False
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Email:** {u['email']}")
                    st.markdown(f"**Email envio:** {u.get('email_envio') or '—'}")
                with c2:
                    if u["username"] != "admin":
                        novo_ativo = st.toggle("Ativo", value=ativo, key=f"ativo_{u['id']}")
                        if novo_ativo != ativo:
                            toggle_user_active(u["id"], novo_ativo)
                            st.rerun()

        st.divider()
        st.subheader("Criar novo usuário")

        with st.form("form_novo_user"):
            c1, c2 = st.columns(2)
            with c1:
                novo_nome     = st.text_input("Nome completo")
                novo_email    = st.text_input("Email de login")
                novo_email_envio = st.text_input("Email de envio (Outlook)", placeholder="vendedor@empresa.com")
            with c2:
                novo_user  = st.text_input("Username (sem espaços, sem acento)")
                novo_senha = st.text_input("Senha inicial", type="password")
                novo_papel = st.selectbox("Papel", ["vendedor", "admin"])

            if st.form_submit_button("✅ Criar Usuário", type="primary"):
                if all([novo_nome, novo_email, novo_user, novo_senha]):
                    ok, msg = create_user(
                        novo_nome, novo_email, novo_user,
                        novo_senha, novo_papel, novo_email_envio
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Preencha todos os campos obrigatórios.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CONFIGURAÇÃO DE EMAIL / AZURE
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Configuração do Outlook via Azure AD")

    st.markdown("""
    O sistema usa a **Microsoft Graph API** para enviar emails em nome do vendedor.
    Siga o passo a passo abaixo para configurar.
    """)

    with st.expander("📋 Passo a passo — Registro no Azure AD", expanded=True):
        st.markdown("""
        **1. Acesse o [portal.azure.com](https://portal.azure.com)**

        **2. Vá em "Azure Active Directory" → "App registrations" → "New registration"**
        - Nome: `Sistema Consignacao`
        - Supported account types: "Accounts in this organizational directory only"
        - Redirect URI: deixe em branco por ora

        **3. Anote o `Application (client) ID` e o `Directory (tenant) ID`**

        **4. Vá em "Certificates & secrets" → "New client secret"**
        - Descrição: `consignacao`
        - Expiração: 24 meses (recomendado)
        - **Anote o valor do secret imediatamente** (não aparece novamente)

        **5. Vá em "API permissions" → "Add a permission" → "Microsoft Graph"**
        - Tipo: **Application permissions**
        - Adicione: `Mail.Send`
        - Clique em "Grant admin consent for [sua org]"

        **6. Salve as credenciais no arquivo `.streamlit/secrets.toml`:**
        """)

        st.code("""
# .streamlit/secrets.toml  (NÃO suba este arquivo para o GitHub!)
AZURE_CLIENT_ID     = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
AZURE_CLIENT_SECRET = "seu-client-secret-aqui"
AZURE_TENANT_ID     = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
""", language="toml")

        st.warning("⚠️ O arquivo `secrets.toml` contém dados sensíveis. Certifique-se de que está no `.gitignore`.")

    with st.expander("☁️ Configuração no Railway (deploy em nuvem)"):
        st.markdown("""
        No Railway, as secrets são configuradas como **variáveis de ambiente**:

        1. Abra seu projeto no [railway.app](https://railway.app)
        2. Vá em **Variables**
        3. Adicione:
           - `AZURE_CLIENT_ID`
           - `AZURE_CLIENT_SECRET`
           - `AZURE_TENANT_ID`

        O Streamlit lê automaticamente variáveis de ambiente como secrets em produção.
        """)

    # Teste de conexão
    st.divider()
    st.subheader("Testar conexão de email")
    test_email = st.text_input("Enviar email de teste para:", placeholder="seu@email.com")
    if st.button("📨 Enviar teste"):
        try:
            client_id = st.secrets.get("AZURE_CLIENT_ID", "")
            client_secret = st.secrets.get("AZURE_CLIENT_SECRET", "")
            tenant_id = st.secrets.get("AZURE_TENANT_ID", "")
            from_em = usuario.get("email_envio") or usuario.get("email") or ""

            if not all([client_id, client_secret, tenant_id, from_em]):
                st.error("Credenciais não configuradas ou email do usuário ausente.")
            else:
                from utils.email_service import send_email_graph
                ok, msg = send_email_graph(
                    from_email=from_em,
                    to_email=test_email,
                    subject="Teste — Sistema de Consignação",
                    body_html="<p>Email de teste enviado com sucesso! ✅</p>",
                    client_id=client_id,
                    client_secret=client_secret,
                    tenant_id=tenant_id,
                )
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
        except Exception as e:
            st.error(f"Erro: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — DEPLOY
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("🚀 Deploy — Supabase + GitHub + Railway")

    st.markdown("""
    ### Arquitetura de produção

    ```
    GitHub (código)  →  Railway (app Streamlit)  →  Supabase (PostgreSQL)
    ```

    ---
    """)

    with st.expander("1️⃣ Supabase — banco de dados em nuvem", expanded=True):
        st.markdown("""
        1. Crie um projeto em [supabase.com](https://supabase.com) (plano gratuito disponível)
        2. Vá em **Settings → Database → Connection string** (URI mode)
        3. Copie a string de conexão no formato:
           ```
           postgresql://postgres:[SENHA]@db.xxxx.supabase.co:5432/postgres
           ```
        4. Adicione no Railway como variável de ambiente `DATABASE_URL`

        > **Nota:** a versão atual usa SQLite localmente. Para usar Supabase em produção,
        > troque a variável `DATABASE_URL` no Railway — o código detecta automaticamente.
        """)

    with st.expander("2️⃣ GitHub — versionamento e CI/CD"):
        st.markdown("""
        1. Crie um repositório no [github.com](https://github.com)
        2. Adicione o `.gitignore` para excluir `secrets.toml` e `data/`:
           ```
           .streamlit/secrets.toml
           data/
           __pycache__/
           *.pyc
           .env
           ```
        3. Faça o push do projeto:
           ```bash
           git init
           git add .
           git commit -m "feat: sistema consignação v1"
           git remote add origin https://github.com/seu-usuario/seu-repo.git
           git push -u origin main
           ```
        """)

    with st.expander("3️⃣ Railway — hospedagem do app"):
        st.markdown("""
        1. Acesse [railway.app](https://railway.app) e conecte sua conta GitHub
        2. Clique em **New Project → Deploy from GitHub repo**
        3. Selecione o repositório
        4. Railway detecta Streamlit automaticamente
        5. Em **Variables**, adicione:
           ```
           AZURE_CLIENT_ID = ...
           AZURE_CLIENT_SECRET = ...
           AZURE_TENANT_ID = ...
           DATABASE_URL = ... (string do Supabase)
           ```
        6. O deploy acontece automaticamente a cada `git push`

        **Arquivo de configuração necessário (`Procfile`):**
        ```
        web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
        ```
        """)

    with st.expander("📦 requirements.txt"):
        st.code("""
streamlit>=1.35.0
pandas>=2.0.0
openpyxl>=3.1.0
plotly>=5.18.0
msal>=1.28.0
requests>=2.31.0
psycopg2-binary>=2.9.9
sqlalchemy>=2.0.0
""", language="text")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MINHA CONTA
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("Minha conta")
    st.markdown(f"**Nome:** {usuario['nome']}")
    st.markdown(f"**Username:** `{usuario['username']}`")
    st.markdown(f"**Email:** {usuario.get('email','—')}")
    st.markdown(f"**Papel:** {usuario['papel'].upper()}")

    st.divider()
    st.subheader("Alterar senha")
    with st.form("form_senha"):
        nova_senha = st.text_input("Nova senha", type="password")
        conf_senha = st.text_input("Confirmar senha", type="password")
        if st.form_submit_button("🔒 Alterar senha"):
            if not nova_senha:
                st.error("Digite a nova senha.")
            elif nova_senha != conf_senha:
                st.error("As senhas não coincidem.")
            elif len(nova_senha) < 6:
                st.error("A senha deve ter ao menos 6 caracteres.")
            else:
                update_user_password(usuario["username"], nova_senha)
                st.success("Senha alterada com sucesso!")
