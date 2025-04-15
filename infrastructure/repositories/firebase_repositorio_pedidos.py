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
            
            # Manejar claves del diccionario
            nit = data.get("nit")
            estado_pedido = EstadoPedido(data.get("estado"))
            valor_neto = data.get("valor", {}).get("neto")
            hora_despacho_raw = data.get("hora_despacho")
            forma_pago_raw = data.get("forma_pago") # Default to empty string

            '''
            Valores falsy:
            - None
            - False
            - 0
            - "" (cadena vacía)
            - [], {}, set() (estructuras vacías)
            '''
            
            if (
                not nit or 
                not estado_pedido or
                not valor_neto or 
                not hora_despacho_raw
                ):
                raise ValueError(f"Pedido {id_pedido} carece de datos críticos.")

            valor_neto = Decimal(str(valor_neto))
            fecha_pedido = datetime.strptime(
                hora_despacho_raw, "%d/%m/%Y %H:%M").date()
            razon_social = data.get("razon", "")  # Default to empty string
            # Obtener el plazo de días de crédito
            if not forma_pago_raw:
                plazo_dias_credito = 0
            else:
                dias_match = re.search(
                    r"A\s+(\d+)\s+d[ií]as", forma_pago_raw, re.IGNORECASE
                )            
                plazo_dias_credito = int(dias_match.group(1)) if dias_match else 0

            return Pedido(
                    id_pedido=id_pedido,
                    estado_pedido=estado_pedido,
                    nit_cliente=nit,
                    plazo_dias_credito=plazo_dias_credito,
                    valor_neto=valor_neto,
                    fecha_pedido=fecha_pedido,
                    razon_social=razon_social,
                )

        except (ValueError, KeyError, TypeError) as e:
            # Log the error with more context
            print(f"Error mapeando pedido {id_pedido}")#: {e}. Data: {data}")
            raise ValueError(f"Fallo al mapear pedido {id_pedido}") from e

    def obtener_pedidos_por_nit(self, nit: str) -> List[Pedido]:
        # Obtener todos los pedidos de Firebase
        pedidos_crudos: Dict[str, Dict[str, Any]] = self.ref.get() or {}

        pedidos_a_credito_crudos = dict(filter(
            self._es_pedido_a_credito_valido,
            pedidos_crudos.items()
        ))
        
        pedidos_mapeados = []
        for id_pedido, data in pedidos_a_credito_crudos.items():
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
        
        pedidos_a_credito_crudos = dict(filter(
            self._es_pedido_a_credito_valido,
            pedidos_crudos.items()
        ))

        pedidos_mapeados = []
        pedidos_ignorados = 0
        for id_pedido, data in pedidos_a_credito_crudos.items():
            try:
                pedido = self._mapear_pedido(id_pedido, data)
                pedidos_mapeados.append(pedido)
            except ValueError as e:
                print(
                    f"Saltando {id_pedido} debido a error de conversión en {self.obtener_pedidos_credito.__qualname__}: {e}"
                )
                pedidos_ignorados += 1

        print(f"Se ignoraron {pedidos_ignorados} pedidos por error de conversión.")

        return pedidos_mapeados

    def _es_pedido_a_credito_valido(self, item: tuple[str, dict]) -> bool:
        """
        Verifica si un pedido es válido para ser considerado a crédito.
        Un pedido es válido si cumple con las siguientes condiciones:
        - La forma de pago contiene la palabra "días" (sin importar mayúsculas o minúsculas).
        - La hora de despacho no es None ni vacío.
        - El estado es 2 (DESPACHADO) o 5 (CREDITO_POBLACION).
        """
        # Desempaquetar el elemento
        _, data = item

        # Verificar las condiciones
        # Data no es None ni vacío
        if not data:
            return False
        # Forma de pago contiene "días"
        forma_pago = data.get("forma_pago", "")
        # Hora de despacho no es None ni vacío
        hora_despacho = data.get("hora_despacho")
        # Estado es 2 (DESPACHADO) o 5 (CREDITO_POBLACION)
        estado = data.get("estado")
        # Valor neto no es None ni vacío
        valor_neto = data.get("valor", {}).get("neto")        

        return (
            re.search(r"\bd[ií]as\b", forma_pago, re.IGNORECASE)
            and hora_despacho  # No vacío ni None
            and estado in {2, 5}  # DESPACHADO o CREDITO_POBLACION
            and valor_neto  # No vacío ni None
        )
