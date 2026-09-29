"""Punto de entrada de la Lambda: descarga las 13 series y sobrescribe el CSV en S3 (carga idempotente:
correr dos veces el mismo mes deja el mismo resultado, no filas duplicadas).

Variables de entorno (las pone Terraform): BUCKET, CLAVE_S3 (con default abajo).
"""
from __future__ import annotations

import logging
import os

import boto3

from . import ingesta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CLAVE_S3_DEFECTO = "raw/ipc_categorias/data.csv"


def handler(event, context):
    bucket = os.environ["BUCKET"]
    clave = os.environ.get("CLAVE_S3", CLAVE_S3_DEFECTO)

    cuerpo = ingesta.descargar()
    filas = ingesta.a_filas_largas(cuerpo)
    if not filas:
        raise RuntimeError("La API respondió sin filas: no piso el CSV existente con datos vacíos.")

    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=clave, Body=ingesta.a_csv(filas), ContentType="text/csv")

    logger.info("Cargadas %d filas (%d categorías) en s3://%s/%s", len(filas), len(ingesta.catalogo.SERIES), bucket, clave)
    return {"filas": len(filas), "bucket": bucket, "clave": clave}
