import pytest
from datetime import date, timedelta
from decimal import Decimal
from domain.models.models import Cliente, Pago, Pedido, ResultadoPagoCliente, TipoCliente, EstadoPedido, EstadoPago

def test_cliente_model():
    cliente = Cliente(
        id_cliente="123",
        nit_cliente="900123456",
        razon_social="Empresa S.A.",
        tipo_cliente=TipoCliente.CREDITO,
        plazo_dias_credito=30
    )
    assert cliente.id_cliente == "123"
    assert cliente.nit_cliente == "900123456"
    assert cliente.razon_social == "Empresa S.A."
    assert cliente.tipo_cliente == TipoCliente.CREDITO
    assert cliente.plazo_dias_credito == 30


def test_pago_model():
    pago = Pago(
        nit_cliente="900123456",
        monto=Decimal("1000.50"),
        fecha_pago=date.today(),
        referencia_bancaria="Pago Factura 001"
    )
    assert pago.nit_cliente == "900123456"
    assert pago.monto == Decimal("1000.50")
    assert pago.fecha_pago == date.today()
    assert pago.referencia_bancaria == "Pago Factura 001"
    assert isinstance(pago.id_pago, str)


def test_pedido_model():
    pedido = Pedido(
        id_pedido="001",
        estado_pedido=EstadoPedido.FACTURADO,
        nit_cliente="900123456",
        valor_neto=Decimal("5000.00"),
        fecha_pedido=date.today(),
        plazo_dias_credito=30,
        razon_social="Empresa S.A."
    )
    assert pedido.id_pedido == "001"
    assert pedido.estado_pedido == EstadoPedido.FACTURADO
    assert pedido.nit_cliente == "900123456"
    assert pedido.valor_neto == Decimal("5000.00")
    assert pedido.fecha_pedido == date.today()
    assert pedido.razon_social == "Empresa S.A."
    assert pedido.plazo_dias_credito == 30
    assert pedido.tipo_cliente == TipoCliente.CREDITO


def test_resultado_pago_cliente_model():
    pedido_pagado = Pedido(
        id_pedido="001",
        estado_pedido=EstadoPedido.FACTURADO,
        nit_cliente="900123456",
        valor_neto=Decimal("5000.00"),
        fecha_pedido=date.today(),
        forma_pago_raw="A 30 días"
    )
    resultado = ResultadoPagoCliente(
        id_pago="12345",
        nit_cliente="900123456",
        fecha_pago=date.today(),
        pago_extracto=Decimal("5000.00"),
        facturas_pagadas=[pedido_pagado],
        facturas_parciales=[],
        facturas_pendientes=[],
        tipo_cliente=TipoCliente.CREDITO,
        deuda_total_anterior=Decimal("5000.00"),
        deuda_restante=Decimal("0.00")
    )
    assert resultado.id_pago == "12345"
    assert resultado.nit_cliente == "900123456"
    assert resultado.fecha_pago == date.today()
    assert resultado.pago_extracto == Decimal("5000.00")
    assert len(resultado.facturas_pagadas) == 1
    assert resultado.facturas_pagadas[0].id_pedido == "001"
    assert resultado.tipo_cliente == TipoCliente.CREDITO
    assert resultado.deuda_total_anterior == Decimal("5000.00")
    assert resultado.deuda_restante == Decimal("0.00")

def test_cliente_model_invalid_data():
    with pytest.raises(ValueError):
        Cliente(
            id_cliente=123,  # Invalid type, should be str
            nit_cliente="900123456",
            razon_social="Empresa S.A.",
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=30
        )

    with pytest.raises(ValueError):
        Cliente(
            id_cliente="123",
            nit_cliente=900123456,  # Invalid type, should be str
            razon_social="Empresa S.A.",
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=30
        )

    with pytest.raises(ValueError):
        Cliente(
            id_cliente="123",
            nit_cliente="900123456",
            razon_social="Empresa S.A.",
            tipo_cliente="INVALID",  # Invalid enum value
            plazo_dias_credito=30
        )
    with pytest.raises(ValueError):
        Cliente(
            id_cliente="",  # Empty string, should not be allowed
            nit_cliente="900123456",
            razon_social="Empresa S.A.",
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=30
        )

    with pytest.raises(ValueError):
        Cliente(
            id_cliente="123",
            nit_cliente="",  # Empty string, should not be allowed
            razon_social="Empresa S.A.",
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=30
        )

    with pytest.raises(ValueError):
        Cliente(
            id_cliente="123",
            nit_cliente="900123456",
            razon_social="",  # Empty string, should not be allowed
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=30
        )

    with pytest.raises(ValueError):
        Cliente(
            id_cliente="123",
            nit_cliente="900123456",
            razon_social="Empresa S.A.",
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=-10  # Negative value, should not be allowed
        )



def test_pago_model_invalid_data():
    with pytest.raises(ValueError):
        Pago(
            nit_cliente="900123456",
            monto="1000.50",  # Invalid type, should be Decimal
            fecha_pago=date.today(),
            referencia_bancaria="Pago Factura 001"
        )

    with pytest.raises(ValueError):
        Pago(
            nit_cliente="900123456",
            monto=Decimal("1000.50"),
            fecha_pago="2023-01-01",  # Invalid type, should be date
            referencia_bancaria="Pago Factura 001"
        )
        
def test_pago_model_invalid_data_complement():
    with pytest.raises(ValueError):
        Pago(
            nit_cliente="",  # Empty string, should not be allowed
            monto=Decimal("1000.50"),
            fecha_pago=date.today(),
            referencia_bancaria="Pago Factura 001"
        )

    with pytest.raises(ValueError):
        Pago(
            nit_cliente="900123456",
            monto=Decimal("-1000.50"),  # Negative value, should not be allowed
            fecha_pago=date.today(),
            referencia_bancaria="Pago Factura 001"
        )

    with pytest.raises(ValueError):
        Pago(
            nit_cliente="900123456",
            monto=Decimal("1000.50"),
            fecha_pago=None,  # None value, should not be allowed
            referencia_bancaria="Pago Factura 001"
        )

    with pytest.raises(ValueError):
        Pago(
            nit_cliente="900123456",
            monto=Decimal("1000.50"),
            fecha_pago=date.today(),
            referencia_bancaria=""  # Empty string, should not be allowed
        )


def test_pedido_model_invalid_data_complement():
    with pytest.raises(ValueError):
        Pedido(
            id_pedido="",  # Empty string, should not be allowed
            estado_pedido=EstadoPedido.FACTURADO,
            nit_cliente="900123456",
            valor_neto=Decimal("5000.00"),
            fecha_pedido=date.today(),
            plazo_dias_credito=30
        )

    with pytest.raises(ValueError):
        Pedido(
            id_pedido="001",
            estado_pedido=EstadoPedido.FACTURADO,
            nit_cliente="",  # Empty string, should not be allowed
            valor_neto=Decimal("5000.00"),
            fecha_pedido=date.today(),
            plazo_dias_credito=30
        )

    with pytest.raises(ValueError):
        Pedido(
            id_pedido="001",
            estado_pedido=EstadoPedido.FACTURADO,
            nit_cliente="900123456",
            valor_neto=Decimal("-5000.00"),  # Negative value, should not be allowed
            fecha_pedido=date.today(),
            plazo_dias_credito=30
        )

    with pytest.raises(ValueError):
        Pedido(
            id_pedido="001",
            estado_pedido=EstadoPedido.FACTURADO,
            nit_cliente="900123456",
            valor_neto=Decimal("5000.00"),
            fecha_pedido=None,  # None value, should not be allowed
            plazo_dias_credito=30
        )

    with pytest.raises(ValueError):
        Pedido(
            id_pedido="001",
            estado_pedido=EstadoPedido.FACTURADO,
            nit_cliente="900123456",
            valor_neto=Decimal("5000.00"),
            fecha_pedido=date.today(),
            plazo_dias_credito=None     # None int, should not be allowed
        )


def test_resultado_pago_cliente_model_invalid_data():
    with pytest.raises(ValueError):
        ResultadoPagoCliente(
            id_pago="",  # Empty string, should not be allowed
            nit_cliente="900123456",
            fecha_pago=date.today(),
            pago_extracto=Decimal("5000.00"),
            facturas_pagadas=[],
            facturas_parciales=[],
            facturas_pendientes=[],
            tipo_cliente=TipoCliente.CREDITO,
            deuda_total_anterior=Decimal("5000.00"),
            deuda_restante=Decimal("0.00")
        )

    with pytest.raises(ValueError):
        ResultadoPagoCliente(
            id_pago="12345",
            nit_cliente="",  # Empty string, should not be allowed
            fecha_pago=date.today(),
            pago_extracto=Decimal("5000.00"),
            facturas_pagadas=[],
            facturas_parciales=[],
            facturas_pendientes=[],
            tipo_cliente=TipoCliente.CREDITO,
            deuda_total_anterior=Decimal("5000.00"),
            deuda_restante=Decimal("0.00")
        )

    with pytest.raises(ValueError):
        ResultadoPagoCliente(
            id_pago="12345",
            nit_cliente="900123456",
            fecha_pago=None,  # None value, should not be allowed
            pago_extracto=Decimal("5000.00"),
            facturas_pagadas=[],
            facturas_parciales=[],
            facturas_pendientes=[],
            tipo_cliente=TipoCliente.CREDITO,
            deuda_total_anterior=Decimal("5000.00"),
            deuda_restante=Decimal("0.00")
        )

    with pytest.raises(ValueError):
        ResultadoPagoCliente(
            id_pago="12345",
            nit_cliente="900123456",
            fecha_pago=date.today(),
            pago_extracto=Decimal("-5000.00"),  # Negative value, should not be allowed
            facturas_pagadas=[],
            facturas_parciales=[],
            facturas_pendientes=[],
            tipo_cliente=TipoCliente.CREDITO,
            deuda_total_anterior=Decimal("5000.00"),
            deuda_restante=Decimal("0.00")
        )

    with pytest.raises(ValueError):
        ResultadoPagoCliente(
            id_pago="12345",
            nit_cliente="900123456",
            fecha_pago=date.today(),
            pago_extracto=Decimal("5000.00"),
            facturas_pagadas=None,  # None value, should not be allowed
            facturas_parciales=[],
            facturas_pendientes=[],
            tipo_cliente=TipoCliente.CREDITO,
            deuda_total_anterior=Decimal("5000.00"),
            deuda_restante=Decimal("0.00")
        )

def test_pedido_model_invalid_data():
    with pytest.raises(ValueError):
        Pedido(
            id_pedido=1,  # Invalid type, should be str
            estado_pedido=EstadoPedido.FACTURADO,
            nit_cliente="900123456",
            valor_neto=Decimal("5000.00"),
            fecha_pedido=date.today(),
            forma_pago_raw="A 30 días"
        )

    with pytest.raises(ValueError):
        Pedido(
            id_pedido="001",
            estado_pedido=10,  # Invalid enum value
            nit_cliente="900123456",
            valor_neto=Decimal("5000.00"),
            fecha_pedido=date.today(),
            forma_pago_raw="A 30 días"
        )

    with pytest.raises(ValueError):
        Pedido(
            id_pedido="001",
            estado_pedido=EstadoPedido.FACTURADO,
            nit_cliente="900123456",
            valor_neto="5000.00",  # Invalid type, should be Decimal
            fecha_pedido=date.today(),
            forma_pago_raw="A 30 días"
        )

    with pytest.raises(ValueError):
        Pedido(
            id_pedido="001",
            estado_pedido=EstadoPedido.FACTURADO,
            nit_cliente="900123456",
            valor_neto=Decimal("5000.00"),
            fecha_pedido="2023-01-01",  # Invalid type, should be date
            forma_pago_raw="A 30 días"
        )
