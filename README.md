# Payment Application System

## Overview

This application matches client payments, extracted from bank statements (PDF), with outstanding client orders (invoices) stored in Firebase. It applies payments according to business rules (e.g., prioritizing older or overdue invoices) and generates TXT reports suitable for import into an accounting system.

The system is designed with a Clean Architecture approach, separating domain logic, application use cases, and infrastructure concerns.

## Key Features

*   Extracts payment information (NIT, amount) from Bancolombia PDF bank statements.
*   Retrieves client order data from a Firebase Realtime Database.
*   Applies payments to orders based on:
    *   Client NIT match.
    *   Order status (Despachado, Credito Poblacion).
    *   Payment status (not already fully paid).
    *   Priority: Overdue orders first, then by oldest order date, then by lowest amount.
    *   Handles full and partial payments.
    *   Considers configured payment tolerance (`config.tolerancia_maxima`).
*   Calculates remaining client debt after payment application.
*   Generates detailed TXT reports per payment application, formatted for accounting system import.
*   Supports different bank account types (Savings/Checking) with specific accounting codes (`config`).

## Architecture

The project follows a layered architecture:

1.  **Domain (`domain/`)**: Contains core business logic and models.
    *   `models/models.py`: Pydantic models defining entities (`Cliente`, `Pago`, `Pedido`, `ResultadoPagoCliente`) and Enums (`EstadoPago`, `EstadoPedido`, etc.).
    *   `services/aplicador_de_pagos.py`: The core service responsible for the payment application logic.
2.  **Application (`application/`)**: Orchestrates use cases, connecting domain and infrastructure.
    *   `ports/interfaces.py`: Defines abstract interfaces for repositories and external services (extractors, report generators). (Note: File not provided, but implied by usage).
    *   `emparejador_pagos_a_credito_caso_uso.py`: Example use case coordinating the payment matching process.
3.  **Infrastructure (`infrastructure/`)**: Handles external concerns like data sources, file parsing, and report generation.
    *   `extractors/`: Modules for extracting data from external sources (e.g., `extractor_pago_pdf.py`, `extractor_de_pagos_por_nit_bancolombia.py`).
    *   `repositories/`: Data access logic (e.g., `firebase_repositorio_pedidos.py`).
    *   `report_generators/`: Modules for creating output reports (e.g., `generador_reporte_txt.py`).
4.  **Configuration (`config/`)**: Application settings.
    *   `app_config.py`: Loads and provides access to configuration values.
    *   `EXTRA_REF.py`: (**Note:** Ideally move this mapping elsewhere) Hardcoded NIT mapping.
5.  **Dependency Injection (`di/`)**: Manages the wiring of dependencies.
    *   `container.py`: Dependency Injection container setup (using `dependency-injector` or similar).
6.  **Tests (`tests/`)**: Unit and integration tests for different layers.

## Technology Stack

*   Python 3.x
*   Pydantic: Data validation and settings management.
*   Firebase Admin SDK (`firebase-admin`): Interacting with Firebase Realtime Database.
*   PyPDF (`pypdf`): Parsing PDF bank statements.
*   pytest: Testing framework.
*   Dependency Injector (implied): For managing DI.
*   (Optional) `python-dotenv`: For loading environment variables.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```
2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt # Assuming a requirements.txt file exists
    ```
4.  **Firebase Setup:**
    *   Obtain your Firebase Admin SDK service account key file (JSON).
    *   Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of this key file.
    *   Ensure the Firebase Realtime Database URL is correctly configured (likely via `config/app_config.py` or environment variables).
    *   Update the Firebase database reference path in `di/container.py` (`firebase_pedidos_reference`) if it's hardcoded or needs specific configuration.
5.  **Configure Environment Variables:**
    *   Set up any necessary environment variables required by `config/app_config.py` (e.g., database URLs, report directories, PDF source directories). Create a `.env` file if using `python-dotenv`.

## Configuration

Key configuration points managed via `config/app_config.py` (and potentially environment variables):

*   `directorio_reportes`: Path where generated TXT reports will be saved.
*   `directorio_bancolombia_data`: Path to the directory containing Bancolombia PDF statements (organized by account type and date).
*   `tolerancia_maxima`: Allowed difference for considering a payment as complete.
*   `porcentaje_minimo_pedido_pagado`: Minimum payment percentage to mark an order as non-overdue even if the due date passes.
*   `dias_gracia_vencimiento`: Grace period added to invoice due dates.
*   `cuentas_ingreso_egreso_ahorro`/`_corriente`: Accounting codes used in TXT reports.
*   Firebase Database URL and reference path.

**NIT Mapping:** The static mapping in `infrastructure/extractors/EXTRA_REF.py` might require manual updates. Consider moving this to a configuration file or database for easier maintenance.

## How to Run

The application is likely run through specific use cases triggered by a main script or task runner.

**Example (Conceptual - adapt based on your actual entry point):**

```bash
# Activate virtual environment
source venv/bin/activate

# Run the payment matching use case for a specific date and account type
python main.py --fecha-pdf 20240115 --tipo-cuenta ahorros


(You'll need to create a main.py or similar entry point that initializes the DI container and executes the desired use case, e.g., EmparejadorPagosACreditoCasoUso)

How to Run Tests
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END
Directory Structure
.
├── application/            # Application layer (use cases, interfaces)
│   ├── ports/
│   └── *.py                # Use case files
├── config/                 # Configuration files and loading logic
│   └── app_config.py
├── di/                     # Dependency Injection setup
│   └── container.py
├── domain/                 # Domain layer (core logic, models)
│   ├── models/
│   │   └── models.py
│   └── services/
│       └── aplicador_de_pagos.py
├── infrastructure/         # Infrastructure layer (external concerns)
│   ├── extractors/         # Data extraction logic (PDF, etc.)
│   │   ├── extractor_pago_pdf.py
│   │   ├── extractor_de_pagos_por_nit_bancolombia.py
│   │   └── EXTRA_REF.py    # <-- Consider moving
│   ├── repositories/       # Data persistence logic
│   │   └── firebase_repositorio_pedidos.py
│   └── report_generators/  # Report generation logic
│       └── generador_reporte_txt.py
├── tests/                  # Unit and integration tests
│   ├── application/
│   ├── di/
│   ├── domain/
│   └── infrastructure/
├── venv/                   # Virtual environment directory (ignored by git)
├── .gitignore
├── main.py                 # Example entry point (if applicable)
├── requirements.txt        # Project dependencies
└── README.md               # This file
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
IGNORE_WHEN_COPYING_END
Known Issues / Future Improvements

Firebase Query Efficiency: Improve obtener_pedidos_por_nit and obtener_pedidos_credito to use Firebase server-side querying instead of client-side filtering.

PDF Parsing Robustness: PDF extraction is sensitive to layout changes. Enhance error handling and monitoring.

EXTRA_REF.py Maintainability: Move the static NIT mapping to a configuration file or database.

Configuration Management: Formalize configuration loading using environment variables or a dedicated library.

Asynchronous Operations: For larger datasets or network latency, consider using asynchronous operations (asyncio) for Firebase calls.

Missing Interfaces: Add the actual Abstract* interface definitions in application/ports/interfaces.py.

IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
IGNORE_WHEN_COPYING_END