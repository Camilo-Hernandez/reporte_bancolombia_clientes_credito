# domain/services/aplicador_de_pagos.py
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Tuple
from config.app_config import config  # Importa la instancia Singleton

from domain.models.models import (
    Cliente,
    EstadoPago,
    EstadoPedido,
    Pago,
    Pedido,
    ResultadoPagoCliente,
)


class AplicadorDePagos:
    """
    Clase para aplicar pagos a pedidos de un cliente.
    Esta clase contiene métodos para filtrar, ordenar y aplicar pagos a los pedidos de un cliente.
    También calcula la deuda total y restante después de aplicar el pago.
    Los métodos son estáticos y no requieren instanciar la clase.
    """

    @staticmethod
    def aplicar_pago_a_pedidos_cliente(
        pedidos: List[Pedido],
        cliente: Cliente,
        pago: Pago,
    ) -> ResultadoPagoCliente:
        """
        Aplica un único pago a los pedidos pendientes de un cliente.
        Modifica el estado de los pedidos en la lista `pedidos_pendientes_cliente` IN-PLACE
        y devuelve un resumen del resultado.
        """
        if not pedidos:
            raise ValueError("La lista de pedidos no puede estar vacía.")
        if not cliente or not isinstance(cliente, Cliente):
            raise ValueError(
                "El cliente debe ser una instancia válida de Cliente.")
        if not pago or not isinstance(pago, Pago):
            raise ValueError("El pago debe ser una instancia válida de Pago.")
        if pago.monto <= 0:
            raise ValueError("El monto del pago debe ser mayor que cero.")
        if pago.fecha_pago > datetime.now().date():
            raise ValueError("La fecha de pago no puede ser futura.")

        # 1. Filtrar y ordenar pedidos
        pedidos_por_pagar = AplicadorDePagos._filtrar_y_ordenar_pedidos(
            pedidos, cliente
        )

        # 2. Separar pedidos vencidos y no vencidos
        vencidos, no_vencidos = AplicadorDePagos._separar_pedidos_por_vencimiento(
            pedidos_por_pagar
        )

        # 3. Aplicar pagos a los pedidos
        pedidos_por_prioridad = vencidos + no_vencidos
        saldo_restante, facturas_pagadas, facturas_parciales, facturas_pendientes = (
            AplicadorDePagos._aplicar_pagos(
                pedidos_por_prioridad, pago.monto, pago.fecha_pago
            )
        )

        # 4. Calcular deuda total y restante
        deuda_total, deuda_restante = AplicadorDePagos._calcular_deuda(
            pedidos_por_pagar, pago.monto, saldo_restante
        )

        # 5. Construir el resultado
        return AplicadorDePagos._construir_resultado(
            cliente=cliente,
            pago=pago,
            facturas_pagadas=facturas_pagadas,
            facturas_parciales=facturas_parciales,
            facturas_pendientes=facturas_pendientes,
            deuda_total_anterior=deuda_total,
            deuda_restante=deuda_restante,
        )

    @staticmethod
    def _filtrar_y_ordenar_pedidos(
        pedidos: List[Pedido], cliente: Cliente
    ) -> List[Pedido]:
        """
        Filtra los pedidos pendientes o parciales del cliente y los ordena por fecha y monto.
        """
        pedidos_filtrados = [
            p
            for p in pedidos
            if p.id_pedido is not None
            and p.fecha_pedido is not None
            and p.fecha_pedido is not ""
            and p.fecha_pedido >= datetime.now().date() - timedelta(days=config.dias_maximo_pedido)
            and p.valor_neto is not None
            and p.valor_neto > 0
            and p.nit_cliente == cliente.nit_cliente
            and p.estado_pedido
            in [EstadoPedido.DESPACHADO, EstadoPedido.CREDITO_POBLACION]
            and p.estado_pago != EstadoPago.PAGADO
        ]
        pedidos_filtrados.sort(key=lambda p: (p.fecha_pedido, p.valor_neto))
        return pedidos_filtrados

    @staticmethod
    def _separar_pedidos_por_vencimiento(
        pedidos: List[Pedido],
    ) -> Tuple[List[Pedido], List[Pedido]]:
        """
        Separa los pedidos en vencidos y no vencidos.
        """
        vencidos = [pedido for pedido in pedidos if pedido.factura_vencida]
        no_vencidos = [
            pedido for pedido in pedidos if not pedido.factura_vencida]
        return vencidos, no_vencidos

    @staticmethod
    def _aplicar_pagos(
        pedidos: List[Pedido], saldo_restante: Decimal, fecha_pago: date
    ) -> Tuple[Decimal, List[Pedido], List[Pedido], List[Pedido]]:
        """
        Aplica un saldo disponible a una lista de pedidos, distribuyendo el pago según prioridades.

        Args:
            pedidos: Lista de objetos Pedido a procesar, ordenados por prioridad (ej: antigüedad).
            saldo_restante: Monto disponible para aplicar a pagos (debe ser positivo). Inicializa en pago.monto
            fecha_pago: Fecha en que se realiza el pago (usada para auditoría).

        Returns:
            Tuple con:
            - Saldo remanente después de aplicar pagos (Decimal)
            - IDs de facturas completamente pagadas (List[str])
            - ID de factura con pago parcial (Optional[str])
            - IDs de facturas pendientes por pagar (List[str])

        """

        # Inicialización de listas para resultados
        facturas_pagadas = []  # Pedidos pagados en su totalidad
        facturas_parciales = []  # Pedidos con pago parcial
        facturas_pendientes = []  # Pedidos no cubiertos por el saldo

        for pedido in pedidos:
            if pedido.fecha_pedido > fecha_pago:
                # Si la fecha de pedido es futura, no se aplica el pago
                facturas_pendientes.append(pedido)
                continue

            # Si no hay saldo disponible, marcar el resto como pendientes
            if saldo_restante <= 0:
                if pedido.estado_pago == EstadoPago.PARCIAL:
                    facturas_parciales.append(pedido)
                elif pedido.estado_pago == EstadoPago.PENDIENTE:
                    facturas_pendientes.append(pedido)
                elif pedido.estado_pago == EstadoPago.PAGADO:
                    raise ValueError(
                        f"El pedido {pedido.id_pedido} (NIT: {pedido.nit_cliente}) ya está pagado y debió filtrarse primero desde cartera."
                    )
                continue

            saldo_pendiente_pedido = pedido.valor_neto - pedido.valor_cobrado

            # Caso 1: Saldo cubre el 100% del pedido
            # Caso 2: Saldo cubre el pedido por debajo de la tolerancia máxima permitida
            if (
                saldo_restante >= saldo_pendiente_pedido or
                saldo_restante >= saldo_pendiente_pedido - config.tolerancia_maxima
            ):
                pedido.valor_cobrado = pedido.valor_neto  # Marcar como pagado
                pedido.estado_pago = EstadoPago.PAGADO  # Actualizar estado de pago
                saldo_restante -= saldo_pendiente_pedido  # Reducir saldo restante
                pedido.fecha_pago_completado = fecha_pago
                facturas_pagadas.append(pedido)  # Registrar factura pagada

                # Agregar a la lista de pagos sólo si fue una transición de parcial a completo
                if saldo_pendiente_pedido > 0:
                    pedido.fechas_abono.append(fecha_pago)

            # Caso 3: Saldo solo cubre parcialmente el pedido
            else:
                pedido.valor_cobrado += saldo_restante  # Acumular abono
                pedido.estado_pago = EstadoPago.PARCIAL  # Actualizar estado de pago
                saldo_restante = Decimal("0")  # Saldo se agota
                facturas_parciales.append(pedido)  # Registrar factura parcial
                # Registrar abono parcial
                pedido.fechas_abono.append(fecha_pago)

                # Verificar si el abono alcanza el mínimo requerido para considerar "no vencido"
                if (pedido.valor_cobrado / pedido.valor_neto) >= Decimal(
                    str(config.porcentaje_minimo_pedido_pagado)
                ):
                    # Considerar como "completado" si cumple el mínimo
                    pedido.fecha_pago_completado = fecha_pago

        return saldo_restante, facturas_pagadas, facturas_parciales, facturas_pendientes

    @staticmethod
    def _calcular_deuda(
        pedidos: List[Pedido], monto_pago: Decimal, saldo_restante: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """
        Calcula la deuda total y la deuda restante después de aplicar el pago.
        Maneja correctamente créditos (valores negativos).
        """
        deuda_total = Decimal(sum(p.valor_neto for p in pedidos))
        # Si el saldo restante es negativo, significa que se ha pagado de más
        deuda_restante = deuda_total - (monto_pago - saldo_restante)
        assert isinstance(deuda_total, Decimal)
        assert isinstance(deuda_restante, Decimal)
        return deuda_total, deuda_restante

    @staticmethod
    def _construir_resultado(
        cliente: Cliente,
        pago: Pago,
        facturas_pagadas: List[Pedido],
        facturas_parciales: List[Pedido],
        facturas_pendientes: List[Pedido],
        deuda_total_anterior: Decimal,
        deuda_restante: Decimal,
    ) -> ResultadoPagoCliente:
        """
        Construye el objeto ResultadoPagoCliente con los datos procesados.
        """
        return ResultadoPagoCliente(
            id_pago=pago.id_pago,
            nit_cliente=cliente.nit_cliente,
            fecha_pago=pago.fecha_pago,
            pago_extracto=pago.monto,
            facturas_pagadas=facturas_pagadas,
            facturas_parciales=facturas_parciales,
            facturas_pendientes=facturas_pendientes,
            tipo_cliente=cliente.tipo_cliente,
            deuda_total_anterior=deuda_total_anterior,
            deuda_restante=deuda_restante,
        )
