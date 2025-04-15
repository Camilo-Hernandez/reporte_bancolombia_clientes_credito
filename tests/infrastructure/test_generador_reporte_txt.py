# tests\infrastructure\test_generador_reporte_txt.py

from datetime import date
import os
import pytest
from unittest.mock import MagicMock, patch
from infrastructure.report_generators.generador_reporte_txt import GeneradorReporteTxt
from domain.models.models import (
    EstadoPago,
    ResultadoPagoCliente,
    TipoCuentaBancaria,
    Pedido,
    ResultadoPagoCliente,
    TipoCliente,
    EstadoPedido,
)
from decimal import Decimal


@pytest.fixture
def mock_config():
    with patch(
        "infrastructure.report_generators.generador_reporte_txt.config"
    ) as mock_config:
        # Override the directorio_reportes for testing
        mock_config.directorio_reportes = "./tests/test_reports/"

        mock_config.cuentas_ingreso_egreso_ahorro = ["1101", "2202"]
        mock_config.cuentas_ingreso_egreso_corriente = ["3301", "4402"]

        yield mock_config


@pytest.fixture
def resultado_pago_cliente():
    # Mock data for Pedido
    pedido_1 = Pedido(
        id_pedido="P001",
        estado_pedido=EstadoPedido.FACTURADO,
        nit_cliente="123456789",
        valor_neto=Decimal("1500.00"),
        valor_cobrado=Decimal("1000.00"),
        fecha_pedido=date(2023, 9, 1),
        forma_pago_raw="A 30 días",
        razon_social="Cliente A",
        estado_pago=EstadoPago.PARCIAL,
    )

    pedido_2 = Pedido(
        id_pedido="P002",
        estado_pedido=EstadoPedido.FACTURADO,
        nit_cliente="123456789",
        valor_neto=Decimal("2000.00"),
        valor_cobrado=Decimal("2000.00"),
        fecha_pedido=date(2023, 9, 5),
        forma_pago_raw="A 30 días",
        razon_social="Cliente A",
        estado_pago=EstadoPago.PAGADO,
    )

    pedido_3 = Pedido(
        id_pedido="P003",
        estado_pedido=EstadoPedido.FACTURADO,
        nit_cliente="123456789",
        valor_neto=Decimal("500.00"),
        valor_cobrado=Decimal("0.00"),
        fecha_pedido=date(2023, 9, 10),
        forma_pago_raw="A 30 días",
        razon_social="Cliente A",
        estado_pago=EstadoPago.PENDIENTE,
    )

    # Mock data for ResultadoPagoCliente
    return ResultadoPagoCliente(
        id_pago="123",
        nit_cliente="123456789",
        fecha_pago=date(2023, 10, 1),
        pago_extracto=Decimal("3500.00"),
        deuda_total_anterior=Decimal("4000.00"),
        deuda_restante=Decimal("500.00"),
        facturas_pagadas=[pedido_1, pedido_2],
        facturas_parciales=[pedido_3],
        facturas_pendientes=[],
        tipo_cliente=TipoCliente.CREDITO,
    )


@pytest.fixture
def generador_reporte_txt(mock_config):
    return GeneradorReporteTxt(
        fecha_pdf="20231001",
        directorio_reportes=mock_config.directorio_reportes,
    )


def test_generar_crea_archivos_correctamente(
    generador_reporte_txt, resultado_pago_cliente,
):
    # Run the generar method
    generador_reporte_txt.generar(
        resultado_pago_cliente, TipoCuentaBancaria.AHORROS.value
    )

    # Verify that the expected files are created
    expected_files = [
        f"./tests/test_reports/ahorros/20231001/123456789_1.txt",
        f"./tests/test_reports/ahorros/20231001/123456789_2.txt",
        f"./tests/test_reports/ahorros/20231001/123456789_3.txt",
    ]
    for file_path in expected_files:
        assert os.path.exists(file_path)
        os.remove(file_path)  # Clean up after test
    os.rmdir("./tests/test_reports/ahorros/20231001")
    os.rmdir("./tests/test_reports/ahorros")
    os.rmdir("./tests/test_reports")


def test_generar_contenido_archivo(
    generador_reporte_txt, resultado_pago_cliente
):
    # Run the generar method
    generador_reporte_txt.generar(
        resultado_pago_cliente, TipoCuentaBancaria.AHORROS.value)

    # Verify the content of the first file
    file_path = "./tests/test_reports/ahorros/20231001/123456789_1.txt"
    with open(file_path, "r") as file:
        lines = file.readlines()
        assert len(lines) == 2  # Two rows for two cuentas_bancarias
        assert lines[0] == "1101,123456789,,P001,,1000.00" + "," * 10 + "\n"
        assert lines[1] == "2202,123456789,,P001,,-1000.00" + "," * 10 + "\n"

    # Clean up after test
    for i in range(1, 4):
        os.remove(f"./tests/test_reports/ahorros/20231001/123456789_{i}.txt")
    os.rmdir("./tests/test_reports/ahorros/20231001")
    os.rmdir("./tests/test_reports/ahorros")
    os.rmdir("./tests/test_reports")


def test_manejar_excepciones_log_error(
    generador_reporte_txt, resultado_pago_cliente, caplog
):
    # Mock an exception in the generar method
    with patch("builtins.open", side_effect=Exception("Mocked exception")):
        generador_reporte_txt.generar(
            resultado_pago_cliente, TipoCuentaBancaria.AHORROS.value)

    # Verify that the error was logged
    assert "Error ejecutando generar >>> Mocked exception" in caplog.text
