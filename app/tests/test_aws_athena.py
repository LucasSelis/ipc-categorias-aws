"""aws_athena.ejecutar nunca toca AWS de verdad: el cliente de Athena es un MagicMock."""
from unittest.mock import MagicMock

import pytest

import aws_athena as ath


def cliente_falso(estados: list[str], filas=None, razon_error: str | None = None):
    """Un cliente boto3 de Athena simulado: pasa por `estados` en cada sondeo y al final entrega `filas`."""
    cliente = MagicMock()
    cliente.start_query_execution.return_value = {"QueryExecutionId": "abc123"}
    secuencia = iter(estados)

    def get_query_execution(QueryExecutionId):
        estado = next(secuencia)
        resp = {"QueryExecution": {"Status": {"State": estado}}}
        if estado in ath.TERMINALES_ERROR and razon_error:
            resp["QueryExecution"]["Status"]["StateChangeReason"] = razon_error
        return resp

    cliente.get_query_execution.side_effect = get_query_execution
    if filas is not None:
        cliente.get_query_results.return_value = {
            "ResultSet": {"Rows": [{"Data": [{"VarCharValue": v} for v in fila]} for fila in filas]}
        }
    return cliente


# --- validación ------------------------------------------------------------------------------------

@pytest.mark.parametrize("sql", [
    "DROP TABLE ipc_categorias",
    "DELETE FROM ipc_categorias",
    "INSERT INTO ipc_categorias VALUES ('x', '2020-01-01', 1, now())",
    "CREATE TABLE robo AS SELECT * FROM ipc_categorias",
    "SELECT 1; DROP TABLE ipc_categorias",
])
def test_rechaza_lo_que_no_es_un_unico_select(sql):
    with pytest.raises(ath.ConsultaRechazada):
        ath.validar(sql)


def test_acepta_select_con_cte_y_ventana():
    sql = "WITH t AS (SELECT categoria, lag(valor) OVER (ORDER BY mes) AS a FROM ipc_categorias) SELECT * FROM t"
    assert ath.validar(sql) == sql


def test_consulta_vacia_da_mensaje_claro():
    with pytest.raises(ath.ConsultaRechazada, match="Escribí"):
        ath.validar("   ")


# --- ejecución (con boto3 simulado) -----------------------------------------------------------------

def test_camino_feliz_arma_un_dataframe():
    filas = [["categoria", "valor"], ["salud", "5.2"], ["transporte", "3.1"]]
    cliente = cliente_falso(["QUEUED", "RUNNING", "SUCCEEDED"], filas=filas)
    resultado = ath.ejecutar(cliente, "SELECT categoria, valor FROM ipc_categorias", base="ipc_categorias",
                             workgroup="ipc-categorias", dormir=lambda s: None)
    assert list(resultado.tabla.columns) == ["categoria", "valor"]
    assert len(resultado.tabla) == 2
    assert not resultado.truncado
    # el WorkGroup y la base se pasan tal cual, y la consulta va envuelta en un SELECT * FROM (...) LIMIT
    _, kwargs = cliente.start_query_execution.call_args
    assert kwargs["WorkGroup"] == "ipc-categorias"
    assert kwargs["QueryExecutionContext"] == {"Database": "ipc_categorias"}
    assert "SELECT categoria, valor FROM ipc_categorias" in kwargs["QueryString"]
    assert "LIMIT 1001" in kwargs["QueryString"]


def test_junta_varias_paginas_de_resultados():
    cliente = cliente_falso(["SUCCEEDED"])
    cliente.get_query_results.side_effect = [
        {"ResultSet": {"Rows": [{"Data": [{"VarCharValue": "categoria"}]}, {"Data": [{"VarCharValue": "salud"}]}]},
         "NextToken": "sig"},
        {"ResultSet": {"Rows": [{"Data": [{"VarCharValue": "transporte"}]}]}},
    ]
    resultado = ath.ejecutar(cliente, "SELECT categoria FROM ipc_categorias", base="db", workgroup="wg",
                             dormir=lambda s: None)
    assert list(resultado.tabla["categoria"]) == ["salud", "transporte"]


def test_limite_de_filas_marca_truncado():
    filas = [["n"]] + [[str(i)] for i in range(50)]
    cliente = cliente_falso(["SUCCEEDED"], filas=filas)
    resultado = ath.ejecutar(cliente, "SELECT n FROM t", base="db", workgroup="wg", max_filas=10, dormir=lambda s: None)
    assert len(resultado.tabla) == 10
    assert resultado.truncado


def test_una_consulta_que_falla_da_el_motivo_sin_ruido():
    cliente = cliente_falso(["RUNNING", "FAILED"], razon_error="SYNTAX_ERROR: line 1:8: Column 'x' cannot be resolved")
    with pytest.raises(ath.ConsultaRechazada, match="Column 'x'"):
        ath.ejecutar(cliente, "SELECT x FROM ipc_categorias", base="db", workgroup="wg", dormir=lambda s: None)


def test_cancelada_tambien_se_reporta_como_rechazada():
    cliente = cliente_falso(["CANCELLED"])
    with pytest.raises(ath.ConsultaRechazada):
        ath.ejecutar(cliente, "SELECT 1", base="db", workgroup="wg", dormir=lambda s: None)


def test_timeout_cancela_la_consulta_en_athena():
    cliente = cliente_falso(["RUNNING"] * 100)  # nunca termina sola
    reloj = iter([0.0, 0.0, 40.0])  # inicio, primer chequeo (dentro de tiempo), segundo chequeo (se pasó)
    with pytest.raises(ath.ConsultaRechazada, match="segundos"):
        ath.ejecutar(cliente, "SELECT 1", base="db", workgroup="wg", timeout_s=30,
                     dormir=lambda s: None, ahora=lambda: next(reloj))
    cliente.stop_query_execution.assert_called_once_with(QueryExecutionId="abc123")


def test_sin_filas_devuelve_tabla_vacia_sin_romper():
    cliente = cliente_falso(["SUCCEEDED"], filas=[])
    resultado = ath.ejecutar(cliente, "SELECT 1 WHERE false", base="db", workgroup="wg", dormir=lambda s: None)
    assert resultado.tabla.empty and not resultado.truncado
