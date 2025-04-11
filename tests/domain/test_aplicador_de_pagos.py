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
    valor_neto,
    fecha_pedido,
    estado_pedido=EstadoPedido.DESPACHADO,
    estado_pago=EstadoPago.PENDIENTE,
    valor_cobrado=Decimal("0.00"),
    forma_pago_raw="A 30 días",
):
    return Pedido(
        id_pedido=id_pedido,
        estado_pedido=estado_pedido,
        nit_cliente=nit_cliente,
        valor_neto=Decimal(valor_neto),
        valor_cobrado=Decimal(valor_cobrado),
        fecha_pedido=fecha_pedido,
        forma_pago_raw=forma_pago_raw,
        estado_pago=estado_pago,
    )


class TestAplicadorDePagos:
    # 1. Complete payment for a single order
    def test_pago_completo_un_pedido(self, cliente_credito, pago_base):
        pedido = crear_pedido(
            "ped-001",
            cliente_credito.nit_cliente,
            "500.00",
            date.today() - timedelta(days=10),
        )
        pago_base.monto = Decimal("500.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago_base
        )

        assert pedido.estado_pago == EstadoPago.PAGADO
        assert pedido.valor_cobrado == Decimal("500.00")
        assert resultado.facturas_pagadas[0].id_pedido == "ped-001"
        assert resultado.facturas_pagadas == [pedido]
        assert resultado.factura_parcial is None
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_restante == Decimal("0.00")

    # 2. Partial payment for a single order
    def test_pago_parcial_un_pedido(self, cliente_credito, pago_base):
        pedido = crear_pedido(
            "ped-001",
            cliente_credito.nit_cliente,
            "1000.00",
            date.today() - timedelta(days=10),
        )
        pago_base.monto = Decimal("300.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago_base
        )

        assert pedido.estado_pago == EstadoPago.PARCIAL
        assert pedido.valor_cobrado == Decimal("300.00")
        assert resultado.facturas_pagadas == []
        assert resultado.factura_parcial == pedido
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_restante == Decimal("700.00")

    # 3. Payment for multiple orders
    def test_pago_multiples_pedidos_completos(self, cliente_credito, pago_base):
        pedidos = [
            crear_pedido(
                "ped-001",
                cliente_credito.nit_cliente,
                "300.00",
                date.today() - timedelta(days=15),
            ),
            crear_pedido(
                "ped-002",
                cliente_credito.nit_cliente,
                "200.00",
                date.today() - timedelta(days=10),
            ),
            crear_pedido(
                "ped-003",
                cliente_credito.nit_cliente,
                "500.00",
                date.today() - timedelta(days=5),
            ),
        ]
        pago_base.monto = Decimal("1000.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        assert all(p.estado_pago == EstadoPago.PAGADO for p in pedidos)
        assert resultado.facturas_pagadas == pedidos
        assert resultado.factura_parcial is None
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_restante == Decimal("0.00")

    # 4. Partial payment for multiple orders
    def test_pago_parcial_multiples_pedidos(self, cliente_credito, pago_base):
        pedidos = [
            crear_pedido(
                "ped-001",
                cliente_credito.nit_cliente,
                "500.00",
                date.today() - timedelta(days=15),
            ),
            crear_pedido(
                "ped-002",
                cliente_credito.nit_cliente,
                "300.00",
                date.today() - timedelta(days=10),
            ),
            crear_pedido(
                "ped-003",
                cliente_credito.nit_cliente,
                "200.00",
                date.today() - timedelta(days=5),
            ),
        ]
        pago_base.monto = Decimal("600.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        assert pedidos[0].estado_pago == EstadoPago.PAGADO
        assert pedidos[1].estado_pago == EstadoPago.PARCIAL
        assert pedidos[2].estado_pago == EstadoPago.PENDIENTE
        assert resultado.facturas_pagadas == pedidos[:1]
        assert resultado.factura_parcial == pedidos[1]
        assert resultado.facturas_pendientes == [pedidos[2]]
        assert resultado.deuda_restante == Decimal("400.00")

    # 5. Priority for overdue orders
    def test_prioridad_pedidos_vencidos(self, cliente_credito, pago_base):
        pedidos = [
            crear_pedido(
                "ped-001",
                cliente_credito.nit_cliente,
                "200.00",
                date.today() - timedelta(days=60),  # Vencido
            ),
            crear_pedido(
                "ped-002",
                cliente_credito.nit_cliente,
                "500.00",
                date.today() - timedelta(days=5),  # No vencido
            ),
            crear_pedido(
                "ped-003",
                cliente_credito.nit_cliente,
                "300.00",
                date.today() - timedelta(days=45),  # Vencido
            ),
        ]
        # Marcar pedidos como vencidos
        for p in pedidos:
            p.actualizar_estado_vencimiento()

        pago_base.monto = Decimal("400.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        # Debería pagar primero los vencidos (ped-001 y ped-003) aunque ped-002 es más reciente
        assert pedidos[0].estado_pago == EstadoPago.PAGADO  # ped-001
        assert pedidos[2].estado_pago == EstadoPago.PARCIAL  # ped-003 (parcial)
        assert pedidos[1].estado_pago == EstadoPago.PENDIENTE  # ped-002
        assert resultado.facturas_pagadas == [pedidos[0]]
        assert resultado.factura_parcial == pedidos[2]
        assert resultado.facturas_pendientes == [pedidos[1]]

    # 6. Payment exceeding total debt
    def test_pago_excede_deuda_total(self, cliente_credito, pago_base):
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
                date.today() - timedelta(days=5),
            ),
        ]
        pago_base.monto = Decimal("600.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        assert all(p.estado_pago == EstadoPago.PAGADO for p in pedidos)
        assert resultado.facturas_pagadas == pedidos
        assert resultado.factura_parcial is None
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_restante == Decimal("0.00")
        # El saldo restante debería ser 100 (600 - 500)
        assert resultado.pago_extracto - sum(p.valor_neto for p in pedidos) == Decimal(
            "100.00"
        )

    # 7. Filtering of already paid orders
    def test_filtrado_pedidos_ya_pagados(self, cliente_credito, pago_base):
        pedidos = [
            crear_pedido(
                "ped-001",
                cliente_credito.nit_cliente,
                "300.00",
                date.today() - timedelta(days=10),
                estado_pago=EstadoPago.PAGADO,
                valor_cobrado=Decimal("300.00"),
            ),
            crear_pedido(
                "ped-002",
                cliente_credito.nit_cliente,
                "200.00",
                date.today() - timedelta(days=5),
            ),
        ]
        pago_base.monto = Decimal("300.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        assert pedidos[0].estado_pago == EstadoPago.PAGADO  # No debería cambiar
        assert pedidos[1].estado_pago == EstadoPago.PAGADO  # Nuevo pago
        assert resultado.facturas_pagadas == pedidos[1:]
        assert resultado.factura_parcial is None
        assert resultado.deuda_restante == Decimal("0.00")

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
        assert resultado.factura_parcial == None
        assert pedidos[0].valor_cobrado == Decimal("300.00")  # ped-001
        assert pedidos[1].valor_cobrado == Decimal("200.00")  # ped-002
        assert pedidos[2].valor_cobrado == Decimal("0.00")  # ped-003 (pendiente)

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
                "500.00",
                date.today() - timedelta(days=10),
            ),
            crear_pedido(
                "ped-002",
                cliente_credito.nit_cliente,
                "300.00",
                date.today() - timedelta(days=5),
            ),
        ]
        pago_base.monto = Decimal("600.00")

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            pedidos, cliente_credito, pago_base
        )

        assert resultado.id_pago == pago_base.id_pago
        assert resultado.nit_cliente == cliente_credito.nit_cliente
        assert resultado.fecha_pago == pago_base.fecha_pago
        assert resultado.pago_extracto == pago_base.monto
        assert resultado.facturas_pagadas == [pedidos[0]]
        assert resultado.factura_parcial == pedidos[1]
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_total_anterior == Decimal("800.00")
        assert resultado.deuda_restante == Decimal("200.00")
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
        assert resultado.factura_parcial is None
        assert resultado.facturas_pendientes == []
        assert resultado.deuda_restante == Decimal("0.00")

    def test_pago_monto_cero(self, cliente_credito, pago_base):
        pedidos = [
            crear_pedido("ped-001", cliente_credito.nit_cliente, "500.00", date.today())
        ]
        pago_base.monto = Decimal("0.00")

        with pytest.raises(
            ValueError, match="El monto del pago debe ser mayor que cero."
        ):
            AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
                pedidos, cliente_credito, pago_base
            )

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

    def test_acumulacion_pagos_parciales(self, cliente_credito):
        pedido = crear_pedido(
            "ped-001", cliente_credito.nit_cliente, "1000.00", date.today()
        )

        # First partial payment (600)
        pago1 = Pago(
            nit_cliente=cliente_credito.nit_cliente,
            cuenta_ingreso_banco="ING001",
            cuenta_egreso_banco="EGR001",
            monto=Decimal("600.00"),
            fecha_pago=date.today(),
        )
        resultado1 = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago1
        )

        # Verify first payment state
        assert pedido.estado_pago == EstadoPago.PARCIAL
        assert pedido.valor_cobrado == Decimal("600.00")
        assert pedido.fechas_abono == [date.today()]
        assert pedido.fecha_pago_completado is None

        # Second partial payment (400)
        pago2 = Pago(
            nit_cliente=cliente_credito.nit_cliente,
            cuenta_ingreso_banco="ING001",
            cuenta_egreso_banco="EGR001",
            monto=Decimal("400.00"),
            fecha_pago=date.today(),
        )
        resultado2 = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago2
        )

        # Verify final state
        assert pedido.estado_pago == EstadoPago.PAGADO
        assert pedido.valor_cobrado == Decimal("1000.00")
        assert len(pedido.fechas_abono) == 2
        assert pedido.fechas_abono == [date.today(), date.today()]
        assert pedido.fecha_pago_completado == date.today()

    def test_pago_monto_negativo(self, cliente_credito, pago_base):
        pedidos = [
            crear_pedido("ped-001", cliente_credito.nit_cliente, "500.00", date.today())
        ]
        pago_base.monto = Decimal("-100.00")

        with pytest.raises(
            ValueError, match="El monto del pago debe ser mayor que cero."
        ):
            AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
                pedidos, cliente_credito, pago_base
            )

    def test_pago_nit_cliente_diferente(self, cliente_credito):
        otro_cliente = Cliente(
            id_cliente="cli-999",
            nit_cliente="999999999",
            razon_social="Otro Cliente",
            tipo_cliente=TipoCliente.CREDITO,
        )
        pedidos = [
            crear_pedido("ped-001", otro_cliente.nit_cliente, "500.00", date.today())
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

    def test_pago_minimo_para_considerar_pagado(self, cliente_credito):
        pedido = crear_pedido(
            "ped-001", cliente_credito.nit_cliente, "1000.00", date.today()
        )
        # Asumiendo config.porcentaje_minimo_pedido_pagado = 0.9 (90%)
        pago = Pago(
            nit_cliente=cliente_credito.nit_cliente,
            cuenta_ingreso_banco="ING001",
            cuenta_egreso_banco="EGR001",
            monto=Decimal("900.00"),  # Exactly 90%
            fecha_pago=date.today(),
        )

        resultado = AplicadorDePagos.aplicar_pago_a_pedidos_cliente(
            [pedido], cliente_credito, pago
        )

        assert pedido.estado_pago == EstadoPago.PARCIAL
        assert pedido.fecha_pago_completado == date.today()
