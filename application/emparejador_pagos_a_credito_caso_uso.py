# application/emparejador_pagos_a_credito_caso_uso.py

from collections import defaultdict
from datetime import date
from typing import Dict, List
from application.ports.interfaces import (
    AbstractExtractorPagos,
    AbstractGeneradorReporte,
    AbstractRepositorioPedidos,
)
from domain.models.models import Cliente, Pago, Pedido
from domain.services.aplicador_de_pagos import AplicadorDePagos


class EmparejadorPagosACreditoCasoUso:
    """
    Clase encargada de generar el reporte de crédito a partir de los pagos y pedidos.
    Utiliza un extractor de pagos, un repositorio de pedidos y un generador de reportes.
    También aplica los pagos a los pedidos utilizando el servicio de dominio AplicadorDePagos.

    Dependencias:
    - extractor_pagos: Interfaz para la extracción de pagos.
    - repositorio_pedidos: Interfaz para el acceso a los pedidos.
    - generador_reporte: Interfaz para la generación de reportes.
    - aplicador_pagos: Servicio de dominio para aplicar pagos a los pedidos.
    """

    def __init__(
        self,
        extractor_pagos: AbstractExtractorPagos,
        repositorio_pedidos: AbstractRepositorioPedidos,
        generador_reporte: AbstractGeneradorReporte,
        aplicador_pagos: AplicadorDePagos,  # Inyectamos el servicio de dominio
    ):
        self.extractor_pagos = extractor_pagos
        self.repositorio_pedidos = repositorio_pedidos
        self.generador_reporte = generador_reporte
        self.aplicador_pagos = aplicador_pagos

    def ejecutar(self, fecha_pago: date, tipo_cuenta: str) -> None:
        """
        Ejecuta el caso de uso de cruzar pagos a crédito.
        Extrae los pagos, obtiene los pedidos de crédito y aplica los pagos a los pedidos.
        Genera un reporte con los resultados.
        """

        # 1. Obtener pagos y pedidos
        pagos: List[Pago] = self.extractor_pagos.obtener_pagos(fecha_pago, tipo_cuenta)
        pedidos: List[Pedido] = self.repositorio_pedidos.obtener_pedidos_credito()

        # 2. Agrupar pedidos por NIT de cliente
        pedidos_por_cliente: Dict[str, List[Pedido]] = defaultdict(list)
        for pedido in pedidos:
            pedidos_por_cliente[pedido.nit_cliente].append(pedido)

        # 3. Procesar cada pago
        for pago in pagos:
            nit = pago.nit_cliente
            if nit not in pedidos_por_cliente:
                continue  # No hay pedidos para este NIT

            pedidos_cliente = pedidos_por_cliente[nit]

            # Se crea el cliente a partir de los pedidos
            cliente = Cliente(
                id_cliente=nit,
                nit_cliente=nit,
                razon_social=pedidos_cliente[0].razon_social,
                tipo_cliente=pedidos_cliente[0].tipo_cliente,
                plazo_dias_credito=pedidos_cliente[0].plazo_dias_credito,
            )

            # 4. Aplicar pago a los pedidos del cliente
            resultado = self.aplicador_pagos.aplicar_pago_a_pedidos_cliente(
                pedidos_cliente,
                cliente,
                pago,
            )

            # 5. Generar reporte
            self.generador_reporte.generar(resultado, tipo_cuenta)
