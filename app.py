import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

st.set_page_config(
    page_title="Scanner IFR2",
    layout="wide"
)

# =========================================================
# FUNÇÃO RSI 2
# =========================================================

def calcular_rsi(close, periodo=2):

    delta = close.diff()

    ganho = delta.clip(lower=0)

    perda = -delta.clip(upper=0)

    media_ganho = ganho.rolling(window=periodo).mean()

    media_perda = perda.rolling(window=periodo).mean()

    rs = media_ganho / media_perda

    rsi = 100 - (100 / (1 + rs))

    return rsi

# =========================================================
# FUNÇÃO BACKTEST
# =========================================================

def backtest_ativo(ticker, periodo):

    try:

        df = yf.download(
            ticker,
            period=periodo,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False
        )

        # =================================================
        # VERIFICAÇÕES
        # =================================================

        if df is None:
            return None

        if df.empty:
            return None

        # =================================================
        # REMOVE MULTIINDEX
        # =================================================

        if isinstance(df.columns, pd.MultiIndex):

            df.columns = df.columns.get_level_values(0)

        # =================================================
        # GARANTE COLUNAS
        # =================================================

        colunas_necessarias = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for coluna in colunas_necessarias:

            if coluna not in df.columns:
                return None

        # =================================================
        # CONVERTE NUMÉRICO
        # =================================================

        for coluna in colunas_necessarias:

            df[coluna] = pd.to_numeric(
                df[coluna],
                errors="coerce"
            )

        df.dropna(inplace=True)

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

        df.dropna(inplace=True)

        # =================================================
        # SINAL
        # =================================================

        df["SINAL"] = (
            (df["IFR2"] < 25)
            &
            (df["EMA17"] > df["EMA20"])
        )

        trades = []

        em_operacao = False

        preco_entrada = 0
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

                preco_entrada = float(
                    df["Open"].iloc[i]
                )

                stop = float(
                    df["Low"].iloc[i - 1]
                )

                alvo = preco_entrada * 1.025

                risco = (
                    (
                        preco_entrada - stop
                    )
                    / preco_entrada
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

        ganhos = len(
            [x for x in trades if x > 0]
        )

        taxa_acerto = (
            ganhos / total
        ) * 100

        media_resultado = np.mean(trades)

        score = (
            (taxa_acerto * 0.7)
            +
            (media_resultado * 10)
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

            "Média (%)": round(
                media_resultado,
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

    except Exception as erro:

        return {

            "Ticker": ticker,

            "Erro": str(erro)
        }

# =========================================================
# INTERFACE
# =========================================================

st.title(
    "📊 Scanner IFR2 + EMA17/20"
)

st.markdown("""

### Regras do Setup

- IFR2 abaixo de 25
- EMA17 acima da EMA20
- Entrada na abertura do candle seguinte
- Stop na mínima do candle sinal
- Gain fixo de 2,5%

""")

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

periodo = st.selectbox(
    "Período do Backtest",
    ["2y", "5y", "10y"],
    index=2
)

# =========================================================
# BOTÃO
# =========================================================

if st.button("Executar Scanner"):

    lista_tickers = [

        x.strip().upper()

        for x in entrada_tickers.split(",")

        if x.strip()
    ]

    resultados = []

    barra = st.progress(0)

    status = st.empty()

    total_tickers = len(lista_tickers)

    for indice, ticker in enumerate(lista_tickers):

        status.text(
            f"Analisando {ticker}..."
        )

        resultado = backtest_ativo(
            ticker,
            periodo
        )

        if resultado is not None:

            resultados.append(resultado)

        barra.progress(
            (indice + 1)
            / total_tickers
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
