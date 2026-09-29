"""Descarga las series y las deja en formato largo (tidy): una fila por (categoría, fecha).

Separado en dos partes a propósito: `descargar` habla con la red (probado con un `abrir` falso,
como en el observatorio de inflación); `a_filas_largas` es una función pura sobre el JSON ya
descargado, así se puede probar con datos fijos sin tocar la red ni el reloj.
"""
from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from . import catalogo


def descargar(abrir=urllib.request.urlopen, reintentos: int = 3, espera: float = 1.5, dormir=time.sleep) -> dict:
    """Devuelve el JSON crudo de la API (lista de meta + data). Reintenta ante 5xx/red; un 4xx no se reintenta."""
    pedido = urllib.request.Request(catalogo.url_series(), headers={"User-Agent": catalogo.USER_AGENT})
    ultimo_error: Exception | None = None
    for intento in range(1, reintentos + 1):
        try:
            with abrir(pedido, timeout=30) as respuesta:
                return json.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if 400 <= error.code < 500:
                raise
            ultimo_error = error
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            ultimo_error = error
        if intento < reintentos:
            dormir(espera * intento)
    raise RuntimeError(f"No se pudo descargar el IPC por categoría tras {reintentos} intentos: {ultimo_error}")


def a_filas_largas(cuerpo: dict, cargado_en: datetime | None = None) -> list[dict]:
    """Convierte la respuesta ancha de la API (una columna por serie) a filas (categoria, fecha, valor).

    Descarta los meses sin valor: la API rellena con null los últimos meses de las series que
    todavía no publicaron ese período.
    """
    cargado_en = cargado_en or datetime.now(timezone.utc)
    nombres = list(catalogo.SERIES.keys())  # mismo orden que se pidió en la URL
    filas = []
    for fila in cuerpo["data"]:
        fecha, valores = fila[0], fila[1:]
        for nombre, valor in zip(nombres, valores):
            if valor is not None:
                filas.append({"categoria": nombre, "fecha": fecha, "valor": float(valor),
                             "cargado_en": cargado_en.strftime("%Y-%m-%dT%H:%M:%SZ")})
    return filas


def a_csv(filas: list[dict]) -> bytes:
    """CSV en memoria, listo para subir a S3. Columnas fijas y en orden, para que el esquema de Glue no dependa
    del orden con que Python recorra un dict."""
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=["categoria", "fecha", "valor", "cargado_en"])
    escritor.writeheader()
    escritor.writerows(filas)
    return buffer.getvalue().encode("utf-8")
