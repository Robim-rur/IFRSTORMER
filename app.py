import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="Scanner IFR2",
    layout="wide"
)

# =====================================================
# TÍTULO
# =====================================================

st.title("📊 Scanner IFR2 + EMA17/20")

st.markdown("""

### Regras do Setup

- IFR2 abaixo de 25
- EMA17 acima da EMA20
- Entrada na abertura do candle seguinte
- Stop na mínima do candle sinal
- Gain fixo de 2,5%

""")

# =====================================================
# RSI
# =====================================================

def calcular_rsi(close, period=2):

    delta = close.diff()

    gain = delta.where(delta > 0, 0)

    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()

    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi

# =====================================================
# BACKTEST
# =====================================================

def backtest(ticker, periodo):

    try:

        df = yf.download(
            ticker,
            period=periodo,
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False
        )

        if df.empty:
            return None

        # =============================================
        # REMOVE MULTIINDEX
        # =============================================

        if isinstance(df.columns, pd.MultiIndex):

            df.columns = df.columns.get_level_values(0)

        # =============================================
        # GARANTE DADOS
        # =============================================

        colunas = [
            "Open",
            "High",
            "Low",
            "Close"
        ]

        for coluna in colunas:

            if coluna not in df.columns:
                return None

        df = df[colunas].copy()

        df.dropna(inplace=True)

        if len(df) < 30:
            return None

        # =============================================
        # INDICADORES
        # =============================================

        df["IFR2"] = calcular_rsi(
            df["Close"],
            2
        )

        df["EMA17"] = (
            df["Close"]
            .ewm(
                span=17,
                adjust=False
            )
            .mean()
        )

        df["EMA20"] = (
            df["Close"]
            .ewm(
                span=20,
                adjust=False
            )
            .mean()
        )

        df.dropna(inplace=True)

        # =============================================
        # SINAL
        # =============================================

        df["SINAL"] = (
            (df["IFR2"] < 25)
            &
            (df["EMA17"] > df["EMA20"])
        )

        # =============================================
        # VARIÁVEIS
        # =============================================

        resultados = []

        em_operacao = False

        entrada = 0
        stop = 0
        alvo = 0
        risco = 0

        # =============================================
        # LOOP
        # =============================================

        for i in range(1, len(df)):

            # =========================================
            # ENTRADA
            # =========================================

            if (
                em_operacao is False
                and df["SINAL"].iloc[i - 1]
            ):

                entrada = float(
                    df["Open"].iloc[i]
                )

                stop = float(
                    df["Low"].iloc[i - 1]
                )

                alvo = entrada * 1.025

                risco = (
                    (
                        entrada - stop
                    )
                    / entrada
                ) * 100

                if risco <= 0:
                    continue

                em_operacao = True

                continue

            # =========================================
            # SAÍDA
            # =========================================

            if em_operacao:

                minima = float(
                    df["Low"].iloc[i]
                )

                maxima = float(
                    df["High"].iloc[i]
                )

                # STOP

                if minima <= stop:

                    resultados.append(-risco)

                    em_operacao = False

                # GAIN

                elif maxima >= alvo:

                    resultados.append(2.5)

                    em_operacao = False

        # =============================================
        # ESTATÍSTICAS
        # =============================================

        if len(resultados) < 5:
            return None

        total = len(resultados)

        ganhos = len([
            x for x in resultados
            if x > 0
        ])

        taxa = (
            ganhos / total
        ) * 100

        media = np.mean(resultados)

        score = (
            (taxa * 0.7)
            +
            (media * 10)
            +
            (total * 0.2)
        )

        sinal_hoje = bool(
            df["SINAL"].iloc[-1]
        )

        return {

            "Ticker": ticker,

            "Trades": total,

            "Acerto (%)": round(
                taxa,
                2
            ),

            "Media (%)": round(
                media,
                2
            ),

            "Score": round(
                score,
                2
            ),

            "Sinal Hoje": (
                "SIM"
                if sinal_hoje
                else "NAO"
            )
        }

    except:

        return None

# =====================================================
# TICKERS
# =====================================================

tickers_padrao = """



"RRRP3","ALOS3","ALPA4","ABEV3","ARZZ3","ASAI3","AZUL4",
"B3SA3","BBAS3","BBDC3","BBDC4","BBSE3","BEEF3","BPAC11",
"BRAP4","BRFS3","BRKM5","CCRO3","CMIG4","CMIN3","COGN3",
"CPFE3","CPLE6","CRFB3","CSAN3","CSNA3","CYRE3","DXCO3",
"EGIE3","ELET3","ELET6","EMBR3","ENEV3","ENGI11","EQTL3",
"EZTC3","FLRY3","GGBR4","GOAU4","GOLL4","HAPV3","HYPE3",
"ITSA4","ITUB4","JBSS3","KLBN11","LREN3","LWSA3","MGLU3",
"MRFG3","MRVE3","MULT3","NTCO3","PETR3","PETR4","PRIO3",
"RADL3","RAIL3","RAIZ4","RENT3","RECV3","SANB11","SBSP3",
"SLCE3","SMTO3","SUZB3","TAEE11","TIMS3","TTEN3","TOTS3",
"TRPL4","UGPA3","USIM5","VALE3","VIVT3","VIVA3","WEGE3",
"YDUQ3","AURE3","BHIA3","CASH3","CVCB3","DIRR3","ENAT3",
"GMAT3","IFCM3","INTB3","JHSF3","KEPL3","MOVI3","ORVR3",
"PETZ3","PLAS3","POMO4","POSI3","RANI3","RAPT4","STBP3",
"TEND3","TUPY3","BRSR6","CXSE3",

"AAPL34","AMZO34","GOGL34","MSFT34","TSLA34","META34",
"NFLX34","NVDC34","MELI34","BABA34","DISB34","PYPL34",
"JNJB34","PGCO34","KOCH34","VISA34","WMTB34","NIKE34",
"ADBE34","AVGO34","CSCO34","COST34","CVSH34","GECO34",
"GSGI34","HDCO34","INTC34","JPMC34","MAEL34","MCDP34",
"MDLZ34","MRCK34","ORCL34","PEP334","PFIZ34","PMIC34",
"QCOM34","SBUX34","TGTB34","TMOS34","TXN34","UNHH34",
"UPSB34","VZUA34","ABTT34","AMGN34","AXPB34","BAOO34",
"C2OL34","HONB34","BICE34","BERK34","GOGL35",

"BOVA11","IVVB11","SMAL11","HASH11","GOLD11","DIVO11",
"NDIV11","SPUB11",

"GARE11","HGLG11","XPLG11","VILG11","BRCO11","BTLG11",
"XPML11","VISC11","HSML11","MALL11","KNRI11","JSRE11",
"PVBI11","HGRE11","MXRF11","KNCR11","KNIP11","CPTS11",
"IRDM11","TGAR11","TRXF11","HGRU11","ALZR11","XPCA11",
"VGIA11","RBRR11","KNSC11","CACR11","HABT11","DEVA11",
"HGCR11","MCCI11","RECR11","VRTA11","BCFF11","HFOF11",
"XPSF11","RBRP11","RBRF11","URIT11","RZTR11","RURA11",
"VGIR11","CVBI11","UTLL11","GGRC11","HERT11","AUVP11","IEEX11"

"""

entrada = st.text_area(
    "Lista de Tickers",
    tickers_padrao,
    height=250
)

# =====================================================
# PERÍODO
# =====================================================

periodo = st.selectbox(
    "Período",
    ["2y", "5y", "10y"],
    index=1
)

# =====================================================
# BOTÃO
# =====================================================

if st.button("🚀 Executar Scanner"):

    lista = [

        x.strip().upper()

        for x in entrada.split(",")

        if x.strip()
    ]

    resultados_finais = []

    barra = st.progress(0)

    total = len(lista)

    for i, ticker in enumerate(lista):

        resultado = backtest(
            ticker,
            periodo
        )

        if resultado:

            resultados_finais.append(
                resultado
            )

        barra.progress(
            (i + 1) / total
        )

    # =============================================
    # RESULTADOS
    # =============================================

    if len(resultados_finais) > 0:

        df_final = pd.DataFrame(
            resultados_finais
        )

        df_final = df_final.sort_values(
            by="Score",
            ascending=False
        )

        tab1, tab2 = st.tabs([
            "🏆 Ranking",
            "📈 Sinais Hoje"
        ])

        # =========================================
        # RANKING
        # =========================================

        with tab1:

            st.dataframe(
                df_final,
                use_container_width=True
            )

        # =========================================
        # SINAIS
        # =========================================

        with tab2:

            sinais = df_final[
                df_final["Sinal Hoje"]
                == "SIM"
            ]

            if len(sinais) > 0:

                st.dataframe(
                    sinais,
                    use_container_width=True
                )

            else:

                st.warning(
                    "Nenhum sinal hoje."
                )

    else:

        st.error(
            "Nenhum resultado encontrado."
        )
