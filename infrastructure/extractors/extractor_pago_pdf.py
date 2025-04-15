# infrastructure/extractors/extractor_pago_pdf.py

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List
from application.ports.interfaces import AbstractExtractorPagos
from domain.models import Pago
from infrastructure.extractors.extractor_de_pagos_por_nit_bancolombia import ExtractorDePagosPorNitBancolombia

class ExtractorPagosPDF(AbstractExtractorPagos):
    """
    Clase que implementa la interfaz AbstractExtractorPagos para extraer datos de pagos desde un PDF.
    Utiliza la clase ExtractorDePagosPorNitBancolombia para realizar la extracción de datos.
    
    Atributos:
    - procesador: Instancia de ExtractorDePagosPorNitBancolombia para procesar el PDF.
    """

    def __init__(self, procesador_pdf: ExtractorDePagosPorNitBancolombia):
        self._procesador_pdf = procesador_pdf

    def obtener_pagos(self, fecha_pdf: str, tipo_cuenta: str) -> List[Pago]:
        # Asumiendo que procesador_pdf toma la fecha en formato YYYYMMDD
        pagos_dict: Dict[str, float] = self._procesador_pdf.extract_data(
            fecha_pdf=fecha_pdf, tipo_cuenta=tipo_cuenta
        )

        fecha_date: date = datetime.strptime(fecha_pdf, "%Y%m%d").date() # YYYMMDD
        return [
            Pago(nit_cliente=nit, monto=Decimal(str(monto)), fecha_pago=fecha_date, cuenta_ingreso_banco="", cuenta_egreso_banco="")
            for nit, monto in pagos_dict.items()
        ]
