# di/container.py

from dependency_injector import containers, providers
from application.emparejador_pagos_a_credito_caso_uso import EmparejadorPagosACreditoCasoUso
from domain.services.aplicador_de_pagos import AplicadorDePagos
from infrastructure.extractors.extractor_de_pagos_por_nit_bancolombia import (
    ExtractorDePagosPorNitBancolombia,
)
from infrastructure.extractors.extractor_pago_pdf import ExtractorPagosPDF
from infrastructure.report_generators.generador_reporte_txt import GeneradorReporteTxt
from firebase_admin import db
from infrastructure.repositories.firebase_repositorio_pedidos import (
    FirebaseRepositorioPedidos,
)
from infrastructure.repositories.r1108_repositorio_cartera import RepositorioCartera


class Container(containers.DeclarativeContainer):
    # ---------- Infraestructura ---------- #

    # Definir un proveedor de configuración
    config = providers.Configuration()

    # Provide the Firebase database reference
    firebase_pedidos_reference = providers.Singleton(
        db.reference, path="/pedidos"
    )
    
    # Bind AbstractRepositorioPedidos to FirebaseRepositorioPedidos
    repositorio_pedidos_firebase = providers.Singleton(
        FirebaseRepositorioPedidos,
        firebase_reference=firebase_pedidos_reference,
    )
    
    # --- Repositorio Cartera (Decorator/Wrapper) ---
    # This repository uses the Firebase one AND the CSV path from config
    repositorio_cartera = providers.Factory(
        RepositorioCartera,
        firebase_repo = repositorio_pedidos_firebase,  # Inject the Firebase repo
        csv_path = config.ruta_archivo_cartera       # Inject the CSV path
    )
    
    # --- Abstract Repository Provider ---
    # This is the provider the rest of the application should use.
    # By changing this single line, you can switch implementations (e.g., back to firebase only).
    repositorio_pedidos = providers.Factory(
        repositorio_cartera  # <-- Use the Cartera repository now
        # repositorio_pedidos_firebase # <-- Si se quiere volver a Firebase solamente, se cambia por este repositorio
    )

    procesador_pdf = providers.Factory(
        ExtractorDePagosPorNitBancolombia,
        directorio_bancolombia_data=config.directorio_pagos,
    )
    extractor_pagos = providers.Factory(
        ExtractorPagosPDF, procesador_pdf=procesador_pdf
    )

    generador_reporte = providers.Factory(
        GeneradorReporteTxt,
        fecha_pdf=config.fecha_pdf,
        directorio_reportes=config.directorio_reportes,
    )

    aplicador_pagos = providers.Singleton(AplicadorDePagos)

    # ---------- Aplicación ---------- #
    emparejador_pagos = providers.Factory(
        EmparejadorPagosACreditoCasoUso,
        extractor_pagos=extractor_pagos,
        repositorio_pedidos=repositorio_pedidos,
        generador_reporte=generador_reporte,
        aplicador_pagos=aplicador_pagos,
    )
