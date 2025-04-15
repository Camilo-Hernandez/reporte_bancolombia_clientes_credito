# tests\domain\test_aplicador_de_pagos.py

from pydoc import cli
import pytest
from datetime import date, timedelta
from decimal import Decimal
from domain.models.models import (
    Cliente,
    EstadoPago,
    EstadoPedido,
    Pago,
    Pedido,
    TipoCliente,
)
from domain.services.aplicador_de_pagos import AplicadorDePagos


@pytest.fixture
def cliente_credito():
    return Cliente(
        id_cliente="cli-001",
        nit_cliente="123456789",
        razon_social="Cliente de Prueba",
        tipo_cliente=TipoCliente.CREDITO,
        plazo_dias_credito=30,
    )


@pytest.fixture
def cliente_contado():
    return Cliente(
        id_cliente="cli-002",
        nit_cliente="987654321",
        razon_social="Cliente Contado",
        tipo_cliente=TipoCliente.CONTADO,
    )


@pytest.fixture
def pago_base(cliente_credito):
    return Pago(
        nit_cliente=cliente_credito.nit_cliente,
        cuenta_ingreso_banco="ING001",
        cuenta_egreso_banco="EGR001",
        monto=Decimal("1000.00"),
        fecha_pago=date.today(),
    )


def crear_pedido(
    id_pedido,
    nit_cliente,
    plazo_dias_credito,
    valor_neto,
    fecha_pedido,
    estado_pedido=EstadoPedido.DESPACHADO,
    estado_pago=EstadoPago.PENDIENTE,
    valor_cobrado=Decimal("0.00"),
):
    return Pedido(
        id_pedido=id_pedido,
        estado_pedido=estado_pedido,
        nit_cliente=nit_cliente,
        plazo_dias_credito=plazo_dias_credito,
        valor_neto=Decimal(valor_neto),
        fecha_pedido=fecha_pedido,
        valor_cobrado=Decimal(valor_cobrado),
        estado_pago=estado_pago,
    )


@pytest.fixture
def pedido_base(cliente_credito):
    return crear_pedido(
        id_pedido="ped-001",
        nit_cliente=cliente_credito.nit_cliente,
        plazo_dias_credito=cliente_credito.plazo_dias_credito,
        valor_neto="1000000.00",
        fecha_pedido=date.today() - timedelta(days=10),
    )

@pytest.fixture
def pedidos_base(cliente_credito):
    return [
        crear_pedido(
            id_pedido="ped-001",
            nit_cliente=cliente_credito.nit_cliente,
            plazo_dias_credito=cliente_credito.plazo_dias_credito + 10,
            valor_neto="300000.00",
            fecha_pedido=date.today() - timedelta(days=15),
        ),
        crear_pedido(
            id_pedido="ped-002",
            nit_cliente=cliente_credito.nit_cliente,
            plazo_dias_credito=cliente_credito.plazo_dias_credito + 10,
            valor_neto="200000.00",
            fecha_pedido=date.today() - timedelta(days=10),
        ),
        crear_pedido(
            id_pedido="ped-003",
            nit_cliente=cliente_credito.nit_cliente,
            plazo_dias_credito=cliente_credito.plazo_dias_credito + 10,
            valor_neto="500000.00",
            fecha_pedido=date.today() - timedelta(days=5),
        ),
    ]


class TestAplicadorDePagos:

    # 1. Complete payment for a single order
    def test_pago_completo_un_pedido(self, cliente_credito, pago_base, pedido_base):
        # + 10 días de gracia
        pago_base.monto = Decimal("1000000.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido_base], cliente_credito, pago_base
        )

        assert pedido_base.estado_pago == EstadoPago.PAGADO
        assert pedido_base.valor_cobrado == Decimal("1000000.00")
        assert resultado.facturas_pagadas[0].id_pedido == "ped-001"
        assert resultado.facturas_pagadas == [pedido_base]
        assert resultado.facturas_parciales == []
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_total_anterior == Decimal("1000000.00")
        assert resultado.deuda_restante == Decimal("0.00")

    # 2. Partial payment for a single order
    def test_pago_parcial_un_pedido(self, cliente_credito, pago_base, pedido_base):
        pago_base.monto = Decimal("300000.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido_base], cliente_credito, pago_base
        )

        assert pedido_base.estado_pago == EstadoPago.PARCIAL
        assert pedido_base.valor_cobrado == Decimal("300000.00")
        assert resultado.facturas_pagadas == []
        assert resultado.facturas_parciales == [pedido_base]
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_restante == Decimal("700000.00")

    # 3. Payment for multiple orders
    def test_pago_multiples_pedidos_completos(self, cliente_credito, pago_base, pedidos_base):

        pago_base.monto = Decimal("1000000.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos_base, cliente_credito, pago_base
        )

        assert all(p.estado_pago == EstadoPago.PAGADO for p in pedidos_base)
        assert resultado.facturas_pagadas == pedidos_base
        assert resultado.facturas_parciales == []
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_restante == Decimal("0.00")

    # 4. Partial payment for multiple orders
    def test_pago_parcial_multiples_pedidos(self, cliente_credito, pago_base, pedidos_base):
        
        pago_base.monto = Decimal("400000.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos_base, cliente_credito, pago_base
        )

        assert pedidos_base[0].estado_pago == EstadoPago.PAGADO
        assert pedidos_base[1].estado_pago == EstadoPago.PARCIAL
        assert pedidos_base[2].estado_pago == EstadoPago.PENDIENTE
        assert resultado.facturas_pagadas == pedidos_base[:1]
        assert resultado.facturas_parciales == [pedidos_base[1]]
        assert resultado.facturas_pendientes == [pedidos_base[2]]
        assert resultado.deuda_restante == Decimal("600000.00")

    # 5. Priority for overdue orders
    def test_prioridad_pedidos_vencidos(self, cliente_credito, pago_base):
        # El pedido 1 y 3 están vencidos, pero el 1 es más antiguo
        pedidos = [
            crear_pedido(
                id_pedido="ped-001",
                nit_cliente=cliente_credito.nit_cliente,
                plazo_dias_credito=cliente_credito.plazo_dias_credito + 10,
                valor_neto="20000.00",
                fecha_pedido=date.today() - timedelta(days=60),
            ),
            crear_pedido(
                id_pedido="ped-002",
                nit_cliente=cliente_credito.nit_cliente,
                plazo_dias_credito=cliente_credito.plazo_dias_credito + 10,
                valor_neto="50000.00",
                fecha_pedido=date.today() - timedelta(days=5),
            ),
            crear_pedido(
                id_pedido="ped-003",
                nit_cliente=cliente_credito.nit_cliente,
                plazo_dias_credito=cliente_credito.plazo_dias_credito + 10,
                valor_neto="30000.00",
                fecha_pedido=date.today() - timedelta(days=45),
            ),
        ]
        pago_base.monto = Decimal("40000.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        # Debería pagar primero los vencidos (ped-001 y ped-003) aunque ped-002 es más reciente
        assert pedidos[0].estado_pago == EstadoPago.PAGADO  # ped-001
        # ped-003 (parcial)
        assert pedidos[2].estado_pago == EstadoPago.PARCIAL
        assert pedidos[1].estado_pago == EstadoPago.PENDIENTE  # ped-002
        assert resultado.facturas_pagadas == [pedidos[0]]
        assert resultado.facturas_parciales == [pedidos[2]]
        assert resultado.facturas_pendientes == [pedidos[1]]

    # 6. Payment exceeding total debt
    def test_pago_excede_deuda_total(self, cliente_credito, pago_base, pedidos_base):
        pago_base.monto = Decimal("1000001.00") # Pago que supera la deuda total por 1.00

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos_base, cliente_credito, pago_base
        )

        assert all(p.estado_pago == EstadoPago.PAGADO for p in pedidos_base)
        assert resultado.facturas_pagadas == pedidos_base
        assert resultado.facturas_parciales == []
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_restante == Decimal("0.00")
        assert resultado.pago_extracto - sum(p.valor_neto for p in pedidos_base) == Decimal("1.00")

    # 7. Filtering of already paid orders
    def test_filtrado_pedidos_ya_pagados(self, cliente_credito, pago_base):
        pedidos = [
            # Pedido ya pagado
            crear_pedido(
                id_pedido="ped-001",
                nit_cliente=cliente_credito.nit_cliente,
                plazo_dias_credito=cliente_credito.plazo_dias_credito + 10,
                valor_neto="300000.00",
                fecha_pedido=date.today() - timedelta(days=10),
                estado_pago=EstadoPago.PAGADO,
                valor_cobrado=Decimal("300000.00"),
            ),
            # Pedido pendiente
            crear_pedido(
                id_pedido="ped-002",
                nit_cliente=cliente_credito.nit_cliente,
                plazo_dias_credito=cliente_credito.plazo_dias_credito + 10,
                valor_neto="200000.00",
                fecha_pedido=date.today() - timedelta(days=5),
            ),
        ]
        pago_base.monto = Decimal("300000.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        # No debería cambiar
        assert pedidos[0].estado_pago == EstadoPago.PAGADO
        assert pedidos[1].estado_pago == EstadoPago.PAGADO  # Nuevo pago
        assert resultado.pago_extracto == Decimal("300000.00")
        assert resultado.deuda_total_anterior == Decimal("200000.00")
        assert resultado.deuda_restante == Decimal("-100000.00")
        assert resultado.facturas_pagadas == pedidos[1:]
        assert resultado.facturas_parciales == []
        assert resultado.facturas_pendientes == []
        assert resultado.facturas_pagadas[0].id_pedido == "ped-002"
        assert resultado.facturas_pagadas[0].valor_cobrado == Decimal("200000.00")
        assert resultado.facturas_pagadas[0].estado_pago == EstadoPago.PAGADO
        assert resultado.facturas_pagadas[0].fechas_abono == [date.today()]
        assert resultado.facturas_pagadas[0].fecha_pago_completado == date.today(
        )

    # 8. Pagar 1 pedido parcial y otro pendiente
    def test_pagar_un_pedido_parcial_y_otro_pendiente(self, cliente_credito, pago_base):
        pedidos = [
            # Pedido parcialmente pagado
            crear_pedido(
                id_pedido="ped-001",
                nit_cliente=cliente_credito.nit_cliente,
                plazo_dias_credito=cliente_credito.plazo_dias_credito + 10,
                valor_neto="300000.00",
                fecha_pedido=date.today() - timedelta(days=10),
                estado_pago=EstadoPago.PARCIAL,
                valor_cobrado=Decimal("200000.00"), # Debe 100000.00
            ),
            # Pedido pendiente
            crear_pedido(
                id_pedido="ped-002",
                nit_cliente=cliente_credito.nit_cliente,
                plazo_dias_credito=cliente_credito.plazo_dias_credito + 10,
                valor_neto="200000.00",
                fecha_pedido=date.today() - timedelta(days=5),
            ),
        ]
        pago_base.monto = Decimal("300000.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        assert pedidos[0].estado_pago == EstadoPago.PAGADO
        assert pedidos[1].estado_pago == EstadoPago.PAGADO
        assert resultado.pago_extracto == Decimal("300000.00")
        assert resultado.deuda_total_anterior == Decimal("300000.00")
        assert resultado.facturas_pagadas == pedidos[:]
        assert resultado.facturas_parciales == []
        assert resultado.deuda_restante == Decimal("0.00")
        assert resultado.fecha_pago == date.today()
        assert resultado.nit_cliente == cliente_credito.nit_cliente
        assert resultado.id_pago == pago_base.id_pago
        assert resultado.tipo_cliente == cliente_credito.tipo_cliente
        assert resultado.facturas_parciales == []
        assert resultado.facturas_pendientes == []
        assert resultado.facturas_pagadas[0].id_pedido == "ped-001"
        assert resultado.facturas_pagadas[0].valor_cobrado == Decimal(
            "100000.00")
        assert resultado.facturas_pagadas[0].estado_pago == EstadoPago.PAGADO
        assert resultado.facturas_pagadas[0].fechas_abono == [date.today()]
        assert resultado.facturas_pagadas[0].fecha_pago_completado == date.today()
        assert resultado.facturas_pagadas[1].id_pedido == "ped-002"

    # 8. Order sorting by date and amount
    def test_ordenamiento_pedidos_fecha_monto(self, cliente_credito, pago_base):
        pedidos = [
            crear_pedido(
                "ped-001",
                cliente_credito.nit_cliente,
                "300.00",
                date.today() - timedelta(days=10),
            ),
            crear_pedido(
                "ped-002",
                cliente_credito.nit_cliente,
                "200.00",
                date.today() - timedelta(days=15),
            ),
            crear_pedido(
                "ped-003",
                cliente_credito.nit_cliente,
                "400.00",
                date.today() - timedelta(days=10),
            ),
        ]
        pago_base.monto = Decimal("500.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        # Debería procesar primero ped-002 (más antiguo), luego ped-001 (mismo día que ped-003 pero menor monto)
        assert resultado.facturas_pagadas == [pedidos[1], pedidos[0]]
        assert pedidos[0].estado_pago == EstadoPago.PAGADO  # ped-001
        assert resultado.facturas_parciales == []
        assert pedidos[0].valor_cobrado == Decimal("300.00")  # ped-001
        assert pedidos[1].valor_cobrado == Decimal("200.00")  # ped-002
        assert pedidos[2].valor_cobrado == Decimal(
            "0.00")  # ped-003 (pendiente)

    # 9. Validation of incorrect inputs
    def test_validacion_entradas_incorrectas(self, cliente_credito, pago_base):
        pedido_valido = crear_pedido(
            "ped-001",
            cliente_credito.nit_cliente,
            "100.00",
            date.today() - timedelta(days=5),
        )

        with pytest.raises(
            ValueError, match="La lista de pedidos no puede estar vacía"
        ):
            AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
                [], cliente_credito, pago_base
            )

        with pytest.raises(
            ValueError, match="El cliente debe ser una instancia válida de Cliente"
        ):
            AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
                [pedido_valido], None, pago_base
            )

        with pytest.raises(
            ValueError, match="El pago debe ser una instancia válida de Pago"
        ):
            AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
                [pedido_valido], cliente_credito, None
            )

    # 10. Result contains correct information
    def test_resultado_contiene_informacion_correcta(self, cliente_credito, pago_base):
        pedidos = [
            crear_pedido(
                "ped-001",
                cliente_credito.nit_cliente,
                "5000000.00",
                date.today() - timedelta(days=10),
            ),
            crear_pedido(
                "ped-002",
                cliente_credito.nit_cliente,
                "3000000.00",
                date.today() - timedelta(days=5),
            ),
        ]
        pago_base.monto = Decimal("6000000.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        assert resultado.id_pago == pago_base.id_pago
        assert resultado.nit_cliente == cliente_credito.nit_cliente
        assert resultado.fecha_pago == pago_base.fecha_pago
        assert resultado.pago_extracto == pago_base.monto
        assert resultado.facturas_pagadas == [pedidos[0]]
        assert resultado.facturas_parciales == [pedidos[1]]
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_total_anterior == Decimal("8000000.00")
        assert resultado.deuda_restante == Decimal("2000000.00")
        assert resultado.tipo_cliente == cliente_credito.tipo_cliente

    # 11. Cliente con pedidos pero no coinciden por NIT
    def test_pedidos_no_coinciden_nit_cliente(self, cliente_credito, pago_base):
        otro_cliente = Cliente(
            id_cliente="cli-999",
            nit_cliente="999999999",
            razon_social="Otro Cliente",
            tipo_cliente=TipoCliente.CREDITO,
            plazo_dias_credito=30,
        )

        pedidos = [
            crear_pedido(
                "ped-001",
                otro_cliente.nit_cliente,  # NIT diferente
                "500.00",
                date.today() - timedelta(days=10),
            ),
        ]
        pago_base.monto = Decimal("500.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        # No debería aplicar el pago a ningún pedido
        assert resultado.facturas_pagadas == []
        assert resultado.facturas_parciales == []
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_restante == Decimal("0.00")

    # 12. Cliente con pedidos pero no tiene un pago de 0
    def test_pago_monto_cero(self, cliente_credito, pago_base):
        pedidos = [
            crear_pedido("ped-001", cliente_credito.nit_cliente,
                         "500.00", date.today())
        ]
        pago_base.monto = Decimal("0.00")

        with pytest.raises(
            ValueError, match="El monto del pago debe ser mayor que cero."
        ):
            AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
                pedidos, cliente_credito, pago_base
            )

    # 13. Cliente paga exactamente el monto de un pedido
    def test_pago_monto_exacto(self, cliente_credito, pago_base):
        pedido = crear_pedido(
            "ped-001", cliente_credito.nit_cliente, "327.50", date.today()
        )
        pago_base.monto = Decimal("327.50")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago_base
        )

        assert pedido.estado_pago == EstadoPago.PAGADO
        assert pedido.valor_cobrado == Decimal("327.50")

    # 14. Se registran 2 pagos parciales y se completa el pedido
    def test_acumulacion_pagos_parciales(self, cliente_credito):
        pedido = crear_pedido(
            "ped-001", cliente_credito.nit_cliente, "1000000.00", date.today()
        )

        # First partial payment (600)
        pago1 = Pago(
            nit_cliente=cliente_credito.nit_cliente,
            cuenta_ingreso_banco="ING001",
            cuenta_egreso_banco="EGR001",
            monto=Decimal("600000.00"),
            fecha_pago=date.today(),
        )
        resultado1 = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago1
        )

        # Verify first payment state
        assert pedido.estado_pago == EstadoPago.PARCIAL
        assert pedido.valor_cobrado == Decimal("600000.00")
        assert pedido.fechas_abono == [date.today()]
        assert pedido.fecha_pago_completado is None

        # Second partial payment (400)
        pago2 = Pago(
            nit_cliente=cliente_credito.nit_cliente,
            cuenta_ingreso_banco="ING001",
            cuenta_egreso_banco="EGR001",
            monto=Decimal("400000.00"),
            fecha_pago=date.today(),
        )
        resultado2 = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago2
        )

        # Verify final state
        assert pedido.estado_pago == EstadoPago.PAGADO
        assert pedido.valor_cobrado == Decimal("1000000.00")
        assert len(pedido.fechas_abono) == 2
        assert pedido.fechas_abono == [date.today(), date.today()]
        assert pedido.fecha_pago_completado == date.today()

    # 15. Pago con monto negativo lanza error
    def test_pago_monto_negativo(self, cliente_credito, pago_base):
        pedidos = [
            crear_pedido("ped-001", cliente_credito.nit_cliente,
                         "500.00", date.today())
        ]
        pago_base.monto = Decimal("-100.00")

        with pytest.raises(
            ValueError, match="El monto del pago debe ser mayor que cero."
        ):
            AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
                pedidos, cliente_credito, pago_base
            )

    # 16. Pago registrado con un NIT diferente al cliente no afecta el estado del pedido del cliente
    def test_pago_nit_cliente_diferente(self, cliente_credito):
        otro_cliente = Cliente(
            id_cliente="cli-999",
            nit_cliente="999999999",
            razon_social="Otro Cliente",
            tipo_cliente=TipoCliente.CREDITO,
        )
        pedidos = [
            crear_pedido("ped-001", otro_cliente.nit_cliente,
                         "500.00", date.today())
        ]
        pago = Pago(
            nit_cliente=cliente_credito.nit_cliente,  # Different NIT
            cuenta_ingreso_banco="ING001",
            cuenta_egreso_banco="EGR001",
            monto=Decimal("500.00"),
            fecha_pago=date.today(),
        )

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago
        )

        assert resultado.facturas_pagadas == []
        assert resultado.deuda_restante == Decimal("0.00")

    # 17. Pago con decimales extendidos
    def test_pago_con_decimales_extendidos(self, cliente_credito):
        pedido = crear_pedido(
            "ped-001", cliente_credito.nit_cliente, "123.456789", date.today()
        )
        pago = Pago(
            nit_cliente=cliente_credito.nit_cliente,
            cuenta_ingreso_banco="ING001",
            cuenta_egreso_banco="EGR001",
            monto=Decimal("123.456789"),
            fecha_pago=date.today(),
        )

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago
        )

        assert pedido.valor_cobrado == Decimal("123.456789")

    # 18. Pago a pedido parcialmente pagado
    def test_pago_a_pedido_parcialmente_pagado(self, cliente_credito):
        pedido = crear_pedido(
            "ped-001",
            cliente_credito.nit_cliente,
            "1000.00",
            date.today(),
            estado_pago=EstadoPago.PARCIAL,
            valor_cobrado=Decimal("400.00"),
        )
        pago = Pago(
            nit_cliente=cliente_credito.nit_cliente,
            cuenta_ingreso_banco="ING001",
            cuenta_egreso_banco="EGR001",
            monto=Decimal("600.00"),
            fecha_pago=date.today(),
        )

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago
        )

        assert pedido.estado_pago == EstadoPago.PAGADO
        assert pedido.valor_cobrado == Decimal("1000.00")

    def test_pago_fecha_anterior_a_pedido(self, cliente_credito):
        pedido = crear_pedido(
            "ped-001", cliente_credito.nit_cliente, "500.00", date.today()
        )

        pago = Pago(
            nit_cliente=cliente_credito.nit_cliente,
            cuenta_ingreso_banco="ING001",
            cuenta_egreso_banco="EGR001",
            monto=Decimal("500.00"),
            fecha_pago=date.today()
            - timedelta(days=1),  # Payment date before order date
        )

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago
        )

        assert pedido.estado_pago == EstadoPago.PENDIENTE  # Should not change to PAGADO
        assert pedido.valor_cobrado == Decimal("0.00")  # No payment applied

    # 19. Factura aún está no vencida la fecha de vencimiento, y vencida después de la fecha de vencimiento
    def test_factura_no_vencida_fecha_vencimiento(self, cliente_credito):
        # Pedido 1 no vencido (dentro de los 30 días de crédito + 10 días de gracia)
        # A punto de vencerse
        pedido1 = crear_pedido(
            id_pedido="ped-001",
            nit_cliente=cliente_credito.nit_cliente,
            valor_neto="1000000.00",
            # + 10 días de gracia
            fecha_pedido=date.today() - timedelta(days=40),
            plazo_dias_credito=cliente_credito.plazo_dias_credito,
        )

        # Pedido 2 vencido por 1 día
        pedido2 = crear_pedido(
            id_pedido="ped-002",
            nit_cliente=cliente_credito.nit_cliente,
            valor_neto="1000000.00",
            # + 10 días de gracia
            fecha_pedido=date.today() - timedelta(days=41),
            plazo_dias_credito=cliente_credito.plazo_dias_credito,
        )

        pago = Pago(
            nit_cliente=cliente_credito.nit_cliente,
            monto=Decimal("1.00"),
            fecha_pago=date.today(),
        )

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido1, pedido2], cliente_credito, pago
        )

        assert pedido1.fecha_pago_completado == None
        assert pedido1.fecha_vencimiento == date.today()
        assert pedido1.factura_vencida == False
        assert pedido1.estado_pago == EstadoPago.PENDIENTE
        assert pedido1.valor_cobrado == Decimal("0.00")
        assert pedido1.fechas_abono == []

        assert pedido2.fecha_pago_completado == None
        assert pedido2.fecha_vencimiento == date.today() - timedelta(days=1)
        assert pedido2.factura_vencida == True
        assert pedido2.estado_pago == EstadoPago.PARCIAL
        assert pedido2.valor_cobrado == Decimal("1.00")
        assert pedido2.fechas_abono == [date.today()]

    # 20. Si el pedido no está vencido y ya se cobró el 90% del pedido, se considera como no vencido
    # aún después de que pase la fecha de vencimiento
    def test_pago_minimo_para_considerar_no_vencido(self, cliente_credito):

        # Pedido 1 no vencido (dentro de los 30 días de crédito + 10 días de gracia)
        pedido = crear_pedido(
            "ped-001",
            cliente_credito.nit_cliente,
            "1000000.00",
            date.today() - timedelta(days=40),
        )

        assert pedido.factura_vencida == False
        assert pedido.fecha_vencimiento == date.today()

        pago = Pago(
            nit_cliente=cliente_credito.nit_cliente,
            cuenta_ingreso_banco="ING001",
            cuenta_egreso_banco="EGR001",
            monto=Decimal("900000.00"),  # Exactly 90%
            fecha_pago=date.today(),
        )

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago
        )

        assert pedido.fecha_pago_completado == date.today()
        assert pedido.estado_pago == EstadoPago.PARCIAL
        assert pedido.valor_cobrado == Decimal("900000.00")
        assert pedido.fechas_abono == [date.today()]
