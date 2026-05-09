import streamlit as st
        )

        if resultado is not None:
            resultados.append(resultado)

        barra.progress(
            (i + 1) / len(TICKERS)
        )

    if len(resultados) > 0:

        df_resultados = pd.DataFrame(resultados)

        if "Score" in df_resultados.columns:

            df_resultados = df_resultados.sort_values(
                by="Score",
                ascending=False
            )

        tab1, tab2 = st.tabs([
            "🏆 Ranking",
            "📈 Sinais Hoje"
        ])

        with tab1:

            st.dataframe(
                df_resultados,
                use_container_width=True
            )

        with tab2:

            sinais = df_resultados[
                df_resultados["Sinal Hoje"] == "SIM"
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
