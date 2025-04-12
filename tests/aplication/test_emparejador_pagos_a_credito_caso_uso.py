import pytest
from datetime import date
from decimal import Decimal
from typing import Optional
from unittest.mock import MagicMock

from di.container import Container
from domain.models.models import (
    EstadoPedido,
    Pago,
    Pedido,
    TipoCliente,
    EstadoPago,
    ResultadoPagoCliente,
)

from application.emparejador_pagos_a_credito_caso_uso import EmparejadorPagosACreditoCasoUso
from infrastructure.repositories.firebase_repositorio_pedidos import FirebaseRepositorioPedidos


@pytest.fixture
def pagos_ejemplo():
    return [
        Pago(
            id_pago="p1",
            nit_cliente="12345",
            cuenta_ingreso_banco="110505",
            cuenta_egreso_banco="111005",
            monto=Decimal("800.00"),
            fecha_pago=date(2025, 3, 30),
        )
    ]


@pytest.fixture
def pedidos_ejemplo():
    return [
        Pedido(
            id_pedido="f1",
            nit_cliente="12345",
            valor_neto=Decimal("300.00"),
            valor_cobrado=Decimal("0.00"),
            fecha_pedido=date(2025, 3, 1),
            estado_pedido=EstadoPedido.DESPACHADO,
            estado_pago=EstadoPago.PENDIENTE,
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=15,
            forma_pago_raw="A 15 días",
            razon_social="Cliente Ejemplo",
        ),
        Pedido(
            id_pedido="f2",
            nit_cliente="12345",
            valor_neto=Decimal("500.00"),
            valor_cobrado=Decimal("0.00"),
            fecha_pedido=date(2025, 3, 5),
            estado_pedido=EstadoPedido.DESPACHADO,
            estado_pago=EstadoPago.PENDIENTE,
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=15,
            forma_pago_raw="A 15 días",
            razon_social="Cliente Ejemplo",
        ),
    ]


def test_generar_reporte_credito_ejecucion_correcta(pagos_ejemplo, pedidos_ejemplo):
    extractor_mock = MagicMock()
    extractor_mock.obtener_pagos.return_value = pagos_ejemplo

    repositorio_mock = MagicMock()
    repositorio_mock.obtener_pedidos_credito.return_value = pedidos_ejemplo

    generador_mock = MagicMock()

    aplicador_de_pagos_mock = MagicMock()

    caso_uso = EmparejadorPagosACreditoCasoUso(
        extractor_pagos=extractor_mock,
        repositorio_pedidos=repositorio_mock,
        generador_reporte=generador_mock,
        aplicador_pagos=aplicador_de_pagos_mock,
    )

    aplicador_de_pagos_mock.aplicar_pago_a_pedidos_cliente.return_value = (
        ResultadoPagoCliente(
            id_pago="p1",
            nit_cliente="12345",
            tipo_cliente=TipoCliente.CREDITO,
            fecha_pago=date(2025, 3, 30),
            pago_extracto=Decimal("800.00"),
            facturas_pagadas=pedidos_ejemplo,
            factura_parcial=None,
            facturas_pendientes=[],
            deuda_total_anterior=Decimal("800.00"),
            deuda_restante=Decimal("0.00"),
        )
    )

    caso_uso.ejecutar(fecha_pago=date(2025, 3, 30), tipo_cuenta="CREDITO")

    generador_mock.generar.assert_called_once()
    resultado: ResultadoPagoCliente = generador_mock.generar.call_args[0][0]

    assert resultado.nit_cliente == "12345"
    assert resultado.pago_extracto == Decimal("800.00")
    assert isinstance(resultado.facturas_pagadas, list)
    assert isinstance(resultado.factura_parcial, Optional[str])
    assert resultado.factura_parcial is None
    assert isinstance(resultado.facturas_pendientes, list)
    assert resultado.pago_extracto == Decimal("800.00")
    assert resultado.deuda_restante == Decimal("0.00")
    assert len(resultado.facturas_pagadas) == 2
    assert len(resultado.facturas_pendientes) == 0


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


def test_integracion_emparejador_pagos_a_credito(container):
    # Arrange
    extractor_mock = MagicMock()
    extractor_mock.obtener_pagos.return_value = [
        Pago(
            id_pago="p1",
            nit_cliente="12345",
            cuenta_ingreso_banco="110505",
            cuenta_egreso_banco="111005",
            monto=Decimal("800.00"),
            fecha_pago=date(2025, 3, 30),
        )
    ]
    container.extractor_pagos.override(extractor_mock)

    container.repositorio_pedidos().obtener_pedidos_credito.return_value = [
        Pedido(
            id_pedido="f1",
            nit_cliente="12345",
            valor_neto=Decimal("300.00"),
            valor_cobrado=Decimal("0.00"),
            fecha_pedido=date(2025, 3, 1),
            estado_pedido=EstadoPedido.DESPACHADO,
            estado_pago=EstadoPago.PENDIENTE,
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=15,
            forma_pago_raw="A 15 días",
            razon_social="Cliente Ejemplo",
        ),
        Pedido(
            id_pedido="f2",
            nit_cliente="12345",
            valor_neto=Decimal("500.00"),
            valor_cobrado=Decimal("0.00"),
            fecha_pedido=date(2025, 3, 5),
            estado_pedido=EstadoPedido.DESPACHADO,
            estado_pago=EstadoPago.PENDIENTE,
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=15,
            forma_pago_raw="A 15 días",
            razon_social="Cliente Ejemplo",
        ),
    ]

    aplicador_de_pagos_mock = MagicMock()
    container.aplicador_pagos.override(aplicador_de_pagos_mock)

    aplicador_de_pagos_mock.aplicar_pago_a_pedidos_cliente.return_value = (
        ResultadoPagoCliente(
            id_pago="p1",
            nit_cliente="12345",
            tipo_cliente=TipoCliente.CREDITO,
            fecha_pago=date(2025, 3, 30),
            pago_extracto=Decimal("800.00"),
            facturas_pagadas=container.repositorio_pedidos().obtener_pedidos_credito.return_value,
            factura_parcial=None,
            facturas_pendientes=[],
            deuda_total_anterior=Decimal("800.00"),
            deuda_restante=Decimal("0.00"),
        )
    )

    generador_mock = MagicMock()
    container.generador_reporte.override(generador_mock)

    caso_uso = EmparejadorPagosACreditoCasoUso(
        extractor_pagos=container.extractor_pagos(),
        repositorio_pedidos=container.repositorio_pedidos(),
        generador_reporte=container.generador_reporte(),
        aplicador_pagos=container.aplicador_pagos(),
    )

    # Act
    caso_uso.ejecutar(fecha_pago=date(2025, 3, 30), tipo_cuenta="CREDITO")

    # Assert
    generador_mock.generar.assert_called_once()
    resultado: ResultadoPagoCliente = generador_mock.generar.call_args[0][0]

    assert resultado.nit_cliente == "12345"
    assert resultado.pago_extracto == Decimal("800.00")
    assert isinstance(resultado.facturas_pagadas, list)
    assert resultado.factura_parcial is None
    assert isinstance(resultado.facturas_pendientes, list)
    assert resultado.deuda_restante == Decimal("0.00")
    assert len(resultado.facturas_pagadas) == 2
    assert len(resultado.facturas_pendientes) == 0