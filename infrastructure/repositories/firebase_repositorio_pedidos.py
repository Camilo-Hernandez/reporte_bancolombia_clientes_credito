# infrastructure/repositories/firebase_repositorio_pedido.py

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Dict
from application.ports.interfaces import AbstractRepositorioPedidos
from firebase_admin.db import Reference 
from domain.models.models import Pedido
from domain.models.models import EstadoPedido


class FirebaseRepositorioPedidos(AbstractRepositorioPedidos):
    """
    Repositorio de pedidos que utiliza Firebase como backend.
    Implementa la interfaz AbstractRepositorioPedidos.
    
    Atributos:
        - ref: Referencia a la base de datos de Firebase.
    """

    def __init__(self, firebase_reference: Reference):
        self.ref = firebase_reference

    def _mapear_pedido(self, id_pedido: str, data: Dict) -> Pedido:

        try: 
            estado_val = data.get("estado")
            estado_pedido = EstadoPedido(estado_val) if estado_val is not None else EstadoPedido.PENDIENTE # Or another sensible default

            # Handle potential missing keys more gracefully
            nit = data.get("nit")
            valor_data = data.get("valor", {})
            valor_neto_raw = valor_data.get("neto")
            hora_despacho_raw = data.get("hora_despacho")
            forma_pago = data.get("forma_pago", "") # Default to empty string
            razon_social = data.get("razon_social", "") # Default to empty string

            if not nit or valor_neto_raw is None or not hora_despacho_raw:
                # Log this error or raise a specific exception if a pedido MUST have these fields
                # print(f"Skipping pedido {id_pedido} due to missing critical data: nit={nit}, valor_neto={valor_neto_raw}, hora_despacho={hora_despacho_raw}")
                # Depending on requirements, you might want to return None or raise an error
                # For now, let's raise to make it explicit during debugging
                raise ValueError(f"Pedido {id_pedido} missing critical data.")

            fecha_pedido = datetime.strptime(hora_despacho_raw, "%d/%m/%Y %H:%M").date()
            valor_neto = Decimal(str(valor_neto_raw))

            return Pedido(
                    id_pedido=id_pedido,
                    estado_pedido=estado_pedido,
                    nit_cliente=nit,
                    valor_neto=valor_neto,
                    fecha_pedido=fecha_pedido,
                    forma_pago_raw=forma_pago,
                    razon_social=razon_social,
                )

        except (ValueError, KeyError, TypeError) as e:
            # Log the error with more context
            # print(f"Error mapping pedido {id_pedido}")#: {e}. Data: {data}")
            # Depending on how critical failures are, either raise the error,
            # return None, or return a default/error Pedido object.
            # Raising is often best during development.
            raise ValueError(f"Failed to map pedido {id_pedido}") from e

    def obtener_pedidos_por_nit(self, nit: str) -> List[Pedido]:
        pedidos_crudos: Dict[str, Dict[str, Any]] = (
            self.ref.get() or {}
        )  # Handle case where ref.get() returns None
        pedidos_mapeados = []
        for id_pedido, data in pedidos_crudos.items():
            if id_pedido is None or not id_pedido.strip():
                continue  # Skip empty or None IDs
            if data and data.get("nit") == nit:  # Check if data is not None/empty
                try:
                    pedido = self._mapear_pedido(id_pedido, data)
                    pedidos_mapeados.append(pedido)
                except ValueError as e:
                    continue
                    # Log or handle the mapping error for this specific pedido
                    # print(f"Skipping pedido {id_pedido} for NIT {nit} due to mapping error: {e}"                    )
        return pedidos_mapeados

    def obtener_pedidos_credito(self) -> List[Pedido]:
        pedidos_crudos: Dict[str, Dict[str, Any]] = (
            self.ref.get() or {}
        )  # Handle case where ref.get() returns None
        pedidos_mapeados = []
        for id_pedido, data in pedidos_crudos.items():
            if data and self._dias_en_forma_pago(
                data.get("forma_pago", "")
            ):  # Check if data is not None/empty
                try:
                    pedido = self._mapear_pedido(id_pedido, data)
                    pedidos_mapeados.append(pedido)
                except ValueError as e:
                    # Log or handle the mapping error for this specific pedido
                    print(
                        # f"Skipping pedido {id_pedido} (credito check) due to mapping error: {e}"
                    )

        return pedidos_mapeados

    def _dias_en_forma_pago(self, forma_pago: str) -> bool:
        """
        Check if the forma_pago string contains the word "días" (case insensitive).
        This is used to determine if the payment type is credit or cash.
        """
        if not isinstance(forma_pago, str): # Add type check for safety
            return False

        match = re.search(r"\bd[ií]as\b", forma_pago, re.IGNORECASE)
        return match is not None
