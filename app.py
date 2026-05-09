import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Terminal Quant IFR2",
    layout="wide"
)

# =========================================================
# FUNÇÃO BACKTEST
# =========================================================

def backtest_estrategia(ticker, periodo="10y"):

    try:

        df = yf.download(
            ticker,
            period=periodo,
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if df.empty or len(df) < 100:
            return None

        # =================================================
        # INDICADORES
        # =================================================

        df["IFR2"] = ta.rsi(df["Close"], length=2)
        df["EMA17"] = ta.ema(df["Close"], length=17)
        df["EMA20"] = ta.ema(df["Close"], length=20)
        df["VOL_MA20"] = df["Volume"].rolling(20).mean()

        df.dropna(inplace=True)

        # =================================================
        # FILTROS
        # =================================================

        df["Signal"] = (
            (df["IFR2"] < 25) &
            (df["EMA17"] > df["EMA20"]) &
            (df["Close"] > df["EMA17"]) &
            (df["Volume"] > df["VOL_MA20"])
        )

        trades = []

        in_position = False

        entry_price = 0
        stop_price = 0
        target_price = 0

        entry_date = None

        # =================================================
        # LOOP
        # =================================================

        for i in range(1, len(df)-1):

            # =============================================
            # ENTRADA
            # =============================================

            if not in_position and df["Signal"].iloc[i-1]:

                entry_price = float(df["Open"].iloc[i])

                stop_price = float(df["Low"].iloc[i-1])

                target_price = entry_price * 1.025

                risk = (
                    (entry_price - stop_price)
                    / entry_price
                ) * 100

                if risk <= 0:
                    continue

                in_position = True

                entry_date = df.index[i]

                continue

            # =============================================
            # SAÍDA
            # =============================================

            if in_position:

                low_atual = float(df["Low"].iloc[i])
                high_atual = float(df["High"].iloc[i])

                # STOP PRIMEIRO
                if low_atual <= stop_price:

                    trades.append({
                        "Resultado": 0,
                        "Gain (%)": -risk,
                        "Dias": (df.index[i] - entry_date).days
                    })

                    in_position = False

                # GAIN
                elif high_atual >= target_price:

                    trades.append({
                        "Resultado": 1,
                        "Gain (%)": 2.5,
                        "Dias": (df.index[i] - entry_date).days
                    })

                    in_position = False

                # EVITA OPERAÇÕES ETERNAS
                elif (df.index[i] - entry_date).days > 20:

                    resultado = (
                        (float(df["Close"].iloc[i]) - entry_price)
                        / entry_price
                    ) * 100

                    trades.append({
                        "Resultado": 1 if resultado > 0 else 0,
                        "Gain (%)": resultado,
                        "Dias": 20
                    })

                    in_position = False

        # =================================================
        # ESTATÍSTICAS
        # =================================================

        if len(trades) < 5:
            return None

        trades_df = pd.DataFrame(trades)

        total = len(trades_df)

        wins = len(trades_df[trades_df["Resultado"] == 1])

        losses = total - wins

        winrate = (wins / total) * 100

        media_gain = trades_df["Gain (%)"].mean()

        payoff = (
            trades_df[trades_df["Gain (%)"] > 0]["Gain (%)"].mean()
            /
            abs(
                trades_df[trades_df["Gain (%)"] < 0]["Gain (%)"].mean()
            )
            if losses > 0 else 0
        )

        expectativa = (
            (winrate / 100) * payoff
            -
            (1 - (winrate / 100))
        )

        tempo_medio = trades_df["Dias"].mean()

        # SCORE MAIS PROFISSIONAL
        score = (
            (winrate * 0.5)
            +
            (payoff * 25)
            +
            (expectativa * 100)
            +
            (min(total, 100) * 0.3)
        )

        # =============================================
        # SINAL ATUAL
        # =============================================

        sinal_agora = bool(df["Signal"].iloc[-1])

        return {

            "Ticker": ticker,

            "Trades": total,

            "Win Rate (%)": round(winrate, 2),

            "Payoff": round(payoff, 2),

            "Expectativa": round(expectativa, 2),

            "Média Gain (%)": round(media_gain, 2),

            "Tempo Médio": round(tempo_medio, 1),

            "Score": round(score, 2),

            "Sinal Hoje": "SIM" if sinal_agora else "NÃO"
        }

    except Exception:
        return None

# =========================================================
# INTERFACE
# =========================================================

st.title("📊 Terminal Quant IFR2 + EMA17/20")

st.markdown("""

### Regras do Setup

- IFR(2) abaixo de 25
- EMA17 acima da EMA20
- Preço acima da EMA17
- Volume acima da média de 20 períodos
- Entrada na abertura do candle seguinte
- Stop na mínima do candle do sinal
- Gain fixo de +2,5%

""")

# =========================================================
# LISTA MELHORADA
# =========================================================

tickers_default = """

PETR4.SA,
PRIO3.SA,
RECV3.SA,
RRRP3.SA,
VALE3.SA,
CSNA3.SA,
USIM5.SA,
GOAU4.SA,
EMBR3.SA,
WEGE3.SA,
SMFT3.SA,
LREN3.SA,
MGLU3.SA,
COGN3.SA,
YDUQ3.SA,
PETZ3.SA,
ALOS3.SA,
SOMA3.SA,
TOTS3.SA,
RADL3.SA,
BBAS3.SA,
BOVA11.SA,
SMAL11.SA,
IVVB11.SA,
NASD11.SA

"""

tickers_input = st.text_area(
    "Tickers:",
    tickers_default,
    height=300
)

periodo = st.selectbox(
    "Período do Backtest",
    ["2y", "5y", "10y"],
    index=2
)

# =========================================================
# BOTÃO
# =========================================================

if st.button("🚀 Executar Backtest"):

    lista_tickers = [
        t.strip().upper()
        for t in tickers_input.split(",")
        if t.strip()
    ]

    resultados = []

    progress = st.progress(0)

    status = st.empty()

    for idx, ticker in enumerate(lista_tickers):

        status.text(f"Analisando {ticker}...")

        resultado = backtest_estrategia(
            ticker,
            periodo
        )

        if resultado:
            resultados.append(resultado)

        progress.progress(
            (idx + 1) / len(lista_tickers)
        )

    status.text("Concluído.")

    # =====================================================
    # RESULTADOS
    # =====================================================

    if resultados:

        df_resultados = pd.DataFrame(resultados)

        df_resultados = df_resultados.sort_values(
            by="Score",
            ascending=False
        )

        tab1, tab2, tab3 = st.tabs([
            "🏆 Ranking",
            "📈 Sinais Atuais",
            "📋 Todos Resultados"
        ])

        # =================================================
        # RANKING
        # =================================================

        with tab1:

            st.subheader("Melhores Ativos")

            st.dataframe(
                df_resultados,
                use_container_width=True
            )

        # =================================================
        # SINAIS
        # =================================================

        with tab2:

            sinais = df_resultados[
                df_resultados["Sinal Hoje"] == "SIM"
            ]

            if len(sinais) > 0:

                st.success(
                    f"{len(sinais)} ativos em sinal hoje."
                )

                st.dataframe(
                    sinais.sort_values(
                        by="Score",
                        ascending=False
                    ),
                    use_container_width=True
                )

            else:

                st.warning(
                    "Nenhum ativo em sinal hoje."
                )

        # =================================================
        # GERAL
        # =================================================

        with tab3:

            st.dataframe(
                df_resultados.sort_values(
                    by="Win Rate (%)",
                    ascending=False
                ),
                use_container_width=True
            )

    else:

        st.error(
            "Nenhum resultado encontrado."
        )
