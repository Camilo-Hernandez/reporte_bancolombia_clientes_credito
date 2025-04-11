import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from decimal import Decimal
from infrastructure.repositories.firebase_repositorio_pedido import (
    FirebaseRepositorioPedidos,
)
from domain.models.models import EstadoPedido


@pytest.fixture
def mock_firebase_reference():
    with patch("firebase_admin.db.reference") as mock_ref:
        yield mock_ref


@pytest.fixture
def firebase_repo(mock_firebase_reference):
    # Mock the Firebase reference instance
    mock_ref_instance = MagicMock()
    mock_ref_instance.get.return_value = {
        "1": {
            "nit": "12345",
            "valor": {"neto": 1000},
            "hora_despacho": "01/01/2023 12:00",
            "estado": 2,
            "forma_pago": "Efectivo",
            "razon_social": "Cliente A",
        },
        "2": {
            "nit": "67890",
            "valor": {"neto": 2000},
            "hora_despacho": "02/01/2023 12:00",
            "estado": 2,
            "forma_pago": "30 días",
            "razon_social": "Cliente B",
        },
    }
    mock_firebase_reference.return_value = mock_ref_instance

    # Pass the mocked reference to the repository
    return FirebaseRepositorioPedidos(firebase_reference=mock_firebase_reference.return_value)


def test_obtener_pedidos_por_nit(firebase_repo, mock_firebase_reference):
    # Mock the Firebase reference instance
    mock_ref_instance = MagicMock()
    mock_firebase_reference.return_value = mock_ref_instance

    # Mock the data returned by the Firebase reference
    mock_ref_instance.get.return_value = {
        "1": {
            "nit": "12345",
            "valor": {"neto": 1000},
            "hora_despacho": "01/01/2023 12:00",
            "estado": 2,
            "forma_pago": "Efectivo",
            "razon_social": "Cliente A",
        },
        "2": {
            "nit": "67890",
            "valor": {"neto": 2000},
            "hora_despacho": "02/01/2023 12:00",
            "estado": 2,
            "forma_pago": "30 días",
            "razon_social": "Cliente B",
        },
    }

    # Call the method under test
    pedidos = firebase_repo.obtener_pedidos_por_nit("12345")

    # Assertions
    assert len(pedidos) == 1
    assert pedidos[0].id_pedido == "1"
    assert pedidos[0].nit_cliente == "12345"
    assert pedidos[0].valor_neto == Decimal("1000")
    assert pedidos[0].fecha_pedido == datetime(2023, 1, 1).date()
    assert pedidos[0].estado_pedido == EstadoPedido.DESPACHADO


def test_obtener_pedidos_credito(firebase_repo, mock_firebase_reference):
    mock_ref_instance = MagicMock()
    mock_firebase_reference.return_value = mock_ref_instance
    mock_ref_instance.get.return_value = {
        "1": {
            "nit": "12345",
            "valor": {"neto": "1000"},
            "hora_despacho": "01/01/2023 12:00",
            "estado": "PENDIENTE",
            "forma_pago": "Efectivo",
            "razon_social": "Cliente A",
        },
        "2": {
            "nit": "67890",
            "valor": {"neto": "2000"},
            "hora_despacho": "02/01/2023 12:00",
            "estado": "ENTREGADO",
            "forma_pago": "30 días",
            "razon_social": "Cliente B",
        },
    }

    pedidos = firebase_repo.obtener_pedidos_credito()

    assert len(pedidos) == 1
    assert pedidos[0].id_pedido == "2"
    assert pedidos[0].nit_cliente == "67890"
    assert pedidos[0].valor_neto == Decimal("2000")
    assert pedidos[0].fecha_pedido == datetime(2023, 1, 2).date()
    assert pedidos[0].estado_pedido == EstadoPedido.DESPACHADO


def test_dias_en_forma_pago(firebase_repo):
    assert firebase_repo._dias_en_forma_pago("30 días") is True
    assert firebase_repo._dias_en_forma_pago("Efectivo") is False
    assert firebase_repo._dias_en_forma_pago("60 DIAS") is True
    assert firebase_repo._dias_en_forma_pago("") is False
