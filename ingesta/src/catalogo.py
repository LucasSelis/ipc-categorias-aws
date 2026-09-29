"""Catálogo de series del IPC por categoría (INDEC, vía la API de datos.gob.ar).

Todas comparten base dic-2016=100, frecuencia mensual y cobertura nacional: son series "hermanas"
del nivel general que ya usé en el observatorio de inflación (mismo formato, mismo origen).
"""
from __future__ import annotations

API = "https://apis.datos.gob.ar/series/api/series/"
USER_AGENT = "ipc-categorias/1.0"  # la API responde 403 al User-Agent por defecto de Python

# nombre_interno -> id de la serie en datos.gob.ar
SERIES: dict[str, str] = {
    "nivel_general": "148.3_INIVELNAL_DICI_M_26",
    # apertura por rigidez de precios (cómo lee el mercado la inflación mes a mes)
    "nucleo": "148.3_INUCLEONAL_DICI_M_19",
    "regulados": "148.3_IREGULANAL_DICI_M_22",
    "estacionales": "148.3_IESTACINAL_DICI_M_25",
    # apertura por división de consumo (qué rubro empuja la inflación)
    "alimentos_y_bebidas": "146.3_IALIMENNAL_DICI_M_45",
    "bebidas_alcoholicas_y_tabaco": "146.3_IBEBIDANAL_DICI_M_39",
    "transporte": "146.3_ITRANSPNAL_DICI_M_23",
    "educacion": "146.3_IEDUCACNAL_DICI_M_22",
    "salud": "146.3_ISALUDNAL_DICI_M_18",
    "comunicaciones": "146.3_ICOMUNINAL_DICI_M_27",
    "hoteles_y_restaurantes": "146.3_IRESTAUNAL_DICI_M_33",
    "recreacion_y_cultura": "146.3_IRECREANAL_DICI_M_31",
    "bienes_y_servicios_varios": "146.3_IBIENESNAL_DICI_M_36",
}


def url_series() -> str:
    ids = ",".join(SERIES.values())
    return f"{API}?ids={ids}&format=json&limit=5000&sort=asc"
