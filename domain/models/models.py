# domain/models/models.py
from datetime import date, timedelta
import datetime
from decimal import Decimal
import re
from typing import Optional, List
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, validator
from enum import Enum

class TipoCuentaBancaria(str, Enum):
    """
    Enum para el tipo de cuenta:
        - AHORROS: Cuenta de ahorros
        - CORRIENTE: Cuenta corriente
    """

    AHORROS = "ahorros"
    CORRIENTE = "corriente"


class TipoCliente(str, Enum):
    """
    Enum para el tipo de cliente:
        - CONTADO: Cliente que paga al contado
        - CREDITO: Cliente que paga a crédito
    """

    CONTADO = "contado"
    CREDITO = "credito"


class EstadoPago(str, Enum):
    """
    Enum para el estado del pago de un pedido.
    Los estados son:
    - PENDIENTE: El pedido está pendiente de pago
    - PARCIAL: El pedido ha sido parcialmente pagado
    - PAGADO: El pedido ha sido completamente pagado
    """

    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    PAGADO = "pagado"


class EstadoPedido(int, Enum):
    """
    Enum para el estado del pedido en el sistema externo.
    """

    FACTURADO = 0
    EMPACADO = 1
    PENDIENTE = 3
    DESPACHADO = 2
    TESORERIA = 4
    CREDITO_POBLACION = 5


class Cliente(BaseModel):
    """
    Attr:
        - id_cliente: str = ID del cliente obtenido del sistema externo
        - nit_cliente: str = NIT o Cédula del cliente
        - razon_social: str = Nombre o Razón Social del cliente
        - tipo_cliente: TipoCliente = Tipo de cliente (Contado/Credito)
        - plazo_dias_credito: Optional[int] = Días de plazo si es a crédito
    """

    id_cliente: str = Field(
        ..., description="ID del cliente obtenido del sistema externo"
    )
    nit_cliente: str = Field(..., description="NIT o Cédula del cliente")
    razon_social: str = Field(..., description="Nombre o Razón Social del cliente")
    tipo_cliente: TipoCliente = Field(
        ..., description="Tipo de cliente (Contado/Credito)"
    )
    plazo_dias_credito: Optional[int] = Field(
        None, description="Días de plazo si es a crédito"
    )


class Pago(BaseModel):
    """
    Attr:
        - id_pago: str = ID único del pago (UUID generado a partir de la fecha y un UUID aleatorio)
        - nit_cliente: str = NIT del cliente que realiza el pago
        - cuenta_ingreso_banco: str = Cuenta contable de ingreso asociada al pago
        - cuenta_egreso_banco: str = Cuenta contable de egreso asociada al pago
        - monto: Decimal = Monto total del pago recibido
        - fechas_pago: date = Fecha en que se registró el pago (del extracto)
        - referencia_bancaria: Optional[str] = Referencia o descripción del pago en el extracto
    """

    id_pago: str = Field(
        default_factory=lambda: str(
            uuid.uuid5(uuid.NAMESPACE_DNS, f"{date.today()}-{uuid.uuid4()}")
        )
    )
    nit_cliente: str = Field(..., description="NIT del cliente que realiza el pago")
    cuenta_ingreso_banco: str = Field(
        ..., description="Cuenta contable de ingreso asociada al pago"
    )
    cuenta_egreso_banco: str = Field(
        ..., description="Cuenta contable de egreso asociada al pago"
    )
    monto: Decimal = Field(..., description="Monto total del pago recibido")
    fecha_pago: date = Field(
        ..., description="Fecha en que se registró el pago (del extracto)"
    )
    referencia_bancaria: Optional[str] = Field(
        None, description="Referencia o descripción del pago en el extracto"
    )


class Pedido(BaseModel):
    """
    Attr:
        - id_pedido: str = ID único del pedido/factura en Firebase
        - estado_pedido: int = Estado del pedido en el sistema externo (ej. 0, 1, 2, 3, 4, 5)
        - nit_cliente: str = NIT del cliente asociado al pedido
        - valor_neto: Decimal = Valor total del pedido/factura
        - valor_cobrado: Decimal = Valor ya abonado a este pedido
        - fecha_pedido: date = Fecha de creación/facturación del pedido
        - forma_pago_raw: str = Texto original de la forma de pago (guardamos el original por si acaso)
    """

    id_pedido: str = Field(
        ...,
        description="ID único del pedido/factura obtenido del sistema externo",
        strict = True, # Ensure it's a string
        min_length = 1,  # Ensure it's not empty
    )
    estado_pedido: EstadoPedido = Field(
        ...,
        description="Estado del pedido en el sistema externo (ej. 0, 1, 2, 3, 4, 5)",
    )
    nit_cliente: str = Field(
        ...,
        description="NIT del cliente asociado al pedido obtenido del sistema externo",
    )
    valor_neto: Decimal = Field(
        ..., description="Valor total del pedido/factura obtenido del sistema externo"
    )
    fecha_pedido: date = Field(
        ...,
        description="Fecha de creación/facturación del pedido obtenido del sistema externo",
    )
    forma_pago_raw: str = Field(
        ..., description="Texto original de la forma de pago"
    )  # Guardamos el original por si acaso}
    razon_social: Optional[str] = Field(
        None, description="Razón social del cliente asociado al pedido"
    )
    # --- Campos de Estado (gestionados por el servicio de dominio) ---
    estado_pago: EstadoPago = Field(
        EstadoPago.PENDIENTE, description="Estado actual del pago del pedido."
    )
    valor_cobrado: Decimal = Field(
        Decimal("0.0"),
        description="Valor ya abonado a este pedido. Se calcula en el servicio.",
    )
    fecha_pago_completado: Optional[date] = Field(
        None,
        description="Fecha en que se registró el pago que supera el porcentaje mínimo para considerar el pedido como pagado, dado en config/setting.py",
    )
    fechas_abono: List[date] = Field(
        [],
        description="Lista de fechas de abono del pedido",
    )
    factura_vencida: bool = Field(
        default=True,
        description="Indica si la factura está vencida (calculada al momento de la consulta)",
    )

    @field_validator("forma_pago_raw")
    def procesar_forma_pago(cls, value):
        """
        Valida o procesa el valor de forma_pago_raw durante la creación del objeto.
        """
        if not value:
            raise ValueError("forma_pago_raw no puede estar vacío.")
        return value

    @property
    def plazo_dias_credito(self) -> int:
        """
        Extrae el plazo en días de crédito desde forma_pago_raw.
        Si no se encuentra, devuelve 0, como sucede con los clientes a contado.
        """
        if not self.forma_pago_raw:
            return 0
        dias_match = re.search(
            r"A\s+(\d+)\s+d[ií]as", self.forma_pago_raw, re.IGNORECASE
        )
        return int(dias_match.group(1)) if dias_match else 0

    @property
    def tipo_cliente(self) -> TipoCliente:
        """
        Tipo de cliente (Contado/Credito)
        """
        return (
            TipoCliente.CONTADO if self.plazo_dias_credito == 0 else TipoCliente.CREDITO
        )

    @property
    def fecha_vencimiento(self) -> date:
        """
        Fecha de vencimiento del pedido.
        """
        return self.fecha_pedido + timedelta(
            days=self.plazo_dias_credito + 10
        )  # 10 días de gracia

    def actualizar_estado_vencimiento(self, fecha_referencia: date = date.today()):
        """Actualiza el estado de vencimiento según la fecha de referencia."""
        self.factura_vencida = (
            self.fecha_pago_completado is None
            or self.fecha_vencimiento < fecha_referencia
        )

    # @property
    # def saldo_pendiente(self) -> Decimal:
    #     """
    #     Calcula el saldo pendiente del pedido.
    #     """
    #     return self.valor_neto - self.valor_cobrado

    model_config = ConfigDict(frozen=False)


class ResultadoPagoCliente(BaseModel):
    """
    Attr:
        - nit_cliente: str = NIT del cliente asociado al pago
        - fecha_pago: date = Fecha en que se registró el pago (del extracto)
        - pago_extracto: Decimal = Monto total del pago recibido del extracto
        - deuda_restante: Decimal = Deuda restante después de aplicar el pago
        - facturas_pagadas: List[str] = IDs de las facturas que fueron pagadas con este pago
        - factura_parcial: Optional[str] = ID de la factura que fue parcialmente pagada
        - facturas_pendientes: List[str] = IDs de las facturas que siguen pendientes después del pago
        - id_pago: str = ID del pago generado en el sistema
    """

    id_pago: str = Field(
        ...,
        description="ID único del pago (UUID generado a partir de la fecha y un UUID aleatorio)",
    )
    nit_cliente: str = Field(..., description="NIT del cliente")
    fecha_pago: date = Field(
        ..., description="Fecha en que se registró el pago (del extracto)"
    )
    pago_extracto: Decimal = Field(
        ..., description="Monto total del pago recibido del extracto"
    )
    facturas_pagadas: List[Pedido] = Field(
        ..., description="IDs de las facturas que fueron pagadas con este pago"
    )
    factura_parcial: Optional[Pedido] = Field(
        None, description="ID de la factura que fue parcialmente pagada"
    )
    facturas_pendientes: List[Pedido] = Field(
        ..., description="IDs de las facturas que siguen pendientes después del pago"
    )
    tipo_cliente: TipoCliente = Field(
        ..., description="Tipo de cliente (Contado/Credito)"
    )
    # --- Resumen de Estado Post-Pago --- #
    deuda_total_anterior: Decimal = Field(
        ..., description="Deuda total antes de aplicar el pago"
    )
    deuda_restante: Decimal = Field(
        ..., description="Deuda restante después de aplicar el pago"
    )
