"""El handler se prueba contra un S3 simulado (moto): nunca toca una cuenta de AWS real."""
import io
import json
import os

import boto3
import pytest
from moto import mock_aws

from src import catalogo, handler

N = len(catalogo.SERIES)
BUCKET = "bucket-de-prueba"


def _json_ok():
    data = [["2024-01-01", *range(N)], ["2024-02-01", *[v * 2 for v in range(N)]]]
    return {"data": data}


@pytest.fixture
def s3_vacio(monkeypatch):
    monkeypatch.setenv("BUCKET", BUCKET)
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        yield s3


def test_el_handler_escribe_el_csv_en_s3(s3_vacio, monkeypatch):
    monkeypatch.setattr(
        "src.ingesta.descargar",
        lambda **kw: _json_ok(),
    )
    resultado = handler.handler({}, None)
    assert resultado["filas"] == 2 * N

    objeto = s3_vacio.get_object(Bucket=BUCKET, Key=handler.CLAVE_S3_DEFECTO)
    texto = objeto["Body"].read().decode("utf-8")
    lineas = texto.strip().splitlines()
    assert lineas[0] == "categoria,fecha,valor,cargado_en"
    assert len(lineas) == 1 + 2 * N


def test_correr_dos_veces_no_duplica_pisa_el_archivo(s3_vacio, monkeypatch):
    monkeypatch.setattr("src.ingesta.descargar", lambda **kw: _json_ok())
    handler.handler({}, None)
    handler.handler({}, None)  # segunda corrida del mismo mes
    objeto = s3_vacio.get_object(Bucket=BUCKET, Key=handler.CLAVE_S3_DEFECTO)
    lineas = objeto["Body"].read().decode("utf-8").strip().splitlines()
    assert len(lineas) == 1 + 2 * N  # no el doble


def test_una_api_vacia_no_pisa_datos_buenos_con_nada(s3_vacio, monkeypatch):
    # Primero carga datos buenos.
    monkeypatch.setattr("src.ingesta.descargar", lambda **kw: _json_ok())
    handler.handler({}, None)
    contenido_previo = s3_vacio.get_object(Bucket=BUCKET, Key=handler.CLAVE_S3_DEFECTO)["Body"].read()

    # Una corrida donde la API no trae filas no debe borrar lo que ya estaba.
    monkeypatch.setattr("src.ingesta.descargar", lambda **kw: {"data": []})
    with pytest.raises(RuntimeError, match="sin filas"):
        handler.handler({}, None)
    contenido_actual = s3_vacio.get_object(Bucket=BUCKET, Key=handler.CLAVE_S3_DEFECTO)["Body"].read()
    assert contenido_actual == contenido_previo


def test_usa_la_clave_s3_de_la_variable_de_entorno(s3_vacio, monkeypatch):
    monkeypatch.setenv("CLAVE_S3", "otra/ruta/datos.csv")
    monkeypatch.setattr("src.ingesta.descargar", lambda **kw: _json_ok())
    handler.handler({}, None)
    # No debe existir en la ruta por defecto.
    with pytest.raises(s3_vacio.exceptions.NoSuchKey):
        s3_vacio.get_object(Bucket=BUCKET, Key=handler.CLAVE_S3_DEFECTO)
    s3_vacio.get_object(Bucket=BUCKET, Key="otra/ruta/datos.csv")  # no debe lanzar
