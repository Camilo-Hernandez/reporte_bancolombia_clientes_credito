# infrastructure/repositories/r1108_repositorio_cartera.py

import chardet
import pandas as pd
from decimal import Decimal
from typing import List
import logging
import os  # Import os for file existence check
from application.ports.interfaces import AbstractRepositorioPedidos
from domain.models.models import Pedido, EstadoPago
from infrastructure.repositories.firebase_repositorio_pedidos import FirebaseRepositorioPedidos


class RepositorioCartera(AbstractRepositorioPedidos):
    """
    Repositorio que enriquece los datos de pedidos de Firebase con información
    de cartera proveniente de un archivo CSV.
    Implementa la interfaz AbstractRepositorioPedidos.
    """

    def __init__(self, firebase_repo: FirebaseRepositorioPedidos, csv_path: str):
        self.firebase_repo = firebase_repo  # The wrapped Firebase repository
        self.csv_path = csv_path
        self._configurar_logger()
        try:
            self.df: pd.DataFrame = self._cargar_y_preparar_csv()
            self.logger.info(
                f"Archivo CSV de cartera cargado y preparado exitosamente desde: {csv_path}")
        except FileNotFoundError:
            self.logger.error(
                f"Error Crítico: Archivo CSV de cartera no encontrado en {csv_path}. El repositorio de cartera no funcionará correctamente.")
            # Handle this critical error: raise, or set df to None/empty and log extensively
            raise  # Or handle more gracefully depending on requirements
        except Exception as e:
            self.logger.error(
                f"Error Crítico al cargar o preparar el CSV de cartera desde {csv_path}: {e}", exc_info=True)
            raise  # Or handle

    def _configurar_logger(self):
        """Configura el logger para registrar información y errores."""
        # Configure root logger is okay, but consider named logger for better isolation
        log_file = "repositorio_cartera.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filemode='a'  # Append to the log file
        )
        # Get a specific logger for this class
        # Use class name as logger name
        self.logger = logging.getLogger(__name__)
        self.logger.info("Logger para RepositorioCartera configurado.")

    def _cargar_y_preparar_csv(self) -> pd.DataFrame:
        """Carga y prepara el archivo CSV para su uso."""
        self.logger.info(f"Intentando cargar CSV desde: {self.csv_path}")
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(
                f"El archivo CSV no se encontró en la ruta: {self.csv_path}")

        # Si el archivo scv está vacío, lanzar error
        if os.path.getsize(self.csv_path) == 0:
            raise ValueError(
                f"El archivo CSV está vacío: {self.csv_path}")
        
        try:
            # Detect encoding
            with open(self.csv_path, 'rb') as f:
                result = chardet.detect(f.read())
                detected_encoding = result['encoding']
                self.logger.info(f"Encoding detectado: {detected_encoding}")
            
            # Read the CSV with the detected encoding
            df = pd.read_csv(
                self.csv_path,
                # Consider adding encoding='utf-8' or 'latin1' if needed
                encoding=detected_encoding,  # Common encoding for CSVs from Windows systems
                # Define dtypes for potentially problematic columns during read
                # Read NIT, Numero, Valor, Aplicado, and Saldo as strings initially
                dtype={'nit': str, 'Número': str, 'Valor': str, 'Aplicado': str, 'Saldo': str},
                # Specify decimal separator if it's not '.'
                # decimal=','
            )
            
            self.logger.info(
                f"CSV cargado. Columnas iniciales: {df.columns.tolist()}")

            # --- Data Cleaning and Preparation ---
            # 1. Rename columns early for consistency
            df.columns = (
                df.columns.str.strip()   # Remove leading/trailing whitespace
                .str.lower()             # Convertir a minúsculas	
                .str.replace(" ", "_", regex=False)
                .str.replace("á", "a", regex=False).str.replace("é", "e", regex=False)
                .str.replace("í", "i", regex=False).str.replace("ó", "o", regex=False)
                .str.replace("ú", "u", regex=False).str.replace("ñ", "n", regex=False)
                # Remove periods if they exist in names
                .str.replace(".", "", regex=False)
            )
            self.logger.info(f"Columnas renombradas: {df.columns.tolist()}")

            # 2. Handle Dates
            date_columns = ['fecha', 'vencimiento', 'fecha_real']
            for col in date_columns:
                if col in df.columns:
                    try:
                        # Formato de fecha en el CSV: '%Y-%m-%d %H:%M:%S'
                        df[col] = pd.to_datetime(
                            df[col], errors='coerce', format='%Y-%m-%d %H:%M:%S')
                    except ValueError as e:
                        self.logger.warning(
                            f"Problema al parsear fechas en columna '{col}': {e}. Algunas fechas pueden ser NaT.")
                        df[col] = pd.to_datetime(
                            df[col], errors='coerce')  # Fallback attempt

            # 3. Handle Numeric Columns (Valor, Aplicado, Saldo)
            numeric_cols = ['valor', 'aplicado', 'saldo']
            for col in numeric_cols:
                if col in df.columns:
                    # Convert to string first to handle commas reliably
                    df[col] = (
                        df[col].astype(str)
                        .str.replace(',', '', regex=False)
                        # Replace empty strings with "0.0"
                        .replace(['', 'NaN', 'nan'], '0.0')
                        .fillna('0.0')       # Replace NaN with "0.0"
                        .apply(lambda x: Decimal(str(x)))
                    )
                    # Convert valid numbers to Decimal
                    # Use .loc to avoid SettingWithCopyWarning if df is a slice
                    valid_indices = df[col].notna()
                    df.loc[valid_indices, col] = df.loc[valid_indices,
                                                        col].apply(lambda x: Decimal(str(x)))

            # 4. Clean NIT (ensure it's string, remove delimiters)
            if 'nit' in df.columns:
                df['nit'] = (
                    df['nit'].astype(str)
                    .str.replace(".", "", regex=False)
                    .str.replace("-", "", regex=False)
                    .str.strip()
                    )
            else:
                self.logger.error(
                    "Columna 'nit' no encontrada en el CSV después del renombrado.")
                raise KeyError("Columna 'nit' esencial no encontrada en el CSV.")

            # 5. Clean Invoice Number ('numero') - assuming this maps to id_pedido
            if 'numero' in df.columns:
                df['numero'] = df['numero'].astype(str).str.strip()
            else:
                self.logger.warning(
                    "Columna 'numero' no encontrada en el CSV. No se podrá mapear por ID de pedido.")
                # This is critical for matching, so handle accordingly
                # Raise an error
                raise KeyError("Columna 'numero' esencial no encontrada en el CSV.")

            # 6. Drop rows with critical NaNs AFTER conversion attempts
            # Add 'numero' if essential for matching
            critical_cols = ['nit', 'valor', 'aplicado', 'numero']
            df.dropna(subset=critical_cols, inplace=True)

            # 7. Sort (Optional, but can be helpful)
            df.sort_values(by=["numero", "fecha", "nit"], inplace=True)

            self.logger.info(
                f"CSV preparado. {len(df)} filas válidas restantes.")
            return df

        
        
        except KeyError as e:
            self.logger.error(
                f"Error de columna faltante durante la preparación del CSV: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(
                f"Error inesperado durante la preparación del CSV: {e}", exc_info=True)
            raise

    def obtener_pedidos_credito(self) -> List[Pedido]:
        """
        Obtiene los pedidos de crédito de Firebase y los actualiza con los
        datos de 'Aplicado' del archivo CSV.
        """
        self.logger.info(
            "Iniciando obtención y actualización de pedidos de crédito.")
        pedidos_actualizados = []
        
        # 1. Get all relevant orders from Firebase first
        # Assuming obtener_pedidos_credito() gets orders needing payment check
        pedidos_firebase = self.firebase_repo.obtener_pedidos_credito()
        self.logger.info(
            f"Obtenidos {len(pedidos_firebase)} pedidos de crédito desde Firebase."
        )

        if self.df is None or self.df.empty:
            self.logger.warning(
                "DataFrame de cartera está vacío o no se cargó. Devolviendo pedidos de Firebase sin actualizar.")
            return pedidos_firebase  # Return original orders if CSV failed

        # 2. Create a lookup from the CSV for efficient access
        # Match by NIT and Invoice Number ('numero' in CSV -> 'id_pedido' in Firebase)
        try:
            # Make sure 'numero' exists before setting index
            if 'numero' not in self.df.columns:
                self.logger.error(
                    "No se puede crear lookup CSV: falta la columna 'numero'.")
                return pedidos_firebase  # Cannot update

            # Drop duplicates based on the key you'll use for lookup to avoid issues
            # Keep the one with the latest date or highest 'aplicado' if duplicates exist
            # df_unique = self.df.sort_values('fecha', ascending=False).drop_duplicates(subset=['nit', 'numero'], keep='first')
            # Or handle duplicates based on business logic

            csv_lookup = self.df.set_index(['nit', 'numero'])
        except KeyError:
            self.logger.error(
                "Error al crear el índice para lookup CSV (faltan 'nit' o 'numero'). Devolviendo pedidos de Firebase sin actualizar.")
            return pedidos_firebase

        # 3. Iterate through Firebase orders and update
        for pedido in pedidos_firebase:
            try:
                # Find corresponding row in CSV using the lookup.
                if (pedido.nit_cliente, pedido.id_pedido) not in csv_lookup.index:
                    # Pedido from Firebase not found in CSV lookup
                    pass
                else:
                    fila_csv = csv_lookup.loc[(
                        pedido.nit_cliente, pedido.id_pedido)]

                    # Handle potential multiple matches if index wasn't unique
                    if isinstance(fila_csv, pd.DataFrame):
                        # If multiple rows match, decide which one to use (e.g., the first, the latest)
                        self.logger.warning(
                            f"Múltiples entradas en CSV para NIT {pedido.nit_cliente}, Pedido {pedido.id_pedido}. Usando la primera.")
                        fila_csv = fila_csv.iloc[0]

                    csv_valor = fila_csv.get('valor')
                    # Default to 0 if missing
                    csv_valor_aplicado = fila_csv.get('aplicado', Decimal("0.0"))

                    # Compare valor_neto (optional logging)
                    if csv_valor is not None and pedido.valor_neto != csv_valor:
                        self.logger.warning(
                            f"Diferencia valor_neto Pedido {pedido.id_pedido} (NIT {pedido.nit_cliente}): "
                            f"Firebase={pedido.valor_neto}, CSV={csv_valor}"
                        )
                        # Decide if you want to *override* valor_neto based on CSV
                        # pedido.valor_neto = csv_valor # Uncomment if CSV is the source of truth

                    # Update valor_cobrado and estado_pago based on 'Aplicado'
                    if csv_valor_aplicado is not None and csv_valor_aplicado > 0:
                        # Check if CSV value is different from existing valor_cobrado
                        if pedido.valor_cobrado != csv_valor_aplicado:
                            self.logger.info(f"Actualizando Pedido {pedido.id_pedido} (NIT {pedido.nit_cliente}): "
                                             f"valor_cobrado anterior={pedido.valor_cobrado}, "
                                             f"CSV aplicado={csv_valor_aplicado}")
                            pedido.valor_cobrado = csv_valor_aplicado
                            # Update state based on the new valor_cobrado
                            if pedido.valor_cobrado >= pedido.valor_neto:
                                 pedido.estado_pago = EstadoPago.PAGADO
                                 self.logger.warning(f"CSV aplicado {csv_valor_aplicado} > Valor factura {pedido.valor_neto}): ")
                            else:
                                 pedido.estado_pago = EstadoPago.PARCIAL

                    # Always add the pedido (even if not updated) to the result list
                    pedidos_actualizados.append(pedido)

            except Exception as e:
                self.logger.error(
                    f"Error procesando actualización para Pedido {pedido.id_pedido} (NIT {pedido.nit_cliente}): {e}", exc_info=True)
                # Include original on error
                pedidos_actualizados.append(pedido)

        self.logger.info(
            f"Proceso de actualización completado. Total pedidos devueltos: {len(pedidos_actualizados)}")
        return pedidos_actualizados

