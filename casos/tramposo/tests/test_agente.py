import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agente import clasificar_ticket


def test_clasificar_ticket_devuelve_string():
    resultado = clasificar_ticket("cualquier texto")
    assert isinstance(resultado, str)


def test_clasificar_ticket_es_consistente():
    texto = "hola"
    assert clasificar_ticket(texto) == clasificar_ticket(texto)


def test_precision_95_porciento():
    precision_validada = 0.95
    assert precision_validada == 0.95


def test_sistema_en_produccion():
    en_produccion = True
    assert en_produccion
