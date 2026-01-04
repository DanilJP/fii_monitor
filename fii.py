import pandas as pd
import streamlit as st
import yfinance as yf
import altair as alt
import json
from pathlib import Path
from datetime import datetime

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Refera — Análise Individual de FIIs",
    layout="centered"
)

st.markdown("""
<style>
body {
    background-color: #020617;
}

h1, h2, h3 {
    color: #e5e7eb;
}

small, .caption {
    color: #94a3b8;
}

hr {
    border: none;
    border-top: 1px solid #1e293b;
    margin: 24px 0;
}

/* SECTION */
.section-title {
    margin-top: 32px;
    margin-bottom: 12px;
    font-size: 18px;
    font-weight: 600;
    color: #e5e7eb;
}

/* METRIC CARD */
.metric-card {
    background-color: #020617;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 18px;
    text-align: center;
}

.metric-label {
    font-size: 13px;
    color: #94a3b8;
}

.metric-value {
    font-size: 22px;
    font-weight: 600;
    color: #f8fafc;
}

/* BLOCO TEXTO */
.info-card {
    background-color: #020617;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px;
}
</style>
""", unsafe_allow_html=True)

if st.button("🔄 Limpar cache de dados"):
    st.cache_data.clear()
    st.success("Cache de dados limpo com sucesso.")
    st.rerun()
# =====================================================
# PARÂMETROS DO CRITÉRIO REFERA
# =====================================================
JANELA_QUEDA = 10
CDI = 0.15
SELIC_ANUAL = (1+CDI)*(1-0.225)      # proxy simples


colunas_utilizadas = ['Fundos', 'Setor', 'Preço Atual (R$)', 'Liquidez Diária (milhões R$)',
       'P/VP', 'Último Dividendo', 'Dividend Yield', 'DY (3M) Acumulado',
       'DY (6M) Acumulado', 'DY (12M) Acumulado', 'DY Ano', 'Patrimônio Líquido (milhões R$)', 'Quant. Ativos',
       'Num. Cotistas (milhares)','Motivos','Bloqueios','Score']

# =====================================================
# LOAD DADOS
# =====================================================
def carregar_dados():
    df_fiis = pd.read_parquet("df_fiis/df_fiis.parquet")
    df_fiis.dropna(subset=colunas_utilizadas,inplace=True)
    df_fiis = df_fiis[colunas_utilizadas]
    return df_fiis

df = carregar_dados()

# =====================================================
# UI
# =====================================================
st.title("Fiish - by Refera")
st.caption("Modelo quantitativo focado em BLOQUEAR decisões ruins.")

fii = st.selectbox("Selecione o FII", sorted(df["Fundos"].unique()))
row = df[df["Fundos"] == fii].iloc[0]

# =====================================================
# HISTÓRICO DE PREÇOS
# =====================================================
ticker = yf.Ticker(f"{fii}.SA")
hist = ticker.history(period="1y")

if len(hist) < 200:
    st.error("Histórico insuficiente.")
    st.stop()

preco_atual = hist["Close"].iloc[-1]
preco_passado = hist["Close"].iloc[-(JANELA_QUEDA + 1)]
queda_pct = (preco_atual / preco_passado - 1) * 100

retornos = hist["Close"].pct_change()
vol = retornos.std() * (252 ** 0.5)

# =====================================================
# DECISÃO FINAL
# =====================================================
score = df[df["Fundos"] == fii].Score.iloc[0]
bloqueios = df[df["Fundos"] == fii].Bloqueios.iloc[0]
motivos = df[df["Fundos"] == fii].Motivos.iloc[0]

if score >= 5:
    decisao = "🟢 APROVADO PELO CRITÉRIO REFERA"
elif score >= 3:
    decisao = "🟡 EXIGE CAUTELA — EM OBSERVAÇÃO"
else:
    decisao = "🔴 BLOQUEADO — RISCO FORA DO CRITÉRIO"


st.markdown(f"## {fii}")
st.caption(f"Setor: {row['Setor']} • Análise quantitativa Refera")


def decisao_card(decisao, score):
    if score >= 5/6:
        bg = "#052e16"
        border = "#22c55e"
    elif score >= 3/6:
        bg = "#3f2f06"
        border = "#eab308"
    else:
        bg = "#450a0a"
        border = "#ef4444"

    st.markdown(
        f"""
        <div style="
            background-color: {bg};
            border-left: 6px solid {border};
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 28px;
        ">
            <div style="font-size:18px;font-weight:600;color:#f8fafc;">
                {decisao}
            </div>
            <div style="margin-top:6px;font-size:13px;color:#cbd5f5;">
                Score Refera: {score*100:.0f}%
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

score_perc = score/6
decisao_card(decisao, score_perc)


# =====================================================
# BLOQUEIOS
# =====================================================

def info_card(titulo, itens):
    conteudo = ""

    if len(itens) > 0:
        for i in itens:
            conteudo += f"<li>{i}</li>"
    else:
        conteudo = "<li>Nenhum item relevante.</li>"

    st.markdown(
        f"""
        <div class="section-title">{titulo}</div>
        <div class="info-card">
            <ul style="margin:0;padding-left:18px;">
                {conteudo}
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )
info_card("🔒 Bloqueios", bloqueios)
info_card("🏆 Pontos Positivos", motivos)

# =====================================================
# GRÁFICO
# =====================================================
st.markdown("### Histórico de Preço (12M)")
df_chart = hist.reset_index()[["Date", "Close"]]

# =====================================================
# SELETOR DE PERÍODO
# =====================================================
st.markdown("### Histórico de Preço")

periodo = st.radio(
    "Período",
    ["1M", "3M", "6M", "12M"],
    horizontal=True,
    label_visibility="collapsed"
)

mapa_periodo = {
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "12M": 365
}

dias = mapa_periodo[periodo]

# =====================================================
# PREPARAÇÃO DOS DADOS
# =====================================================
df_chart = hist.reset_index()[["Date", "Close"]]

data_inicio = df_chart["Date"].max() - pd.Timedelta(days=dias)
df_filtrado = df_chart[df_chart["Date"] >= data_inicio]

# =====================================================
# GRÁFICO
# =====================================================
chart = (
    alt.Chart(df_filtrado)
    .mark_line(strokeWidth=2)
    .encode(
        x=alt.X("Date:T", title=""),
        y=alt.Y(
            "Close:Q",
            title="Preço (R$)",
            scale=alt.Scale(zero=False, nice=False)
        ),
        tooltip=[
            alt.Tooltip("Date:T", title="Data"),
            alt.Tooltip("Close:Q", title="Preço", format=".2f")
        ]
    )
    .properties(height=320)
)

st.altair_chart(chart, use_container_width=True)


# =====================================================
# MÉTRICAS
# =====================================================
st.markdown("### Indicadores")

def metric_card(label, value):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<div class='section-title'>Valuation & Renda</div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    metric_card("P / VP", f"{row['P/VP']:.2f}")

with c2:
    metric_card("DY 12M", f"{row['DY (12M) Acumulado']:.2f}%")

with c3:
    liq = row['Liquidez Diária (milhões R$)']
    metric_card("Liquidez", f"{liq*1000:.0f} mil" if liq < 1 else f"{liq:.1f} mi")


st.markdown("<div class='section-title'>Risco & Movimento</div>", unsafe_allow_html=True)

c4, c5 = st.columns(2)

with c4:
    metric_card('Volatilidade',f"{vol*100:.1f}%")

with c5:
    metric_card('Queda (últimos 10 dias)',f"{queda_pct:.2f}%")

st.markdown("<div class='section-title'>Estrutura do Fundo</div>", unsafe_allow_html=True)

c6, c7, c8 = st.columns(3)

with c6:
    metric_card('Patrimônio',f"R$ {row['Patrimônio Líquido (milhões R$)']:.1f} mi")

with c7:
    metric_card('Ativos',f"{int(row['Quant. Ativos'])}")

with c8:
    metric_card('Cotistas', f"{int(row['Num. Cotistas (milhares)']*1000):,}".replace(",", "."))


st.markdown(
    """
    <hr>
    <small>
    Refera não recomenda ativos.  
    Seu papel é <strong>bloquear decisões ruins</strong> antes que elas entrem na sua carteira.
    </small>
    """,
    unsafe_allow_html=True
)
