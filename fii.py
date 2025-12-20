import pandas as pd
import streamlit as st
from datetime import datetime

# =====================================================
# CONFIG STREAMLIT
# =====================================================
st.set_page_config(
    page_title="FIIs Descontados com Qualidade",
    layout="centered"
)

# =====================================================
# TÍTULO E CONTEXTO
# =====================================================
st.title("📊 FIIs Descontados com Qualidade")

st.caption(
    "Lista diária de FIIs que passam em critérios rígidos de preço, "
    "renda recente e saúde operacional."
)

st.info(
    "⚠️ **Aviso importante**: esta é uma análise quantitativa. "
    "Eventos recentes como emissões, vendas pontuais de ativos ou fatos relevantes "
    "podem não estar totalmente refletidos nos dados. "
    "Sempre verifique comunicados oficiais antes de investir."
)

# =====================================================
# CONTROLE DE CACHE
# =====================================================
if st.button("🧹 Atualizado a página ai Tekinildas"):
    st.cache_data.clear()
    st.success("Cache limpo com sucesso!")
    st.rerun()

# =====================================================
# LOAD E TRATAMENTO DOS DADOS
# =====================================================
@st.cache_data(ttl=60 * 60 * 24, show_spinner=True)
def carregar_dados():
    df = pd.read_parquet("df_fiis.parquet")

    # Remove linhas críticas
    df = df.dropna(subset=[
        'P/VP',
        'DY (3M) Acumulado',
        'DY (6M) Acumulado',
        'DY (12M) Acumulado',
        'Liquidez Diária (R$)',
        'Patrimônio Líquido',
        'Num. Cotistas'
    ])

    # Conversões
    df['P/VP'] = df['P/VP'] / 100

    for col in ['DY (3M) Acumulado', 'DY (6M) Acumulado', 'DY (12M) Acumulado']:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace('%', '', regex=False)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float)
        )

    df['Liquidez Diária (R$)'] = (
        df['Liquidez Diária (R$)']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
        .astype(float) / 1_000_000
    )

    df['Patrimônio Líquido'] = (
        df['Patrimônio Líquido']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
        .astype(float) / 1_000_000
    )

    df['Num. Cotistas'] = (
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
        .astype(float)/100
    )

    df.rename(columns={
        'Liquidez Diária (R$)': 'Liquidez Diária (milhões R$)',
        'Patrimônio Líquido': 'Patrimônio Líquido (milhões R$)',
        'Num. Cotistas': 'Num. Cotistas (milhares)'
    }, inplace=True)

    return df

# =====================================================
# FILTRO CORE DO PRODUTO
# =====================================================
def filtrar_fiis_descontados_com_qualidade(df):
    filtros = (
        (df["P/VP"] >= 0.8) &
        (df["P/VP"] < 1.0) &
        (df["DY (3M) Acumulado"] >= 0.8 * 3) &
        (df["DY (6M) Acumulado"] >= 0.8 * 6) &
        (df["DY (12M) Acumulado"] >= 0.8 * 12) &
        (df["Liquidez Diária (milhões R$)"] >= 1) &
        (df["Patrimônio Líquido (milhões R$)"] >= 500) &
        (df["Num. Cotistas (milhares)"] >= 10)
    )
    return df[filtros].copy()

# =====================================================
# EXECUÇÃO
# =====================================================
df = carregar_dados()
df_filtrados = filtrar_fiis_descontados_com_qualidade(df)

st.write(f"🕒 Atualizado em **{datetime.now().strftime('%d/%m/%Y')}**")

# UI MOBILE-FIRST
fiis_achados = len(df_filtrados)

df_top10 = (
    df_filtrados
    .sort_values("DY (12M) Acumulado", ascending=False)
    .head(15)
    .sort_values("P/VP")
    .head(10)
)

st.markdown(
    """
    **Mostramos abaixo os 10 FIIs com melhor combinação de rendimento (12M) e desconto (P/VP)**
    entre todos os fundos que passaram nos critérios mínimos de qualidade.
    """
)
if df_top10.empty:
    st.warning("Hoje, nenhum FII atende a todos os critérios definidos.")
else:
    st.success(f"{fiis_achados} FIIs atendem aos critérios hoje")
    st.title('Top 10 FIIs com melhor P/VP entre os que atendem aos critérios:')
    for _, row in df_top10.iterrows():
        with st.container(border=True):

            # Nome e setor
            st.markdown(f"### {row['Fundos']}")
            st.caption(f"Setor: {row['Setor']}")

            cols_header = st.columns([1, 2, 3])

            with cols_header[0]:
                st.metric(
                    label="P/VP",
                    value=f"{row['P/VP']:.2f}",
                    help="Preço em relação ao valor patrimonial"
                )

            with cols_header[1]:
                st.metric(
                    label="Liquidez Diária",
                    value=f"R$ {row['Liquidez Diária (milhões R$)']:.1f} mi",
                    help="Média diária negociada"
                )

            with cols_header[2]:
                st.metric(
                    label="Preço Atual",
                    value=f"R$ {row['Preço Atual (R$)']:.2f}",
                    help="Valor total dos ativos do fundo"
                )
            cols = st.columns([1, 2])
            with cols[0]:
                st.metric(
                    label="Dividend Yield (12M)",
                    value=f"{row['DY (12M) Acumulado']:.1f}%",
                    help="Dividendos acumulados nos últimos 12 meses"
                )
            rendimento_mes = (1 + (row['DY (12M) Acumulado']/100))**(1/12) - 1
            rendimento_mes *= 100
                        
            with cols[1]:
                st.markdown(
                    f"""> Rendimento equivalente : <u>{rendimento_mes:.2f}%</u> ao mês""",unsafe_allow_html=True
                )


            # DY recente compacto
            st.markdown(
                f"""DY 3 meses: {row['DY (3M) Acumulado']:.1f}% > Equivalente : <u>{((1 + (row['DY (3M) Acumulado']/100))**(1/3) - 1)*100:.2f}%</u> ao mês""", unsafe_allow_html=True)
            
            st.markdown(
                f""" **DY 6 meses: {row['DY (6M) Acumulado']:.1f}%** > Equivalente : <u>{((1 + (row['DY (6M) Acumulado']/100))**(1/6) - 1)*100:.2f}%</u> ao mês""", unsafe_allow_html=True)

            ticker = row['Fundos'].split(" - ")[0]
            st.markdown(
                f"""
                <a href="https://www.fundsexplorer.com.br/fiagros/{ticker}" target="_blank">
                    🔗 Olhar mais detalhes do FII
                </a>
                """,
                unsafe_allow_html=True
            )
            st.write("")
            # Detalhes
            with st.expander("🔎 Ver detalhes do fundo"):
                st.markdown(
                    f"""
                    - **Patrimônio Líquido:** R$ {row['Patrimônio Líquido (milhões R$)']:.0f} milhões  
                    - **Cotistas:** {row['Num. Cotistas (milhares)']:.0f} mil  
                    - **Critérios atendidos:**  
                        - ✔️ Desconto (P/VP < 1)  
                        - ✔️ Dividendos recentes e consistentes  
                        - ✔️ Saúde operacional mínima  
                    """
                )

with st.expander("📄 Ver todos os FIIs que passaram nos critérios hoje"):
    st.write(f"Total de FIIs aprovados: **{fiis_achados}**")

    lista_fiis = (
        df_filtrados["Fundos"]
        .sort_values()
        .unique()
        .tolist()
    )

    st.markdown(
        " • " + " • ".join(lista_fiis)
    )
