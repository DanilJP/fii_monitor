import pandas as pd
import streamlit as st

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Refera — Diagnóstico da Carteira",
    layout="centered"
)

motivos_max = 9
motivos_obs = 6

# =====================================================
# ESTILO
# =====================================================
st.markdown("""
<style>
body { background-color: #020617; }
h1,h2,h3,strong { color: #e5e7eb; }
.caption,small { color: #94a3b8; }

.alert {
    border-left:6px solid;
    border-radius:14px;
    padding:18px;
    margin-bottom:18px;
    color:#e5e7eb;
}

/* status */
.ok   { background:#052e16; border-color:#22c55e; }
.warn { background:#3f2f06; border-color:#eab308; }
.bad  { background:#450a0a; border-color:#ef4444; }

/* elementos internos */
.alert ul {
    margin:8px 0 0 18px;
    padding:0;
}

.alert li {
    margin-bottom:6px;
    font-size:14px;
}

.alert hr {
    border:0.5px solid #334155;
    margin:12px 0;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# LOAD DADOS
# =====================================================
@st.cache_data
def carregar_dados():
    df = pd.read_parquet("df_fiis.parquet")
    data_ref = df["ano_mes_dia"].iloc[0]
    return df, data_ref

df, data_ref = carregar_dados()

# =====================================================
# FUNÇÕES
# =====================================================
def classificar_status(score):
    if score >= motivos_max:
        return "🟢 APROVADO", "ok"
    elif score >= motivos_obs:
        return "🟡 EM OBSERVAÇÃO", "warn"
    else:
        return "🔴 BLOQUEADO", "bad"


def render_lista_html(itens):
    itens = list(itens)
    if isinstance(itens, list) and len(itens) > 0:
        li = "".join(f"<li>{i}</li>" for i in itens)
    else:
        li = "<li>Nenhum ponto relevante identificado</li>"
    return f"<ul>{li}</ul>"

# =====================================================
# HEADER
# =====================================================
st.title("📊 Diagnóstico da Carteira — Refera")
st.caption("Avaliação dos FIIs da sua carteira com foco em riscos e fragilidades.")
st.write("Base de dados:", data_ref)

st.markdown("---")

# =====================================================
# SESSION STATE — CARTEIRA (DEFAULT)
# =====================================================
carteira_padrao = {
    'BTAL11': {'tipo': 'Agro', 'quantidade': 63, 'preco_medio': 78.50},
    'CACR11': {'tipo': 'Papel', 'quantidade': 68, 'preco_medio': 73.94},
    'KNCR11': {'tipo': 'Papel', 'quantidade': 20, 'preco_medio':     103.94},
    'LIFE11': {'tipo': 'Hospitalar', 'quantidade': 610, 'preco_medio': 8.13},
    'RURA11': {'tipo': 'Tijolo', 'quantidade': 290, 'preco_medio': 8.61},
    'RZAK11': {'tipo': 'Papel', 'quantidade': 124, 'preco_medio': 82.52},
    'SPXS11': {'tipo': 'Multi', 'quantidade': 590, 'preco_medio': 8.40},
}

def carteira_dict_para_df(carteira):
    return pd.DataFrame([
        {
            "FII": fii,
            "Preço Médio (R$)": dados["preco_medio"],
            "Quantidade": dados["quantidade"],
            "Tipo": dados["tipo"]
        }
        for fii, dados in carteira.items()
    ])

if "carteira" not in st.session_state:
    st.session_state["carteira"] = carteira_dict_para_df(carteira_padrao)

# =====================================================
# INPUT — FIIs
# =====================================================
st.markdown("### Informe sua carteira")

fiis_user = st.multiselect(
    "Selecione os FIIs",
    options=sorted(df["Fundos"].unique()),
    default=st.session_state["carteira"]["FII"].tolist()
)

df_atual = st.session_state["carteira"]

novos = set(fiis_user) - set(df_atual["FII"])
if novos:
    df_atual = pd.concat([
        df_atual,
        pd.DataFrame({
            "FII": list(novos),
            "Preço Médio (R$)": [0.0] * len(novos)
        })
    ], ignore_index=True)

df_atual = df_atual[df_atual["FII"].isin(fiis_user)]
st.session_state["carteira"] = df_atual.reset_index(drop=True)

# =====================================================
# DATA EDITOR
# =====================================================
df_editado = st.data_editor(
    st.session_state["carteira"],
    key="editor_carteira",
    use_container_width=True,
    column_config={
        "FII": st.column_config.TextColumn(disabled=True),
        "Quantidade": st.column_config.NumberColumn(disabled=True),
        "Tipo": st.column_config.TextColumn(disabled=True),
        "Preço Médio (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
    }
)

st.session_state["carteira"] = df_editado

if df_editado.empty:
    st.info("Adicione FIIs para visualizar o diagnóstico.")
    st.stop()

# =====================================================
# MERGE 
# =====================================================
df_user = df_editado.merge(
    df,
    left_on="FII",
    right_on="Fundos",
    how="left"
)

df_user["Resultado %"] = (
    (df_user["Preço Atual (R$)"] - df_user["Preço Médio (R$)"])
    / df_user["Preço Médio (R$)"] * 100
)

# =====================================================
# RESUMO
# =====================================================
st.markdown("### Resumo da Carteira")

c1, c2, c3, c4 = st.columns(4)
c1.metric("FIIs", len(df_user))
c2.metric("Bloqueados", (df_user["Score"] < motivos_obs).sum())
c3.metric("Abaixo do PM", (df_user["Resultado %"] < 0).sum())
c4.metric(
    "Bloq. & Perdendo",
    ((df_user["Score"] < motivos_obs) & (df_user["Resultado %"] < 0)).sum()
)

st.markdown("---")

# =====================================================
# DIAGNÓSTICO INDIVIDUAL
# =====================================================
st.markdown("### Diagnóstico Individual")

for _, row in df_user.iterrows():

    status, css = classificar_status(row["Score"])
    resultado = row["Resultado %"]
    sinal = "🔻" if resultado < 0 else "✅"
    lista_bloqueios = render_lista_html(row["Bloqueios"])

    st.markdown(f"""
    <div class="alert {css}">
        <strong>{row['Fundos']} — {status}</strong><br>
        <small>
            Preço atual: R$ {row['Preço Atual (R$)']:.2f} |
            Seu PM: R$ {row['Preço Médio (R$)']:.2f} |
            Resultado: {sinal} {resultado:.1f}%
        </small>
        <br>
        🔒 Pontos de Atenção  Bloqueios:    
        {lista_bloqueios}

    </div>
    """, unsafe_allow_html=True)

# =====================================================
# FOOTER
# =====================================================
st.markdown("""
<hr>
<small>
Refera não recomenda compra ou venda.<br>
Seu objetivo é <strong>expor riscos</strong> e apoiar decisões conscientes.
</small>
""", unsafe_allow_html=True)
