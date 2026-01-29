import pandas as pd
import streamlit as st
import yfinance as yf
import altair as alt
from datetime import timedelta

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Fiish — by Refera",
    layout="centered"
)

# =====================================================
# ESTILO
# =====================================================
st.markdown("""
<style>
body { background-color: #020617; }
h1,h2,h3 { color: #e5e7eb; }
.caption,small { color: #94a3b8; }

.metric-card {
    background:#020617;
    border:1px solid #1e293b;
    border-radius:14px;
    padding:16px;
    text-align:center;
}

.metric-label {
    font-size:13px;
    color:#94a3b8;
}

.metric-value {
    font-size:20px;
    font-weight:600;
    color:#f8fafc;
}

.info-card {
    background:#020617;
    border:1px solid #1e293b;
    border-radius:12px;
    padding:14px;
}

.section-title {
    margin-top:32px;
    margin-bottom:12px;
    font-size:18px;
    font-weight:600;
    color:#e5e7eb;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# CACHE
# =====================================================
if st.button("🧹 Limpar Cache de Dados"):
    st.cache_data.clear()

# =====================================================
# LOAD DADOS
# =====================================================
@st.cache_data
def carregar_dados():
    df = pd.read_parquet("df_fiis.parquet")
    data_ref = df["ano_mes_dia"].iloc[0]
    return df, data_ref

df, data_ref = carregar_dados()
motivos_max = df["Score"].max()
motivos_obs = motivos_max - 2

# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================
def metric_card(label, value):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def classificar_status(score):
    if score >= motivos_max:
        return "🟢 RECOMENDADO", "#052e16", "#22c55e"
    elif score >= motivos_obs:
        return "🟡 EM OBSERVAÇÃO", "#3f2f06", "#eab308"
    else:
        return "🔴 BLOQUEADO", "#450a0a", "#ef4444"

def render_lista(titulo, itens):
    conteudo = "".join([f"<li>{i}</li>" for i in itens]) or "<li>Nenhum item relevante</li>"
    st.markdown(f"""
    <div class="section-title">{titulo}</div>
    <div class="info-card">
        <ul style="margin:0;padding-left:18px;">
            {conteudo}
        </ul>
    </div>
    """, unsafe_allow_html=True)

def parse_taxa(valor):
    try:
        if pd.isna(valor):
            return None
        valor = (
            str(valor)
            .lower()
            .replace("a.a", "")
            .replace("%", "")
            .replace(",", ".")
            .strip()
        )
        return float(valor)
    except:
        return None

# =====================================================
# HEADER
# =====================================================
st.title("Fiish — by Refera")
st.caption("Modelo quantitativo focado em BLOQUEAR decisões ruins.")
st.write("Última atualização:", data_ref)

# =====================================================
# ANÁLISE INDIVIDUAL
# =====================================================
st.markdown("---")
fii = st.selectbox("Analisar FII individualmente", sorted(df["Fundos"].unique()))
row = df[df["Fundos"] == fii].iloc[0]
st.markdown(f"Setor : {row['Setor']}")

# =====================================================
# DECISÃO
# =====================================================
status, cor, borda = classificar_status(int(row["Score"]))

st.markdown(f"""
<div style="
    background:{cor};
    border-left:6px solid {borda};
    padding:20px;
    border-radius:12px;
    margin-bottom:24px;">
    <div style="font-size:18px;font-weight:600;color:#f8fafc;">{status}</div>
    <div style="font-size:13px;color:#cbd5f5;margin-top:6px;">
        Score Refera: {int(row['Score'])}/{motivos_max}
    </div>
</div>
""", unsafe_allow_html=True)

render_lista("🔒 Bloqueios", row["Bloqueios"])
render_lista("🏆 Pontos Positivos", row["Motivos"])

# =====================================================
# GRÁFICO DE PREÇO
# =====================================================
st.markdown("### Histórico de Preço")
periodo = st.radio(
    "Período",
    ["1M","3M","6M","1y","2y","3y","4y","5y"],
    index=3,
    horizontal=True
)

dias = {
    "1M":30,"3M":90,"6M":180,"1y":365,
    "2y":730,"3y":1095,"4y":1460,"5y":1825
}[periodo]

ticker = yf.Ticker(f"{fii}.SA")
hist = ticker.history(period="5y")

df_chart = hist.reset_index()
df_chart = df_chart[df_chart["Date"] >= df_chart["Date"].max() - timedelta(days=dias)]

if st.checkbox("Mostrar Média Móvel (28 dias)"):
    df_chart["Close"] = df_chart["Close"].rolling(window=28).mean()

chart = alt.Chart(df_chart).mark_line(strokeWidth=2).encode(
    x="Date:T",
    y=alt.Y("Close:Q", scale=alt.Scale(zero=False)),
    tooltip=["Date:T","Close:Q"]
).properties(height=320)

st.altair_chart(chart, use_container_width=True)

# =====================================================
# 🔥 NOVO — DIVIDENDOS & DY NO PERÍODO
# =====================================================
st.markdown("### Dividendos e Dividend Yield no Período")

div = ticker.dividends.reset_index()
div.columns = ["Date", "Dividends"]
div = div[div["Date"] >= df_chart["Date"].min()]

df_div = pd.merge(
    df_chart[["Date", "Close"]],
    div,
    on="Date",
    how="left"
)

df_div["Dividends"] = df_div["Dividends"].fillna(0)

# --- Dividendos ---
chart_div = alt.Chart(df_div[df_div["Dividends"] > 0]).mark_bar().encode(
    x="Date:T",
    y=alt.Y("Dividends:Q", title="Dividendos (R$)"),
    tooltip=["Date:T","Dividends:Q"]
).properties(height=180)

st.altair_chart(chart_div, use_container_width=True)

# --- DY acumulado ---
preco_base = df_div["Close"].iloc[0]
df_div["DY_periodo"] = (df_div["Dividends"].cumsum() / preco_base) * 100

chart_dy = alt.Chart(df_div).mark_line(strokeWidth=2).encode(
    x="Date:T",
    y=alt.Y("DY_periodo:Q", title="DY Acumulado (%)", scale=alt.Scale(zero=True)),
    tooltip=["Date:T", alt.Tooltip("DY_periodo:Q", format=".2f")]
).properties(height=180)

st.altair_chart(chart_dy, use_container_width=True)

# =====================================================
# LISTAS MACRO
# =====================================================
df_core = df[(df["Score"] >= motivos_max)]
df_watch = df[(df["Score"] >= motivos_obs) & (df["Score"] < motivos_max)]
df_block = df[(df["Score"] < motivos_obs)]
# =====================================================
# VISÃO MACRO
# =====================================================
with st.expander("🟢 Core Refera — FIIs Aprovados"):
    for _, r in df_core.sort_values(["Score", "DY (12M) Acumulado"], ascending=False).iterrows():
        st.markdown(f"""
        <div style="
            background:#052e16;
            border:1px solid #22c55e;
            border-radius:10px;
            padding:12px;
            margin-bottom:8px;">
            <strong>{r['Fundos']}</strong><br>
            <small>
                Score {int(r['Score'])}/{motivos_max} • DY 12M {r['DY (12M) Acumulado']:.1f}% • P/VP {r['P/VP']:.2f}
            </small>
        </div>
        """, unsafe_allow_html=True)

with st.expander("🟡 Watchlist — Em Observação"):
    for _, r in df_watch.sort_values('DY (12M) Acumulado',ascending=False).sort_values("Score", ascending=False).iterrows():
        st.write(f"- {r['Fundos']} | Score {int(r['Score'])}/9 | P/VP : {r['P/VP']} | DY 12M: {r['DY (12M) Acumulado']:.1f}%")

with st.expander("🔴 FIIs Bloqueados"):
    for _, r in df_block.iterrows():
        st.write(f"- {r['Fundos']} | {r['Bloqueios'][0]}")
# =====================================================
# FOOTER
# =====================================================
st.markdown("""
<hr>
<small>
Refera não recomenda ativos.<br>
Seu papel é <strong>bloquear decisões ruins</strong>.
</small>
""", unsafe_allow_html=True)
