import io
import json
import urllib.error
from datetime import datetime, timezone

import pytest

from src import catalogo, ingesta


class Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def respuesta_con(filas_por_fecha: dict[str, list]) -> Respuesta:
    """filas_por_fecha: {'2024-01-01': [valor_serie1, valor_serie2, ...]} en el orden de catalogo.SERIES."""
    data = [[fecha, *valores] for fecha, valores in filas_por_fecha.items()]
    return Respuesta(json.dumps({"data": data}).encode("utf-8"))


def error_http(codigo):
    return urllib.error.HTTPError("http://x", codigo, "err", {}, None)


N = len(catalogo.SERIES)  # cantidad de series pedidas: los tests arman filas de este largo


def test_envia_user_agent_propio():
    vistos = []

    def abrir(pedido, timeout):
        vistos.append(pedido.get_header("User-agent"))
        return respuesta_con({"2024-01-01": [1.0] * N})

    ingesta.descargar(abrir=abrir)
    assert vistos == [catalogo.USER_AGENT]


def test_reintenta_ante_5xx_y_luego_funciona():
    llamadas = []

    def abrir(pedido, timeout):
        llamadas.append(1)
        if len(llamadas) < 3:
            raise error_http(503)
        return respuesta_con({"2024-01-01": [1.0] * N})

    ingesta.descargar(abrir=abrir, dormir=lambda s: None)
    assert len(llamadas) == 3


def test_un_4xx_no_se_reintenta():
    llamadas = []

    def abrir(pedido, timeout):
        llamadas.append(1)
        raise error_http(403)

    with pytest.raises(urllib.error.HTTPError):
        ingesta.descargar(abrir=abrir, dormir=lambda s: None)
    assert len(llamadas) == 1


def test_falla_con_mensaje_claro_tras_agotar_reintentos():
    def abrir(pedido, timeout):
        raise urllib.error.URLError("sin red")

    with pytest.raises(RuntimeError, match="IPC por categoría"):
        ingesta.descargar(abrir=abrir, reintentos=2, dormir=lambda s: None)


def test_a_filas_largas_una_fila_por_categoria_y_mes():
    cuerpo = {"data": [["2024-01-01", *range(N)]]}
    filas = ingesta.a_filas_largas(cuerpo, cargado_en=datetime(2024, 2, 1, tzinfo=timezone.utc))
    assert len(filas) == N
    nombres = list(catalogo.SERIES.keys())
    assert {f["categoria"] for f in filas} == set(nombres)
    fila_nivel_general = next(f for f in filas if f["categoria"] == "nivel_general")
    assert fila_nivel_general["valor"] == 0.0  # primer nombre del catálogo -> primer valor (0) de range(N)
    assert fila_nivel_general["fecha"] == "2024-01-01"
    assert fila_nivel_general["cargado_en"] == "2024-02-01T00:00:00Z"


def test_a_filas_largas_descarta_nulos():
    cuerpo = {"data": [["2024-01-01", *([None] * N)], ["2024-02-01", *range(N)]]}
    filas = ingesta.a_filas_largas(cuerpo)
    assert {f["fecha"] for f in filas} == {"2024-02-01"}


def test_a_filas_largas_sin_datos_da_lista_vacia():
    assert ingesta.a_filas_largas({"data": []}) == []


def test_a_csv_tiene_encabezado_y_columnas_fijas():
    filas = [{"categoria": "salud", "fecha": "2024-01-01", "valor": 123.45, "cargado_en": "2024-02-01T00:00:00Z"}]
    texto = ingesta.a_csv(filas).decode("utf-8")
    lineas = texto.strip().splitlines()
    assert lineas[0] == "categoria,fecha,valor,cargado_en"
    assert lineas[1] == "salud,2024-01-01,123.45,2024-02-01T00:00:00Z"
