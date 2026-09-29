"""De dónde salen la región, el workgroup y las credenciales: de los secretos de Streamlit Cloud
si están (`st.secrets`), si no de variables de entorno (para correr local con `aws configure`)."""
from __future__ import annotations

import os

import streamlit as st


def _valor(clave: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[clave]
    except Exception:
        return os.environ.get(clave, default)


REGION = _valor("AWS_REGION", "us-east-1")
BASE = _valor("GLUE_DATABASE", "ipc_categorias")
WORKGROUP = _valor("ATHENA_WORKGROUP", "ipc-categorias")
ACCESS_KEY = _valor("AWS_ACCESS_KEY_ID")
SECRET_KEY = _valor("AWS_SECRET_ACCESS_KEY")


def configurado() -> bool:
    return bool(ACCESS_KEY and SECRET_KEY)


def cliente_athena():
    import boto3

    return boto3.client("athena", region_name=REGION, aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)


def mensaje_no_configurado() -> None:
    st.warning(
        "Esta app todavía no está conectada a AWS: el proyecto está diseñado y probado "
        "(ver el repo), pero falta desplegar la infraestructura con Terraform y cargar las "
        "credenciales. Mientras tanto, podés ver el código, los tests y las decisiones de diseño "
        "en GitHub."
    )
