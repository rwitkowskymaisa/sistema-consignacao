"""
Tema visual — Artmed Editora
Layout inspirado no Librion: sidebar escura, conteúdo claro, cards brancos.
"""

# Cores da marca Artmed
COR_TEAL    = "#00A99D"
COR_DARK    = "#2C2C2C"
COR_SIDEBAR = "#1F2937"
COR_BG      = "#F3F4F6"
COR_CARD    = "#FFFFFF"
COR_TEXTO   = "#111827"
COR_CINZA   = "#6B7280"
COR_BORDA   = "#E5E7EB"
COR_SUCESSO = "#10B981"
COR_ALERTA  = "#F59E0B"
COR_ERRO    = "#EF4444"
COR_AZUL    = "#3B82F6"


LOGO_SVG = """
<svg width="160" height="52" viewBox="0 0 160 52" xmlns="http://www.w3.org/2000/svg">
  <text x="4" y="36" font-family="Georgia, serif" font-size="30" font-weight="700"
        fill="#FFFFFF" letter-spacing="-1">artmed</text>
  <text x="4" y="50" font-family="Arial, sans-serif" font-size="11" font-weight="400"
        fill="#9CA3AF" letter-spacing="4">EDITORA</text>
  <text x="138" y="18" font-family="Arial, sans-serif" font-size="20" font-weight="700"
        fill="#00A99D">+</text>
</svg>
"""


CSS_GLOBAL = f"""
<style>
/* ── Reset e base ── */
html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
}}

/* ── Fundo principal ── */
.stApp {{
    background-color: {COR_BG};
}}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {{
    background-color: {COR_SIDEBAR} !important;
    border-right: none !important;
    min-width: 230px !important;
    max-width: 230px !important;
}}
section[data-testid="stSidebar"] * {{
    color: #D1D5DB !important;
}}
section[data-testid="stSidebar"] .stButton > button {{
    background: transparent !important;
    color: #D1D5DB !important;
    border: none !important;
    text-align: left !important;
    padding: 6px 12px !important;
    font-size: 14px !important;
    width: 100% !important;
    border-radius: 6px !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,0.08) !important;
    color: #FFFFFF !important;
}}
.sidebar-logo {{
    padding: 20px 16px 12px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 8px;
}}
.sidebar-section {{
    padding: 16px 16px 4px 16px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #6B7280 !important;
    text-transform: uppercase;
}}
.sidebar-user {{
    padding: 12px 16px;
    border-top: 1px solid rgba(255,255,255,0.08);
    margin-top: auto;
    font-size: 13px;
}}
.sidebar-badge {{
    display: inline-block;
    background: {COR_TEAL};
    color: white !important;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

/* ── Cabeçalho de página ── */
.page-header {{
    background: {COR_CARD};
    border-bottom: 1px solid {COR_BORDA};
    padding: 16px 24px;
    margin: -16px -16px 24px -16px;
    display: flex;
    align-items: center;
    gap: 12px;
}}
.page-title {{
    font-size: 20px;
    font-weight: 700;
    color: {COR_TEXTO};
    margin: 0;
}}
.page-subtitle {{
    font-size: 13px;
    color: {COR_CINZA};
    margin: 2px 0 0 0;
}}

/* ── Cards KPI ── */
.kpi-card {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
.kpi-label {{
    font-size: 12px;
    font-weight: 600;
    color: {COR_CINZA};
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
}}
.kpi-value {{
    font-size: 28px;
    font-weight: 800;
    color: {COR_TEXTO};
    line-height: 1.1;
}}
.kpi-value.teal  {{ color: {COR_TEAL}; }}
.kpi-value.blue  {{ color: {COR_AZUL}; }}
.kpi-value.green {{ color: {COR_SUCESSO}; }}
.kpi-value.amber {{ color: {COR_ALERTA}; }}
.kpi-value.red   {{ color: {COR_ERRO}; }}
.kpi-sub {{
    font-size: 12px;
    color: {COR_CINZA};
    margin-top: 4px;
}}

/* ── Cards de conteúdo (gráficos, tabelas) ── */
.content-card {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    margin-bottom: 16px;
}}
.card-title {{
    font-size: 14px;
    font-weight: 700;
    color: {COR_TEXTO};
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid {COR_BORDA};
}}

/* ── Filtros ── */
.filter-bar {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 12px;
    padding: 14px 20px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}

/* ── Tabelas Streamlit ── */
[data-testid="stDataFrame"] {{
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid {COR_BORDA} !important;
}}

/* ── Inputs e selects ── */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stMultiSelect > div > div {{
    background: {COR_CARD} !important;
    border: 1px solid {COR_BORDA} !important;
    border-radius: 8px !important;
    color: {COR_TEXTO} !important;
}}

/* ── Botões primários ── */
.stButton > button[kind="primary"] {{
    background: {COR_TEAL} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: #009589 !important;
}}

/* ── Botões secundários ── */
.stButton > button:not([kind="primary"]) {{
    background: {COR_CARD} !important;
    color: {COR_TEXTO} !important;
    border: 1px solid {COR_BORDA} !important;
    border-radius: 8px !important;
}}

/* ── Expander ── */
.stExpander {{
    background: {COR_CARD} !important;
    border: 1px solid {COR_BORDA} !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}}

/* ── Métricas nativas do Streamlit ── */
[data-testid="metric-container"] {{
    background: {COR_CARD} !important;
    border: 1px solid {COR_BORDA} !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}}
[data-testid="metric-container"] label {{
    color: {COR_CINZA} !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {COR_TEXTO} !important;
    font-size: 26px !important;
    font-weight: 800 !important;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    background: {COR_CARD};
    border-bottom: 1px solid {COR_BORDA};
    border-radius: 0;
    gap: 0;
}}
.stTabs [data-baseweb="tab"] {{
    color: {COR_CINZA} !important;
    font-weight: 600;
    font-size: 13px;
    padding: 10px 20px;
    border-bottom: 2px solid transparent;
}}
.stTabs [aria-selected="true"] {{
    color: {COR_TEAL} !important;
    border-bottom: 2px solid {COR_TEAL} !important;
    background: transparent !important;
}}

/* ── Divider ── */
hr {{
    border-color: {COR_BORDA} !important;
    margin: 16px 0 !important;
}}

/* ── Ocultar elementos padrão do Streamlit ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}

/* ── Sidebar sempre visível (fixa, sem colapso) ── */
section[data-testid="stSidebar"] {{
    transform: translateX(0px) !important;
    min-width: 230px !important;
    max-width: 230px !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}}
/* Esconde os botões de recolher/expandir */
[data-testid="stSidebarCollapseButton"] {{
    display: none !important;
}}
[data-testid="collapsedControl"] {{
    display: none !important;
}}

/* ── Ocultar rótulo "app" e separadores do menu lateral ── */
section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] span,
section[data-testid="stSidebar"] .st-emotion-cache-1rtdyuf,
section[data-testid="stSidebar"] .st-emotion-cache-6tkfeg,
section[data-testid="stSidebar"] p.st-emotion-cache-pkbazv {{
    display: none !important;
}}
</style>
"""


def sidebar_header(usuario: dict):
    """Renderiza cabeçalho da sidebar com logo e info do usuário."""
    import streamlit as st

    # Logo sem div aninhado para evitar tag solta
    st.sidebar.markdown(
        f'<div class="sidebar-logo">{LOGO_SVG}</div>',
        unsafe_allow_html=True
    )


def sidebar_footer(usuario: dict):
    """Renderiza rodapé da sidebar com usuário e botão sair."""
    import streamlit as st

    st.sidebar.markdown("<hr style='border-color:rgba(255,255,255,0.08);margin:8px 0;'>",
                        unsafe_allow_html=True)
    st.sidebar.markdown(f"""
    <div class="sidebar-user">
        <div style="font-size:13px;color:#F9FAFB;font-weight:600;">{usuario['nome']}</div>
        <div style="margin-top:4px;">
            <span class="sidebar-badge">{usuario['papel']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Sair", key="btn_sair_sidebar"):
        from utils.auth import logout
        logout()


def page_header(titulo: str, subtitulo: str = "", icone: str = ""):
    """Renderiza cabeçalho padronizado de página."""
    import streamlit as st
    st.markdown(f"""
    <div class="page-header">
        <div>
            <div class="page-title">{icone} {titulo}</div>
            {'<div class="page-subtitle">' + subtitulo + '</div>' if subtitulo else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label: str, valor: str, sub: str = "", cor: str = "") -> str:
    """Retorna HTML de um card KPI."""
    cls = f"kpi-value {cor}" if cor else "kpi-value"
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="{cls}">{valor}</div>
        {sub_html}
    </div>
    """


_JS_SIDEBAR = """
<script>
(function() {
    function forceSidebar() {
        // Clica no botão expandir se a sidebar estiver colapsada
        var btn = window.parent.document.querySelector('[data-testid="collapsedControl"]');
        if (btn) { btn.click(); }
        // Remove transform inline que colapsa a sidebar
        var sb = window.parent.document.querySelector('section[data-testid="stSidebar"]');
        if (sb) { sb.style.transform = 'translateX(0px)'; }
    }
    setTimeout(forceSidebar, 200);
    setTimeout(forceSidebar, 600);
})();
</script>
"""

def apply_theme():
    """Aplica o CSS global — chamar no início de cada página."""
    import streamlit as st
    st.markdown(CSS_GLOBAL, unsafe_allow_html=True)
    st.components.v1.html(_JS_SIDEBAR, height=0)
