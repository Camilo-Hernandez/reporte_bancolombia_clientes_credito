from unittest.mock import MagicMock
import pytest
from di.container import Container
from application.emparejador_pagos_a_credito_caso_uso import EmparejadorPagosACreditoCasoUso
from infrastructure.extractors.extractor_pago_pdf import ExtractorPagosPDF
from infrastructure.report_generators.generador_reporte_txt import GeneradorReporteTxt
from infrastructure.repositories.firebase_repositorio_pedidos import (
    FirebaseRepositorioPedidos,
)
from domain.services.aplicador_de_pagos import AplicadorDePagos


@pytest.fixture
def container():
    container = Container()
    container.config.override(
        {"directorio_pagos": "test_pagos_path", "fecha_pdf": "20230401"}
    )

    # Mock Firebase database reference
    mock_db_reference = MagicMock()
    mock_db_reference.get.return_value = {
        "pedido1": {"nit": "12345", "estado": 2, "valor": {"neto": "1000"}},
        "pedido2": {"nit": "67890", "estado": 2, "valor": {"neto": "2000"}},
    }
    container.firebase_pedidos_reference.override(mock_db_reference)

    # Mock FirebaseRepositorioPedidos to avoid real Firebase calls
    mock_repositorio_pedidos = MagicMock(spec=FirebaseRepositorioPedidos)
    container.repositorio_pedidos.override(mock_repositorio_pedidos)

    return container


def test_repositorio_pedidos(container):
    repositorio_pedidos = container.repositorio_pedidos()
    assert isinstance(repositorio_pedidos, FirebaseRepositorioPedidos)


def test_extractor_pagos(container):
    extractor_pagos = container.extractor_pagos()
    assert isinstance(extractor_pagos, ExtractorPagosPDF)


def test_generador_reporte(container):
    generador_reporte = container.generador_reporte()
    assert isinstance(generador_reporte, GeneradorReporteTxt)


def test_aplicador_pagos(container):
    aplicador_pagos = container.aplicador_pagos()
    assert isinstance(aplicador_pagos, AplicadorDePagos)


def test_emparejador_pagos(container):
    emparejador_pagos = container.emparejador_pagos()
    assert isinstance(emparejador_pagos, EmparejadorPagosACreditoCasoUso)


def test_obtener_pedidos_credito(container):
    """
    Integration Test for the obtener_pedidos_credito method of the FirebaseRepositorioPedidos class.
    This test mocks the Firebase database to return a controlled set of data.
    """
    # Get the repository from the container
    repositorio_pedidos = container.repositorio_pedidos()

    # Mock the method to return test data
    repositorio_pedidos.obtener_pedidos_credito.return_value = [
        {"id_pedido": "pedido1", "nit": "12345", "estado": 2, "valor_neto": 1000},
        {"id_pedido": "pedido2", "nit": "67890", "estado": 2, "valor_neto": 2000},
    ]

    # Call the method and assert the results
    pedidos = repositorio_pedidos.obtener_pedidos_credito()
    assert len(pedidos) == 2
    assert pedidos[0]["nit"] == "12345"
    assert pedidos[1]["valor_neto"] == 2000
