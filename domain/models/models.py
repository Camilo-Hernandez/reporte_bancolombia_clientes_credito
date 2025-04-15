# domain/models/models.py

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import config
from typing import Optional, List
from datetime import date, timedelta
import datetime
from decimal import Decimal
import re
from turtle import st
from typing import Optional, List, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from enum import Enum

from config.app_config import config


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
    
    Valor de los estados:
    - 0: Facturado
    - 1: Empacado
    - 2: Despachado
    - 3: Pendiente
    - 4: Tesorería
    - 5: Crédito Población
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
        ...,
        description="ID del cliente obtenido del sistema externo",
        strict=True,
        min_length=1,  # Ensure it's not empty
    )
    nit_cliente: str = Field(
        ...,
        description="NIT o Cédula del cliente",
        strict=True,
        min_length=1,  # Ensure it's not empty
        )
    razon_social: str = Field(
        ...,
        description="Nombre o Razón Social del cliente",
        strict=True,
        min_length=1,  # Ensure it's not empty
        )
    tipo_cliente: TipoCliente = Field(
        ...,
        description="Tipo de cliente (Contado/Credito)",
        strict=True,
        # min_length=1
    )
    plazo_dias_credito: int = Field(
        None,
        description="Días de plazo si es a crédito",
        strict=True,
    )
    @field_validator("plazo_dias_credito")
    def validate_plazo_dias_credito_non_negative(cls, value):
        if value < 0:
            raise ValueError(
                "El campo 'plazo_dias_credito' no puede ser negativo.")
        return value

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
    nit_cliente: str = Field(
        ...,
        description="NIT del cliente que realiza el pago",
        strict=True,  # Ensure it's a string
        min_length=1
    )
    monto: Decimal = Field(
        ...,
        description="Monto total del pago recibido",
        strict=True,  # Ensure it's a Decimal
    )
    fecha_pago: date = Field(
        ...,
        description="Fecha en que se registró el pago (del extracto)",
        strict=True,        
    )
    referencia_bancaria: Optional[str] = Field(
        None,
        description="Referencia o descripción del pago en el extracto",
        strict=True,
    )

    @field_validator("nit_cliente")
    def validate_nit_cliente(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError(
                "El campo 'nit_cliente' debe ser una cadena no vacía.")
        return value

    @field_validator("monto")
    def validate_monto(cls, value):
        if value < 0:
            raise ValueError("El campo 'monto' no puede ser negativo.")
        return value

    @field_validator("fecha_pago")
    def validate_fecha_pago(cls, value):
        if value is None or not isinstance(value, date):
            raise ValueError(
                "El campo 'fecha_pago' debe ser una fecha válida.")
        return value

    @field_validator("referencia_bancaria")
    def validate_referencia_bancaria(cls, value):
        if value is not None and value.strip() == "":
            raise ValueError(
                "El campo 'referencia_bancaria' no puede ser una cadena vacía.")
        return value

class Pedido(BaseModel):
    """
    Attr:
        - id_pedido: str = ID único del pedido/factura en Firebase
        - estado_pedido: int = Estado del pedido en el sistema externo (ej. 0, 1, 2, 3, 4, 5)
        - nit_cliente: str = NIT del cliente asociado al pedido
        - valor_neto: Decimal = Valor total del pedido/factura
        - valor_cobrado: Decimal = Valor ya abonado a este pedido
        - fecha_pedido: date = Fecha de creación/facturación del pedido
        - plazo_dias_credito: str = Texto original de la forma de pago (guardamos el original por si acaso)
    """

    id_pedido: str = Field(
        ...,
        description="ID único del pedido/factura obtenido del sistema externo",
        strict=True,  # Ensure it's a string
        min_length=1,  # Ensure it's not empty
    )
    estado_pedido: EstadoPedido = Field(
        ...,
        description="Estado del pedido en el sistema externo (ej. 0, 1, 2, 3, 4, 5)",
        strict=True, 
    )
    nit_cliente: str = Field(
        ...,
        strict=True,
        description="NIT del cliente asociado al pedido obtenido del sistema externo",
        min_length=1,
    )
    plazo_dias_credito: int = Field(
        0,
        description="Plazo de días de crédito del cliente asociado al pedido",
        strict=True,
        ge=0,  # Ensure it's a non-negative integer
    )
    valor_neto: Decimal = Field(
        ...,
        description="Valor total del pedido/factura obtenido del sistema externo",
        strict=True,
    )
    fecha_pedido: date = Field(
        ...,
        description="Fecha de creación/facturación del pedido obtenido del sistema externo",
        strict=True,
    )
    razon_social: str = Field(
        None,
        description="Razón social del cliente asociado al pedido",
        strict=True,
    )
    # --- Campos de Estado (gestionados por el servicio de dominio) ---
    estado_pago: EstadoPago = Field(
        EstadoPago.PENDIENTE,
        strict=True,
        description="Estado actual del pago del pedido.",
        min_length=1
    )
    valor_cobrado: Decimal = Field(
        Decimal("0.0"),
        strict=True,
        description="Valor ya abonado a este pedido. Se calcula en el servicio.",
    )
    fechas_abono: List[date] = Field(
        [],  
        strict=True,
        description="Lista de fechas de abono del pedido",
    )
    fecha_pago_completado: Union[date, None] = Field(
        None,
        strict=True,
        description="Fecha en que se registró el pago que supera el porcentaje mínimo para considerar el pedido como pagado, dado en config/setting.py",
    )
    factura_vencida: bool = Field(
        default=False,
        strict=True,
        description="Indica si la factura está vencida (calculada al momento de la consulta)",
    )

    # Permitir cambios post-creación
    model_config = ConfigDict(frozen=False, strict=True)

    @field_validator("valor_neto", "valor_cobrado")
    @classmethod
    def validar_valores_no_negativos(cls, value):
        if value < 0:
            raise ValueError("Debe ser un valor no negativo")
        return value


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
            days=self.plazo_dias_credito + config.dias_gracia_vencimiento
        )

    def _actualizar_factura_vencida(self) -> None:
        referencia = self.fecha_pago_completado or date.today()
        self.factura_vencida = self.fecha_vencimiento <= referencia

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in {"fecha_pedido", "plazo_dias_credito", "fecha_pago_completado"}:
            try:
                self._actualizar_factura_vencida()
            except Exception:
                pass  # Evita errores durante validación o creación temprana del modelo




class ResultadoPagoCliente(BaseModel):
    """
    Attr:
        - nit_cliente: str = NIT del cliente asociado al pago
        - fecha_pago: date = Fecha en que se registró el pago (del extracto)
        - pago_extracto: Decimal = Monto total del pago recibido del extracto
        - deuda_restante: Decimal = Deuda restante después de aplicar el pago. Puede ser positivo si aún debe o negativo si tiene a favor.
        - facturas_pagadas: List[Pedido] = Facturas que fueron pagadas con este pago
        - facturas_parciales: List[Pedido] = Facturas que están o fueron parcialmente pagadas
        - facturas_pendientes: List[Pedido] = Facturas que siguen pendientes después del pago
        - id_pago: str = ID del pago generado en el sistema
    """

    id_pago: str = Field(
        ...,
        description="ID único del pago (UUID generado a partir de la fecha y un UUID aleatorio)",
        strict=True,
        min_length=1
    )
    nit_cliente: str = Field(
        ...,
        description="NIT del cliente",
        strict=True,
        min_length=1
        )
    fecha_pago: date = Field(
        ...,
        description="Fecha en que se registró el pago (del extracto)",
        strict=True,
    )
    pago_extracto: Decimal = Field(
        ...,
        description="Monto total del pago recibido del extracto",
        strict=True,
        gt=0,  # Ensure it's a positive value
    )
    facturas_pagadas: List[Pedido] = Field(
        ..., 
        description="IDs de las facturas que fueron pagadas con este pago",
        strict=True,
    )
    facturas_parciales: List[Pedido] = Field(
        None, 
        description="ID de la factura que fue parcialmente pagada",
        strict=True,
    )
    facturas_pendientes: List[Pedido] = Field(
        ..., 
        description="IDs de las facturas que siguen pendientes después del pago",
        strict=True,
    )
    tipo_cliente: TipoCliente = Field(
        ..., 
        description="Tipo de cliente (Contado/Credito)",
        strict=True,
        min_length=1
    )
    # --- Resumen de Estado Post-Pago --- #
    deuda_total_anterior: Decimal = Field(
        ..., 
        description="Deuda total antes de aplicar el pago",
        strict=True,
    )
    deuda_restante: Decimal = Field(
        ..., 
        description="Deuda restante después de aplicar el pago",
        strict=True,
    )

    @field_validator("pago_extracto")
    def validate_pago_extracto_non_negative(cls, value):
        if value < 0:
            raise ValueError(
                "The 'pago_extracto' field must be a non-negative value.")
        return value

    @field_validator("deuda_total_anterior")
    def validate_deuda_total_anterior_non_negative(cls, value):
        if value < 0:
            raise ValueError(
                "The 'deuda_total_anterior' field must be a non-negative value.")
        return value
