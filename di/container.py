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


class Container(containers.DeclarativeContainer):
    # ---------- Infraestructura ---------- #

    # Definir un proveedor de configuración
    config = providers.Configuration()

    # Provide the Firebase database reference
    firebase_pedidos_reference = providers.Singleton(
        db.reference, path="/pedidos"
    )
    
    # Bind AbstractRepositorioPedidos to FirebaseRepositorioPedidos
    repositorio_pedidos = providers.Singleton(
        FirebaseRepositorioPedidos,
        firebase_reference=firebase_pedidos_reference,
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
        repositorio_pedidos=repositorio_pedidos,
        extractor_pagos=extractor_pagos,
        generador_reporte=generador_reporte,
        aplicador_pagos=aplicador_pagos,
    )
