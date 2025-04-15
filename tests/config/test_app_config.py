import os
import pytest
from config.app_config import AppConfig

@pytest.fixture
def app_config():
    return AppConfig()

def test_singleton_instance(app_config):
    instance1 = AppConfig()
    instance2 = AppConfig()
    assert instance1 is instance2, "AppConfig should be a singleton"

def test_firebase_database_url(app_config):
    assert app_config.firebase_database_url == "https://emes-digital-cartera.firebaseio.com"

def test_porcentaje_minimo_pedido_pagado(app_config):
    assert app_config.porcentaje_minimo_pedido_pagado == 0.9

def test_tolerancia_maxima(app_config):
    assert app_config.tolerancia_maxima == 300

def test_dias_gracia_vencimiento(app_config):
    assert app_config.dias_gracia_vencimiento == 10

def test_dias_maximo_pedido(app_config):
    assert app_config.dias_maximo_pedido == 90

def test_cuentas_ingreso_egreso_corriente(app_config):
    assert app_config.cuentas_ingreso_egreso_corriente == ("11100501", "130505")

def test_cuentas_ingreso_egreso_ahorro(app_config):
    assert app_config.cuentas_ingreso_egreso_ahorro == ("11200501", "130505")

def test_directorio_reportes(app_config):
    assert app_config.directorio_reportes == "reportes"

def test_directorio_pagos(app_config):
    assert app_config.directorio_pagos == r"G:\.shortcut-targets-by-id\1A2UP-JKrQvJV0SCMSD0IDa3ts-uOUJVR\Despachos\bancolombia_data"

def test_ruta_archivo_cartera(app_config):
    assert app_config.ruta_archivo_cartera == r"G:\.shortcut-targets-by-id\1dyg6svJ1m1iFvbY0rdj1F0qDTuhhljes\Cartera\r1108\r1108.csv"

from unittest.mock import patch

def test_initialize_firebase(monkeypatch):
    monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", "test_credentials.json")
    os.environ["FIREBASE_CREDENTIALS_PATH"] = "test_credentials.json"

    class MockCredentials:
        @staticmethod
        def Certificate(path):
            assert path == "test_credentials.json"
            return "mock_cred"

    class MockFirebaseAdmin:
        _apps = []

        @staticmethod
        def initialize_app(cred, options):
            assert cred == "mock_cred"
            assert options == {'databaseURL': "https://emes-digital-cartera.firebaseio.com"}
            MockFirebaseAdmin._apps.append("mock_app")

    with patch("firebase_admin.credentials", MockCredentials):
        with patch("firebase_admin", MockFirebaseAdmin):
            from config.app_config import AppConfig
            AppConfig.initialize_firebase()
            assert len(MockFirebaseAdmin._apps) == 1
    monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", "test_credentials.json")
    os.environ["FIREBASE_CREDENTIALS_PATH"] = "test_credentials.json"

    class MockCredentials:
        @staticmethod
        def Certificate(path):
            assert path == "test_credentials.json"
            return "mock_cred"

    class MockFirebaseAdmin:
        _apps = []

        @staticmethod
        def initialize_app(cred, options):
            assert cred == "mock_cred"
            assert options == {'databaseURL': "https://emes-digital-cartera.firebaseio.com"}
            MockFirebaseAdmin._apps.append("mock_app")

    monkeypatch.setattr("firebase_admin.credentials", MockCredentials)
    monkeypatch.setattr("firebase_admin", MockFirebaseAdmin)

    AppConfig.initialize_firebase()
    assert len(MockFirebaseAdmin._apps) == 1