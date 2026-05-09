import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="IFR2 Scanner",
    layout="wide"
)

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
            auto_adjust=True
        )

        # =============================================
        # AJUSTE MULTIINDEX
        # =============================================

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty:
            return None

        if len(df) < 50:
            return None

        # =============================================
        # INDICADORES
        # =============================================

        df["IFR2"] = calcular_rsi(df["Close"], 2)

        df["EMA17"] = df["Close"].ewm(
            span=17,
            adjust=False
        ).mean()

        df["EMA20"] = df["Close"].ewm(
            span=20,
            adjust=False
        ).mean()

        df.dropna(inplace=True)

        # =============================================
        # SINAL
        # =============================================

        df["Signal"] = (
            (df["IFR2"] < 25)
            &
            (df["EMA17"] > df["EMA20"])
        )

        trades = []

        in_position = False

        for i in range(1, len(df)-1):

            # =========================================
            # ENTRADA
            # =========================================

            if (
                not in_position
                and df["Signal"].iloc[i-1]
            ):

                entry = float(df["Open"].iloc[i])

                stop = float(df["Low"].iloc[i-1])

                target = entry * 1.025

                risk = (
                    (entry - stop)
                    / entry
                ) * 100

                if risk <= 0:
                    continue

                in_position = True

                continue

            # =========================================
            # SAÍDA
            # =========================================

            if in_position:

                low = float(df["Low"].iloc[i])

                high = float(df["High"].iloc[i])

                # LOSS

                if low <= stop:

                    trades.append(-risk)

                    in_position = False

                # GAIN

                elif high >= target:

                    trades.append(2.5)

                    in_position = False

        # =============================================
        # ESTATÍSTICAS
        # =============================================

        if len(trades) < 5:
            return None

        total = len(trades)

        wins = len([x for x in trades if x > 0])

        winrate = (wins / total) * 100

        media = np.mean(trades)

        score = (
            (winrate * 0.7)
            +
            (media * 10)
            +
            (total * 0.2)
        )

        sinal_hoje = bool(
            df["Signal"].iloc[-1]
        )

        return {

            "Ticker": ticker,

            "Trades": total,

            "Win Rate (%)": round(
                winrate,
                2
            ),

            "Média (%)": round(
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
                else "NÃO"
            )
        }

    except Exception as e:

        return {
            "Ticker": ticker,
            "Erro": str(e)
        }

# =====================================================
# INTERFACE
# =====================================================

st.title(
    "📊 Scanner IFR2 + EMA17/20"
)

st.markdown("""

### Regras

- IFR2 abaixo de 25
- EMA17 acima da EMA20
- Entrada na abertura seguinte
- Stop na mínima do candle sinal
- Gain de 2,5%

""")

# =====================================================
# TICKERS
# =====================================================

tickers_default = """

PRIO3.SA,
RRRP3.SA,
RECV3.SA,
MGLU3.SA,
PETZ3.SA,
COGN3.SA,
YDUQ3.SA,
SMFT3.SA,
LREN3.SA,
ALOS3.SA,
SOMA3.SA,
EMBR3.SA,
WEGE3.SA,
PETR4.SA,
VALE3.SA,
BBAS3.SA,
SMAL11.SA,
NASD11.SA

"""

tickers = st.text_area(
    "Tickers",
    tickers_default,
    height=250
)

periodo = st.selectbox(
    "Período",
    ["2y", "5y", "10y"],
    index=2
)

# =====================================================
# BOTÃO
# =====================================================

if st.button("Executar Scanner"):

    lista = [

        x.strip().upper()

        for x in tickers.split(",")

        if x.strip()
    ]

    resultados = []

    progresso = st.progress(0)

    for i, ticker in enumerate(lista):

        resultado = backtest(
            ticker,
            periodo
        )

        if resultado:
            resultados.append(resultado)

        progresso.progress(
            (i + 1) / len(lista)
        )

    # =============================================
    # RESULTADOS
    # =============================================

    if resultados:

        df_resultado = pd.DataFrame(
            resultados
        )

        if "Score" in df_resultado.columns:

            df_resultado = (
                df_resultado
                .sort_values(
                    by="Score",
                    ascending=False
                )
            )

        tab1, tab2 = st.tabs([
            "🏆 Ranking",
            "📈 Sinais"
        ])

        with tab1:

            st.dataframe(
                df_resultado,
                use_container_width=True
            )

        with tab2:

            sinais = df_resultado[
                df_resultado["Sinal Hoje"]
                == "SIM"
            ]

            st.dataframe(
                sinais,
                use_container_width=True
            )

    else:

        st.error(
            "Nenhum resultado encontrado."
        )
    else:

        st.error(
            "Nenhum resultado encontrado."
        )
