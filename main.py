# main.py

from annotated_types import T
from config.app_config import config as app_config
from di.container import Container
from domain.models.models import TipoCuentaBancaria


def main(fecha: str):
    # Initialize app_config (to ensure Firebase credentials are loaded)
    # Beware this must be done only once in the main thread of the whole application
    # and before any Firebase operation is performed.
    app_config.initialize_firebase()

    container = Container()
    # Configure the container with values from app_config
    container.config.directorio_pagos.from_value(app_config.directorio_pagos)
    container.config.directorio_reportes.from_value(
        app_config.directorio_reportes
    )

    container.config.fecha_pdf.from_value(fecha)

    # Wire up dependencies (this will now correctly use the single Firebase connection)
    container.wire(modules=[__name__])  # Optional: explicit wiring

    caso_uso = container.emparejador_pagos()
    # Execute the use case
    try:
        print(f"\n\nEjecutando para Ahorros - Fecha: {fecha}")
        caso_uso.ejecutar(fecha, tipo_cuenta=TipoCuentaBancaria.AHORROS.value)
        print(f"\n\nEjecutando para Corriente - Fecha: {fecha}")
        caso_uso.ejecutar(fecha, tipo_cuenta=TipoCuentaBancaria.CORRIENTE.value)
        print("Ejecución completada.")
    except Exception as e:
        print(f"Error durante la ejecución del caso de uso: {e}")
        # Add more specific error handling or logging if needed
        import traceback

        traceback.print_exc()

    # Unwire if you wired explicitly
    container.unwire()


if __name__ == "__main__":
    main("20250301")
