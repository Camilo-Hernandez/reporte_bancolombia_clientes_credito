# infrastructure/txt/generador_reporte_txt.py

import re
from config.app_config import config
import os
import logging
from application.ports.interfaces import AbstractGeneradorReporte
from domain.models.models import ResultadoPagoCliente, TipoCuentaBancaria


def manejar_excepciones(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error ejecutando {func.__name__} >>> {e}", exc_info=True)

    return wrapper


class GeneradorReporteTxt(AbstractGeneradorReporte):

    def __init__(
        self,
        fecha_pdf: str,
        directorio_reportes: str,
    ):
        """
        Generador de reportes en formato TXT.
        Este generador crea un archivo TXT para cada pedido pagado y lo guarda en un directorio específico.

        Dependencias:
        - fecha_pdf (str): Fecha del reporte en formato YYYYMMDD.
        - directorio_reportes (str): Directorio donde se guardarán los reportes generados.
        """
        # Validate fecha format (YYYYMMDD)
        if not re.match(
            r"^(?:20\d{2})(?:(?:(?:0[13578]|1[02])(?:0[1-9]|[12]\d|3[01]))|(?:(?:0[469]|11)(?:0[1-9]|[12]\d|30))|(?:02(?:0[1-9]|1\d|2[0-9])))$",
            fecha_pdf,
        ):
            raise ValueError("El formato de la fecha debe ser YYYYMMDD.")

        self._directorio_reportes = directorio_reportes
        self._fecha_pdf = fecha_pdf

    @manejar_excepciones
    def generar(self, resultado: ResultadoPagoCliente, tipo_cuenta: str) -> None:
        # Crea el directorio de salida si no existe
        directorio_final = os.path.join(
            self._directorio_reportes, tipo_cuenta, self._fecha_pdf
        )
        os.makedirs(directorio_final, exist_ok=True)
        # Genera el nombre del archivo y lo crea
        for i, pedido in enumerate(
            resultado.facturas_pagadas + [resultado.factura_parcial], start=1
        ):
            # Crea el nombre del archivo
            # El nombre del archivo es el NIT del cliente seguido de un número secuencial
            # (1, 2, 3, ...) que representa el pedido i de la lista de pedidos pagados
            archivo = os.path.join(
                directorio_final,
                f"{resultado.nit_cliente}_{i}.txt",
            )
            with open(archivo, "w") as file:
                if tipo_cuenta == TipoCuentaBancaria.AHORROS.value:
                    cuentas_bancarias = config.cuentas_ingreso_egreso_ahorro
                else:
                    cuentas_bancarias = config.cuentas_ingreso_egreso_corriente

                for cuenta in cuentas_bancarias:
                    row = [""] * 16
                    row[0] = cuenta
                    row[1] = resultado.nit_cliente
                    row[3] = pedido.id_pedido
                    row[5] = (
                        str(pedido.valor_cobrado)
                        if cuenta[:2] == "11"
                        else str(pedido.valor_cobrado * -1)
                    )
                    line = ",".join(row)
                    file.write(line + "\n")
