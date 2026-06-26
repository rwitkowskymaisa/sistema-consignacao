"""
Módulo de banco de dados — SQLite (dev) / PostgreSQL via Supabase (produção)
Sistema de Análise de Consignação

Schema baseado nos arquivos reais:
  - Saldo Consignado: Cod., Cliente, Gcon, Codigo (ISBN), Qtde Remet/Dev/Acert/Saldo, Valor
  - Base de Produtos: ISBN, Produto, Preço de Venda, Curva, Cobertura, vendas 3/6/12/24m
"""
import sqlite3
import hashlib
import os
import secrets
from datetime import datetime
from pathlib import Path
import pandas as pd

# ─── CONEXÃO ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "consignacao.db"


def get_connection():
    """
    Retorna conexão ativa.
    Em produção com DATABASE_URL, usa PostgreSQL (Supabase).
    Em desenvolvimento, usa SQLite local.
    """
    db_url = os.environ.get("DATABASE_URL", "")

    if db_url and db_url.startswith("postgresql"):
        # Produção — PostgreSQL / Supabase
        try:
            import sqlalchemy
            from sqlalchemy import create_engine, text
            engine = create_engine(db_url)
            return engine.connect()
        except ImportError:
            pass  # fallback para SQLite

    # Desenvolvimento — SQLite
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _is_sqlite(conn) -> bool:
    return isinstance(conn, sqlite3.Connection)


# ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────
def init_db():
    """Cria todas as tabelas se não existirem."""
    conn = get_connection()
    c = conn.cursor() if _is_sqlite(conn) else conn

    # ── USUÁRIOS ──────────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            papel TEXT NOT NULL DEFAULT 'vendedor',
            email_envio TEXT,
            cod_gcon TEXT,          -- código Gcon do vendedor no sistema (ex: VD0005)
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── BASE DE PRODUTOS ──────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn TEXT NOT NULL UNIQUE,
            cod_barras TEXT,
            autor TEXT,
            produto TEXT NOT NULL,      -- título
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
            curva TEXT,                 -- A / B / C
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
            upload_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── SALDO CONSIGNADO ──────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saldo_consignado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod_loja TEXT,              -- Cod+Loja
            cnpj TEXT,                  -- CNPJ do cliente
            codigo_cliente TEXT,        -- Cod.
            loja TEXT,                  -- Lj.
            cod_gcon TEXT,              -- Gcon (código do vendedor)
            uf TEXT,
            razao_social TEXT,          -- Cliente
            nf_serie TEXT,              -- NF/Serie
            data_emissao DATE,          -- Data Emissão
            isbn TEXT,                  -- Codigo (ISBN)
            cod_barras TEXT,
            titulo TEXT,
            autor TEXT,
            desconto REAL,              -- Desconto (ex: 0.5 = 50%)
            status_titulo TEXT,         -- STATUS (Disponivel, etc.)
            qtde_remessa INTEGER,       -- Qtde Remet
            qtde_dev_acert INTEGER,     -- Qtde Dev/Acert
            qtde_saldo INTEGER,         -- Qtde Saldo (em estoque no cliente)
            valor_liquido REAL,         -- Valor Liquido
            valor_bruto REAL,           -- Valor Bruto
            upload_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── TABELA TES ────────────────────────────────────────────────────────────
    # Classifica cada código TES como: Venda | Acerto Consignação | Envio Consignação | Outros
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tabela_tes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod_tes INTEGER NOT NULL UNIQUE,
            txt_padrao TEXT,
            finalidade TEXT,
            tipo_tes TEXT,
            faturamento TEXT,
            status TEXT,
            tipo TEXT NOT NULL          -- Venda | Acerto Consignação | Envio Consignação | Outros
        )
    """)

    # ── FATURAMENTO ───────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS faturamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_pedido TEXT,
            filial TEXT,
            codigo_cliente TEXT,        -- Codigo Cliente
            loja TEXT,
            razao_social TEXT,          -- Cliente
            data_emissao DATE,          -- Data Emissão (pedido)
            isbn TEXT,                  -- Codigo Produto
            titulo TEXT,                -- Produto
            editora TEXT,
            qtd_solicitada INTEGER,
            qtd_atendida INTEGER,       -- quantidade efetivamente faturada
            qtd_nao_atendida INTEGER,
            valor_unitario REAL,
            valor_atendido REAL,        -- receita realizada
            valor_nao_atendido REAL,
            preco_capa REAL,            -- Preço Capa Unitário
            desconto_pct REAL,          -- Desconto %
            status_produto TEXT,
            cod_gcon TEXT,              -- Codigo Vendedor (= Gcon)
            controle TEXT,              -- Controle Atendimento
            data_nota DATE,             -- Data Emissão Nota
            nro_nota TEXT,              -- Nro Nota Faturamento
            cod_tes INTEGER,            -- Código TES (FK para tabela_tes)
            upload_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── CLIENTES ──────────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_cliente TEXT NOT NULL,
            cnpj TEXT,
            cod_gcon TEXT,
            razao_social TEXT NOT NULL,
            uf TEXT,
            email TEXT,
            ativo INTEGER DEFAULT 1,
            UNIQUE(codigo_cliente)
        )
    """)

    # ── ENVIOS DO MAPA ────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS envios_mapa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        )
    """)

    conn.commit()

    # ── Migrações para bancos já existentes ──────────────────────────────────
    # Adiciona coluna cod_tes na tabela faturamento se ainda não existir
    try:
        conn.execute("ALTER TABLE faturamento ADD COLUMN cod_tes INTEGER")
        conn.commit()
    except Exception:
        pass  # Coluna já existe

    # Admin padrão
    row = conn.execute("SELECT id FROM usuarios WHERE username = 'admin'").fetchone()
    if not row:
        _insert_user(conn, "Administrador", "admin@empresa.com", "admin", "admin123", "admin")
        conn.commit()

    conn.close()


# ─── USUÁRIOS ─────────────────────────────────────────────────────────────────

def _hash(pw: str) -> str:
    return hashlib.sha256(f"consignacao_salt_v1{pw}".encode()).hexdigest()


def _insert_user(conn, nome, email, username, password, papel="vendedor",
                 email_envio=None, cod_gcon=None):
    conn.execute("""
        INSERT OR IGNORE INTO usuarios
        (nome, email, username, password_hash, papel, email_envio, cod_gcon)
        VALUES (?,?,?,?,?,?,?)
    """, (nome, email, username, _hash(password), papel, email_envio or email, cod_gcon))


def authenticate(username: str, password: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE username=? AND ativo=1", (username,)
    ).fetchone()
    conn.close()
    if row and row["password_hash"] == _hash(password):
        return dict(row)
    return None


def get_all_users() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id,nome,email,username,papel,email_envio,cod_gcon,ativo FROM usuarios ORDER BY nome"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(nome, email, username, password, papel="vendedor",
                email_envio=None, cod_gcon=None):
    conn = get_connection()
    try:
        _insert_user(conn, nome, email, username, password, papel, email_envio, cod_gcon)
        conn.commit()
        return True, "Usuário criado com sucesso."
    except sqlite3.IntegrityError as e:
        return False, f"Usuário ou email já existe."
    finally:
        conn.close()


def update_user_password(username, new_password):
    conn = get_connection()
    conn.execute("UPDATE usuarios SET password_hash=? WHERE username=?",
                 (_hash(new_password), username))
    conn.commit()
    conn.close()


def toggle_user_active(user_id: int, ativo: bool):
    conn = get_connection()
    conn.execute("UPDATE usuarios SET ativo=? WHERE id=?", (int(ativo), user_id))
    conn.commit()
    conn.close()


# ─── UPLOAD DE DADOS ──────────────────────────────────────────────────────────

def upsert_produtos(df: pd.DataFrame) -> int:
    """
    Importa a base de produtos.
    Colunas esperadas (após mapeamento): isbn, produto, preco_venda, curva, etc.
    """
    conn = get_connection()
    conn.execute("DELETE FROM produtos")
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
    df = df[cols_base].copy()
    df = df.dropna(subset=["isbn"])
    df.to_sql("produtos", conn, if_exists="append", index=False)
    conn.commit()
    n = len(df)
    conn.close()
    return n


def upsert_saldo_consignado(df: pd.DataFrame) -> int:
    """
    Importa o saldo consignado completo.
    Substitui todos os registros existentes.
    """
    conn = get_connection()
    conn.execute("DELETE FROM saldo_consignado")

    cols = [
        "cod_loja", "cnpj", "codigo_cliente", "loja", "cod_gcon", "uf",
        "razao_social", "nf_serie", "data_emissao", "isbn", "cod_barras",
        "titulo", "autor", "desconto", "status_titulo",
        "qtde_remessa", "qtde_dev_acert", "qtde_saldo",
        "valor_liquido", "valor_bruto"
    ]
    for col in cols:
        if col not in df.columns:
            df[col] = None
    df = df[cols].copy()
    df = df.dropna(subset=["codigo_cliente", "isbn"])
    df.to_sql("saldo_consignado", conn, if_exists="append", index=False)
    conn.commit()
    n = len(df)
    conn.close()
    _sync_clientes()
    return n


def upsert_tes(df: pd.DataFrame) -> int:
    """
    Importa a tabela TES completa.
    Colunas esperadas: cod_tes, txt_padrao, finalidade, tipo_tes, faturamento, status, tipo
    """
    conn = get_connection()
    conn.execute("DELETE FROM tabela_tes")
    cols = ["cod_tes", "txt_padrao", "finalidade", "tipo_tes", "faturamento", "status", "tipo"]
    for col in cols:
        if col not in df.columns:
            df[col] = None
    df = df[cols].copy()
    df = df.dropna(subset=["cod_tes"])
    df["tipo"] = df["tipo"].fillna("Outros").str.strip()
    df.to_sql("tabela_tes", conn, if_exists="append", index=False)
    conn.commit()
    n = len(df)
    conn.close()
    return n


def upsert_faturamento(df: pd.DataFrame) -> int:
    conn = get_connection()
    conn.execute("DELETE FROM faturamento")
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
    df = df[cols].copy()
    df = df.dropna(subset=["codigo_cliente", "isbn"])
    df.to_sql("faturamento", conn, if_exists="append", index=False)
    conn.commit()
    n = len(df)
    conn.close()
    return n


def _sync_clientes():
    """Sincroniza tabela de clientes a partir do saldo (inclui CNPJ)."""
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO clientes (codigo_cliente, cnpj, cod_gcon, razao_social, uf)
        SELECT DISTINCT codigo_cliente, cnpj, cod_gcon, razao_social, uf
        FROM saldo_consignado
        WHERE codigo_cliente IS NOT NULL
    """)
    # Atualiza CNPJ dos que já existem mas podem não ter CNPJ
    conn.execute("""
        UPDATE clientes
        SET cnpj = (
            SELECT cnpj FROM saldo_consignado s
            WHERE s.codigo_cliente = clientes.codigo_cliente
            AND s.cnpj IS NOT NULL LIMIT 1
        )
        WHERE cnpj IS NULL
    """)
    conn.commit()
    conn.close()


# ─── CONSULTAS ────────────────────────────────────────────────────────────────

def get_saldo_df(cod_gcon: str = None) -> pd.DataFrame:
    conn = get_connection()
    q = "SELECT * FROM saldo_consignado"
    params = None
    if cod_gcon:
        q += " WHERE cod_gcon=?"
        params = (cod_gcon,)
    df = pd.read_sql(q, conn, params=params)
    conn.close()
    return df


def get_produtos_df() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM produtos", conn)
    conn.close()
    return df


def get_tes_df() -> pd.DataFrame:
    """Retorna a tabela TES completa."""
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM tabela_tes", conn)
    conn.close()
    return df


def get_faturamento_df(cod_gcon: str = None, tipos_tes: list = None) -> pd.DataFrame:
    """
    Retorna faturamento enriquecido com tipo_tes da tabela TES.

    tipos_tes: lista de tipos para filtrar, ex: ['Venda', 'Acerto Consignação']
               None = todos os tipos.
    """
    conn = get_connection()
    q = """
        SELECT f.*, COALESCE(t.tipo, 'Outros') AS tipo_tes
        FROM faturamento f
        LEFT JOIN tabela_tes t ON f.cod_tes = t.cod_tes
        WHERE 1=1
    """
    params = []
    if cod_gcon:
        q += " AND f.cod_gcon=?"
        params.append(cod_gcon)
    df = pd.read_sql(q, conn, params=params or None)
    conn.close()

    # Normaliza a coluna tipo_tes (remove espaços)
    df["tipo_tes"] = df["tipo_tes"].fillna("Outros").str.strip()

    # Filtra por tipo se solicitado
    if tipos_tes:
        tipos_norm = [t.strip() for t in tipos_tes]
        df = df[df["tipo_tes"].isin(tipos_norm)]

    return df


def get_clientes(cod_gcon: str = None) -> list:
    conn = get_connection()
    if cod_gcon:
        rows = conn.execute(
            "SELECT * FROM clientes WHERE cod_gcon=? AND ativo=1 ORDER BY razao_social",
            (cod_gcon,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM clientes WHERE ativo=1 ORDER BY razao_social"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_cliente_email(codigo_cliente: str, email: str):
    conn = get_connection()
    conn.execute("UPDATE clientes SET email=? WHERE codigo_cliente=?", (email, codigo_cliente))
    conn.commit()
    conn.close()


# ─── ENVIOS ───────────────────────────────────────────────────────────────────

def registrar_envio(codigo_cliente, razao_social, email_cliente,
                    cod_gcon, mes_referencia, status="enviado",
                    observacao=None, reenviado=False) -> str:
    codigo_rastreio = secrets.token_hex(8).upper()
    conn = get_connection()
    conn.execute("""
        INSERT INTO envios_mapa
        (codigo_cliente, razao_social, email_cliente, cod_gcon,
         mes_referencia, status, codigo_rastreio, observacao, reenviado)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (codigo_cliente, razao_social, email_cliente, cod_gcon,
          mes_referencia, status, codigo_rastreio, observacao, int(reenviado)))
    conn.commit()
    conn.close()
    return codigo_rastreio


def get_envios_df(cod_gcon: str = None, mes_referencia: str = None) -> pd.DataFrame:
    conn = get_connection()
    q = "SELECT * FROM envios_mapa WHERE 1=1"
    params = []
    if cod_gcon:
        q += " AND cod_gcon=?"
        params.append(cod_gcon)
    if mes_referencia:
        q += " AND mes_referencia=?"
        params.append(mes_referencia)
    q += " ORDER BY data_envio DESC"
    df = pd.read_sql(q, conn, params=params or None)
    conn.close()
    return df


def update_status_envio(envio_id: int, novo_status: str, observacao: str = None):
    conn = get_connection()
    conn.execute("UPDATE envios_mapa SET status=?, observacao=? WHERE id=?",
                 (novo_status, observacao, envio_id))
    conn.commit()
    conn.close()


def get_status_envio_mes(cod_gcon: str = None) -> pd.DataFrame:
    mes_atual = datetime.now().strftime("%Y-%m")
    conn = get_connection()
    q = """
        SELECT c.codigo_cliente, c.cod_gcon, c.razao_social, c.uf, c.email,
               MAX(e.data_envio) as ultimo_envio,
               MAX(e.status) as ultimo_status,
               COUNT(e.id) as total_envios
        FROM clientes c
        LEFT JOIN envios_mapa e
            ON c.codigo_cliente = e.codigo_cliente
            AND e.mes_referencia = ?
        WHERE c.ativo = 1
    """
    params = [mes_atual]
    if cod_gcon:
        q += " AND c.cod_gcon = ?"
        params.append(cod_gcon)
    q += " GROUP BY c.codigo_cliente ORDER BY c.razao_social"
    df = pd.read_sql(q, conn, params=params)
    conn.close()
    df["mapa_enviado"] = df["ultimo_envio"].notna()
    return df


# ─── ANALYTICS ────────────────────────────────────────────────────────────────

def get_analise_consignacao(cod_gcon: str = None) -> pd.DataFrame:
    """
    Análise principal: saldo + produto + acerto.

    Acerto = qtde_dev_acert / qtde_remessa × 100
    Sem giro = qtde_dev_acert == 0 e qtde_saldo > 0
    """
    saldo = get_saldo_df(cod_gcon)
    if saldo.empty:
        return pd.DataFrame()

    produtos = get_produtos_df()

    # Garante tipos numéricos
    for col in ["qtde_remessa", "qtde_dev_acert", "qtde_saldo", "valor_liquido", "valor_bruto"]:
        saldo[col] = pd.to_numeric(saldo[col], errors="coerce").fillna(0)

    # Merge com base de produtos (enriquece com preço, curva, giro)
    if not produtos.empty:
        produtos_slim = produtos[[
            "isbn", "preco_venda", "curva", "cobertura_estoque",
            "vendas_12m", "vendas_6m", "vendas_3m",
            "status_publicacao", "editora", "area"
        ]].copy()
        saldo = saldo.merge(produtos_slim, on="isbn", how="left", suffixes=("", "_prod"))

    # Métricas derivadas
    saldo["pct_acerto"] = (saldo["qtde_dev_acert"] / saldo["qtde_remessa"].replace(0, 1) * 100).round(1)
    saldo["sem_giro"] = (saldo["qtde_dev_acert"] == 0) & (saldo["qtde_saldo"] > 0)

    # Dias em saldo (a partir da data de emissão)
    saldo["data_emissao"] = pd.to_datetime(saldo["data_emissao"], errors="coerce")
    saldo["dias_em_saldo"] = (pd.Timestamp.now() - saldo["data_emissao"]).dt.days

    # Valor potencial de acerto (preço de venda × saldo)
    if "preco_venda" in saldo.columns:
        saldo["valor_potencial"] = saldo["qtde_saldo"] * pd.to_numeric(saldo["preco_venda"], errors="coerce").fillna(0)
    else:
        saldo["valor_potencial"] = 0

    return saldo


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
        "total_clientes": int(df["codigo_cliente"].nunique()),
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
        "clientes_sem_giro": int(df[df["sem_giro"]]["codigo_cliente"].nunique()),
    }


def get_ranking_clientes(cod_gcon: str = None) -> pd.DataFrame:
    """Ranking de clientes por volume e acerto."""
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
    """
    Faturamento mensal para gráfico de evolução.

    Retorna colunas: mes, receita_total, receita_venda, receita_acerto_csg,
                     qtde_total, clientes
    - receita_total = Venda + Acerto Consignação
    - receita_venda = somente tipo_tes == 'Venda'
    - receita_acerto_csg = somente tipo_tes == 'Acerto Consignação'
    """
    fat = get_faturamento_df(cod_gcon)
    if fat.empty:
        return pd.DataFrame()

    # Usa data_nota (data da NF) ou data_emissao como fallback
    date_col = "data_nota" if "data_nota" in fat.columns else "data_emissao"
    fat[date_col] = pd.to_datetime(fat[date_col], errors="coerce")
    fat = fat.dropna(subset=[date_col])
    fat["mes"] = fat[date_col].dt.to_period("M").astype(str)

    val_col = "valor_atendido" if "valor_atendido" in fat.columns else "valor_faturado"
    qty_col = "qtd_atendida" if "qtd_atendida" in fat.columns else "quantidade_faturada"

    # Considera faturamento total = Venda + Acerto Consignação
    fat_faturamento = fat[fat["tipo_tes"].isin(["Venda", "Acerto Consignação"])]

    mes_total = fat_faturamento.groupby("mes").agg(
        receita_total=(val_col, "sum"),
        qtde_total=(qty_col, "sum"),
        clientes=("codigo_cliente", "nunique"),
    ).reset_index()

    # Separado por tipo
    mes_venda = (fat_faturamento[fat_faturamento["tipo_tes"] == "Venda"]
                 .groupby("mes")[[val_col]]
                 .sum().rename(columns={val_col: "receita_venda"}).reset_index())

    mes_acerto = (fat_faturamento[fat_faturamento["tipo_tes"] == "Acerto Consignação"]
                  .groupby("mes")[[val_col]]
                  .sum().rename(columns={val_col: "receita_acerto_csg"}).reset_index())

    result = mes_total.merge(mes_venda, on="mes", how="left")
    result = result.merge(mes_acerto, on="mes", how="left")
    result[["receita_venda", "receita_acerto_csg"]] = (
        result[["receita_venda", "receita_acerto_csg"]].fillna(0)
    )

    return result.sort_values("mes")


def get_acerto_vs_faturamento(cod_gcon: str = None) -> pd.DataFrame:
    """
    Cruza saldo consignado com faturamento por cliente.
    Compara o que foi consignado vs o que foi efetivamente faturado.
    """
    saldo = get_saldo_df(cod_gcon)
    fat = get_faturamento_df(cod_gcon)

    if saldo.empty:
        return pd.DataFrame()

    # Agrupa saldo por cliente
    saldo_cli = saldo.groupby(["codigo_cliente", "razao_social"]).agg(
        qtde_remessa=("qtde_remessa", "sum"),
        qtde_saldo=("qtde_saldo", "sum"),
        qtde_dev_acert=("qtde_dev_acert", "sum"),
        valor_liquido=("valor_liquido", "sum"),
    ).reset_index()

    if not fat.empty:
        # Agrupa faturamento por cliente
        qty_col = "qtd_atendida" if "qtd_atendida" in fat.columns else "quantidade_faturada"
        val_col = "valor_atendido" if "valor_atendido" in fat.columns else "valor_faturado"
        fat_cli = fat.groupby("codigo_cliente").agg(
            qtde_faturada=(qty_col, "sum"),
            valor_faturado=(val_col, "sum"),
        ).reset_index()

        merged = saldo_cli.merge(fat_cli, on="codigo_cliente", how="left")
    else:
        merged = saldo_cli.copy()
        merged["qtde_faturada"] = 0
        merged["valor_faturado"] = 0.0

    merged["qtde_faturada"] = merged["qtde_faturada"].fillna(0)
    merged["valor_faturado"] = merged["valor_faturado"].fillna(0.0)
    merged["pct_acerto"] = (
        merged["qtde_dev_acert"] / merged["qtde_remessa"].replace(0, 1) * 100
    ).round(1)

    return merged
