import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="Scanner IFR2",
    layout="wide"
)

# =========================================================
# TÍTULO
# =========================================================

st.title("📊 Scanner IFR2 + EMA17/20")

st.markdown("""

### Regras do Setup

- IFR2 abaixo de 25
- EMA17 acima da EMA20
- Entrada na abertura do candle seguinte
- Stop na mínima do candle do sinal
- Gain de 2,5%

""")

# =========================================================
# FUNÇÃO RSI
# =========================================================

def calcular_rsi(close, period=2):

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period).mean()

    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi

# =========================================================
# BACKTEST
# =========================================================

def backtest(ticker, periodo):

    try:

        # =================================================
        # DOWNLOAD
        # =================================================

        df = yf.download(
            ticker,
            period=periodo,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False
        )

        # =================================================
        # VALIDAÇÕES
        # =================================================

        if df is None:
            return None

        if len(df) == 0:
            return None

        # =================================================
        # REMOVE MULTIINDEX
        # =================================================

        if isinstance(df.columns, pd.MultiIndex):

            df.columns = df.columns.get_level_values(0)

        # =================================================
        # GARANTE COLUNAS
        # =================================================

        colunas = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for coluna in colunas:

            if coluna not in df.columns:
                return None

        # =================================================
        # CONVERTE PARA NUMÉRICO
        # =================================================

        for coluna in colunas:

            df[coluna] = pd.to_numeric(
                df[coluna],
                errors="coerce"
            )

        # =================================================
        # REMOVE NAN
        # =================================================

        df = df.dropna()

        if len(df) < 50:
            return None

        # =================================================
        # INDICADORES
        # =================================================

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

        # =================================================
        # REMOVE NAN
        # =================================================

        df = df.dropna()

        # =================================================
        # SINAL
        # =================================================

        df["SINAL"] = (
            (df["IFR2"] < 25)
            &
            (df["EMA17"] > df["EMA20"])
        )

        # =================================================
        # VARIÁVEIS
        # =================================================

        trades = []

        em_operacao = False

        entrada = 0
        stop = 0
        alvo = 0
        risco = 0

        # =================================================
        # LOOP
        # =================================================

        for i in range(1, len(df)):

            # =============================================
            # ENTRADA
            # =============================================

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

            # =============================================
            # SAÍDA
            # =============================================

            if em_operacao:

                minima = float(
                    df["Low"].iloc[i]
                )

                maxima = float(
                    df["High"].iloc[i]
                )

                # STOP

                if minima <= stop:

                    trades.append(-risco)

                    em_operacao = False

                # GAIN

                elif maxima >= alvo:

                    trades.append(2.5)

                    em_operacao = False

        # =================================================
        # RESULTADOS
        # =================================================

        if len(trades) < 5:
            return None

        total = len(trades)

        ganhos = len([
            x for x in trades
            if x > 0
        ])

        taxa_acerto = (
            ganhos / total
        ) * 100

        media = np.mean(trades)

        score = (
            (taxa_acerto * 0.7)
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
                taxa_acerto,
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

    except Exception as erro:

        return {

            "Ticker": ticker,

            "Erro": str(erro)
        }

# =========================================================
# TICKERS
# =========================================================

tickers_padrao = """

PRIO3.SA,
RRRP3.SA,
RECV3.SA,
MGLU3.SA,
PETZ3.SA,
COGN3.SA,
YDUQ3.SA,
LREN3.SA,
ALOS3.SA,
SOMA3.SA,
SMFT3.SA,
EMBR3.SA,
WEGE3.SA,
PETR4.SA,
VALE3.SA,
BBAS3.SA,
SMAL11.SA,
NASD11.SA

"""

entrada_tickers = st.text_area(
    "Lista de Tickers",
    tickers_padrao,
    height=250
)

# =========================================================
# PERÍODO
# =========================================================

periodo = st.selectbox(
    "Período",
    ["2y", "5y", "10y"],
    index=1
)

# =========================================================
# EXECUTAR
# =========================================================

if st.button("🚀 Executar Scanner"):

    lista = [

        x.strip().upper()

        for x in entrada_tickers.split(",")

        if x.strip()
    ]

    resultados = []

    barra = st.progress(0)

    status = st.empty()

    total = len(lista)

    for indice, ticker in enumerate(lista):

        status.text(
            f"Analisando {ticker}..."
        )

        resultado = backtest(
            ticker,
            periodo
        )

        if resultado is not None:

            resultados.append(resultado)

        barra.progress(
            (indice + 1) / total
        )

    status.text("Concluído.")

    # =====================================================
    # RESULTADOS
    # =====================================================

    if len(resultados) > 0:

        df_resultados = pd.DataFrame(
            resultados
        )

        if "Score" in df_resultados.columns:

            df_resultados = (
                df_resultados
                .sort_values(
                    by="Score",
                    ascending=False
                )
            )

        # =================================================
        # ABAS
        # =================================================

        aba1, aba2 = st.tabs([
            "🏆 Ranking",
            "📈 Sinais Hoje"
        ])

        # =================================================
        # RANKING
        # =================================================

        with aba1:

            st.dataframe(
                df_resultados,
                use_container_width=True
            )

        # =================================================
        # SINAIS
        # =================================================

        with aba2:

            sinais = df_resultados[
                df_resultados[
                    "Sinal Hoje"
                ] == "SIM"
            ]

            if len(sinais) > 0:

                st.dataframe(
                    sinais,
                    use_container_width=True
                )

            else:

                st.warning(
                    "Nenhum sinal encontrado hoje."
                )

    else:

        st.error(
            "Nenhum resultado encontrado."
        )
