"""Explorador SQL sobre AWS Athena. La protección real es el usuario IAM de solo lectura
(ver terraform/iam_app.tf): no puede escribir, borrar ni crear nada, pase lo que pase acá."""
import streamlit as st

import aws_athena
import config

EJEMPLOS = {
    "Ranking del último mes": "SELECT * FROM mart_ranking_ultimo_mes ORDER BY puesto",
    "Serie completa de Transporte": "SELECT mes, variacion_m FROM mart_variacion_categorias "
                                    "WHERE categoria = 'transporte' ORDER BY mes",
    "Promedio de variación por categoría (todo el período)": (
        "SELECT categoria, round(avg(variacion_m), 2) AS variacion_promedio\n"
        "FROM mart_variacion_categorias\nGROUP BY categoria\nORDER BY variacion_promedio DESC"
    ),
    "Meses en que Regulados subió más de 8% (LAG)": (
        "WITH t AS (\n"
        "    SELECT mes, variacion_m, lag(variacion_m) OVER (ORDER BY mes) AS mes_anterior\n"
        "    FROM mart_variacion_categorias WHERE categoria = 'regulados'\n"
        ")\nSELECT mes, variacion_m, mes_anterior FROM t WHERE variacion_m > 8 ORDER BY mes"
    ),
    "Top 3 categorías por mes (RANK)": (
        "SELECT * FROM (\n"
        "    SELECT mes, categoria, variacion_m,\n"
        "           rank() OVER (PARTITION BY mes ORDER BY variacion_m DESC) AS puesto\n"
        "    FROM mart_variacion_categorias\n"
        ")\nWHERE puesto <= 3 ORDER BY mes DESC, puesto"
    ),
}

st.set_page_config(page_title="Explorador SQL", page_icon="🔎", layout="wide")

st.title("Explorador SQL")
st.markdown(f"Consultá con SQL el IPC por categoría (Núcleo, Regulados, Estacionales y las 9 divisiones "
           f"de consumo). Corre sobre **AWS Athena** en solo lectura: una sola sentencia `SELECT` por vez, "
           f"hasta {aws_athena.MAX_FILAS} filas y {aws_athena.TIMEOUT_S:g} segundos.")

if not config.configurado():
    config.mensaje_no_configurado()
    st.stop()

nombre = st.selectbox("Ejemplos", list(EJEMPLOS), index=0)
ejemplo_nuevo = st.session_state.get("_ejemplo") != nombre
if ejemplo_nuevo:
    st.session_state["_ejemplo"] = nombre
    st.session_state["sql"] = EJEMPLOS[nombre]

sql = st.text_area("Tu consulta", key="sql", height=220)

if st.button("Ejecutar", type="primary") or ejemplo_nuevo:
    cliente = config.cliente_athena()
    try:
        resultado = aws_athena.ejecutar(cliente, sql, config.BASE, config.WORKGROUP)
        st.session_state["resultado"], st.session_state["error"] = resultado, None
    except aws_athena.ConsultaRechazada as error:
        st.session_state["error"] = str(error)

if st.session_state.get("error"):
    st.error(st.session_state["error"])
elif st.session_state.get("resultado") is not None:
    res = st.session_state["resultado"]
    st.caption(f"{len(res.tabla)} filas" + (f" (se muestran las primeras {aws_athena.MAX_FILAS})" if res.truncado else ""))
    st.dataframe(res.tabla, hide_index=True, width="stretch")
