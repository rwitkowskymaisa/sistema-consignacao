"""
Página 1 — Upload de Arquivos
Cards de status com última atualização + formulário de importação.
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.database import (
    upsert_produtos, upsert_saldo_consignado,
    upsert_faturamento, upsert_tes, upsert_pipeline_b2b,
    upsert_pipeline_metas,
    get_ultima_atualizacao, get_ultima_atualizacao_pipeline, init_db
)
from utils.style import apply_theme, sidebar_header, sidebar_footer, COR_TEAL
from utils.auth import require_login

st.set_page_config(page_title="Upload · Consignação", page_icon="📂",
                   layout="wide", initial_sidebar_state="expanded")
init_db()
apply_theme()

usuario  = require_login()
is_admin = usuario["papel"] == "admin"

sidebar_header(usuario)
sidebar_footer(usuario)

# ─── CABEÇALHO ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <div>
    <div class="page-title">Upload de Arquivos</div>
    <div class="page-subtitle">Importe os arquivos Excel para atualizar a base de dados</div>
  </div>
</div>
""", unsafe_allow_html=True)

if not is_admin:
    st.info(f"Seus dados serão vinculados ao Gcon: **{usuario.get('cod_gcon') or 'não configurado'}**")

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def fmt_data(iso_str):
    if not iso_str:
        return "Nunca importado"
    try:
        dt = datetime.fromisoformat(str(iso_str))
        return dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(iso_str)[:16]

def preview_df(df, n=5):
    st.dataframe(df.head(n), use_container_width=True, height=160)


def parse_numero_br(series: pd.Series) -> pd.Series:
    """
    Converte colunas numéricas em formato brasileiro (1.234,56) para float.
    Funciona também com formato americano (1234.56) e valores já numéricos.
    """
    if pd.api.types.is_numeric_dtype(series):
        return series
    s = (series.astype(str)
               .str.strip()
               .str.replace(r"R\$\s*", "", regex=True)   # remove R$
               .str.replace(r"\s+", "", regex=True))      # remove espaços internos
    # Formato BR: tem ponto como milhar E vírgula como decimal → "1.234,56"
    br_mask = s.str.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$")
    if br_mask.any():
        s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:
        # Só vírgula → provavelmente decimal BR → "1234,56"
        s = s.str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def select_col(label, cols_list, defaults, key, required=False):
    opcoes = ["(não usar)"] + cols_list
    idx = 0
    for d in (defaults if isinstance(defaults, list) else [defaults]):
        if d in cols_list:
            idx = cols_list.index(d) + 1
            break
    return st.selectbox(label + (" *" if required else ""), opcoes, index=idx, key=key)

# ─── CARDS DE STATUS ──────────────────────────────────────────────────────────
ult = get_ultima_atualizacao()

def status_card(icone, titulo, chave, descricao):
    data    = fmt_data(ult.get(chave))
    count   = ult.get(f"{chave}_count", 0)
    ok      = ult.get(chave) is not None
    cor_dot = "#10B981" if ok else "#F59E0B"
    cor_dt  = "#6B7280" if ok else "#F59E0B"
    badge   = f"{count:,} registros" if ok else "Aguardando importação"

    st.markdown(f"""
    <div class="kpi-card" style="padding:16px 20px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <span style="font-size:22px;">{icone}</span>
        <div>
          <div style="font-size:13px;font-weight:700;color:#111827;">{titulo}</div>
          <div style="font-size:11px;color:#6B7280;">{descricao}</div>
        </div>
        <div style="margin-left:auto;text-align:right;">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                background:{cor_dot};margin-right:4px;"></span>
          <span style="font-size:11px;color:{cor_dot};font-weight:600;">
            {"Atualizado" if ok else "Pendente"}
          </span>
        </div>
      </div>
      <div style="font-size:12px;color:{cor_dt};margin-bottom:2px;">
        🕐 {data}
      </div>
      <div style="font-size:11px;color:#9CA3AF;">{badge}</div>
    </div>
    """, unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
with c1: status_card("📖", "Base de Produtos",    "produtos",         "Catálogo · Preços · Estoque")
with c2: status_card("📦", "Saldo Consignado",    "saldo_consignado", "Remessa · Dev/Acerto · Saldo")
with c3: status_card("💰", "Faturamento",         "faturamento",      "Vendas realizadas por cliente")
with c4: status_card("🏷️", "Tabela TES",          "tabela_tes",       "Classificação de faturamento")

# Card Pipeline B2B (usa função própria pois não está em get_ultima_atualizacao)
_ult_pipe = get_ultima_atualizacao_pipeline()
_ok_pipe  = _ult_pipe is not None
with c5:
    st.markdown(f"""
    <div class="kpi-card" style="padding:16px 20px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <span style="font-size:22px;">📈</span>
        <div>
          <div style="font-size:13px;font-weight:700;color:#111827;">Pipeline B2B</div>
          <div style="font-size:11px;color:#6B7280;">Receita · Carteira · Canal · Pipeline</div>
        </div>
        <div style="margin-left:auto;text-align:right;">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                background:{'#10B981' if _ok_pipe else '#F59E0B'};margin-right:4px;"></span>
          <span style="font-size:11px;color:{'#10B981' if _ok_pipe else '#F59E0B'};font-weight:600;">
            {"Atualizado" if _ok_pipe else "Pendente"}
          </span>
        </div>
      </div>
      <div style="font-size:12px;color:{'#6B7280' if _ok_pipe else '#F59E0B'};margin-bottom:2px;">
        🕐 {_ult_pipe or "Nunca importado"}
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

# ─── FORMULÁRIOS DE IMPORTAÇÃO ────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
# 1. BASE DE PRODUTOS
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("📖  **1. Base de Produtos**  (catálogo de títulos, preços, curva ABC, giro)", expanded=False):
    f1 = st.file_uploader("Excel de Base de Produtos", type=["xlsx","xls"], key="f_prod")
    if f1:
        try:
            df_raw = pd.read_excel(f1, dtype=str)
            df_raw.columns = df_raw.columns.str.strip()
            cols = list(df_raw.columns)
            st.success(f"✅ {len(df_raw):,} linhas · {len(cols)} colunas")
            preview_df(df_raw)
            st.markdown("**Mapeamento de colunas:**")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown("**Identificação**")
                p_isbn    = select_col("ISBN / Código",    cols, ["ISBN","Codigo","isbn"],    "p_isbn",  True)
                p_barras  = select_col("Cód. de Barras",   cols, ["Código Barras","Cod Barras"], "p_barras")
                p_produto = select_col("Título / Produto", cols, ["Produto","Titulo","titulo"], "p_prod",  True)
                p_autor   = select_col("Autor",            cols, ["Autor","autor"],           "p_autor")
                p_editora = select_col("Editora",          cols, ["Editora","editora"],       "p_editora")
            with c2:
                st.markdown("**Preço e status**")
                p_preco  = select_col("Preço de Venda",    cols, ["Preço de Venda","preco_venda"], "p_preco")
                p_status = select_col("Status",            cols, ["Status","status"],        "p_status")
                p_st_pub = select_col("Status Publicação", cols, ["Status Publicação","Status Publicacao"], "p_stpub")
                p_curva  = select_col("Curva (A/B/C)",     cols, ["Curva","curva"],          "p_curva")
                p_phase  = select_col("Phase Out",         cols, ["PhaseOut","Phase Out"],   "p_phase")
            with c3:
                st.markdown("**Estoque**")
                p_est_sp  = select_col("Estoque SP",    cols, ["Estoque SP"],    "p_esp")
                p_est_cl  = select_col("Estoque CL",    cols, ["Estoque CL"],    "p_ecl")
                p_est_pr  = select_col("Estoque PR",    cols, ["Estoque PR"],    "p_epr")
                p_est_tot = select_col("Estoque Total", cols, ["Estoque Total"], "p_etot")
                p_cobert  = select_col("Cobertura",     cols, ["Cobertura Estoque","Cobertura"], "p_cob")
            with c4:
                st.markdown("**Histórico de vendas**")
                p_v60   = select_col("Vendas 60 meses", cols, ["60 meses"],          "p_v60")
                p_v24   = select_col("Vendas 24 meses", cols, ["24 meses"],          "p_v24")
                p_v12   = select_col("Vendas 12 meses", cols, ["12 meses"],          "p_v12")
                p_v6    = select_col("Vendas 6 meses",  cols, ["6 meses"],           "p_v6")
                p_v3    = select_col("Vendas 3 meses",  cols, ["3 meses"],           "p_v3")
                p_med12 = select_col("Mediana 12m",     cols, ["Mediana 12 meses"],  "p_m12")
                p_med24 = select_col("Mediana 24m",     cols, ["Mediana 24 meses"],  "p_m24")

            if st.button("💾 Importar Base de Produtos", type="primary", key="btn_prod"):
                if p_isbn == "(não usar)" or p_produto == "(não usar)":
                    st.error("ISBN e Título são obrigatórios.")
                else:
                    mapa = {
                        "isbn": p_isbn, "cod_barras": p_barras,
                        "produto": p_produto, "autor": p_autor, "editora": p_editora,
                        "preco_venda": p_preco, "status": p_status,
                        "status_publicacao": p_st_pub, "curva": p_curva, "phase_out": p_phase,
                        "estoque_sp": p_est_sp, "estoque_cl": p_est_cl,
                        "estoque_pr": p_est_pr, "estoque_total": p_est_tot,
                        "cobertura_estoque": p_cobert,
                        "vendas_60m": p_v60, "vendas_24m": p_v24, "vendas_12m": p_v12,
                        "vendas_6m": p_v6, "vendas_3m": p_v3,
                        "mediana_12m": p_med12, "mediana_24m": p_med24,
                    }
                    rename = {v: k for k, v in mapa.items() if v and v != "(não usar)" and v in df_raw.columns}
                    df_out = df_raw.rename(columns=rename)
                    for nc in ["preco_venda","estoque_sp","estoque_cl","estoque_pr","estoque_total",
                               "cobertura_estoque","vendas_60m","vendas_24m","vendas_12m",
                               "vendas_6m","vendas_3m","mediana_12m","mediana_24m"]:
                        if nc in df_out.columns:
                            df_out[nc] = pd.to_numeric(df_out[nc], errors="coerce")
                    with st.spinner("Importando..."):
                        n = upsert_produtos(df_out)
                    st.success(f"✅ {n:,} produtos importados!")
                    st.rerun()
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 2. SALDO CONSIGNADO
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("📦  **2. Saldo Consignado**  (remessa, devolução/acerto, saldo atual)", expanded=False):
    f2 = st.file_uploader("Excel de Saldo Consignado", type=["xlsx","xls"], key="f_saldo")
    if f2:
        try:
            df_raw = pd.read_excel(f2, dtype=str)
            df_raw.columns = df_raw.columns.str.strip()
            cols = list(df_raw.columns)
            st.success(f"✅ {len(df_raw):,} linhas · {len(cols)} colunas")
            preview_df(df_raw)
            st.markdown("**Mapeamento de colunas:**")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Cliente**")
                s_cod_loja = select_col("Cod+Loja",        cols, ["Cod+Loja"],                  "s_codloja")
                s_cnpj     = select_col("CNPJ",            cols, ["CNPJ","cnpj"],               "s_cnpj")
                s_cod_cli  = select_col("Cód. Cliente",    cols, ["Cod.","Cod","codigo_cliente"],"s_codcli", True)
                s_loja     = select_col("Loja",            cols, ["Lj.","Loja"],                "s_loja")
                s_gcon     = select_col("Gcon (código)",   cols, ["Gcon","gcon"],               "s_gcon")
                s_nome_gcon= select_col("Vendedor (nome)", cols, ["Vendedor","vendedor","Nome Vendedor"],"s_nomegcon")
                s_uf       = select_col("UF",              cols, ["UF","uf"],                   "s_uf")
                s_razao    = select_col("Razão Social",    cols, ["Cliente","Razao Social"],     "s_razao", True)
            with c2:
                st.markdown("**Livro / NF**")
                s_nf         = select_col("NF/Série",       cols, ["NF/Serie","NF"],             "s_nf")
                s_data_em    = select_col("Data Emissão",   cols, ["Data Emissão","Data Emissao"],"s_dataem")
                s_isbn       = select_col("Código / ISBN",  cols, ["Codigo","ISBN","isbn"],      "s_isbn", True)
                s_barras     = select_col("Cód. de Barras", cols, ["Cod Barras"],               "s_barras")
                s_titulo     = select_col("Título",         cols, ["Titulo","titulo","Produto"], "s_titulo")
                s_autor      = select_col("Autor",          cols, ["Autor"],                    "s_autor")
                s_desconto   = select_col("Desconto",       cols, ["Desconto"],                 "s_desc")
                s_status_tit = select_col("Status Título",  cols, ["STATUS","Status"],          "s_stattit")
            with c3:
                st.markdown("**Quantidades e Valores**")
                s_qtde_rem   = select_col("Qtde Remessa",   cols, ["Qtde Remet","Qtde Remessa"],"s_qtrem", True)
                s_qtde_dev   = select_col("Qtde Dev/Acert", cols, ["Qtde Dev/Acert"],           "s_qtdev", True)
                s_qtde_saldo = select_col("Qtde Saldo",     cols, ["Qtde Saldo","Saldo"],       "s_qtsaldo", True)
                s_vl         = select_col("Valor Líquido",  cols, ["Valor Liquido","Valor Líquido","VLR LIQUIDO","Vlr Liquido","valor_liquido"],"s_vl")
                s_vb         = select_col("Valor Bruto",    cols, ["Valor Bruto","VLR BRUTO","Vlr Bruto","valor_bruto"],"s_vb")

            if st.button("💾 Importar Saldo Consignado", type="primary", key="btn_saldo"):
                if any(v == "(não usar)" for v in [s_cod_cli, s_razao, s_isbn, s_qtde_rem, s_qtde_dev, s_qtde_saldo]):
                    st.error("Obrigatórios: Cód. Cliente, Razão Social, ISBN, Qtde Remessa, Dev/Acert, Saldo.")
                else:
                    mapa = {
                        "cod_loja": s_cod_loja, "cnpj": s_cnpj,
                        "codigo_cliente": s_cod_cli, "loja": s_loja,
                        "cod_gcon": s_gcon, "nome_gcon": s_nome_gcon,
                        "uf": s_uf, "razao_social": s_razao, "nf_serie": s_nf,
                        "data_emissao": s_data_em, "isbn": s_isbn, "cod_barras": s_barras,
                        "titulo": s_titulo, "autor": s_autor, "desconto": s_desconto,
                        "status_titulo": s_status_tit,
                        "qtde_remessa": s_qtde_rem, "qtde_dev_acert": s_qtde_dev,
                        "qtde_saldo": s_qtde_saldo, "valor_liquido": s_vl, "valor_bruto": s_vb,
                    }
                    rename = {v: k for k, v in mapa.items() if v and v != "(não usar)" and v in df_raw.columns}
                    df_out = df_raw.rename(columns=rename)
                    for nc in ["qtde_remessa","qtde_dev_acert","qtde_saldo","valor_liquido","valor_bruto","desconto"]:
                        if nc in df_out.columns:
                            df_out[nc] = parse_numero_br(df_out[nc]).fillna(0)
                    df_out["data_emissao"] = pd.to_datetime(df_out.get("data_emissao"), errors="coerce")
                    with st.spinner("Importando..."):
                        n = upsert_saldo_consignado(df_out)
                    gcons = df_out["cod_gcon"].dropna().unique().tolist() if "cod_gcon" in df_out.columns else []
                    st.success(f"✅ {n:,} registros importados!")
                    if gcons:
                        st.info(f"💡 Gcon encontrados: {gcons} — vincule em **Configurações → Usuários**.")
                    st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 3. FATURAMENTO
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("💰  **3. Faturamento dos Clientes**  (vendas realizadas)", expanded=False):
    st.info("O faturamento enriquece a análise com receita realizada mês a mês.")
    f3 = st.file_uploader("Excel de Faturamento", type=["xlsx","xls"], key="f_fat")
    if f3:
        try:
            df_raw = pd.read_excel(f3, dtype=str)
            df_raw.columns = df_raw.columns.str.strip()
            cols = list(df_raw.columns)
            st.success(f"✅ {len(df_raw):,} linhas · {len(cols)} colunas")
            preview_df(df_raw)
            st.markdown("**Mapeamento de colunas:**")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown("**Cliente / Pedido**")
                f_nro_ped = select_col("Nro Pedido",   cols, ["Nro Pedido"],          "f_nped")
                f_filial  = select_col("Filial",        cols, ["Filial"],              "f_fil")
                f_cod_cli = select_col("Cód. Cliente",  cols, ["Codigo Cliente","Cod."],"f_cc", True)
                f_loja    = select_col("Loja",          cols, ["Loja","Lj."],          "f_lj")
                f_razao   = select_col("Razão Social",  cols, ["Cliente","Razao Social"],"f_razao")
            with c2:
                st.markdown("**Produto**")
                f_isbn    = select_col("ISBN / Cód.",   cols, ["Codigo Produto","Codigo","ISBN"],"f_isbn", True)
                f_titulo  = select_col("Título",        cols, ["Produto","Titulo"],    "f_tit")
                f_editora = select_col("Editora",       cols, ["Editora"],             "f_edit")
                f_st_prod = select_col("Status Produto",cols, ["Status Produto"],      "f_stprod")
                f_gcon    = select_col("Gcon/Vendedor", cols, ["Codigo Vendedor","Gcon","Vendedor"],"f_gcon")
            with c3:
                st.markdown("**Quantidades**")
                f_qtd_sol  = select_col("Qtd Solicitada",   cols, ["Qtd Solicitada"],           "f_qtsol")
                f_qtd_at   = select_col("Qtd Atendida ★",  cols, ["Qtd Atendida"],             "f_qtat", True)
                f_qtd_nao  = select_col("Qtd Não Atendida", cols, ["Qtd Não Atendida"],         "f_qtnao")
                f_controle = select_col("Controle Atend.",  cols, ["Controle Atendimento"],      "f_ctrl")
            with c4:
                st.markdown("**Valores, Datas e TES**")
                f_vunit    = select_col("Valor Unitário",    cols, ["Valor Unitário"],           "f_vunit")
                f_val_at   = select_col("Valor Atendido ★", cols, ["Valor Atendido"],           "f_valat", True)
                f_val_nao  = select_col("Valor Não Atend.", cols, ["Valor Não Atendido"],       "f_valnao")
                f_preco_c  = select_col("Preço Capa",       cols, ["Preço Capa Unitário"],      "f_pcapa")
                f_desc_pct = select_col("Desconto %",       cols, ["Desconto %","Desconto"],    "f_desc")
                f_data_em  = select_col("Data Emissão",     cols, ["Data Emissão","Data Emissao"],"f_dataem")
                f_data_nf  = select_col("Data Nota",        cols, ["Data Emissão Nota","Data Nota"],"f_datanf")
                f_nro_nota = select_col("Nro Nota",         cols, ["Nro Nota Faturamento","Nro Nota"],"f_nota")
                f_cod_tes  = select_col("Código TES ★",    cols, ["Codigo TES","Codigo Tes","cod_tes"],"f_tes")

            if st.button("💾 Importar Faturamento", type="primary", key="btn_fat"):
                if any(v == "(não usar)" for v in [f_cod_cli, f_isbn, f_qtd_at, f_val_at]):
                    st.error("Obrigatórios: Cód. Cliente, ISBN, Qtd Atendida, Valor Atendido.")
                else:
                    mapa = {
                        "nro_pedido": f_nro_ped, "filial": f_filial,
                        "codigo_cliente": f_cod_cli, "loja": f_loja, "razao_social": f_razao,
                        "data_emissao": f_data_em, "isbn": f_isbn, "titulo": f_titulo,
                        "editora": f_editora, "qtd_solicitada": f_qtd_sol,
                        "qtd_atendida": f_qtd_at, "qtd_nao_atendida": f_qtd_nao,
                        "valor_unitario": f_vunit, "valor_atendido": f_val_at,
                        "valor_nao_atendido": f_val_nao, "preco_capa": f_preco_c,
                        "desconto_pct": f_desc_pct, "status_produto": f_st_prod,
                        "cod_gcon": f_gcon, "controle": f_controle,
                        "data_nota": f_data_nf, "nro_nota": f_nro_nota, "cod_tes": f_cod_tes,
                    }
                    rename = {v: k for k, v in mapa.items() if v and v != "(não usar)" and v in df_raw.columns}
                    df_out = df_raw.rename(columns=rename)
                    for nc in ["qtd_solicitada","qtd_atendida","qtd_nao_atendida"]:
                        if nc in df_out.columns:
                            df_out[nc] = pd.to_numeric(df_out[nc], errors="coerce").fillna(0).astype(int)
                    for nc in ["valor_unitario","valor_atendido","valor_nao_atendido","preco_capa","desconto_pct"]:
                        if nc in df_out.columns:
                            df_out[nc] = pd.to_numeric(df_out[nc], errors="coerce").fillna(0)
                    for dc in ["data_emissao","data_nota"]:
                        if dc in df_out.columns:
                            df_out[dc] = pd.to_datetime(df_out[dc], errors="coerce")
                    if "cod_tes" in df_out.columns:
                        df_out["cod_tes"] = pd.to_numeric(df_out["cod_tes"], errors="coerce")
                    with st.spinner("Importando..."):
                        n = upsert_faturamento(df_out)
                    st.success(f"✅ {n:,} registros de faturamento importados!")
                    if f_cod_tes == "(não usar)":
                        st.warning("⚠️ Coluna TES não mapeada. Importe a Tabela TES abaixo.")
                    st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 4. TABELA TES
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("🏷️  **4. Tabela TES**  (classifica faturamento: Venda / Acerto / Envio / Outros)", expanded=False):
    st.info(
        "Obrigatória para distinguir **vendas diretas** de **acertos de consignação**. "
        "Importe o arquivo `TES COMPLETA.xlsx`. Deve conter: código TES e Tipo."
    )
    f4 = st.file_uploader("Excel da Tabela TES", type=["xlsx","xls"], key="f_tes_file")
    if f4:
        try:
            df_raw = pd.read_excel(f4, dtype=str)
            df_raw.columns = df_raw.columns.str.strip()
            cols = list(df_raw.columns)
            st.success(f"✅ {len(df_raw):,} códigos TES · {len(cols)} colunas")
            preview_df(df_raw)
            st.markdown("**Mapeamento de colunas:**")
            c1, c2 = st.columns(2)
            with c1:
                t_cod      = select_col("Código TES ★",   cols, ["TES","Cod TES","cod_tes"],  "t_cod", True)
                t_txt      = select_col("Descrição",       cols, ["Txt Padrao","Descricao"],   "t_txt")
                t_final    = select_col("Finalidade",      cols, ["Finalidade"],               "t_final")
            with c2:
                t_tipo_tes = select_col("Tipo do TES",    cols, ["Tipo do TES","Tipo TES"],   "t_tipes")
                t_fat      = select_col("Faturamento",     cols, ["Faturamento"],              "t_fat")
                t_status   = select_col("Status",         cols, ["Status","status"],           "t_status")
                t_tipo     = select_col("Tipo ★ (Venda/Acerto/Envio/Outros)", cols,
                                        ["Tipo","tipo"], "t_tipo", True)

            if st.button("💾 Importar Tabela TES", type="primary", key="btn_tes"):
                if any(v == "(não usar)" for v in [t_cod, t_tipo]):
                    st.error("Obrigatórios: Código TES e Tipo.")
                else:
                    mapa = {
                        "cod_tes": t_cod, "txt_padrao": t_txt, "finalidade": t_final,
                        "tipo_tes": t_tipo_tes, "faturamento": t_fat,
                        "status": t_status, "tipo": t_tipo,
                    }
                    rename = {v: k for k, v in mapa.items() if v and v != "(não usar)" and v in df_raw.columns}
                    df_out = df_raw.rename(columns=rename)
                    df_out["cod_tes"] = pd.to_numeric(df_out["cod_tes"], errors="coerce")
                    with st.spinner("Importando..."):
                        n = upsert_tes(df_out)
                    st.success(f"✅ {n:,} códigos TES importados!")
                    if "tipo" in df_out.columns:
                        contagem = df_out["tipo"].str.strip().value_counts()
                        st.dataframe(
                            contagem.reset_index().rename(columns={"index":"Tipo","tipo":"Qtde"}),
                            use_container_width=True, hide_index=True
                        )
                    st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 5. PIPELINE B2B
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("📈  **5. Pipeline B2B**  (receita por carteira/canal · evolutivo 2023-2026 · pipeline)", expanded=False):
    st.info(
        "Importe o arquivo **Receita_Clientes_Mensal.xlsx** (aba **Agrupado**). "
        "O sistema lê automaticamente os dados mensais 2023-2026, totais anuais e pipeline do mês."
    )
    f5 = st.file_uploader("Excel Pipeline B2B (aba Agrupado)", type=["xlsx","xls"], key="f_pipeline")
    if f5:
        try:
            df_raw = pd.read_excel(f5, sheet_name="Agrupado", header=3, dtype=str)
            df_raw.columns = [str(c) for c in df_raw.columns]
            df_raw = df_raw[df_raw["Carteira"].notna()].copy()
            st.success(f"✅ {len(df_raw):,} clientes encontrados na aba Agrupado")
            preview_df(df_raw[["Clientes","Carteira","Canais"]].head(5))

            if st.button("💾 Importar Pipeline B2B", type="primary", key="btn_pipeline"):
                with st.spinner("Processando dados..."):
                    # ── Colunas mensais 2023-2026 ────────────────────────────
                    meses_cols = {}
                    for ano in [2023, 2024, 2025, 2026]:
                        for mes in range(1, 13):
                            chave = f"{ano}-{mes:02d}-01 00:00:00"
                            if chave in df_raw.columns:
                                meses_cols[(ano, mes)] = chave

                    # ── Formato longo (mensal) ───────────────────────────────
                    rows_mensal = []
                    for (ano, mes), col in meses_cols.items():
                        tmp = df_raw[["Agrupador2","Clientes","Carteira","Canais", col]].copy()
                        tmp.columns = ["cod_cliente","nome_cliente","carteira","canal","valor"]
                        tmp["ano"] = ano
                        tmp["mes"] = mes
                        tmp["valor"] = pd.to_numeric(tmp["valor"], errors="coerce").fillna(0)
                        rows_mensal.append(tmp)
                    df_mensal = pd.concat(rows_mensal, ignore_index=True)

                    # ── Resumo por cliente ───────────────────────────────────
                    def _num(col):
                        return pd.to_numeric(
                            df_raw.get(col, pd.Series([0]*len(df_raw))), errors="coerce"
                        ).fillna(0).values

                    df_resumo = pd.DataFrame({
                        "cod_cliente":  df_raw["Agrupador2"].astype(str).values,
                        "nome_cliente": df_raw["Clientes"].values,
                        "carteira":     df_raw["Carteira"].values,
                        "canal":        df_raw["Canais"].values,
                        "tt_2023":      _num("TT 2023"),
                        "tt_2024":      _num("TT 2024"),
                        "tt_2025":      _num("TT2025"),
                        "ytd_2026":     _num("TT2026"),
                        "ytd_2025":     _num("YTD AA"),
                        "pct_ytd":      _num("(%) YTD AA"),
                        "gap_ytd":      _num("Gap YTD 25vs26"),
                        "pipeline_jul": _num("Pipelie Jul/26"),
                    })

                    n_m, n_r = upsert_pipeline_b2b(df_mensal, df_resumo)

                st.success(f"✅ {n_r:,} clientes · {n_m:,} registros mensais importados!")

                # Sumário por carteira
                st.markdown("**Resumo por Carteira:**")
                cart = df_resumo.groupby("carteira").agg(
                    Clientes=("cod_cliente","count"),
                    YTD_2026=("ytd_2026","sum"),
                    YTD_2025=("ytd_2025","sum"),
                    Pipeline=("pipeline_jul","sum"),
                ).reset_index()
                for col in ["YTD_2026","YTD_2025","Pipeline"]:
                    cart[col] = cart[col].map("R$ {:,.0f}".format)
                st.dataframe(cart, use_container_width=True, hide_index=True)

                # ── Aba Metas (Budget / Forecast / Real por canal/mês) ───────
                MESES_MAP = {
                    "jan":"01","fev":"02","mar":"03","abr":"04","mai":"05","jun":"06",
                    "jul":"07","ago":"08","set":"09","out":"10","nov":"11","dez":"12"
                }
                try:
                    xl_sheets = pd.ExcelFile(f5).sheet_names
                    if "Metas" in xl_sheets:
                        with st.spinner("Lendo aba Metas..."):
                            df_metas_raw = pd.read_excel(f5, sheet_name="Metas", header=None)
                            months_row  = df_metas_raw.iloc[0]
                            ano_atual   = datetime.now().year

                            # Encontra grupos de colunas por mês (posição onde aparece o nome do mês)
                            month_groups = []
                            for idx, val in enumerate(months_row):
                                if pd.notna(val):
                                    chave = str(val).strip().lower()[:3]
                                    if chave in MESES_MAP:
                                        month_groups.append((str(val).strip(), int(idx)))

                            # Linhas de dados (a partir da linha 3 do Excel = iloc[2])
                            # Exclui linhas de totais e cabeçalho
                            data_rows = df_metas_raw.iloc[2:].copy()
                            data_rows = data_rows[data_rows.iloc[:, 0].notna()].copy()
                            data_rows = data_rows[
                                ~data_rows.iloc[:, 0].astype(str).str.strip()
                                 .str.lower().isin(["nan", "", "canais"])
                                & ~data_rows.iloc[:, 0].astype(str).str.strip()
                                 .str.startswith("Total")
                            ].copy()

                            def _safe_float(x):
                                try:
                                    return float(x) if pd.notna(x) else None
                                except (ValueError, TypeError):
                                    return None

                            records_metas = []
                            for month_name, start_col in month_groups:
                                chave = month_name.lower()[:3]
                                mes_str = f"{ano_atual}-{MESES_MAP[chave]}"
                                for _, row in data_rows.iterrows():
                                    canal = str(row.iloc[0]).strip()
                                    records_metas.append({
                                        "canal":      canal,
                                        "mes":        mes_str,
                                        "budget":     _safe_float(row.iloc[start_col]),
                                        "forecast":   _safe_float(row.iloc[start_col + 1]),
                                        "real_value": _safe_float(row.iloc[start_col + 2]),
                                    })

                            df_metas_long = pd.DataFrame(records_metas)
                            n_metas = upsert_pipeline_metas(df_metas_long)
                        st.success(f"✅ Metas: {n_metas:,} registros importados (Budget/Forecast/Real por canal/mês)")
                    else:
                        st.warning("⚠️ Aba 'Metas' não encontrada no arquivo — Budget/Forecast não foram importados. "
                                   "Adicione a aba 'Metas' ao Excel e reimporte.")
                except Exception as e_metas:
                    st.warning(f"⚠️ Não foi possível ler a aba Metas: {e_metas}")

                st.rerun()
        except Exception as e:
            st.error(f"Erro ao processar Pipeline B2B: {e}")
