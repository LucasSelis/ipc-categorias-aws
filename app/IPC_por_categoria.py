"""¿Qué rubro empuja la inflación este mes? Panel + Explorador SQL, sobre AWS Athena."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import aws_athena
import config

ETIQUETAS = {
    "alimentos_y_bebidas": "Alimentos y bebidas", "bebidas_alcoholicas_y_tabaco": "Bebidas alcohólicas y tabaco",
    "transporte": "Transporte", "educacion": "Educación", "salud": "Salud", "comunicaciones": "Comunicaciones",
    "hoteles_y_restaurantes": "Hoteles y restaurantes", "recreacion_y_cultura": "Recreación y cultura",
    "bienes_y_servicios_varios": "Bienes y servicios varios",
}

st.set_page_config(page_title="IPC por categoría", page_icon="🛒", layout="wide")

st.title("¿Qué rubro empuja la inflación este mes?")
st.markdown(
    "El INDEC no solo publica el IPC general: también lo abre por categoría de consumo "
    "(Alimentos, Transporte, Salud, ...) y por rigidez de precios (Núcleo, Regulados, Estacionales). "
    "Este panel construye ese detalle con SQL sobre **AWS Athena**, alimentado por un pipeline "
    "serverless (Lambda + S3 + Glue), todo con Terraform."
)
st.page_link("pages/1_Explorador_SQL.py", label="Probá tus propias consultas SQL sobre estos datos", icon="🔎")

if not config.configurado():
    config.mensaje_no_configurado()
    st.stop()

cliente = config.cliente_athena()


@st.cache_data(ttl=1800)
def leer(nombre_tabla: str) -> pd.DataFrame:
    return aws_athena.ejecutar(cliente, f"SELECT * FROM {nombre_tabla}", config.BASE, config.WORKGROUP).tabla


try:
    ranking = leer("mart_ranking_ultimo_mes")
    variaciones = leer("mart_variacion_categorias")
except Exception as error:  # boto3/Athena pueden fallar de muchas formas (permisos, workgroup, red)
    st.error(f"No pude consultar Athena: {error}")
    st.stop()

if ranking.empty:
    st.info("Todavía no hay datos cargados (el pipeline corre una vez por mes).")
    st.stop()

ranking["variacion_m"] = ranking["variacion_m"].astype(float)
ranking["categoria"] = ranking["categoria"].map(lambda c: ETIQUETAS.get(c, c))
mes = ranking["mes"].iloc[0]

st.subheader(f"Ranking del último mes publicado ({mes})")
fig = go.Figure(go.Bar(x=ranking["variacion_m"], y=ranking["categoria"], orientation="h",
                       marker_color=["#c0392b" if v > 0 else "#2980b9" for v in ranking["variacion_m"]]))
fig.update_layout(height=380, xaxis_title="Variación mensual (%)", margin=dict(t=10))
st.plotly_chart(fig, width="stretch")

st.subheader("Serie completa por categoría")
variaciones["variacion_m"] = variaciones["variacion_m"].astype(float)
sel = st.multiselect("Categorías", list(ETIQUETAS), default=["alimentos_y_bebidas", "transporte"],
                     format_func=ETIQUETAS.get)
fig2 = go.Figure()
for cat in sel:
    sub = variaciones[variaciones["categoria"] == cat]
    fig2.add_trace(go.Scatter(x=sub["mes"], y=sub["variacion_m"], name=ETIQUETAS[cat]))
fig2.update_layout(height=380, yaxis_title="Variación mensual (%)", margin=dict(t=10), legend=dict(orientation="h", y=-0.2))
st.plotly_chart(fig2, width="stretch")
