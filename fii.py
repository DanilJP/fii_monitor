import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import feedparser
from datetime import datetime, timedelta
from urllib.parse import quote

import streamlit_analytics as st_analytics

# =====================================================
# CONFIG STREAMLIT
# =====================================================
st.set_page_config(
    page_title="FIIs Monitor",
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
st.title("📊 FIIs Monitor")

st.caption(
    "Seleção diária de FIIs com análises, simuladores e notícias em um só lugar."
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    [
        "📊 Top 10 Descontados",
        "🏦 Grandes FIIs",
        "💸 FIIs de Entrada",
        "🧠 Screener Personalizado",
        "⚖️ Comparador de FIIs",
        "📰 Notícias",
        "🔁 Simluador de Reivestimento",
        "💼 Simulador de Carteira"
    ]
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

        with st.expander(f"📋 Demais FIIs aprovados nos critérios - {len(df_filtrados)} FIIs", expanded=False):
            fiis = sorted(df_filtrados["Fundos"].unique())

            cols = st.columns(3)

            for i, fii in enumerate(fiis):
                cols[i % 3].markdown(f"- {fii}")

# =====================================================
# TAB — GRANDES FIIs
# =====================================================

with tab2:
    st.subheader("🏦 Grandes FIIs do Mercado")
    st.caption("FIIs com maior patrimônio e alta relevância no mercado.")

    df_grandes = (
        df.sort_values("Patrimônio Líquido (milhões R$)", ascending=False)
        .head(5)
    )

    for _, row in df_grandes.iterrows():
        with st.container(border=True):
            st.markdown(f"### {row['Fundos']}")
            st.caption(f"Setor: {row['Setor']}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Preço", f"R$ {row['Preço Atual (R$)']:.2f}")
            c2.metric("P/VP", f"{row['P/VP']:.2f}")
            c3.metric("Liquidez", f"R$ {row['Liquidez Diária (milhões R$)']:.1f} mi")

            st.metric(
                "Patrimônio Líquido",
                f"R$ {(row['Patrimônio Líquido (milhões R$)']/1000):.2f} bi"
            )

            ticker = row["Fundos"].split(" - ")[0]
            st.markdown(
                f"""
                <a href="https://www.fundsexplorer.com.br/funds/{ticker}" target="_blank">
                    🔗 Explorar FII
                </a>
                """,
                unsafe_allow_html=True
            )
            st.write('')
            with st.expander("🔎 Detalhes do fundo"):
                st.markdown(
                    f"""
                    - **Cotistas:** {row['Num. Cotistas (milhares)']:.0f} mil  
                    - **Último Dividendo: R$ {row['Último Dividendo']:.2f}**  
                    - **DY (3M) Acumulado:** {row['DY (3M) Acumulado']:.1f}%  
                    - **DY (6M) Acumulado:** {row['DY (6M) Acumulado']:.1f}%  
                    """
                )


# =====================================================
# TAB — FIIs DE ENTRADA
# =====================================================
with tab3:
    st.subheader("💸 FIIs de Entrada (até R$ 30)")
    st.caption("Fundos com cotas mais acessíveis e bom histórico de dividendos.")

    df_entrada = (
        df[df["Preço Atual (R$)"] <= 30]
        .sort_values("DY (12M) Acumulado", ascending=False)
        .head(5)
    )

    for _, row in df_entrada.iterrows():
        with st.container(border=True):
            st.markdown(f"### {row['Fundos']}")
            st.caption(f"Setor: {row['Setor']}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Preço", f"R$ {row['Preço Atual (R$)']:.2f}")
            c2.metric("P/VP", f"{row['P/VP']:.2f}")
            c3.metric("DY 12M", f"{row['DY (12M) Acumulado']:.1f}%")

            ticker = row["Fundos"].split(" - ")[0]
            st.markdown(
                f"""
                <a href="https://www.fundsexplorer.com.br/funds/{ticker}" target="_blank">
                    🔗 Ver no Funds Explorer
                </a>
                """,
                unsafe_allow_html=True
            )
            st.write('')


# =====================================================
# TAB — SCREENER PERSONALIZADO
# =====================================================
with tab4:
    st.subheader("🧠 Screener Personalizado de FIIs")
    st.caption("Crie seus próprios filtros para encontrar FIIs que façam sentido para você.")

    c1, c2, c3 = st.columns(3)

    pv_min, pv_max = c1.slider("P/VP", 0.5, 1.5, (0.8, 1.0))
    dy_min = c2.slider("DY 12M mínimo (%)", 5.0, 20.0, 9.0)
    preco_max = c3.slider("Preço máximo da cota (R$)", 5.0, 150.0, 100.0)

    c4, c5, c6 = st.columns(3)
    liquidez_min = c4.slider("Liquidez mínima (R$ mi)", 0.5, 10.0, 1.0)
    pl_min = c5.slider("Patrimônio mínimo (R$ mi)", 100.0, 10_000.0, 500.0)
    cotistas_min = c6.slider("Cotistas mínimos (mil)", 1.0, 200.0, 10.0)

    df_screener = df[
        (df["P/VP"].between(pv_min, pv_max)) &
        (df["DY (12M) Acumulado"] >= dy_min) &
        (df["Preço Atual (R$)"] <= preco_max) &
        (df["Liquidez Diária (milhões R$)"] >= liquidez_min) &
        (df["Patrimônio Líquido (milhões R$)"] >= pl_min) &
        (df["Num. Cotistas (milhares)"] >= cotistas_min)
    ].sort_values("DY (12M) Acumulado", ascending=False)

    st.divider()
    st.success(f"{len(df_screener)} FIIs encontrados")

    st.dataframe(
        df_screener[
            [
                "Fundos",
                "Setor",
                "Preço Atual (R$)",
                "P/VP",
                "DY (12M) Acumulado",
                "Liquidez Diária (milhões R$)"
            ]
        ],
        use_container_width=True
    )

# =====================================================
# TAB 5 — COMPARADOR DE FIIs
# =====================================================
with tab5:
    st.subheader("⚖️ Comparador de FIIs")
    st.caption("Compare dois FIIs e veja quem vence em cada métrica.")

    c1, c2 = st.columns(2)
    fii_a = c1.selectbox("FII A", sorted(df["Fundos"].unique()), key="fii_a")
    fii_b = c2.selectbox("FII B", sorted(df["Fundos"].unique()), key="fii_b")

    if fii_a != fii_b:
        a = df[df["Fundos"] == fii_a].iloc[0]
        b = df[df["Fundos"] == fii_b].iloc[0]

        pontos_a = 0
        pontos_b = 0

        comparacao = [
            ("Preço da cota (menor melhor)", a["Preço Atual (R$)"], b["Preço Atual (R$)"], False),
            ("P/VP (menor melhor)", a["P/VP"], b["P/VP"], False),
            ("DY 12M (maior melhor)", a["DY (12M) Acumulado"], b["DY (12M) Acumulado"], True),
            ("Liquidez (maior melhor)", a["Liquidez Diária (milhões R$)"], b["Liquidez Diária (milhões R$)"], True),
            ("Patrimônio (maior melhor)", a["Patrimônio Líquido (milhões R$)"], b["Patrimônio Líquido (milhões R$)"], True),
        ]

        st.divider()

        for nome, va, vb, maior_melhor in comparacao:
            if va == vb:
                vencedor = "Empate"
            elif maior_melhor:
                vencedor = fii_a if va > vb else fii_b
            else:
                vencedor = fii_a if va < vb else fii_b

            if vencedor == fii_a:
                pontos_a += 1
            elif vencedor == fii_b:
                pontos_b += 1

            st.markdown(
                f"""
                **{nome}**  
                - {fii_a}: `{va:.2f}`  
                - {fii_b}: `{vb:.2f}`  
                🏆 **Vencedor:** {vencedor}
                """
            )
            st.divider()

        # Resultado final
        st.subheader("🏁 Resultado final")

        if pontos_a > pontos_b:
            st.success(f"✅ **{fii_a} vence por {pontos_a} x {pontos_b}**")
        elif pontos_b > pontos_a:
            st.success(f"✅ **{fii_b} vence por {pontos_b} x {pontos_a}**")
        else:
            st.info(f"⚖️ **Empate técnico: {pontos_a} x {pontos_b}**")

    else:
        st.info("Selecione dois FIIs diferentes para comparar.")



# =====================================================
# TAB 3 — NOTÍCIAS
# =====================================================
with tab6:
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

# =====================================================
# TAB 3 — SIMULADOR DE REINVESTIMENTO
# =====================================================
with tab7:
    df_reinvestimento = df.copy()
    st.subheader("🔁 Simulador de Reinvestimento de Dividendos")

    st.caption(
        "Calcule quantas cotas de um FII são necessárias para que "
        "os dividendos mensais comprem uma nova cota do mesmo fundo."
    )

    fii_simulador = st.selectbox(
        "Selecione o FII",
        df_reinvestimento["Fundos"].unique(),key="fii_simulador"
    )

    row = df_reinvestimento[df_reinvestimento["Fundos"] == fii_simulador].iloc[0]

    preco = row["Preço Atual (R$)"]
    dy12 = row["DY (12M) Acumulado"]

    dividendo_mensal_por_cota = preco * (dy12 / 100) / 12
    import math
    cotas_necessarias = math.ceil(preco / dividendo_mensal_por_cota)

    colunas_tab3 = st.columns(3)
    colunas_tab3[0].metric("Preço da cota", f"R$ {preco:.2f}")
    colunas_tab3[1].metric(
        "Dividendo mensal por cota",
        f"R$ {dividendo_mensal_por_cota:.2f}"
    )
    valor_necessario_investir = cotas_necessarias * preco
    colunas_tab3[2].metric(
        "Valor necessário para comprar 1 cota",
        f"R$ {valor_necessario_investir:.2f}"
    )

    st.divider()

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
# TAB 4 — MINHA CARTEIRA
# =====================================================
with tab8:
    st.subheader("💼 Simulação rápida da sua carteira de FIIs")
    st.caption(
        "Informe os FIIs e a quantidade de cotas para calcular "
        "renda mensal estimada e DY da carteira."
    )

    # Seleção dos FIIs
    fiis_selecionados = st.multiselect(
        "Selecione os FIIs da sua carteira",
        options=sorted(df["Fundos"].unique())
    )

    if not fiis_selecionados:
        st.info("Selecione ao menos um FII para começar.")
    else:
        dados_carteira = []

        for fii in fiis_selecionados:
            row = df[df["Fundos"] == fii].iloc[0]

            qtd = st.number_input(
                f"Quantidade de cotas — {fii}",
                min_value=0,
                step=1,
                key=f"qtd_{fii}"
            )

            if qtd > 0:
                preco = row["Preço Atual (R$)"]
                dy12 = row["DY (12M) Acumulado"]

                valor_aplicado = qtd * preco
                dividendo_mensal = valor_aplicado * (dy12 / 100) / 12

                dados_carteira.append({
                    "FII": fii,
                    "Quantidade": qtd,
                    "Preço Atual": preco,
                    "Valor Aplicado": valor_aplicado,
                    "DY 12M (%)": dy12,
                    "Dividendo Mensal (R$)": dividendo_mensal
                })

        if dados_carteira:
            df_carteira = pd.DataFrame(dados_carteira)

            total_investido = df_carteira["Valor Aplicado"].sum()
            total_div_mensal = df_carteira["Dividendo Mensal (R$)"].sum()

            dy_mensal_carteira = (total_div_mensal / total_investido) * 100
            dy_anual_carteira = dy_mensal_carteira * 12

            st.divider()

            c1, c2, c3 = st.columns(3)
            c1.metric("Valor investido", f"R$ {total_investido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c2.metric("Renda mensal estimada", f"R$ {total_div_mensal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c3.metric("DY mensal da carteira", f"{dy_mensal_carteira:.2f}%")

            st.metric("DY anual estimado da carteira", f"{dy_anual_carteira:.2f}%")

            st.divider()

            st.dataframe(
                df_carteira.style.format({
                    "Preço Atual": "R$ {:.2f}",
                    "Valor Aplicado": "R$ {:.2f}",
                    "Dividendo Mensal (R$)": "R$ {:.2f}",
                    "DY 12M (%)": "{:.2f}%"
                }),
                use_container_width=True
            )

            st.caption(
                "⚠️ Valores estimados com base no DY histórico (12M). "
                "Dividendos podem variar."
            )


