# main.py
from annotated_types import T
from config.app_config import config as app_config
from di.container import Container
from domain.models.models import TipoCuentaBancaria


def main(fecha: str):
    # Initialize app_config (to ensure Firebase credentials are loaded)
    app_config.initialize_firebase()

    container = Container()
    container.config.directorio_pagos.from_value(app_config.directorio_pagos)
    container.config.fecha_pdf.from_value(fecha)
    container.config.firebase_database_url.from_value(app_config.firebase_database_url)
    container.config.directorio_reportes.from_value(
        app_config.directorio_reportes
    )

    caso_uso = container.emparejador_pagos()
    caso_uso.ejecutar(fecha, tipo_cuenta=TipoCuentaBancaria.AHORROS.value)
    caso_uso.ejecutar(fecha, tipo_cuenta=TipoCuentaBancaria.CORRIENTE.value)


if __name__ == "__main__":
    main("20250330")
