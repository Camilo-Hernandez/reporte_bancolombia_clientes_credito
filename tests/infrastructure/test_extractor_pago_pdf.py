import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
import uuid

from domain.models.models import Pago
from infrastructure.extractors.extractor_pago_pdf import ExtractorPagosPDF


@pytest.fixture
def mock_procesador_pdf():
    extractor_pagos_por_nit_bancolombia_mock = MagicMock()
    extractor_pagos_por_nit_bancolombia_mock.extract_data.return_value = {
        "123456789": 1000.50,
        "987654321": 2000.75,
    }
    return extractor_pagos_por_nit_bancolombia_mock


@pytest.fixture
def extractor_pagos_pdf(mock_procesador_pdf):
    return ExtractorPagosPDF(procesador_pdf= mock_procesador_pdf)


def test_obtener_pagos_returns_correct_list_of_pagos(extractor_pagos_pdf, monkeypatch):
    # Mock the UUID generation to return a fixed value
    def mock_uuid5(namespace, name):
        return uuid.UUID("12345678-1234-5678-1234-567812345678")

    monkeypatch.setattr(uuid, "uuid5", mock_uuid5)

    pagos = extractor_pagos_pdf.obtener_pagos(fecha_pdf="20231010", tipo_cuenta="ahorros")

    assert len(pagos) == 2
    assert pagos[0] == Pago(
        id_pago="12345678-1234-5678-1234-567812345678",  # Match the mocked UUID
        nit_cliente="123456789",
        monto=Decimal("1000.50"),
        fecha_pago=date(2023, 10, 10),
        cuenta_ingreso_banco="",
        cuenta_egreso_banco="",
    )
    assert pagos[1] == Pago(
        id_pago="12345678-1234-5678-1234-567812345678",  # Match the mocked UUID
        nit_cliente="987654321",
        monto=Decimal("2000.75"),
        fecha_pago=date(2023, 10, 10),
        cuenta_ingreso_banco="",
        cuenta_egreso_banco="",
    )


def test_extraer_pagos_calls_procesador_extract_data_once(
    extractor_pagos_pdf, mock_procesador_pdf
):
    extractor_pagos_pdf.obtener_pagos(fecha_pdf="20231010", tipo_cuenta="ahorros")
    mock_procesador_pdf.extract_data.assert_called_once()


def test_extraer_pagos_handles_empty_data(extractor_pagos_pdf, mock_procesador_pdf):
    mock_procesador_pdf.extract_data.return_value = {}
    pagos = extractor_pagos_pdf.obtener_pagos(
        fecha_pdf="20231010", tipo_cuenta="ahorros"
    )

    assert pagos == []
