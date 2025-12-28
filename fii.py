# =====================================================
# IMPORTS
# =====================================================
import math
from datetime import datetime, timedelta
from urllib.parse import quote

import feedparser
import pandas as pd
import streamlit as st
import yfinance as yf

st.markdown("""
<style>
.home-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    margin-top: 12px;
}

.home-card {
    background-color: #0b1f33;
    border: 1px solid rgba(120,160,200,0.25);
    border-radius: 16px;
    padding: 18px 14px;
    transition: all 0.2s ease;
}

.home-card:hover {
    background-color: #102a44;
    border-color: rgba(140,180,220,0.35);
    transform: translateY(-2px);
}

.home-card a {
    text-decoration: none;
    display: block;
    height: 100%;
}

.home-card-title {
    font-size: 15px;
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 6px;
    text-align: center;
}

.home-card-desc {
    font-size: 13px;
    color: #b8c4d6;
    line-height: 1.4;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


# st.markdown("""
# <style>
# /* Container do botão */
# div.stButton > button {
#     height: 110px;
#     width: 100%;
#     font-size: 16px;
#     font-weight: 600;
#     border-radius: 16px;

#     /* Cores */
#     background: linear-gradient(180deg, #0b1f33 0%, #081726 100%);
#     color: #e8edf3;

#     /* Borda elegante */
#     border: 1px solid #123a5f;

#     /* Espaçamento e alinhamento */
#     padding: 12px 14px;
#     text-align: center;

#     /* Transição suave */
#     transition: all 0.25s ease-in-out;
# }

# /* Hover */
# div.stButton > button:hover {
#     background: linear-gradient(180deg, #102a44 0%, #0b1f33 100%);
#     border-color: #1f5c8f;
#     transform: translateY(-2px);
# }

# /* Clique */
# div.stButton > button:active {
#     transform: translateY(0px);
#     background: #081726;
# }
# </style>
# """, unsafe_allow_html=True)
# st.markdown("""
# <style>
# /* Botões da Home – estilo institucional */
# div[data-testid="column"] > div > div > div.stButton > button {
#     height: 96px;
#     width: 100%;

#     /* Tipografia limpa */
#     font-size: 15px;
#     font-weight: 500;
#     letter-spacing: 0.2px;

#     /* Forma */
#     border-radius: 14px;

#     /* Cor sólida (nada de gradiente) */
#     background-color: #0b1f33;
#     color: #e6edf3;

#     /* Borda sutil */
#     border: 1px solid rgba(120, 160, 200, 0.25);

#     /* Layout */
#     padding: 12px;
#     text-align: center;

#     /* Sem sombra chamativa */
#     box-shadow: none;

#     /* Transição quase imperceptível */
#     transition: background-color 0.15s ease, border-color 0.15s ease;
# }

# /* Hover discreto */
# div[data-testid="column"] > div > div > div.stButton > button:hover {
#     background-color: #102a44;
#     border-color: rgba(140, 180, 220, 0.35);
# }

# /* Click */
# div[data-testid="column"] > div > div > div.stButton > button:active {
#     background-color: #081726;
# }
# </style>
# """, unsafe_allow_html=True)


# =====================================================
# CONFIG STREAMLIT
# =====================================================
st.set_page_config(
    page_title="FIIs Monitor",
    layout="centered"
)
# =========================
# ROTEAMENTO VIA QUERY PARAM
# =========================
params = st.query_params
if "page" in params:
    st.session_state.page = params["page"]

# =====================================================
# SESSION STATE PADRÃO
# =====================================================
if "page" not in st.session_state:
    st.session_state.page = "home"

if "aviso_aceito" not in st.session_state:
    st.session_state.aviso_aceito = False

def grid_button(label, page_key):
    if st.button(label, key=page_key, use_container_width=True):
        st.session_state.page = page_key
        st.rerun()

# =====================================================
# CONSTANTES GLOBAIS
# =====================================================
ALIQUOTA_IR = 0.225
SELIC_BRUTA = 15.0
SELIC_ANUAL = SELIC_BRUTA * (1 - ALIQUOTA_IR)

CACHE_DIARIO = 60 * 60 * 24
CACHE_HORA = 60 * 60


# =====================================================
# ESTILO GLOBAL
# =====================================================


# =====================================================
# HELPERS DE NAVEGAÇÃO
# =====================================================
def botao_voltar():
    if st.button("← Voltar"):
        st.session_state.page = "home"
        st.rerun()

def scroll_to_top():
    st.markdown(
        """
        <script>
            window.scrollTo(0, 0);
        </script>
        """,
        unsafe_allow_html=True
    )
    
def card(titulo, descricao, page_key):
    if st.button(
        f"{titulo}\n\n{descricao}",
        key=page_key,
        use_container_width=True
    ):
        st.session_state.page = page_key
        st.rerun()

def home_card(titulo, descricao, page_key):
    st.markdown(
        f"""
        <div class="home-card">
            <a href="?page={page_key}">
                <div class="home-card-title">{titulo}</div>
                <div class="home-card-desc">{descricao}</div>
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_home_card(titulo, descricao, page_key):
    clicked = st.button(
        label="",
        key=f"btn_{page_key}",
        use_container_width=True
    )

    st.markdown(
        f"""
        <div class="home-card">
            <div class="home-card-title">{titulo}</div>
            <div class="home-card-desc">{descricao}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if clicked:
        st.session_state.page = page_key
        st.rerun()


import plotly.express as px

def grafico_preco_acao(hist, ticker):
    fig = px.line(
        hist,
        x=hist.index,
        y="Close",
        title=f"Histórico de Preço — {ticker}",
        labels={"Close": "Preço (R$)", "index": "Data"},
    )

    fig.update_layout(
        template="plotly_dark",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    return fig
def safe(v, fmt=None):
    if v is None:
        return "—"
    try:
        return fmt(v) if fmt else v
    except:
        return "—"

def pct(v):
    return f"{v:.1f}%"

def brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
# =====================================================
# FUNÇÕES DE NEGÓCIO — FIIs
# =====================================================
st.title("📊 FIIs Monitor")

st.caption(
    "Seleção diária de FIIs com análises, simuladores e notícias em um só lugar."
)


# =====================================================
# LOAD E TRATAMENTO DOS DADOS
# =====================================================
@st.cache_data(ttl=CACHE_DIARIO, show_spinner=True)
def carregar_dados():
    df = pd.read_parquet("df_fiis.parquet")

    colunas_obrigatorias = [
        'P/VP', 'DY (3M) Acumulado', 'DY (6M) Acumulado',
        'DY (12M) Acumulado', 'Liquidez Diária (R$)',
        'Patrimônio Líquido', 'Num. Cotistas',
        'Preço Atual (R$)', 'Último Dividendo'
    ]

    df = df.dropna(subset=colunas_obrigatorias)

    df['P/VP'] /= 100

    for col in ['DY (3M) Acumulado', 'DY (6M) Acumulado', 'DY (12M) Acumulado']:
        df[col] = (
            df[col].astype(str)
            .str.replace('%', '', regex=False)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float)
        )

    def normalizar_milhoes(col):
        return (
            df[col].astype(str)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float) / 1_000_000
        )

    df['Liquidez Diária (milhões R$)'] = normalizar_milhoes('Liquidez Diária (R$)')
    df['Patrimônio Líquido (milhões R$)'] = normalizar_milhoes('Patrimônio Líquido')

    df['Num. Cotistas (milhares)'] = (
        df['Num. Cotistas']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
        .astype(float) / 1_000
    )

    df['Preço Atual (R$)'] = (
        df['Preço Atual (R$)']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
        .astype(float) / 100
    )

    df['Último Dividendo'] = (
        df['Último Dividendo']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
        .astype(float) / 100
    )

    return df


def filtrar_fiis_descontados_com_qualidade(df):
    return df[
        (df["P/VP"].between(0.85, 1.0)) &
        (df["DY (3M) Acumulado"] >= 3) &
        (df["DY (6M) Acumulado"] >= 6) &
        (df["DY (12M) Acumulado"] >= 12) &
        (df["Liquidez Diária (milhões R$)"] >= 1) &
        (df["Patrimônio Líquido (milhões R$)"] >= 500) &
        (df["Num. Cotistas (milhares)"] >= 10)
    ].copy()




# =====================================================
# NOTÍCIAS — GOOGLE NEWS (RSS)
# =====================================================
@st.cache_data(ttl=CACHE_HORA)
def buscar_noticias_fii(ticker, dias=30, limite=10):
    """
    Busca notícias recentes de um FII via Google News RSS.

    Parâmetros:
    - ticker: código do FII (ex: HGLG11)
    - dias: janela de tempo (default 30 dias)
    - limite: número máximo de notícias retornadas

    Retorno:
    - Lista de dicionários com titulo, link e data
    """
    query = quote(f"{ticker} fundo imobiliário FII")
    url = (
        "https://news.google.com/rss/search?"
        f"q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )

    feed = feedparser.parse(url)
    data_minima = datetime.now() - timedelta(days=dias)

    noticias = []

    for entry in feed.entries:
        if not hasattr(entry, "published_parsed"):
            continue

        data_noticia = datetime(*entry.published_parsed[:6])

        if data_noticia < data_minima:
            continue

        noticias.append({
            "titulo": entry.title,
            "link": entry.link,
            "data": data_noticia.strftime("%d/%m/%Y")
        })

        if len(noticias) >= limite:
            break

    return noticias


# =====================================================
# AÇÕES — DADOS FUNDAMENTALISTAS
# =====================================================
def carregar_dados_acao(ticker):
    """
    Carrega dados de uma ação usando yfinance com fallback seguro.
    """
    acao = yf.Ticker(ticker)

    try:
        info = acao.info
    except Exception:
        info = {}

    hist = acao.history(period="5y")

    return info, hist


def extrair_metricas_acao(info):
    """
    Extrai métricas fundamentais de forma segura.
    """
    def pct(valor):
        return valor * 100 if isinstance(valor, (int, float)) else None

    return {
        "Preço Atual": info.get("currentPrice"),
        "P/L": info.get("trailingPE"),
        "P/VP": info.get("priceToBook"),
        "ROE (%)": pct(info.get("returnOnEquity")),
        "ROA (%)": pct(info.get("returnOnAssets")),
        "Margem Líquida (%)": pct(info.get("profitMargins")),
        "Dívida/Patrimônio": info.get("debtToEquity"),
        "Crescimento Receita (%)": pct(info.get("revenueGrowth")),
        "Market Cap (R$ bi)": (
            info.get("marketCap") / 1e9
            if info.get("marketCap") else None
        ),
    }


def backtest_valorizacao(hist):
    """
    Retorno total e anualizado baseado em preço de fechamento.
    """
    if hist.empty or len(hist) < 2:
        return None, None

    preco_inicial = hist["Close"].iloc[0]
    preco_final = hist["Close"].iloc[-1]

    retorno_total = ((preco_final / preco_inicial) - 1) * 100

    anos = (hist.index[-1] - hist.index[0]).days / 365
    retorno_anual = ((preco_final / preco_inicial) ** (1 / anos) - 1) * 100

    return retorno_total, retorno_anual
# =====================================================
# UI — CARDS DE FIIs
# =====================================================
def comparar_com_selic(dy_anual):
    """
    Compara o Dividend Yield anual do FII com a Selic líquida.
    
    Retorna uma leitura qualitativa objetiva.
    """

    if dy_anual is None:
        return "Sem dados"

    margem = 2.0  # margem de segurança em pontos percentuais

    if dy_anual >= SELIC_ANUAL + margem:
        return "Acima da Selic"
    elif dy_anual <= SELIC_ANUAL - margem:
        return "Abaixo da Selic"
    else:
        return "Em linha com a Selic"
def calcular_rendimento_mensal(dy_anual):
    """
    Converte Dividend Yield anual (%) em rendimento mensal equivalente (%),
    assumindo capitalização composta.
    """

    if dy_anual is None or dy_anual <= 0:
        return None

    return ((1 + dy_anual / 100) ** (1 / 12) - 1) * 100

def fii_cards(df_cards):
    """
    Renderiza cards padronizados de FIIs.
    Espera um DataFrame com as colunas já tratadas.
    """

    for _, row in df_cards.iterrows():
        with st.container(border=True):

            st.markdown(f"### {row['Fundos']}")
            st.caption(f"Setor: {row.get('Setor', '—')}")

            # ===============================
            # MÉTRICAS PRINCIPAIS
            # ===============================
            c1, c2, c3 = st.columns(3)
            c1.metric("P/VP", f"{row['P/VP']:.2f}")
            c2.metric(
                "Liquidez Diária",
                f"R$ {row['Liquidez Diária (milhões R$)']:.1f} mi"
            )
            c3.metric(
                "Preço Atual",
                f"R$ {row['Preço Atual (R$)']:.2f}"
            )

            # ===============================
            # DY E COMPARAÇÃO COM SELIC
            # ===============================
            dy12 = row["DY (12M) Acumulado"]
            status_selic = comparar_com_selic(dy12)
            rendimento_mes = calcular_rendimento_mensal(dy12)

            st.metric("Dividend Yield (12M)", f"{dy12:.1f}%")
            st.caption(
                f"Renda vs Selic: **{status_selic}** "
                f"(DY 12M: {dy12:.1f}% | Selic líquida ref.: {SELIC_ANUAL:.1f}%)"
            )

            st.markdown(
                f"> Rendimento equivalente: "
                f"<u>{rendimento_mes:.2f}%</u> ao mês",
                unsafe_allow_html=True
            )

            # ===============================
            # LINK EXTERNO
            # ===============================
            ticker = row["Fundos"].split(" - ")[0]
            st.markdown(
                f"""
                <a href="https://www.fundsexplorer.com.br/funds/{ticker}"
                   target="_blank">
                    🔗 Ver no Funds Explorer
                </a>
                """,
                unsafe_allow_html=True
            )

            # ===============================
            # DETALHES
            # ===============================
            with st.expander("🔎 Detalhes do fundo"):
                st.markdown(
                    f"""
                    - **Patrimônio Líquido:** R$ {row['Patrimônio Líquido (milhões R$)']:.0f} mi  
                    - **Cotistas:** {row['Num. Cotistas (milhares)']:.0f} mil  
                    - **Último Dividendo:** R$ {row['Último Dividendo']:.2f}  
                    - **DY 3M:** {row['DY (3M) Acumulado']:.1f}%  
                    - **DY 6M:** {row['DY (6M) Acumulado']:.1f}%  
                    """
    )
                
df = carregar_dados()
df_filtrados = filtrar_fiis_descontados_com_qualidade(df)
# =====================================================
# TOP 10 — RANKING GLOBAL
# =====================================================
fiis_achados = len(df_filtrados)

df_top10 = (
    df_filtrados
    .sort_values("DY (12M) Acumulado", ascending=False)
    .head(10)
)
# =====================================================
# TABS
# =====================================================
@st.cache_data(ttl=60 * 60)
def carregar_dados_acao(ticker):
    acao = yf.Ticker(ticker)
    info = acao.info
    hist = acao.history(period="5y")
    return info, hist


def extrair_metricas_acao(info):
    return {
        "Preço Atual": info.get("currentPrice"),
        "P/L": info.get("trailingPE"),
        "P/VP": info.get("priceToBook"),
        "ROE (%)": (info.get("returnOnEquity") or 0) * 100,
        "ROA (%)": (info.get("returnOnAssets") or 0) * 100,
        "Margem Líquida (%)": (info.get("profitMargins") or 0) * 100,
        "Dívida/Patrimônio": info.get("debtToEquity"),
        "Market Cap (R$ bi)": (info.get("marketCap") or 0) / 1e9,
        "Crescimento Receita (%)": (info.get("revenueGrowth") or 0) * 100,
        "Crescimento Lucro (%)": (info.get("earningsGrowth") or 0) * 100,
    }


def classificar_saude(metricas):
    pontos = 0
    if metricas["ROE (%)"] and metricas["ROE (%)"] > 15:
        pontos += 1
    if metricas["Dívida/Patrimônio"] and metricas["Dívida/Patrimônio"] < 1.5:
        pontos += 1
    if metricas["Margem Líquida (%)"] and metricas["Margem Líquida (%)"] > 10:
        pontos += 1

    if pontos >= 3:
        return "🟢 Saudável"
    elif pontos == 2:
        return "🟡 Atenção"
    else:
        return "🔴 Frágil"


def backtest_valorizacao(hist):
    if hist.empty:
        return None, None

    preco_inicial = hist["Close"].iloc[0]
    preco_final = hist["Close"].iloc[-1]

    retorno_total = (preco_final / preco_inicial - 1) * 100
    anos = (hist.index[-1] - hist.index[0]).days / 365
    retorno_anual = ((preco_final / preco_inicial) ** (1 / anos) - 1) * 100

    return retorno_total, retorno_anual
def leitura_valor_acao(metricas):
    """
    Gera uma leitura qualitativa simples de valuation e qualidade
    a partir das métricas fundamentais da ação.
    """

    leitura = []

    pl = metricas.get("P/L")
    pvp = metricas.get("P/VP")
    roe = metricas.get("ROE (%)")
    crescimento = metricas.get("Crescimento Lucro (%)")
    divida = metricas.get("Dívida/Patrimônio")

    # ======================
    # P/L
    # ======================
    if pl:
        if pl < 10:
            leitura.append("P/L baixo para o mercado — pode indicar desconto ou risco percebido.")
        elif pl <= 18:
            leitura.append("P/L em faixa saudável para empresa madura.")
        else:
            leitura.append("P/L elevado — mercado precifica crescimento futuro.")

    # ======================
    # P/VP
    # ======================
    if pvp:
        if pvp < 1:
            leitura.append("P/VP abaixo de 1 — empresa negociada abaixo do valor patrimonial.")
        elif pvp <= 2:
            leitura.append("P/VP compatível com empresas de boa qualidade.")
        else:
            leitura.append("P/VP elevado — qualidade e retornos já estão no preço.")

    # ======================
    # ROE
    # ======================
    if roe:
        if roe >= 15:
            leitura.append("ROE elevado — empresa eficiente na geração de retorno ao acionista.")
        elif roe >= 10:
            leitura.append("ROE aceitável para empresa estável.")
        else:
            leitura.append("ROE baixo — atenção à eficiência operacional.")

    # ======================
    # Crescimento
    # ======================
    if crescimento:
        if crescimento >= 10:
            leitura.append("Lucro em crescimento consistente.")
        elif crescimento > 0:
            leitura.append("Crescimento de lucro modesto.")
        else:
            leitura.append("Lucro em queda — ponto de atenção.")

    # ======================
    # Dívida
    # ======================
    if divida:
        if divida < 1:
            leitura.append("Estrutura de capital saudável.")
        elif divida < 2:
            leitura.append("Alavancagem moderada.")
        else:
            leitura.append("Alavancagem elevada — exige atenção.")

    if not leitura:
        leitura.append("Dados insuficientes para uma leitura clara de valuation.")

    return leitura

if st.session_state.page == "home":
    scroll_to_top()

    st.markdown("""
    <h2 style="margin-bottom:4px;">🪙 Refera</h2>
    <p style="font-size:15px; color:#c9d4e3;">
        Onde decisões de investimento encontram fundamento
    </p>
    """, unsafe_allow_html=True)

    st.markdown("""
    <p style="font-size:14px; line-height:1.6; color:#b8c4d6;">
        Plataforma quantitativa para análise de FIIs e ações,
        com foco em consistência, critérios objetivos e visão de longo prazo.
    </p>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 Rankings e Descoberta")
    st.markdown('<div class="home-grid">', unsafe_allow_html=True)

    home_card("📊 Rankings", "Top FIIs por critérios", "top10")
    st.write('')
    home_card("🏦 Grandes FIIs", "Maior patrimônio do mercado", "grandes")
    st.write('')
    home_card("💸 FIIs de Entrada", "Cotas acessíveis e liquidez", "entrada")
    st.write('')
    home_card("🧠 Screener", "Filtros personalizados", "screener")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### 🧭 Análise e Decisão")
    st.markdown('<div class="home-grid">', unsafe_allow_html=True)

    home_card("🔎 FII Individual", "Análise completa do fundo", "fii")
    st.write('')
    home_card("⚖️ Comparador", "Comparação lado a lado", "comparador")
    st.write('')
    home_card("📈 Ações", "Análise fundamentalista", "acao")
    st.write('')
    home_card("📰 Notícias", "Contexto recente por FII", "noticias")
    st.write('')

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### 🔁 Planejamento ")
    st.markdown('<div class="home-grid">', unsafe_allow_html=True)

    home_card("🔁 Reinvestimento", "Simulador de dividendos", "reinvestimento")
    st.write('')
    home_card("💼 Carteira", "Simulação da carteira", "carteira")

    st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# TAB — MÉTRICAS
# =====================================================
elif st.session_state.page == 'metricas':
    scroll_to_top()
    st.subheader("📘 Entendendo as principais métricas dos FIIs")

    st.caption(
        "Aqui estão as métricas mais usadas no FIIs Monitor e como interpretá-las "
        "de forma objetiva e sem achismo."
    )

    st.divider()

    # =================================================
    # P/VP
    # =================================================
    with st.expander("📉 P/VP (Preço / Valor Patrimonial)"):
        st.markdown(
            """
            O **P/VP** compara o preço da cota com o valor patrimonial do fundo.

            - **P/VP < 1,0** → mercado pagando abaixo do patrimônio  
            - **P/VP ≈ 1,0** → preço próximo do valor justo  
            - **P/VP > 1,0** → mercado pagando prêmio  

            ⚠️ **Importante**: P/VP baixo pode indicar oportunidade **ou** risco percebido
            (problemas operacionais, emissões, concentração etc.).
            """
        )

    # =================================================
    # DIVIDEND YIELD
    # =================================================
    with st.expander("💰 Dividend Yield (DY)"):
        st.markdown(
            """
            O **Dividend Yield (DY)** mostra quanto o fundo distribuiu
            em relação ao preço da cota.

            No FIIs Monitor utilizamos três janelas:
            - **DY 3M** → tendência recente  
            - **DY 6M** → consistência  
            - **DY 12M** → visão estrutural  

            Dividendos passados **não garantem pagamentos futuros**.
            """
        )

    # =================================================
    # LIQUIDEZ
    # =================================================
    with st.expander("💧 Liquidez Diária"):
        st.markdown(
            """
            A **liquidez diária** indica quanto dinheiro é negociado por dia.

            Maior liquidez significa:
            - facilidade para comprar e vender  
            - menor risco de distorções de preço  

            No Monitor, priorizamos FIIs com **liquidez ≥ R$ 1 milhão/dia**.
            """
        )

    # =================================================
    # PATRIMÔNIO LÍQUIDO
    # =================================================
    with st.expander("🏢 Patrimônio Líquido"):
        st.markdown(
            """
            Representa o tamanho do fundo.

            Fundos maiores tendem a:
            - ter mais ativos  
            - maior diversificação  
            - maior acompanhamento do mercado  

            No Monitor, fundos com **PL ≥ R$ 500 milhões**
            são considerados estruturalmente relevantes.
            """
        )

    # =================================================
    # COTISTAS
    # =================================================
    with st.expander("👥 Número de Cotistas"):
        st.markdown(
            """
            Indica quantos investidores possuem cotas do fundo.

            Um número elevado de cotistas geralmente indica:
            - maior liquidez  
            - maior visibilidade  
            - menor risco de manipulação de preço  

            O Monitor utiliza **≥ 10 mil cotistas** como referência mínima.
            """
        )

    st.divider()

    st.info(
        "📌 As métricas apresentadas são **quantitativas** e devem ser "
        "avaliadas em conjunto com relatórios gerenciais, fatos relevantes "
        "e contexto macroeconômico."
                    )

# =====================================================
# TAB — TOP 10 DESCONTADOS
# =====================================================
elif st.session_state.page == 'top10':
    scroll_to_top()
    st.subheader("📊 Top 10 FIIs Descontados com Qualidade")

    if df_top10.empty:
        st.warning("Nenhum FII atende aos critérios hoje.")
        st.stop()

    st.success(f"{fiis_achados} FIIs atendem aos critérios mínimos hoje")

    # =================================================
    # CRITÉRIOS DO RANKING
    # =================================================
    with st.expander("📌 Critérios mínimos para aprovação", expanded=False):
        st.markdown(
            """
            Um FII **só aparece neste ranking** se atender **todos** os critérios abaixo:

            **📉 Preço**
            - P/VP entre **0,85 e 1,00**

            **💰 Dividendos**
            - DY 3 meses ≥ **3,0%**
            - DY 6 meses ≥ **6,0%**
            - DY 12 meses ≥ **12,0%**

            **📊 Liquidez e porte**
            - Liquidez diária ≥ **R$ 1 milhão**
            - Patrimônio líquido ≥ **R$ 500 milhões**
            - Cotistas ≥ **10 mil**
            """
        )

    st.divider()

    # =================================================
    # CARDS TOP 10
    # =================================================
    fii_cards(df_top10)

    st.divider()

    # =================================================
    # DEMAIS FIIs APROVADOS
    # =================================================
    with st.expander(
        f"📋 Demais FIIs aprovados nos critérios ({len(df_filtrados)} FIIs)",
        expanded=False
    ):
        fiis = sorted(df_filtrados["Fundos"].unique())
        cols = st.columns(3)

        for i, fii in enumerate(fiis):
            cols[i % 3].markdown(f"- {fii}")

    st.info(
        "⚠️ Este ranking é baseado exclusivamente em critérios quantitativos "
        "objetivos. Não constitui recomendação de investimento."
    )


# =====================================================
# TAB — GRANDES FIIs
# =====================================================
elif st.session_state.page == 'grandes':
    scroll_to_top()
    st.subheader("🏦 Grandes FIIs do Mercado")
    st.caption("Fundos com maior patrimônio líquido e alta relevância no mercado.")

    df_grandes = (
        df.sort_values("Patrimônio Líquido (milhões R$)", ascending=False)
        .head(5)
    )

    if df_grandes.empty:
        st.warning("Nenhum FII encontrado.")
        st.stop()

    fii_cards(df_grandes)

    st.info(
        "📌 Fundos grandes tendem a apresentar maior estabilidade e liquidez, "
        "mas ainda devem ser avaliados quanto à qualidade dos ativos, "
        "gestão e contexto macroeconômico."
    )


# =====================================================
# TAB — FIIs DE ENTRADA
# =====================================================
elif st.session_state.page == 'entrada':
    scroll_to_top()
    st.subheader("💸 FIIs de Entrada")
    st.caption(
        "Fundos com cotas mais acessíveis, boa liquidez e histórico consistente de dividendos."
    )

    df_entrada = (
        df_filtrados[
            (df_filtrados["Preço Atual (R$)"] <= 30) &
            (df_filtrados["DY (12M) Acumulado"] <= 24)
        ]
        .sort_values("DY (12M) Acumulado", ascending=False)
        .head(5)
    )

    if df_entrada.empty:
        st.warning("Nenhum FII de entrada atende aos critérios hoje.")
        st.stop()

    fii_cards(df_entrada)

    st.info(
        "📌 FIIs de entrada facilitam o início no mercado, "
        "mas preço baixo não significa menor risco. "
        "Avalie sempre fundamentos, gestão e qualidade dos ativos."
    )


# =====================================================
# TAB — SCREENER PERSONALIZADO
# =====================================================
elif st.session_state.page == 'screener':
    scroll_to_top()
    st.subheader("🧠 Screener Personalizado de FIIs")
    st.caption("Crie seus próprios filtros para encontrar FIIs alinhados ao seu perfil.")

    st.divider()

    # ===============================
    # FILTROS
    # ===============================
    c1, c2, c3 = st.columns(3)
    pv_min, pv_max = c1.slider("P/VP", 0.5, 1.5, (0.8, 1.0))
    dy_min = c2.slider("DY 12M mínimo (%)", 5.0, 25.0, 9.0)
    preco_max = c3.slider("Preço máximo da cota (R$)", 5.0, 200.0, 100.0)

    c4, c5, c6 = st.columns(3)
    liquidez_min = c4.slider("Liquidez mínima (R$ mi/dia)", 0.5, 15.0, 1.0)
    pl_min = c5.slider("Patrimônio mínimo (R$ mi)", 100.0, 10_000.0, 500.0)
    cotistas_min = c6.slider("Cotistas mínimos (mil)", 1.0, 300.0, 10.0)

    # ===============================
    # FILTRAGEM
    # ===============================
    df_screener = df[
        (df["P/VP"].between(pv_min, pv_max)) &
        (df["DY (12M) Acumulado"] >= dy_min) &
        (df["Preço Atual (R$)"] <= preco_max) &
        (df["Liquidez Diária (milhões R$)"] >= liquidez_min) &
        (df["Patrimônio Líquido (milhões R$)"] >= pl_min) &
        (df["Num. Cotistas (milhares)"] >= cotistas_min)
    ].sort_values("DY (12M) Acumulado", ascending=False)

    st.divider()

    # ===============================
    # RESULTADOS
    # ===============================
    st.success(f"{len(df_screener)} FIIs encontrados")

    if df_screener.empty:
        st.warning("Nenhum FII atende aos filtros selecionados.")
        st.stop()

    st.dataframe(
        df_screener[
            [
                "Fundos",
                "Setor",
                "Preço Atual (R$)",
                "P/VP",
                "DY (12M) Acumulado",
                "Liquidez Diária (milhões R$)",
                "Patrimônio Líquido (milhões R$)"
            ]
        ],
        use_container_width=True
    )

    st.caption(
        "📌 Use o screener como ponto de partida. "
        "A decisão final deve considerar relatórios, gestão e riscos específicos."
    )



# =====================================================
# TAB — COMPARADOR DE FIIs
# =====================================================
elif st.session_state.page == 'comparador':
    scroll_to_top()
    st.subheader("⚖️ Comparador de FIIs")
    st.caption("Compare dois FIIs lado a lado com critérios objetivos.")

    st.divider()

    c1, c2 = st.columns(2)
    fii_a = c1.selectbox("FII A", sorted(df["Fundos"].unique()), key="fii_a")
    fii_b = c2.selectbox("FII B", sorted(df["Fundos"].unique()), key="fii_b")

    if fii_a == fii_b:
        st.info("Selecione dois FIIs diferentes para comparar.")
        st.stop()

    a = df[df["Fundos"] == fii_a].iloc[0]
    b = df[df["Fundos"] == fii_b].iloc[0]

    pontos_a = 0
    pontos_b = 0

    comparacoes = [
        ("Preço (menor é melhor)", a["Preço Atual (R$)"], b["Preço Atual (R$)"], False, 1),
        ("P/VP (menor é melhor)", a["P/VP"], b["P/VP"], False, 2),
        ("DY 12M (maior é melhor)", a["DY (12M) Acumulado"], b["DY (12M) Acumulado"], True, 3),
        ("Liquidez (maior é melhor)", a["Liquidez Diária (milhões R$)"], b["Liquidez Diária (milhões R$)"], True, 1),
    ]

    st.divider()

    for nome, va, vb, maior_melhor, peso in comparacoes:

        if va == vb:
            vencedor = "Empate"
        elif maior_melhor:
            vencedor = fii_a if va > vb else fii_b
        else:
            vencedor = fii_a if va < vb else fii_b

        if vencedor == fii_a:
            pontos_a += peso
        elif vencedor == fii_b:
            pontos_b += peso

        st.markdown(
            f"""
            **{nome}** (peso {peso})  
            - {fii_a}: `{va:.2f}`  
            - {fii_b}: `{vb:.2f}`  
            🏆 **Vencedor:** {vencedor}
            """
        )
        st.divider()

    # ===============================
    # RESULTADO FINAL
    # ===============================
    st.subheader("🏁 Resultado final")

    if pontos_a > pontos_b:
        st.success(f"✅ **{fii_a} vence por {pontos_a} x {pontos_b}**")
    elif pontos_b > pontos_a:
        st.success(f"✅ **{fii_b} vence por {pontos_b} x {pontos_a}**")
    else:
        st.info(f"⚖️ **Empate técnico: {pontos_a} x {pontos_b}**")

    st.caption(
        "📌 Comparação baseada em critérios quantitativos. "
        "Não substitui análise qualitativa do fundo."
    )


# =====================================================
# TAB — NOTÍCIAS
# =====================================================
elif st.session_state.page == 'noticias':
    scroll_to_top()
    st.subheader("📰 Notícias recentes por FII")
    st.caption(
        "Acompanhe notícias recentes para entender o contexto "
        "e possíveis eventos relevantes de cada fundo."
    )

    st.divider()

    fii_noticia = st.selectbox(
        "Selecione o FII",
        sorted(df["Fundos"].unique())
    )

    ticker = fii_noticia.split(" - ")[0]

    if st.button("🔎 Buscar notícias"):
        noticias = buscar_noticias_fii(ticker)

        st.divider()

        if not noticias:
            st.warning("Nenhuma notícia recente encontrada para este FII.")
        else:
            if len(noticias) >= 5:
                st.warning("⚠️ Volume elevado de notícias recentes")

            for n in noticias:
                st.markdown(
                    f"""
                    **📰 {n['titulo']}**  
                    <a href="{n['link']}" target="_blank">Ler notícia</a>  
                    <small>{n['data']}</small>
                    """,
                    unsafe_allow_html=True
                )
                st.divider()
    else:
        st.info(
            "Selecione um FII e clique em **Buscar notícias** "
            "para visualizar as notícias recentes."
        )

    st.caption(
        "📌 Notícias servem como **contexto** e não devem ser usadas "
        "isoladamente como decisão de investimento."
    )

# =====================================================
# TAB — SIMULADOR DE REINVESTIMENTO
# =====================================================
elif st.session_state.page == 'reinvestimento':
    scroll_to_top()
    st.subheader("🔁 Simulador de Reinvestimento de Dividendos")
    st.caption(
        "Calcule quantas cotas de um FII são necessárias para que "
        "os dividendos mensais comprem uma nova cota do mesmo fundo."
    )

    st.divider()

    fii_simulador = st.selectbox(
        "Selecione o FII",
        sorted(df["Fundos"].unique()),
        key="fii_simulador"
    )

    row = df[df["Fundos"] == fii_simulador].iloc[0]

    preco = row["Preço Atual (R$)"]
    dy12 = row["DY (12M) Acumulado"]

    if dy12 <= 0:
        st.warning("DY inválido para simulação.")
        st.stop()

    dividendo_mensal_por_cota = preco * (dy12 / 100) / 12
    cotas_necessarias = math.ceil(preco / dividendo_mensal_por_cota)

    # ===============================
    # MÉTRICAS
    # ===============================
    c1, c2, c3 = st.columns(3)
    c1.metric("Preço da cota", f"R$ {preco:.2f}")
    c2.metric(
        "Dividendo mensal por cota",
        f"R$ {dividendo_mensal_por_cota:.2f}"
    )
    c3.metric(
        "Valor necessário investido",
        f"R$ {cotas_necessarias * preco:.2f}"
    )

    st.divider()

    # ===============================
    # CARD RESULTADO
    # ===============================
    st.markdown(
        f"""
        <div style="
            background-color:#f8f9fa;
            border-radius:16px;
            padding:20px;
            border:1px solid #e0e0e0;
            text-align:center;
            margin-top:16px;">
            <div style="font-size:22px; color:#666;">
                Você deveria comprar
            </div>
            <div style="
                font-size:40px;
                font-weight:700;
                margin:8px 0;
                color:#111;">
                {cotas_necessarias}
            </div>
            <div style="font-size:18px; color:#666;">
                cotas para que os dividendos mensais
                comprem <b>1 nova cota</b> deste FII
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption(
        "⚠️ Simulação baseada em dividendos históricos. "
        "Dividendos podem variar ao longo do tempo."
    )


# =====================================================
# TAB — SIMULAÇÃO DE CARTEIRA
# =====================================================
elif st.session_state.page == 'carteira':
    scroll_to_top()
    st.subheader("💼 Simulação da sua Carteira de FIIs")
    st.caption(
        "Informe os FIIs e a quantidade de cotas para estimar "
        "renda mensal e Dividend Yield da carteira."
    )

    st.divider()

    fiis_selecionados = st.multiselect(
        "Selecione os FIIs da sua carteira",
        options=sorted(df["Fundos"].unique())
    )

    if not fiis_selecionados:
        st.info("Selecione ao menos um FII para começar.")
        st.stop()

    dados_carteira = []

    for fii in fiis_selecionados:
        row = df[df["Fundos"] == fii].iloc[0]

        qtd = st.number_input(
            f"Quantidade de cotas — {fii}",
            min_value=0,
            step=1,
            key=f"qtd_{fii}"
        )

        if qtd <= 0:
            continue

        preco = row["Preço Atual (R$)"]
        dy12 = row["DY (12M) Acumulado"]

        valor_aplicado = qtd * preco
        dividendo_mensal = valor_aplicado * (dy12 / 100) / 12

        dados_carteira.append({
            "FII": fii,
            "Quantidade": qtd,
            "Preço Atual (R$)": preco,
            "Valor Aplicado (R$)": valor_aplicado,
            "DY 12M (%)": dy12,
            "Dividendo Mensal (R$)": dividendo_mensal
        })

    if not dados_carteira:
        st.warning("Informe a quantidade de cotas de ao menos um FII.")
        st.stop()

    df_carteira = pd.DataFrame(dados_carteira)

    total_investido = df_carteira["Valor Aplicado (R$)"].sum()
    total_div_mensal = df_carteira["Dividendo Mensal (R$)"].sum()

    dy_mensal = (total_div_mensal / total_investido) * 100
    dy_anual = dy_mensal * 12

    st.divider()

    # ===============================
    # MÉTRICAS DA CARTEIRA
    # ===============================
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Valor total investido",
        f"R$ {total_investido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    c2.metric(
        "Renda mensal estimada",
        f"R$ {total_div_mensal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    c3.metric("DY mensal da carteira", f"{dy_mensal:.2f}%")

    st.metric("DY anual estimado da carteira", f"{dy_anual:.2f}%")

    st.divider()

    # ===============================
    # TABELA DETALHADA
    # ===============================
    st.dataframe(
        df_carteira.style.format({
            "Preço Atual (R$)": "R$ {:.2f}",
            "Valor Aplicado (R$)": "R$ {:.2f}",
            "Dividendo Mensal (R$)": "R$ {:.2f}",
            "DY 12M (%)": "{:.2f}%"
        }),
        use_container_width=True
    )

    st.caption(
        "⚠️ Valores estimados com base no DY histórico (12 meses). "
        "Dividendos podem variar ao longo do tempo."
    )



 # =====================================================
# TAB — ANÁLISE INDIVIDUAL DE FII
# =====================================================
elif st.session_state.page == 'fii':
    scroll_to_top()
    st.subheader("🔎 Análise Individual de FII")
    st.caption("Visão consolidada e objetiva para apoio à decisão")

    fii_escolhido = st.selectbox(
        "Selecione o FII",
        sorted(df["Fundos"].unique()),
        key="analise_individual_fii"
    )

    row = df[df["Fundos"] == fii_escolhido].iloc[0]

    # ===============================
    # VISÃO RÁPIDA
    # ===============================
    st.markdown("### 📌 Visão rápida")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Preço", f"R$ {row['Preço Atual (R$)']:.2f}")
    c2.metric("P/VP", f"{row['P/VP']:.2f}")
    c3.metric("DY 12M", f"{row['DY (12M) Acumulado']:.1f}%")
    c4.metric("Liquidez", f"R$ {row['Liquidez Diária (milhões R$)']:.1f} mi")

    status_preco = "Desconto" if row["P/VP"] < 1 else "Prêmio"
    status_dy = comparar_com_selic(row["DY (12M) Acumulado"])

    st.caption(
        f"Preço vs Patrimônio: **{status_preco}** | "
        f"Renda vs Selic: **{status_dy}**"
    )

    st.divider()

    # ===============================
    # FUNDAMENTAÇÃO QUANTITATIVA
    # ===============================
    st.markdown("### 🧱 Fundamentação Quantitativa")

    criterios = {
        "P/VP saudável (0,80–1,00)": 0.8 <= row["P/VP"] < 1.0,
        "DY 12M consistente (≥ 9,6%)": row["DY (12M) Acumulado"] >= 9.6,
        "Liquidez adequada (≥ R$ 1 mi)": row["Liquidez Diária (milhões R$)"] >= 1,
        "Porte relevante (PL ≥ R$ 500 mi)": row["Patrimônio Líquido (milhões R$)"] >= 500,
        "Base sólida de cotistas (≥ 10 mil)": row["Num. Cotistas (milhares)"] >= 10,
    }

    score = 0
    for nome, ok in criterios.items():
        if ok:
            score += 1
        st.markdown(f"- {'✅' if ok else '❌'} {nome}")

    st.divider()

    # ===============================
    # HISTÓRICO DE DIVIDENDOS
    # ===============================
    st.markdown("### 💰 Histórico de Dividendos")

    c1, c2, c3 = st.columns(3)
    c1.metric("DY 3M", f"{row['DY (3M) Acumulado']:.1f}%")
    c2.metric("DY 6M", f"{row['DY (6M) Acumulado']:.1f}%")
    c3.metric("DY 12M", f"{row['DY (12M) Acumulado']:.1f}%")

    st.caption(f"Último dividendo pago: **R$ {row['Último Dividendo']:.2f}**")

    if row["DY (3M) Acumulado"] > row["DY (6M) Acumulado"] / 2:
        st.caption("📈 Dividendos recentes acima da média histórica")
    else:
        st.caption("📉 Dividendos recentes abaixo da média histórica")

    st.divider()

    # ===============================
    # PORTE E RELEVÂNCIA
    # ===============================
    st.markdown("### 🏢 Porte e Relevância")

    c1, c2 = st.columns(2)
    c1.metric(
        "Patrimônio Líquido",
        f"R$ {row['Patrimônio Líquido (milhões R$)']:.0f} mi"
    )
    c2.metric(
        "Cotistas",
        f"{row['Num. Cotistas (milhares)']:.0f} mil"
    )

    if row["Patrimônio Líquido (milhões R$)"] >= 1000:
        st.caption("🏦 Fundo de grande porte, com maior robustez estrutural")
    else:
        st.caption("⚠️ Fundo de porte médio — acompanhar eventos e liquidez")

    st.divider()

    # ===============================
    # SIMULAÇÃO RÁPIDA
    # ===============================
    st.markdown("### 💡 Simulação de Renda (12 meses)")

    valor_simulado = 10_000
    renda_estimada = valor_simulado * (row["DY (12M) Acumulado"] / 100)

    st.caption(
        f"Com **R$ {valor_simulado:,.0f}**, este FII teria gerado "
        f"aproximadamente **R$ {renda_estimada:,.0f}** em dividendos "
        "nos últimos 12 meses."
    )

    st.divider()

    # ===============================
    # LEITURA FINAL
    # ===============================
    if score >= 4:
        st.success("FII bem posicionado dentro dos critérios quantitativos do Monitor.")
    elif score == 3:
        st.warning("FII com equilíbrio entre pontos fortes e pontos de atenção.")
    else:
        st.error("FII com fragilidades relevantes frente aos critérios do Monitor.")

    st.info(
        "Esta análise é baseada exclusivamente em critérios quantitativos objetivos. "
        "Não constitui recomendação de compra ou venda."
    )

    ticker = row["Fundos"].split(" - ")[0]
    st.markdown(
        f"[🔗 Ver dados completos no Funds Explorer]"
        f"(https://www.fundsexplorer.com.br/funds/{ticker})",
        unsafe_allow_html=True
    )

elif st.session_state.page == "acao":
    scroll_to_top()

    st.subheader("📈 Análise Fundamentalista de Ações")
    st.caption("Saúde financeira, qualidade e crescimento no tempo")

    ticker = st.selectbox(
        "Selecione a ação",
        [
            "ITUB4.SA","BBAS3.SA","BBDC4.SA","SANB11.SA","BPAC11.SA",
            "EGIE3.SA","TAEE11.SA","ELET3.SA","EQTL3.SA","CPFE3.SA",
            "PETR4.SA","PRIO3.SA","VALE3.SA","SUZB3.SA","KLBN11.SA",
            "WEGE3.SA","EMBR3.SA","RAIL3.SA","RENT3.SA","CCRO3.SA",
            "ABEV3.SA","LREN3.SA","ASAI3.SA","MGLU3.SA","ARZZ3.SA",
            "RADL3.SA","FLRY3.SA","HAPV3.SA","RDOR3.SA",
            "VIVT3.SA","TIMS3.SA","TOTS3.SA","LWSA3.SA",
            "SBSP3.SA","CSMG3.SA","SAPR11.SA"
        ],
        key="acao_individual"
    )

    # =====================
    # CARREGA DADOS (COM TRY)
    # =====================
    try:
        info, hist = carregar_dados_acao(ticker)
        m = extrair_metricas_acao(info)
    except Exception as e:
        st.error("Erro ao carregar dados da ação.")
        st.stop()

    # =====================
    # VISÃO RÁPIDA
    # =====================
    st.markdown("### 📌 Visão rápida")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Preço", safe(m.get("Preço Atual"), brl))
    c2.metric("P/L", safe(m.get("P/L"), lambda x: f"{x:.1f}"))
    c3.metric("P/VP", safe(m.get("P/VP"), lambda x: f"{x:.2f}"))
    c4.metric("ROE", safe(m.get("ROE (%)"), pct))

    st.divider()

    # =====================
    # SAÚDE FINANCEIRA
    # =====================
    st.markdown("### 🧱 Saúde da empresa")

    st.metric(
        "Classificação Refera",
        classificar_saude(m)
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Margem Líquida", safe(m.get("Margem Líquida (%)"), pct))
    c2.metric("ROA", safe(m.get("ROA (%)"), pct))
    c3.metric("Dívida / Patrimônio", safe(m.get("Dívida/Patrimônio"), lambda x: f"{x:.2f}"))

    st.divider()

    # =====================
    # QUALIDADE & EFICIÊNCIA
    # =====================
    st.markdown("### 🧠 Qualidade operacional")

    c1, c2, c3 = st.columns(3)
    c1.metric("ROIC", safe(m.get("ROIC (%)"), pct))
    c2.metric("Margem Operacional", safe(m.get("Margem Operacional (%)"), pct))
    c3.metric("Free Cash Flow", safe(m.get("FCF (R$ bi)"), lambda x: f"R$ {x:.1f} bi"))

    st.divider()

    # =====================
    # CRESCIMENTO
    # =====================
    st.markdown("### 🚀 Crescimento")

    c1, c2, c3 = st.columns(3)
    c1.metric("Receita (5a)", safe(m.get("Crescimento Receita (%)"), pct))
    c2.metric("Lucro (5a)", safe(m.get("Crescimento Lucro (%)"), pct))
    c3.metric("EPS (5a)", safe(m.get("Crescimento EPS (%)"), pct))

    st.divider()

    # =====================
    # VALUATION SIMPLES
    # =====================
    st.markdown("### 💰 Leitura de valuation")

    leitura = leitura_valor_acao(m)
    for l in leitura:
        st.markdown(f"- {l}")

    st.divider()

    # =====================
    # BACKTEST
    # =====================
    st.markdown("### ⏱️ Valorização histórica")

    if hist is not None and not hist.empty:
        retorno_total, retorno_anual = backtest_valorizacao(hist)

        c1, c2 = st.columns(2)
        c1.metric("Retorno total", safe(retorno_total, pct))
        c2.metric("Retorno anualizado", safe(retorno_anual, pct))

        st.plotly_chart(grafico_preco_acao(hist, ticker),use_container_width=True)

    st.divider()

    st.info(
        "Análise quantitativa baseada em dados públicos. "
        "Não constitui recomendação de investimento."
    )

    
st.markdown(
    """
    <a href="?page=home"
       style="
           display:inline-block;
           margin-top:12px;
           text-decoration:none;
           font-size:14px;
           color:#9fb3c8;
           cursor:pointer;
       ">
       ← Voltar
    </a>
    """,
    unsafe_allow_html=True
)





























































