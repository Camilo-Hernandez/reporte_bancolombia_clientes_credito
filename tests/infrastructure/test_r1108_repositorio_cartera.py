# infrastructure/tests/test_r1108_repositorio_cartera.py

from datetime import datetime
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from decimal import Decimal
from infrastructure.repositories.r1108_repositorio_cartera import RepositorioCartera
from domain.models.models import EstadoPedido, Pedido, EstadoPago
from infrastructure.repositories.firebase_repositorio_pedidos import FirebaseRepositorioPedidos


@pytest.fixture
def mock_firebase_repo():
    return MagicMock(spec=FirebaseRepositorioPedidos)


@pytest.fixture
def mock_csv_path(tmp_path):
    csv_file = tmp_path / "cartera.csv"
    csv_file.write_text(
        "nit,Número,Valor,Aplicado,Fecha\n"
        "123456789,001,1000.00,500.00,2025-02-27\n"
        "987654321,002,2000.00,2000.00,2023-03-14\n"
        "111111111,003,1500.00,,2024-01-15\n"
        "222222222,004,2500.00,,2024-06-10"
    )
    return str(csv_file)



@pytest.fixture
def mock_empty_csv(tmp_path):
    csv_file = tmp_path / "empty_csv.csv"
    csv_file.write_text("")
    return str(csv_file)


@pytest.fixture
def repositorio_cartera(mock_firebase_repo, mock_csv_path):
    return RepositorioCartera(mock_firebase_repo, mock_csv_path)


# Ensures that the CSV file is loaded successfully and contains the expected columns.
def test_csv_loading_success(repositorio_cartera):
    assert not repositorio_cartera.df.empty
    assert "nit" in repositorio_cartera.df.columns
    assert "numero" in repositorio_cartera.df.columns

# Verifies that a FileNotFoundError is raised when the specified CSV file does not exist.
def test_csv_file_not_found(mock_firebase_repo):
    with pytest.raises(FileNotFoundError):
        RepositorioCartera(mock_firebase_repo, "non_existent_file.csv")

# Tests the behavior when the CSV data is empty, ensuring that pedidos are still retrieved from Firebase.
def test_obtener_pedidos_credito_no_csv_data(mock_firebase_repo, mock_empty_csv):
    mock_firebase_repo.obtener_pedidos_credito.return_value = [
        Pedido(
            nit_cliente="123456789",
            id_pedido="001",
            valor_neto=Decimal("1000.00"),
            valor_cobrado=Decimal("0.00"),
            estado_pago=EstadoPago.PENDIENTE,
            estado_pedido=EstadoPedido.DESPACHADO,
            fecha_pedido=datetime.strptime("2025-02-27", "%Y-%m-%d").date(),
            forma_pago_raw="A 20 días (10%)"
        )
    ]
    # Expect an exception to be raised
    with pytest.raises(ValueError,  match=r"El archivo CSV está vacío: .*empty_csv.csv"):
        RepositorioCartera(mock_firebase_repo, mock_empty_csv)

# Validates that a pedido with partial payment is updated correctly based on the CSV data.
def test_obtener_pedidos_credito_update_partial_payment(repositorio_cartera, mock_firebase_repo):
    mock_firebase_repo.obtener_pedidos_credito.return_value = [
        Pedido(
            nit_cliente="123456789",
            id_pedido="001",
            valor_neto=Decimal("1000.00"),
            valor_cobrado=Decimal("0.00"),
            estado_pago=EstadoPago.PENDIENTE,
            estado_pedido=EstadoPedido.DESPACHADO,
            fecha_pedido=datetime.strptime("2025-02-27", "%Y-%m-%d").date(),
            forma_pago_raw="A 20 días (10%)"
        )
    ]
    pedidos = repositorio_cartera.obtener_pedidos_credito()
    assert len(pedidos) == 1
    assert pedidos[0].valor_cobrado == Decimal("500.00")
    assert pedidos[0].estado_pago == EstadoPago.PARCIAL

# Ensures that a pedido with full payment is updated correctly based on the CSV data.
def test_obtener_pedidos_credito_update_full_payment(repositorio_cartera, mock_firebase_repo):
    mock_firebase_repo.obtener_pedidos_credito.return_value = [
        Pedido(
            nit_cliente="987654321",
            id_pedido="002",
            valor_neto=Decimal("2000.00"),
            valor_cobrado=Decimal("0.00"),
            estado_pago=EstadoPago.PENDIENTE,
            estado_pedido=EstadoPedido.DESPACHADO,
            fecha_pedido=datetime.strptime("2025-02-27", "%Y-%m-%d").date(),
            forma_pago_raw="A 20 días (10%)"
        )
    ]
    pedidos = repositorio_cartera.obtener_pedidos_credito()
    assert len(pedidos) == 1
    assert pedidos[0].valor_cobrado == Decimal("2000.00")
    assert pedidos[0].estado_pago == EstadoPago.PAGADO

# Verifies that pedidos with no matching records in the CSV are not returned by repositorio_cartera.
def test_obtener_pedidos_credito_no_match_in_csv(repositorio_cartera, mock_firebase_repo):
    mock_firebase_repo.obtener_pedidos_credito.return_value = [
        Pedido(
            nit_cliente="111111111",
            id_pedido="006",
            valor_neto=Decimal("1500.00"),
            valor_cobrado=Decimal("0.00"),
            estado_pago=EstadoPago.PENDIENTE,
            estado_pedido=EstadoPedido.DESPACHADO,
            fecha_pedido=datetime.strptime("2025-02-27", "%Y-%m-%d").date(),
            forma_pago_raw="A 20 días (10%)"

            )
    ]
    pedidos = repositorio_cartera.obtener_pedidos_credito()
    assert len(pedidos) == 0

# Ensures that a pedido with no 'aplicado' value in the CSV defaults to 0.00 in the DataFrame.
def test_obtener_pedidos_credito_no_aplicado_value_generates_zero_value_in_df(repositorio_cartera, mock_firebase_repo):
    mock_firebase_repo.obtener_pedidos_credito.return_value = [
        Pedido(
            nit_cliente="111111111",
            id_pedido="003",
            valor_neto=Decimal("1500.00"),
            valor_cobrado=Decimal("0.00"),
            estado_pago=EstadoPago.PENDIENTE,
            estado_pedido=EstadoPedido.DESPACHADO,
            fecha_pedido=datetime.strptime("2025-02-27", "%Y-%m-%d").date(),
            forma_pago_raw="A 20 días (10%)"
        ),
        Pedido(
            nit_cliente="222222222",
            id_pedido="004",
            valor_neto=Decimal("2500.00"),
            valor_cobrado=Decimal("0.00"),
            estado_pago=EstadoPago.PENDIENTE,
            estado_pedido=EstadoPedido.DESPACHADO,
            fecha_pedido=datetime.strptime("2025-02-27", "%Y-%m-%d").date(),
            forma_pago_raw="A 20 días (10%)"
        )
    ]
    pedidos = repositorio_cartera.obtener_pedidos_credito()
    assert len(pedidos) == 2
    assert pedidos[0].valor_cobrado == Decimal("0.00")  # No 'aplicado' value in CSV, should default to 0.00
    assert pedidos[0].estado_pago == EstadoPago.PENDIENTE  # Should remain PENDIENTE
    assert pedidos[1].valor_cobrado == Decimal("0.00")  # No 'aplicado' value in CSV, should default to 0.00
    assert pedidos[1].estado_pago == EstadoPago.PENDIENTE  # Should remain PENDIENTE
    
# Ensures that a KeyError is raised when the CSV file is missing required columns.
def test_csv_column_missing(mock_firebase_repo, tmp_path):
    csv_file = tmp_path / "cartera.csv"
    csv_file.write_text("nit,valor,aplicado\n123456789,1000.00,500.00")
    with pytest.raises(KeyError):
        RepositorioCartera(mock_firebase_repo, str(csv_file))

# Verifies that an exception is raised when the CSV contains invalid data.
def test_csv_invalid_data(mock_firebase_repo, tmp_path):
    csv_file = tmp_path / "cartera.csv"
    csv_file.write_text(
        "nit,numero,valor,aplicado\n123456789,001,invalid,500.00")
    with pytest.raises(Exception):
        RepositorioCartera(mock_firebase_repo, str(csv_file))

# Checks that the logger is configured correctly during the initialization of RepositorioCartera.
def test_logger_configuration(mock_firebase_repo, mock_csv_path):
    with patch("infrastructure.repositories.r1108_repositorio_cartera.logging") as mock_logging:
        RepositorioCartera(mock_firebase_repo, mock_csv_path)
        mock_logging.basicConfig.assert_called_once()

# Tests the behavior when multiple matching records exist in the CSV for a single pedido, ensuring the first match is used.
def test_obtener_pedidos_credito_multiple_matches_in_csv(repositorio_cartera, mock_firebase_repo):
    repositorio_cartera.df = pd.DataFrame({
        "nit": ["123456789", "123456789"],
        "numero": ["001", "001"],
        "valor": [Decimal("1000.00"), Decimal("1000.00")],
        "aplicado": [Decimal("500.00"), Decimal("600.00")]
    })
    mock_firebase_repo.obtener_pedidos_credito.return_value = [
        Pedido(
            nit_cliente="123456789",
            id_pedido="001",
            valor_neto=Decimal(
            "1000.00"),
            valor_cobrado=Decimal("0.00"),
            estado_pago=EstadoPago.PENDIENTE,
            estado_pedido=EstadoPedido.DESPACHADO,
            fecha_pedido=datetime.strptime("2025-02-27", "%Y-%m-%d").date(),
            forma_pago_raw="A 20 días (10%)"
            )
    ]
    pedidos = repositorio_cartera.obtener_pedidos_credito()
    assert len(pedidos) == 1
    assert pedidos[0].valor_cobrado == Decimal("500.00")  # First match used
