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

# Bancos
"BBAS3.SA","ITUB4.SA","ITSA4.SA","BBDC4.SA","BBDC3.SA","SANB11.SA",
"BPAC11.SA","BRSR6.SA","BMGB4.SA","PSSA3.SA","IRBR3.SA",

# Energia / Petróleo
"PETR4.SA","PETR3.SA","PRIO3.SA","RECV3.SA","RRRP3.SA",
"UGPA3.SA","VBBR3.SA",

# Mineração
"VALE3.SA","CSNA3.SA","USIM5.SA","GGBR4.SA","GOAU4.SA","BRAP4.SA",

# Papel e Celulose
"SUZB3.SA","KLBN11.SA","KLBN4.SA","KLBN3.SA",

# Energia elétrica
"CMIG4.SA","TAEE11.SA","CPFE3.SA","EQTL3.SA","ELET3.SA","ELET6.SA",
"ALUP11.SA","TRPL4.SA","NEOE3.SA","ENGI11.SA",

# Saneamento
"SBSP3.SA","SAPR11.SA","CSMG3.SA",

# Consumo
"MGLU3.SA","LREN3.SA","ASAI3.SA","PCAR3.SA","CRFB3.SA",
"ARZZ3.SA","SOMA3.SA",

# Saúde
"HAPV3.SA","QUAL3.SA","FLRY3.SA","RDOR3.SA",

# Construção
"MRVE3.SA","EZTC3.SA","CYRE3.SA","DIRR3.SA","TEND3.SA",

# Tecnologia
"TOTS3.SA","POSI3.SA","LWSA3.SA",

# Transporte
"RAIL3.SA","CCRO3.SA","ECOR3.SA","AZUL4.SA","GOLL4.SA",

# Industriais
"WEGE3.SA","ROMI3.SA","KEPL3.SA","RAPT4.SA",

# Alimentos
"JBSS3.SA","BRFS3.SA","MRFG3.SA","BEEF3.SA",

# ETFs
"BOVA11.SA","SMAL11.SA","IVVB11.SA","DIVO11.SA",

# FIIs
"KNRI11.SA","HGLG11.SA","MXRF11.SA","XPML11.SA",
"VISC11.SA","XPLG11.SA","HGRE11.SA","BRCO11.SA",

# BDRs
"AAPL34.SA","MSFT34.SA","GOGL34.SA","AMZO34.SA",
"META34.SA","TSLA34.SA","NVDC34.SA",
"JPMC34.SA","BOAC34.SA","WFCB34.SA",
"WALM34.SA","COST34.SA","PEPB34.SA","KOCA34.SA",
"JNJB34.SA","PFEF34.SA","MRCK34.SA",
"DISB34.SA","NKEE34.SA","SBUX34.SA"

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
