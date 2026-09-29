"""Ejecuta SQL de un visitante contra Athena. La barrera real es el usuario IAM de solo lectura
(terraform/iam_app.tf: no puede escribir, borrar ni crear nada); esta validación es una segunda
capa que da un mensaje claro antes de gastar una consulta, no la que impide el daño.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd
import sqlparse

MAX_FILAS = 1000
TIMEOUT_S = 30.0
ESPERA_ENTRE_SONDEOS_S = 1.0

TERMINALES_OK = {"SUCCEEDED"}
TERMINALES_ERROR = {"FAILED", "CANCELLED"}


class ConsultaRechazada(ValueError):
    """La consulta no es un único SELECT, o falló al ejecutarse; el mensaje es apto para mostrar."""


@dataclass(frozen=True)
class Resultado:
    tabla: pd.DataFrame
    truncado: bool


def validar(sql: str) -> str:
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise ConsultaRechazada("Escribí una consulta.")
    sentencias = [s for s in sqlparse.parse(sql) if s.token_first(skip_cm=True) is not None]
    if len(sentencias) != 1:
        raise ConsultaRechazada("Solo se permite una consulta por vez.")
    if sentencias[0].get_type() != "SELECT":
        raise ConsultaRechazada("Solo se permiten consultas SELECT (con WITH, JOIN, funciones de ventana, etc.).")
    return sql


def ejecutar(cliente_athena, sql: str, base: str, workgroup: str, max_filas: int = MAX_FILAS,
            timeout_s: float = TIMEOUT_S, dormir=time.sleep, ahora=time.monotonic) -> Resultado:
    sql = validar(sql)
    envuelta = f"SELECT * FROM (\n{sql}\n) consulta LIMIT {max_filas + 1}"

    id_ejecucion = cliente_athena.start_query_execution(
        QueryString=envuelta,
        QueryExecutionContext={"Database": base},
        WorkGroup=workgroup,
    )["QueryExecutionId"]

    inicio = ahora()
    while True:
        estado_resp = cliente_athena.get_query_execution(QueryExecutionId=id_ejecucion)
        estado = estado_resp["QueryExecution"]["Status"]["State"]
        if estado in TERMINALES_OK:
            break
        if estado in TERMINALES_ERROR:
            razon = estado_resp["QueryExecution"]["Status"].get("StateChangeReason", "")
            raise ConsultaRechazada(_limpio(razon) or f"La consulta terminó en estado {estado}.")
        if ahora() - inicio > timeout_s:
            cliente_athena.stop_query_execution(QueryExecutionId=id_ejecucion)
            raise ConsultaRechazada(f"La consulta tardó más de {timeout_s:g} segundos y se canceló.")
        dormir(ESPERA_ENTRE_SONDEOS_S)

    filas = _traer_resultados(cliente_athena, id_ejecucion)
    if not filas:
        return Resultado(pd.DataFrame(), truncado=False)
    encabezado, *datos = filas
    tabla = pd.DataFrame(datos, columns=encabezado)
    truncado = len(tabla) > max_filas
    return Resultado(tabla.head(max_filas), truncado=truncado)


def _traer_resultados(cliente_athena, id_ejecucion: str) -> list[list[str]]:
    """Junta todas las páginas de GetQueryResults. La primera fila de la primera página es el encabezado."""
    filas: list[list[str]] = []
    token = None
    while True:
        kwargs = {"QueryExecutionId": id_ejecucion}
        if token:
            kwargs["NextToken"] = token
        pagina = cliente_athena.get_query_results(**kwargs)
        for fila in pagina["ResultSet"]["Rows"]:
            filas.append([c.get("VarCharValue", "") for c in fila["Data"]])
        token = pagina.get("NextToken")
        if not token:
            return filas


def _limpio(texto: str) -> str:
    return texto.splitlines()[0][:300] if texto else ""
