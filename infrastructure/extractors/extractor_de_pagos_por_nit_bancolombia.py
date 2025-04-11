import os
import re
import json
import logging
from pypdf import PdfReader
from typing import Dict
from pydantic import BaseModel, Field

from .EXTRA_REF import EXTRA_REF

class ExtractorDePagosPorNitBancolombia(BaseModel):
    """
    Extractor for Bancolombia PDF files.
    This class extracts NIT and associated values from the PDF file.
    """
        
    directorio_bancolombia_data: str = Field(..., description="Directorio donde se encuentran las carpetas de Ahorro y Corriente de Bancolombia")

    def extract_data(self, fecha_pdf: str, tipo_cuenta: str) -> Dict[str, float]:
        """
        Extracts NIT and associated values from the PDF file.

        Returns:
            dict: A dictionary where the key is the NIT (str) and the value is a list of transaction amounts (float).
        """
        try:
            directorio_pdf = os.path.join(self.directorio_bancolombia_data, tipo_cuenta, f"{fecha_pdf}.pdf")
            reader = PdfReader(directorio_pdf)
            text = ""

            # Extract text from all pages in the PDF
            for page in reader.pages:
                text += page.extract_text()

            # Pattern to extract rows with the format (date, referencia 1, and valor)
            pattern = r"(\d{4}/\d{2}/\d{2})\s+.*?\s+(\d+)\s+\d+\s+([-\d.,]+)"

            data_dict = {}

            # Iterate over each match found using the pattern
            for match in re.finditer(pattern, text):
                nit_orig = match.group(2)

                if nit_orig.startswith("0"):
                    nit_cleaned = nit_orig.lstrip('0')
                    nit = EXTRA_REF.get(nit_cleaned, "")
                else:
                    nit = nit_orig

                if not nit:
                    continue

                description = match.group(1)
                valor_str = match.group(3)

                # Convert VALOR to float by removing commas
                valor = float(valor_str.replace(",", ""))

                # Filter positive values and skip rows with "ABONO INTERESES AHORROS"
                if valor > 0 and \
                        "ABONO INTERESES AHORROS" not in description:
                    # Add to the dictionary; append to the list if the key exists
                    if nit in data_dict:
                        data_dict[nit].append(valor)
                    else:
                        # Create a new list with the first value
                        data_dict[nit] = [valor]

            nit_pagos_total: Dict[str, float] = {k: sum(v) for k, v in data_dict.items()}

            return nit_pagos_total

        except Exception as e:
            logging.error(
                f"Error al obtener los datos del archivo .pdf >>> {e}",
                exc_info=True
            )
            return {}

if __name__ == "__main__":
    
    logging.basicConfig(
        filename="logs/resultado_extractor_de_pagos_por_nit_bancolombia.log",  # Log file name
        format="\n%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO  # Log level (INFO, DEBUG, ERROR, etc.)
    )

    pdf_name = "20250401" # Nombrado como YYYYMMDD
    base_path = r"G:\.shortcut-targets-by-id\1A2UP-JKrQvJV0SCMSD0IDa3ts-uOUJVR\Despachos\bancolombia_data"
    pdf_path = "\\".join([base_path, f"{pdf_name}.pdf"])
    extractor = ExtractorDePagosPorNitBancolombia(directorio_bancolombia_data=pdf_path)
    nit_pagos_totales: Dict = extractor.extract_data()
    logging.info(json.dumps(nit_pagos_totales, indent=4))

