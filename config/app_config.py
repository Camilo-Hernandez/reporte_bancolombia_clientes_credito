import os
import firebase_admin
from firebase_admin import credentials

class AppConfig:
    _instance = None

    _firebase_database_url = "https://emes-digital-cartera.firebaseio.com"

    # Porcentaje mínimo del valor del pedido para considerarlo como no vencido dentro de la fecha de vencimiento
    _porcentaje_minimo_pedido_pagado = 0.9  # Valor predeterminado

    # Cuentas contables para ingresos y egresos
    _cuentas_contables_ingreso_egreso_corriente = ("11100501", "130505")
    _cuentas_contables_ingreso_egreso_ahorro = ("11200501", "130505")

    # Directorio de donde se extraen los reportes de pagos (extractos bancarios)
    _directorio_pagos = "G:\.shortcut-targets-by-id\1A2UP-JKrQvJV0SCMSD0IDa3ts-uOUJVR\Despachos\bancolombia_data"

    # Directorio donde se guardarán los reportes generados

    # Producción
    # _directorio_reportes = "G:\.shortcut-targets-by-id\1A2UP-JKrQvJV0SCMSD0IDa3ts-uOUJVR\Despachos\bancolombia" # tipo_cuenta\fecha_pdf

    # Pruebas
    _directorio_reportes = "reportes"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def firebase_database_url(self):
        return self._firebase_database_url

    @property
    def porcentaje_minimo_pedido_pagado(self):
        return self._porcentaje_minimo_pedido_pagado

    @property
    def cuentas_ingreso_egreso_corriente(self):
        return self._cuentas_contables_ingreso_egreso_corriente

    @property
    def cuentas_ingreso_egreso_ahorro(self):
        return self._cuentas_contables_ingreso_egreso_ahorro

    @property
    def directorio_reportes(self):
        return self._directorio_reportes

    @property
    def directorio_pagos(self):
        return self._directorio_pagos

    @staticmethod
    def initialize_firebase():
        """
        Initializes Firebase with the credentials.json file.
        """
        cred_path = os.getenv(
            "FIREBASE_CREDENTIALS_PATH",
            "secrets/credentials/emes-digital.json",
        )
        cred = credentials.Certificate(cred_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'databaseURL': AppConfig._firebase_database_url
            })


# Instancia global accesible (opcional, pero útil)
config = AppConfig()
