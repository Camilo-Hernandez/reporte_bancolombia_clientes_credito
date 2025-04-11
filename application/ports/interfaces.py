# domain/ports/repositorio_pedidos.py
from abc import ABC, abstractmethod
from typing import List
from datetime import date
from domain.models.models import Pago, Pedido, ResultadoPagoCliente

# Interfaces abstractas para los adaptadores de entrada y salida

class AbstractRepositorioPedidos(ABC):
    @abstractmethod
    def obtener_pedidos_credito(self) -> List[Pedido]:
        pass


class AbstractExtractorPagos(ABC):
    @abstractmethod
    def obtener_pagos(self, fecha: str, tipo_cuenta: str) -> List[Pago]:
        pass


class AbstractGeneradorReporte(ABC):
    @abstractmethod
    def generar(self, resultado: ResultadoPagoCliente, tipo_cuenta: str) -> None:
        pass
