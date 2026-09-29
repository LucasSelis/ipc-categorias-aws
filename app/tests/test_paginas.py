"""Sin credenciales de AWS (el estado real hasta que se despliegue), las páginas deben avisar
con claridad en vez de tirar una excepción."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
PRINCIPAL = str(RAIZ / "IPC_por_categoria.py")
EXPLORADOR = str(RAIZ / "pages" / "1_Explorador_SQL.py")


def test_pagina_principal_sin_credenciales_no_rompe(monkeypatch):
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(var, raising=False)
    at = AppTest.from_file(PRINCIPAL, default_timeout=30).run()
    assert not at.exception
    assert at.warning and "no está conectada a AWS" in at.warning[0].value


def test_explorador_sin_credenciales_no_rompe(monkeypatch):
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(var, raising=False)
    at = AppTest.from_file(EXPLORADOR, default_timeout=30).run()
    assert not at.exception
    assert at.warning and "no está conectada a AWS" in at.warning[0].value
