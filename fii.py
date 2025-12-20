import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import feedparser
from datetime import datetime, timedelta
from urllib.parse import quote

import streamlit_analytics as st_analytics

with st_analytics.track():
    # =====================================================
    # CONFIG STREAMLIT
    # =====================================================
    st.set_page_config(
        page_title="FIIs Descontados com Qualidade",
        layout="centered"
    )

    # =====================================================
    # AVISO LEGAL — POPUP APENAS NA PRIMEIRA VISITA
    # =====================================================
    if "aviso_aceito" not in st.session_state:
        st.session_state.aviso_aceito = False

    @st.dialog("⚠️ Aviso importante")
    def aviso_legal():
        st.markdown(
            """
            **Antes de continuar, leia com atenção:**

            - Este aplicativo **não é recomendação de investimento**.
            - A análise é **quantitativa e baseada em dados históricos**.
            - Dividendos passados **não garantem resultados futuros**.
            - Emissões, alavancagem, eventos de crédito ou fatos relevantes
            podem não estar refletidos imediatamente nos dados.

            👉 **Sempre consulte relatórios gerenciais e comunicados oficiais.**
            """
        )

        if st.button("✅ Entendi e desejo continuar"):
            st.session_state.aviso_aceito = True
            st.rerun()

    # Mostrar o popup apenas se ainda não foi aceito
    if not st.session_state.aviso_aceito:
        aviso_legal()
        st.stop()

    # =====================================================
    # TÍTULO E CONTEXTO
    # =====================================================
    st.title("📊 FIIs Descontados com Qualidade")

    st.caption(
        "Seleção quantitativa diária de FIIs com desconto patrimonial, "
        "boa liquidez e histórico consistente de dividendos."
    )


    # =====================================================
    # LOAD E TRATAMENTO DOS DADOS
    # =====================================================
    @st.cache_data(ttl=60 * 60 * 24, show_spinner=True)
    def carregar_dados():
        df = pd.read_parquet("df_fiis.parquet")

        df = df.dropna(subset=[
            'P/VP',
            'DY (3M) Acumulado',
            'DY (6M) Acumulado',
            'DY (12M) Acumulado',
            'Liquidez Diária (R$)',
            'Patrimônio Líquido',
            'Num. Cotistas',
            'Preço Atual (R$)'
        ])

        df['P/VP'] = df['P/VP'] / 100

        for col in ['DY (3M) Acumulado', 'DY (6M) Acumulado', 'DY (12M) Acumulado']:
            df[col] = (
                df[col].astype(str)
                .str.replace('%', '', regex=False)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
                .astype(float)
            )

        df['Liquidez Diária (R$)'] = (
            df['Liquidez Diária (R$)']
            .astype(str).str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float) / 1_000_000
        )

        df['Patrimônio Líquido'] = (
            df['Patrimônio Líquido']
            .astype(str).str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float) / 1_000_000
        )

        df['Num. Cotistas'] = (
            df['Num. Cotistas']
            .astype(str).str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float) / 1_000
        )

        df['Preço Atual (R$)'] = (
            df['Preço Atual (R$)']
            .astype(str).str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float) / 100
        )

        df['Último Dividendo'] = (
            df['Último Dividendo']
            .astype(str).str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float) / 100
        )

        df.rename(columns={
            'Liquidez Diária (R$)': 'Liquidez Diária (milhões R$)',
            'Patrimônio Líquido': 'Patrimônio Líquido (milhões R$)',
            'Num. Cotistas': 'Num. Cotistas (milhares)'
        }, inplace=True)

        return df


    # =====================================================
    # FILTRO CORE
    # =====================================================
    def filtrar_fiis_descontados_com_qualidade(df):
        filtros = (
            (df["P/VP"] >= 0.8) &
            (df["P/VP"] < 1.0) &
            (df["DY (3M) Acumulado"] >= 2.4) &
            (df["DY (6M) Acumulado"] >= 4.8) &
            (df["DY (12M) Acumulado"] >= 9.6) &
            (df["Liquidez Diária (milhões R$)"] >= 1) &
            (df["Patrimônio Líquido (milhões R$)"] >= 500) &
            (df["Num. Cotistas (milhares)"] >= 10)
        )
        return df[filtros].copy()


    # =====================================================
    # NOTÍCIAS
    # =====================================================


    @st.cache_data(ttl=60 * 60)
    def buscar_noticias(ticker, max_noticias=10):
        query = quote(f"{ticker} fundo imobiliário FII")
        url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

        feed = feedparser.parse(url)

        limite_data = datetime.now() - timedelta(days=30)

        noticias = []
        for entry in feed.entries:
            if not hasattr(entry, "published_parsed"):
                continue

            data_noticia = datetime(*entry.published_parsed[:6])

            if data_noticia >= limite_data:
                noticias.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "data": data_noticia.strftime("%d/%m/%Y")
                })

            if len(noticias) >= max_noticias:
                break

        return noticias



    # =====================================================
    # EXECUÇÃO
    # =====================================================
    df = carregar_dados()
    df_filtrados = filtrar_fiis_descontados_com_qualidade(df)

    st.write(f"🕒 Atualizado em **{datetime.now().strftime('%d/%m/%Y')}**")

    fiis_achados = len(df_filtrados)

    df_top10 = (
        df_filtrados
        .sort_values("DY (12M) Acumulado", ascending=False)
        .head(15)
        .sort_values("P/VP")
        .head(10)
    )

    # =====================================================
    # TABS
    # =====================================================
    tab1, tab2 = st.tabs(
        ["📊 Top 10 FIIs", "📰 Notícias"]
    )

    # =====================================================
    # TAB 1 — TOP 10
    # =====================================================
    with tab1:

        if df_top10.empty:
            st.warning("Nenhum FII atende aos critérios hoje.")
        else:
            st.success(f"{fiis_achados} FIIs atendem aos critérios mínimos hoje")
            with st.expander("📌 Critérios mínimos para aprovação", expanded=False):

                st.markdown(
                    """
                    Um FII **só aparece no ranking** se atender **todos** os critérios abaixo:
                    
                    **📉 Preço**
                    - P/VP entre **0,80 e 1,00**
                    
                    **💰 Dividendos**
                    - DY 3 meses ≥ **2,4%**
                    - DY 6 meses ≥ **4,8%**
                    - DY 12 meses ≥ **9,6%**
                    
                    **📊 Liquidez e porte**
                    - Liquidez diária ≥ **R$ 1 milhão**
                    - Patrimônio líquido ≥ **R$ 500 milhões**
                    - Cotistas ≥ **10 mil**
                    """
                )

            for _, row in df_top10.iterrows():
                with st.container(border=True):

                    st.markdown(f"### {row['Fundos']}")
                    st.caption(f"Setor: {row['Setor']}")

                    c1, c2, c3 = st.columns(3)

                    c1.metric("P/VP", f"{row['P/VP']:.2f}")
                    c2.metric("Liquidez Diária", f"R$ {row['Liquidez Diária (milhões R$)']:.1f} mi")
                    c3.metric("Preço Atual", f"R$ {row['Preço Atual (R$)']:.2f}")

                    dy12 = row['DY (12M) Acumulado']
                    rendimento_mes = ((1 + dy12 / 100) ** (1 / 12) - 1) * 100

                    st.metric("Dividend Yield (12M)", f"{dy12:.1f}%")
                    st.markdown(
                        f"> Rendimento equivalente: <u>{rendimento_mes:.2f}%</u> ao mês",
                        unsafe_allow_html=True
                    )

                    # if dy12 > 15:
                    #     st.warning("⚠️ DY elevado — verifique sustentabilidade")

                    # if row["P/VP"] < 0.9:
                    #     st.success("📉 Negociado com desconto relevante")

                    ticker = row['Fundos'].split(" - ")[0]
                    st.markdown(
                        f"""
                        <a href="https://www.fundsexplorer.com.br/fiagros/{ticker}" target="_blank">
                            🔗 Explorar FII
                        </a>
                        """,
                        unsafe_allow_html=True
                    )
                    st.write('')

                    with st.expander("🔎 Detalhes do fundo"):
                        st.markdown(
                            f"""
                            - **Patrimônio Líquido:** R$ {row['Patrimônio Líquido (milhões R$)']:.0f} mi  
                            - **Cotistas:** {row['Num. Cotistas (milhares)']:.0f} mil  
                            - **Último Dividendo: R$ {row['Último Dividendo']:.2f}**  
                            - **DY (3M) Acumulado:** {row['DY (3M) Acumulado']:.1f}%  
                            - **DY (6M) Acumulado:** {row['DY (6M) Acumulado']:.1f}%  
                            """
                        )



    # =====================================================
    # TAB 3 — NOTÍCIAS
    # =====================================================
    with tab2:
        st.subheader("📰 Notícias recentes por FII")

        ticker_noticia = st.selectbox(
            "Selecione o FII",
            sorted(df["Fundos"].unique())
        )

        # Add a button to search news
        if st.button("Buscar notícias"):
            noticias = buscar_noticias(ticker_noticia)
        else:
            noticias = 'primeiro'

        st.caption("Notícias publicadas nos últimos 30 dias")


        if noticias == 'primeiro':
            st.info('Selecione o FII deseja buscar notícias e clique no botão acima.')
        else:
            if len(noticias) == 0:
                st.warning("Nenhuma notícia recente encontrada para este FII.")
            else:
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

