from annotated_types import T
import pytest
from unittest.mock import patch, MagicMock
from domain.models.models import TipoCuentaBancaria
from main import main

@pytest.fixture
def mock_app_config():
    with patch("main.app_config") as mock_config:
        mock_config.ruta_archivo_cartera = "mock_ruta_archivo_cartera"
        mock_config.directorio_pagos = "mock_directorio_pagos"
        mock_config.directorio_reportes = "mock_directorio_reportes"
        mock_config.initialize_firebase = MagicMock()
        yield mock_config


@pytest.fixture
def mock_container():
    with patch("main.Container") as mock_container_class:
        mock_container_instance = MagicMock()
        mock_container_class.return_value = mock_container_instance
        mock_container_instance.config.ruta_archivo_cartera.from_value = MagicMock()
        mock_container_instance.config.directorio_pagos.from_value = MagicMock()
        mock_container_instance.config.directorio_reportes.from_value = MagicMock()
        mock_container_instance.config.fecha_pdf.from_value = MagicMock()
        mock_container_instance.emparejador_pagos.return_value.ejecutar = MagicMock()
        yield mock_container_instance


@pytest.fixture
def mock_logger():
    with patch("main.setup_logger") as mock_logger_func:
        mock_logger_instance = MagicMock()
        mock_logger_func.return_value = mock_logger_instance
        yield mock_logger_instance


def test_main_success(mock_app_config, mock_container, mock_logger):
    with patch("main.sys.stdout", new_callable=MagicMock):
        main("20250410")

        # Verify Firebase initialization
        mock_app_config.initialize_firebase.assert_called_once()

        # Verify container configuration
        mock_container.config.ruta_archivo_cartera.from_value.assert_called_once_with(
            mock_app_config.ruta_archivo_cartera
        )
        mock_container.config.directorio_pagos.from_value.assert_called_once_with(
            mock_app_config.directorio_pagos
        )
        mock_container.config.directorio_reportes.from_value.assert_called_once_with(
            mock_app_config.directorio_reportes
        )
        mock_container.config.fecha_pdf.from_value.assert_called_once_with("20250410")

        # Verify use case execution
        mock_container.emparejador_pagos.return_value.ejecutar.assert_any_call(
            "20250410", tipo_cuenta=TipoCuentaBancaria.AHORROS.value
        )
        mock_container.emparejador_pagos.return_value.ejecutar.assert_any_call(
            "20250410", tipo_cuenta=TipoCuentaBancaria.CORRIENTE.value
        )


def test_main_exception_handling(mock_app_config, mock_container, mock_logger):
    with patch("main.sys.stdout", new_callable=MagicMock):
        # Simulate an exception during use case execution
        mock_container.emparejador_pagos.return_value.ejecutar.side_effect = Exception(
            "Mocked exception"
        )

        with pytest.raises(Exception, match="Mocked exception"):
            main("20250410")