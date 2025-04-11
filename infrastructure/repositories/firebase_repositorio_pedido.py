# infrastructure/firebase/repositorio_pedidos_firebase.py
from config.app_config import config
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
        
        # Initialize Firebase
        config.initialize_firebase()

    def _mapear_pedido(self, id_pedido: str, data: Dict) -> Pedido:

        return Pedido(
            id_pedido=id_pedido,
            estado_pedido=EstadoPedido(data.get("estado", "")),
            nit_cliente=data["nit"],
            valor_neto=Decimal(str(data["valor"]["neto"])),
            fecha_pedido=datetime.strptime(
                data["hora_despacho"], "%d/%m/%Y %H:%M"
            ).date(),
            forma_pago_raw=data.get("forma_pago", ""),
            razon_social=data.get("razon_social", ""),
        )

    def obtener_pedidos_por_nit(self, nit: str) -> List[Pedido]:
        pedidos_crudos: Dict[str, Dict[str, Any]] = self.ref.get()
        # print("pedidos_crudos", pedidos_crudos)
        return [
            self._mapear_pedido(id_pedido, data)
            for id_pedido, data in pedidos_crudos.items()
            if data.get("nit") == nit
        ]

    def obtener_pedidos_credito(self) -> List[Pedido]:
        pedidos_crudos: Dict[str, Dict[str, Any]] = self.ref.get()
        return [
            self._mapear_pedido(id_pedido, data)
            for id_pedido, data in pedidos_crudos.items()
            if self._dias_en_forma_pago(data.get("forma_pago", ""))
        ]

    def _dias_en_forma_pago(self, forma_pago: str) -> bool:
        """
        Check if the forma_pago string contains the word "días" (case insensitive).
        This is used to determine if the payment type is credit or cash.
        """
        match = re.search(r"\bd[ií]as\b", forma_pago, re.IGNORECASE)
        return match is not None
