"""
Módulo de banco de dados — SQLite (dev) / PostgreSQL via Supabase (produção)
Sistema de Análise de Consignação
"""
import hashlib
import os
import secrets
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

# ─── ENGINE ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DB_PATH  = BASE_DIR / "data" / "consignacao.db"

_engine = None

def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    db_url = os.environ.get("DATABASE_URL", "")
    if db_url and "postgresql" in db_url:
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    else:
        DB_PATH.parent.mkdir(exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def _is_pg() -> bool:
    return "postgresql" in os.environ.get("DATABASE_URL", "")


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _exec(conn, sql: str, params: dict = None):
    """Executa SQL usando text() — compatível com SQLite e PostgreSQL."""
    if params:
        return conn.execute(text(sql), params)
    return conn.execute(text(sql))


def _serial() -> str:
    """Tipo de coluna auto-incremento conforme o banco."""
    return "SERIAL" if _is_pg() else "INTEGER"


def _insert_ignore() -> str:
    """Prefixo de INSERT que ignora duplicatas."""
    return "INSERT" if _is_pg() else "INSERT OR IGNORE"


def _conflict_ignore() -> str:
    """Sufixo para ignorar conflito de chave única no PostgreSQL."""
    return "ON CONFLICT DO NOTHING" if _is_pg() else ""


# ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────
def init_db():
    """Cria todas as tabelas se não existirem."""
    eng = get_engine()
    serial = _serial()
    ci = _conflict_ignore()

    ddl_list = [
        # USUÁRIOS
        f"""CREATE TABLE IF NOT EXISTS usuarios (
            id {serial} PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            papel TEXT NOT NULL DEFAULT 'vendedor',
            email_envio TEXT,
            cod_gcon TEXT,
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(email),
            UNIQUE(username)
        )""",
        # BASE DE PRODUTOS
        f"""CREATE TABLE IF NOT EXISTS produtos (
            id {serial} PRIMARY KEY,
            isbn TEXT NOT NULL,
            cod_barras TEXT,
            autor TEXT,
            produto TEXT NOT NULL,
            preco_venda REAL,
            status TEXT,
            estoque_sp INTEGER,
            estoque_cl INTEGER,
            estoque_pr INTEGER,
            estoque_total INTEGER,
            editora TEXT,
            edicao TEXT,
            data_lancamento DATE,
            status_publicacao TEXT,
            area TEXT,
            subarea TEXT,
            formato TEXT,
            curva TEXT,
            phase_out TEXT,
            custo_stand REAL,
            estoque_terc INTEGER,
            cobertura_estoque REAL,
            vendas_60m REAL,
            vendas_24m REAL,
            vendas_12m REAL,
            vendas_6m REAL,
            vendas_3m REAL,
            mediana_12m REAL,
            mediana_24m REAL,
            upload_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(isbn)
        )""",
        # SALDO CONSIGNADO
        f"""CREATE TABLE IF NOT EXISTS saldo_consignado (
            id {serial} PRIMARY KEY,
            cod_loja TEXT,
            cnpj TEXT,
            codigo_cliente TEXT,
            loja TEXT,
            cod_gcon TEXT,
            nome_gcon TEXT,
            uf TEXT,
            razao_social TEXT,
            nf_serie TEXT,
            data_emissao DATE,
            isbn TEXT,
            cod_barras TEXT,
            titulo TEXT,
            autor TEXT,
            desconto REAL,
            status_titulo TEXT,
            qtde_remessa INTEGER,
            qtde_dev_acert INTEGER,
            qtde_saldo INTEGER,
            valor_liquido REAL,
            valor_bruto REAL,
            upload_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        # TABELA TES
        f"""CREATE TABLE IF NOT EXISTS tabela_tes (
            id {serial} PRIMARY KEY,
            cod_tes INTEGER NOT NULL,
            txt_padrao TEXT,
            finalidade TEXT,
            tipo_tes TEXT,
            faturamento TEXT,
            status TEXT,
            tipo TEXT NOT NULL,
            upload_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cod_tes)
        )""",
        # FATURAMENTO
        f"""CREATE TABLE IF NOT EXISTS faturamento (
            id {serial} PRIMARY KEY,
            nro_pedido TEXT,
            filial TEXT,
            codigo_cliente TEXT,
            loja TEXT,
            razao_social TEXT,
            data_emissao DATE,
            isbn TEXT,
            titulo TEXT,
            editora TEXT,
            qtd_solicitada INTEGER,
            qtd_atendida INTEGER,
            qtd_nao_atendida INTEGER,
            valor_unitario REAL,
            valor_atendido REAL,
            valor_nao_atendido REAL,
            preco_capa REAL,
            desconto_pct REAL,
            status_produto TEXT,
            cod_gcon TEXT,
            controle TEXT,
            data_nota DATE,
            nro_nota TEXT,
            cod_tes INTEGER,
            upload_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        # CLIENTES
        f"""CREATE TABLE IF NOT EXISTS clientes (
            id {serial} PRIMARY KEY,
            codigo_cliente TEXT NOT NULL,
            cnpj TEXT,
            cod_gcon TEXT,
            razao_social TEXT NOT NULL,
            uf TEXT,
            email TEXT,
            ativo INTEGER DEFAULT 1,
            UNIQUE(codigo_cliente)
        )""",
        # ENVIOS DO MAPA
        f"""CREATE TABLE IF NOT EXISTS envios_mapa (
            id {serial} PRIMARY KEY,
            codigo_cliente TEXT NOT NULL,
            razao_social TEXT,
            email_cliente TEXT,
            cod_gcon TEXT,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mes_referencia TEXT,
            status TEXT DEFAULT 'enviado',
            codigo_rastreio TEXT,
            observacao TEXT,
            reenviado INTEGER DEFAULT 0
        )""",
        # SESSÕES (persistência de login)
        f"""CREATE TABLE IF NOT EXISTS sessoes (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            criado_em TEXT,
            expira_em TEXT
        )""",
    ]

    # ── Bloco 1: cria tabelas ──────────────────────────────────────────────────
    with eng.connect() as conn:
        for ddl in ddl_list:
            _exec(conn, ddl)
        conn.commit()

    # ── Bloco 2: migrações isoladas (conexão própria para não contaminar) ───────
    _migrate_tabela_tes(eng)
    _migrate_saldo_nome_gcon(eng)

    # ── Bloco 3: admin padrão ─────────────────────────────────────────────────
    with eng.connect() as conn:
        row = _exec(conn, "SELECT id FROM usuarios WHERE username = 'admin'").fetchone()
        if not row:
            _insert_user_conn(conn, "Administrador", "admin@empresa.com",
                              "admin", "admin123", "admin")
            conn.commit()


def _migrate_saldo_nome_gcon(eng):
    """Adiciona coluna nome_gcon em saldo_consignado se não existir (migração segura)."""
    try:
        with eng.connect() as conn:
            if _is_pg():
                row = _exec(conn, """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name='saldo_consignado' AND column_name='nome_gcon'
                """).fetchone()
                if not row:
                    _exec(conn, "ALTER TABLE saldo_consignado ADD COLUMN nome_gcon TEXT")
                    conn.commit()
            else:
                rows = _exec(conn, "PRAGMA table_info(saldo_consignado)").fetchall()
                cols = [dict(r._mapping)["name"] for r in rows]
                if "nome_gcon" not in cols:
                    _exec(conn, "ALTER TABLE saldo_consignado ADD COLUMN nome_gcon TEXT")
                    conn.commit()
    except Exception:
        pass


def _migrate_tabela_tes(eng):
    """Adiciona coluna upload_em em tabela_tes se não existir (migração segura)."""
    try:
        with eng.connect() as conn:
            if _is_pg():
                row = _exec(conn, """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'tabela_tes'
                      AND column_name = 'upload_em'
                """).fetchone()
                if not row:
                    _exec(conn,
                        "ALTER TABLE tabela_tes "
                        "ADD COLUMN upload_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                    )
                    conn.commit()
            else:
                # SQLite: PRAGMA table_info nunca falha
                rows = _exec(conn, "PRAGMA table_info(tabela_tes)").fetchall()
                col_names = [dict(r._mapping)["name"] for r in rows]
                if "upload_em" not in col_names:
                    _exec(conn,
                        "ALTER TABLE tabela_tes ADD COLUMN upload_em TIMESTAMP"
                    )
                    conn.commit()
    except Exception:
        pass  # Se falhar, o sistema continua — upload_em será gravado pelo pandas


# ─── SESSÕES ──────────────────────────────────────────────────────────────────

def criar_sessao(username: str) -> str:
    """Gera token de sessão persistente (7 dias)."""
    from datetime import timedelta
    token   = secrets.token_urlsafe(32)
    criado  = datetime.now().isoformat()
    expira  = (datetime.now() + timedelta(days=7)).isoformat()
    eng = get_engine()
    with eng.connect() as conn:
        _exec(conn,
            "INSERT INTO sessoes (token, username, criado_em, expira_em) VALUES (:t, :u, :c, :e)",
            {"t": token, "u": username, "c": criado, "e": expira}
        )
        conn.commit()
    return token


def validar_sessao(token: str):
    """Valida token e retorna usuário ou None."""
    if not token:
        return None
    eng = get_engine()
    try:
        with eng.connect() as conn:
            row = _exec(conn,
                "SELECT username, expira_em FROM sessoes WHERE token = :t",
                {"t": token}
            ).fetchone()
            if not row:
                return None
            row = dict(row._mapping)
            try:
                from datetime import datetime as dt
                if dt.fromisoformat(str(row["expira_em"])) < dt.now():
                    return None
            except Exception:
                pass
            user = _exec(conn,
                "SELECT * FROM usuarios WHERE username = :u AND ativo = 1",
                {"u": row["username"]}
            ).fetchone()
            return dict(user._mapping) if user else None
    except Exception:
        return None


def deletar_sessao(token: str):
    """Remove sessão do banco."""
    if not token:
        return
    eng = get_engine()
    try:
        with eng.connect() as conn:
            _exec(conn, "DELETE FROM sessoes WHERE token = :t", {"t": token})
            conn.commit()
    except Exception:
        pass


# ─── USUÁRIOS ─────────────────────────────────────────────────────────────────

def _hash(pw: str) -> str:
    return hashlib.sha256(f"consignacao_salt_v1{pw}".encode()).hexdigest()


def _insert_user_conn(conn, nome, email, username, password,
                      papel="vendedor", email_envio=None, cod_gcon=None):
    ci = _conflict_ignore()
    sql = f"""
        INSERT INTO usuarios
        (nome, email, username, password_hash, papel, email_envio, cod_gcon)
        VALUES (:nome, :email, :username, :pw, :papel, :email_envio, :cod_gcon)
        {ci}
    """
    _exec(conn, sql, {
        "nome": nome, "email": email, "username": username,
        "pw": _hash(password), "papel": papel,
        "email_envio": email_envio or email, "cod_gcon": cod_gcon,
    })


def authenticate(username: str, password: str):
    eng = get_engine()
    with eng.connect() as conn:
        row = _exec(conn,
            "SELECT * FROM usuarios WHERE username=:u AND ativo=1",
            {"u": username}
        ).fetchone()
    if row and row._mapping["password_hash"] == _hash(password):
        return dict(row._mapping)
    return None


def get_all_users() -> list:
    eng = get_engine()
    with eng.connect() as conn:
        rows = _exec(conn,
            "SELECT id,nome,email,username,papel,email_envio,cod_gcon,ativo "
            "FROM usuarios ORDER BY nome"
        ).fetchall()
    return [dict(r._mapping) for r in rows]


@st.cache_data(ttl=3600, show_spinner=False)
def get_gcon_vendedores() -> list:
    """
    Retorna lista de vendedores únicos a partir dos Gcon presentes em saldo_consignado.
    Prioridade de nome: nome_gcon (coluna do próprio arquivo) → usuarios.nome → cod_gcon.
    Retorna: [{"cod_gcon": "VD0004", "nome": "Tatiana"}, ...]
    """
    eng = get_engine()
    with eng.connect() as conn:
        rows = _exec(conn, """
            SELECT sc.cod_gcon,
                   COALESCE(sc.nome_gcon, u.nome, sc.cod_gcon) AS nome
            FROM (
                SELECT cod_gcon, MAX(nome_gcon) AS nome_gcon
                FROM saldo_consignado
                WHERE cod_gcon IS NOT NULL AND cod_gcon != ''
                GROUP BY cod_gcon
            ) sc
            LEFT JOIN usuarios u ON u.cod_gcon = sc.cod_gcon AND u.ativo = 1
            ORDER BY COALESCE(sc.nome_gcon, u.nome, sc.cod_gcon)
        """).fetchall()
    return [dict(r._mapping) for r in rows]


def create_user(nome, email, username, password, papel="vendedor",
                email_envio=None, cod_gcon=None):
    eng = get_engine()
    try:
        with eng.connect() as conn:
            _insert_user_conn(conn, nome, email, username, password,
                              papel, email_envio, cod_gcon)
            conn.commit()
        return True, "Usuário criado com sucesso."
    except Exception as e:
        return False, "Usuário ou email já existe."


def update_user_password(username, new_password):
    eng = get_engine()
    with eng.connect() as conn:
        _exec(conn,
            "UPDATE usuarios SET password_hash=:pw WHERE username=:u",
            {"pw": _hash(new_password), "u": username}
        )
        conn.commit()


def toggle_user_active(user_id: int, ativo: bool):
    eng = get_engine()
    with eng.connect() as conn:
        _exec(conn,
            "UPDATE usuarios SET ativo=:a WHERE id=:id",
            {"a": int(ativo), "id": user_id}
        )
        conn.commit()


# ─── UPLOAD DE DADOS ──────────────────────────────────────────────────────────

def upsert_produtos(df: pd.DataFrame) -> int:
    eng = get_engine()
    cols_base = [
        "isbn", "cod_barras", "autor", "produto", "preco_venda", "status",
        "estoque_sp", "estoque_cl", "estoque_pr", "estoque_total",
        "editora", "edicao", "data_lancamento", "status_publicacao",
        "area", "subarea", "formato", "curva", "phase_out",
        "custo_stand", "estoque_terc", "cobertura_estoque",
        "vendas_60m", "vendas_24m", "vendas_12m", "vendas_6m", "vendas_3m",
        "mediana_12m", "mediana_24m"
    ]
    for col in cols_base:
        if col not in df.columns:
            df[col] = None
    df = df[cols_base].dropna(subset=["isbn"]).copy()
    df["upload_em"] = datetime.now()
    with eng.connect() as conn:
        _exec(conn, "DELETE FROM produtos")
        conn.commit()
    df.to_sql("produtos", eng, if_exists="append", index=False)
    st.cache_data.clear()
    return len(df)


def upsert_saldo_consignado(df: pd.DataFrame) -> int:
    eng = get_engine()
    cols = [
        "cod_loja", "cnpj", "codigo_cliente", "loja", "cod_gcon", "nome_gcon", "uf",
        "razao_social", "nf_serie", "data_emissao", "isbn", "cod_barras",
        "titulo", "autor", "desconto", "status_titulo",
        "qtde_remessa", "qtde_dev_acert", "qtde_saldo",
        "valor_liquido", "valor_bruto"
    ]
    for col in cols:
        if col not in df.columns:
            df[col] = None
    df = df[cols].dropna(subset=["codigo_cliente", "isbn"]).copy()
    df["upload_em"] = datetime.now()
    with eng.connect() as conn:
        _exec(conn, "DELETE FROM saldo_consignado")
        conn.commit()
    df.to_sql("saldo_consignado", eng, if_exists="append", index=False)
    _sync_clientes()
    st.cache_data.clear()
    return len(df)


def upsert_tes(df: pd.DataFrame) -> int:
    eng = get_engine()
    cols = ["cod_tes", "txt_padrao", "finalidade", "tipo_tes",
            "faturamento", "status", "tipo"]
    for col in cols:
        if col not in df.columns:
            df[col] = None
    df = df[cols].dropna(subset=["cod_tes"]).copy()
    df["tipo"] = df["tipo"].fillna("Outros").str.strip()
    # Registra timestamp de importação
    df["upload_em"] = datetime.now()
    with eng.connect() as conn:
        _exec(conn, "DELETE FROM tabela_tes")
        conn.commit()
    df.to_sql("tabela_tes", eng, if_exists="append", index=False)
    st.cache_data.clear()
    return len(df)


def upsert_faturamento(df: pd.DataFrame) -> int:
    eng = get_engine()
    cols = [
        "nro_pedido", "filial", "codigo_cliente", "loja", "razao_social",
        "data_emissao", "isbn", "titulo", "editora",
        "qtd_solicitada", "qtd_atendida", "qtd_nao_atendida",
        "valor_unitario", "valor_atendido", "valor_nao_atendido",
        "preco_capa", "desconto_pct", "status_produto",
        "cod_gcon", "controle", "data_nota", "nro_nota", "cod_tes"
    ]
    for col in cols:
        if col not in df.columns:
            df[col] = None
    df = df[cols].dropna(subset=["codigo_cliente", "isbn"]).copy()
    df["upload_em"] = datetime.now()
    with eng.connect() as conn:
        _exec(conn, "DELETE FROM faturamento")
        conn.commit()
    df.to_sql("faturamento", eng, if_exists="append", index=False)
    st.cache_data.clear()
    return len(df)


def _sync_clientes():
    eng = get_engine()
    ci = _conflict_ignore()
    with eng.connect() as conn:
        _exec(conn, f"""
            INSERT INTO clientes (codigo_cliente, cnpj, cod_gcon, razao_social, uf)
            SELECT DISTINCT codigo_cliente, cnpj, cod_gcon, razao_social, uf
            FROM saldo_consignado
            WHERE codigo_cliente IS NOT NULL
            {ci}
        """)
        _exec(conn, """
            UPDATE clientes
            SET cnpj = sq.cnpj
            FROM (
                SELECT DISTINCT ON (codigo_cliente) codigo_cliente, cnpj
                FROM saldo_consignado
                WHERE cnpj IS NOT NULL
            ) sq
            WHERE clientes.codigo_cliente = sq.codigo_cliente
            AND clientes.cnpj IS NULL
        """ if _is_pg() else """
            UPDATE clientes
            SET cnpj = (
                SELECT cnpj FROM saldo_consignado s
                WHERE s.codigo_cliente = clientes.codigo_cliente
                AND s.cnpj IS NOT NULL LIMIT 1
            )
            WHERE cnpj IS NULL
        """)
        conn.commit()


# ─── CONSULTAS ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_saldo_df(cod_gcon: str = None) -> pd.DataFrame:
    eng = get_engine()
    if cod_gcon:
        return pd.read_sql(
            text("SELECT * FROM saldo_consignado WHERE cod_gcon=:g"),
            eng, params={"g": cod_gcon}
        )
    return pd.read_sql(text("SELECT * FROM saldo_consignado"), eng)


@st.cache_data(ttl=3600, show_spinner=False)
def get_produtos_df() -> pd.DataFrame:
    return pd.read_sql(text("SELECT * FROM produtos"), get_engine())


@st.cache_data(ttl=3600, show_spinner=False)
def get_tes_df() -> pd.DataFrame:
    return pd.read_sql(text("SELECT * FROM tabela_tes"), get_engine())


@st.cache_data(ttl=3600, show_spinner=False)
def get_faturamento_df(cod_gcon: str = None, tipos_tes: tuple = None) -> pd.DataFrame:
    eng = get_engine()
    q = """
        SELECT f.*, COALESCE(t.tipo, 'Outros') AS tipo_tes
        FROM faturamento f
        LEFT JOIN tabela_tes t ON f.cod_tes = t.cod_tes
        WHERE 1=1
    """
    params = {}
    if cod_gcon:
        q += " AND f.cod_gcon=:g"
        params["g"] = cod_gcon

    df = pd.read_sql(text(q), eng, params=params or None)
    df["tipo_tes"] = df["tipo_tes"].fillna("Outros").str.strip()

    if tipos_tes:
        tipos_norm = [t.strip() for t in tipos_tes]
        df = df[df["tipo_tes"].isin(tipos_norm)]
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def get_clientes(cod_gcon: str = None) -> list:
    eng = get_engine()
    with eng.connect() as conn:
        if cod_gcon:
            rows = _exec(conn,
                "SELECT * FROM clientes WHERE cod_gcon=:g AND ativo=1 ORDER BY razao_social",
                {"g": cod_gcon}
            ).fetchall()
        else:
            rows = _exec(conn,
                "SELECT * FROM clientes WHERE ativo=1 ORDER BY razao_social"
            ).fetchall()
    return [dict(r._mapping) for r in rows]


def update_cliente_email(codigo_cliente: str, email: str):
    eng = get_engine()
    with eng.connect() as conn:
        _exec(conn,
            "UPDATE clientes SET email=:e WHERE codigo_cliente=:c",
            {"e": email, "c": codigo_cliente}
        )
        conn.commit()


# ─── ENVIOS ───────────────────────────────────────────────────────────────────

def registrar_envio(codigo_cliente, razao_social, email_cliente,
                    cod_gcon, mes_referencia, status="enviado",
                    observacao=None, reenviado=False) -> str:
    codigo_rastreio = secrets.token_hex(8).upper()
    eng = get_engine()
    with eng.connect() as conn:
        _exec(conn, """
            INSERT INTO envios_mapa
            (codigo_cliente, razao_social, email_cliente, cod_gcon,
             mes_referencia, status, codigo_rastreio, observacao, reenviado)
            VALUES (:cc, :rs, :ec, :cg, :mr, :st, :cr, :obs, :re)
        """, {
            "cc": codigo_cliente, "rs": razao_social, "ec": email_cliente,
            "cg": cod_gcon, "mr": mes_referencia, "st": status,
            "cr": codigo_rastreio, "obs": observacao, "re": int(reenviado),
        })
        conn.commit()
    return codigo_rastreio


def get_envios_df(cod_gcon: str = None, mes_referencia: str = None) -> pd.DataFrame:
    eng = get_engine()
    q = "SELECT * FROM envios_mapa WHERE 1=1"
    params = {}
    if cod_gcon:
        q += " AND cod_gcon=:g"
        params["g"] = cod_gcon
    if mes_referencia:
        q += " AND mes_referencia=:mr"
        params["mr"] = mes_referencia
    q += " ORDER BY data_envio DESC"
    return pd.read_sql(text(q), eng, params=params or None)


def update_status_envio(envio_id: int, novo_status: str, observacao: str = None):
    eng = get_engine()
    with eng.connect() as conn:
        _exec(conn,
            "UPDATE envios_mapa SET status=:s, observacao=:o WHERE id=:id",
            {"s": novo_status, "o": observacao, "id": envio_id}
        )
        conn.commit()


def get_status_envio_mes(cod_gcon: str = None) -> pd.DataFrame:
    mes_atual = datetime.now().strftime("%Y-%m")
    eng = get_engine()
    q = """
        SELECT c.codigo_cliente, c.cod_gcon, c.razao_social, c.uf, c.email,
               MAX(e.data_envio) as ultimo_envio,
               MAX(e.status) as ultimo_status,
               COUNT(e.id) as total_envios
        FROM clientes c
        LEFT JOIN envios_mapa e
            ON c.codigo_cliente = e.codigo_cliente
            AND e.mes_referencia = :mes
        WHERE c.ativo = 1
    """
    params = {"mes": mes_atual}
    if cod_gcon:
        q += " AND c.cod_gcon = :g"
        params["g"] = cod_gcon
    q += " GROUP BY c.codigo_cliente, c.cod_gcon, c.razao_social, c.uf, c.email ORDER BY c.razao_social"
    df = pd.read_sql(text(q), eng, params=params)
    df["mapa_enviado"] = df["ultimo_envio"].notna()
    return df


# ─── ANALYTICS ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_analise_consignacao(cod_gcon: str = None) -> pd.DataFrame:
    saldo = get_saldo_df(cod_gcon)
    if saldo.empty:
        return pd.DataFrame()

    produtos = get_produtos_df()

    for col in ["qtde_remessa", "qtde_dev_acert", "qtde_saldo", "valor_liquido", "valor_bruto"]:
        saldo[col] = pd.to_numeric(saldo[col], errors="coerce").fillna(0)

    if not produtos.empty:
        cols_prod = [c for c in ["isbn", "preco_venda", "curva", "cobertura_estoque",
                                  "vendas_12m", "vendas_6m", "vendas_3m",
                                  "status_publicacao", "editora", "area"]
                     if c in produtos.columns]
        saldo = saldo.merge(produtos[cols_prod], on="isbn", how="left", suffixes=("", "_prod"))

    saldo["pct_acerto"] = (
        saldo["qtde_dev_acert"] / saldo["qtde_remessa"].replace(0, 1) * 100
    ).round(1)
    saldo["sem_giro"] = (saldo["qtde_dev_acert"] == 0) & (saldo["qtde_saldo"] > 0)
    saldo["data_emissao"] = pd.to_datetime(saldo["data_emissao"], errors="coerce")
    saldo["dias_em_saldo"] = (pd.Timestamp.now() - saldo["data_emissao"]).dt.days

    if "preco_venda" in saldo.columns:
        saldo["valor_potencial"] = (
            saldo["qtde_saldo"] *
            pd.to_numeric(saldo["preco_venda"], errors="coerce").fillna(0)
        )
    else:
        saldo["valor_potencial"] = 0

    return saldo


def get_ultima_atualizacao() -> dict:
    """Retorna data/hora da última importação de cada tabela."""
    eng = get_engine()
    resultado = {}
    tabelas = {
        "produtos":         "produtos",
        "saldo_consignado": "saldo_consignado",
        "faturamento":      "faturamento",
        "tabela_tes":       "tabela_tes",
    }
    with eng.connect() as conn:
        for chave, tabela in tabelas.items():
            try:
                row = _exec(conn,
                    f"SELECT MAX(upload_em) as ult FROM {tabela}"
                ).fetchone()
                val = dict(row._mapping)["ult"] if row else None
                resultado[chave] = str(val) if val else None
            except Exception:
                resultado[chave] = None
        # Contagens
        for chave, tabela in tabelas.items():
            try:
                row = _exec(conn, f"SELECT COUNT(*) as n FROM {tabela}").fetchone()
                resultado[f"{chave}_count"] = dict(row._mapping)["n"]
            except Exception:
                resultado[f"{chave}_count"] = 0
    return resultado


@st.cache_data(ttl=3600, show_spinner=False)
def get_kpis(cod_gcon: str = None) -> dict:
    df = get_analise_consignacao(cod_gcon)
    if df.empty:
        return {
            "total_clientes": 0, "total_titulos": 0,
            "qtde_remessa_total": 0, "qtde_saldo_total": 0,
            "qtde_acerto_total": 0, "pct_acerto_medio": 0,
            "valor_liquido_total": 0, "valor_potencial": 0,
            "titulos_sem_giro": 0, "clientes_sem_giro": 0,
        }
    return {
        # Clientes ativos: conta por cod_loja (código + loja) para distinguir
        # clientes com mesmo nome mas lojas diferentes (filiais).
        "total_clientes": int(df["cod_loja"].nunique()) if "cod_loja" in df.columns else int(df["codigo_cliente"].nunique()),
        "total_titulos": int(df["isbn"].nunique()),
        "qtde_remessa_total": int(df["qtde_remessa"].sum()),
        "qtde_saldo_total": int(df["qtde_saldo"].sum()),
        "qtde_acerto_total": int(df["qtde_dev_acert"].sum()),
        "pct_acerto_medio": round(float(
            df["qtde_dev_acert"].sum() / df["qtde_remessa"].sum() * 100
        ) if df["qtde_remessa"].sum() > 0 else 0, 1),
        "valor_liquido_total": float(df["valor_liquido"].sum()),
        "valor_potencial": float(df.get("valor_potencial", pd.Series([0])).sum()),
        "titulos_sem_giro": int(df[df["sem_giro"]]["isbn"].nunique()),
        "clientes_sem_giro": int(df[df["sem_giro"]]["cod_loja"].nunique()) if "cod_loja" in df.columns else int(df[df["sem_giro"]]["codigo_cliente"].nunique()),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_ranking_clientes(cod_gcon: str = None) -> pd.DataFrame:
    df = get_analise_consignacao(cod_gcon)
    if df.empty:
        return pd.DataFrame()

    ranking = df.groupby(["codigo_cliente", "razao_social", "uf"]).agg(
        qtde_remessa=("qtde_remessa", "sum"),
        qtde_dev_acert=("qtde_dev_acert", "sum"),
        qtde_saldo=("qtde_saldo", "sum"),
        valor_liquido=("valor_liquido", "sum"),
        titulos=("isbn", "nunique"),
    ).reset_index()
    ranking["pct_acerto"] = (
        ranking["qtde_dev_acert"] / ranking["qtde_remessa"].replace(0, 1) * 100
    ).round(1)
    return ranking.sort_values("qtde_saldo", ascending=False)


def get_faturamento_por_mes(cod_gcon: str = None) -> pd.DataFrame:
    fat = get_faturamento_df(cod_gcon)
    if fat.empty:
        return pd.DataFrame()

    date_col = "data_nota" if "data_nota" in fat.columns else "data_emissao"
    fat[date_col] = pd.to_datetime(fat[date_col], errors="coerce")
    fat = fat.dropna(subset=[date_col])
    fat["mes"] = fat[date_col].dt.to_period("M").astype(str)

    val_col = "valor_atendido" if "valor_atendido" in fat.columns else "valor_faturado"
    qty_col = "qtd_atendida" if "qtd_atendida" in fat.columns else "quantidade_faturada"

    fat_fat = fat[fat["tipo_tes"].isin(["Venda", "Acerto Consignação"])]

    mes_total = fat_fat.groupby("mes").agg(
        receita_total=(val_col, "sum"),
        qtde_total=(qty_col, "sum"),
        clientes=("codigo_cliente", "nunique"),
    ).reset_index()

    mes_venda = (fat_fat[fat_fat["tipo_tes"] == "Venda"]
                 .groupby("mes")[[val_col]].sum()
                 .rename(columns={val_col: "receita_venda"}).reset_index())

    mes_acerto = (fat_fat[fat_fat["tipo_tes"] == "Acerto Consignação"]
                  .groupby("mes")[[val_col]].sum()
                  .rename(columns={val_col: "receita_acerto_csg"}).reset_index())

    result = mes_total.merge(mes_venda, on="mes", how="left")
    result = result.merge(mes_acerto, on="mes", how="left")
    result[["receita_venda", "receita_acerto_csg"]] = (
        result[["receita_venda", "receita_acerto_csg"]].fillna(0)
    )
    return result.sort_values("mes")


def get_acerto_vs_faturamento(cod_gcon: str = None) -> pd.DataFrame:
    saldo = get_saldo_df(cod_gcon)
    fat = get_faturamento_df(cod_gcon, tipos_tes=["Venda", "Acerto Consignação"])

    if saldo.empty:
        return pd.DataFrame()

    saldo_grp = saldo.groupby(["codigo_cliente", "razao_social"]).agg(
        qtde_remessa=("qtde_remessa", "sum"),
        qtde_dev_acert=("qtde_dev_acert", "sum"),
        qtde_saldo=("qtde_saldo", "sum"),
    ).reset_index()
    saldo_grp["pct_acerto"] = (
        saldo_grp["qtde_dev_acert"] / saldo_grp["qtde_remessa"].replace(0, 1) * 100
    ).round(1)

    if fat.empty:
        saldo_grp["receita_total"] = 0
        return saldo_grp

    val_col = "valor_atendido" if "valor_atendido" in fat.columns else "valor_faturado"
    fat_grp = fat.groupby("codigo_cliente")[[val_col]].sum().rename(
        columns={val_col: "receita_total"}
    ).reset_index()

    return saldo_grp.merge(fat_grp, on="codigo_cliente", how="left").fillna({"receita_total": 0})
