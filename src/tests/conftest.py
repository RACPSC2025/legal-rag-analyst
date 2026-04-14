"""
Fixtures compartidos para tests del RAG Legal Colombiano.

Uso:
    pytest src/tests/  # conftest.py se carga automáticamente
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# ── Project root ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


# ── Fixtures de configuración ───────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_project_path():
    """Agrega PROJECT_ROOT al sys.path para todos los tests."""
    import sys
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_legal_question() -> str:
    """Pregunta legal de ejemplo para tests."""
    return "¿Qué dice el artículo 2.2.2.4.11 sobre la tabla de negociadores?"


@pytest.fixture
def sample_pdf_path() -> Path:
    """Ruta a un PDF de ejemplo para tests de ingestion."""
    return PROJECT_ROOT / "data" / "input"


@pytest.fixture
def temp_upload_dir(tmp_path) -> Path:
    """Directorio temporal para uploads de tests."""
    upload_dir = tmp_path / "temp_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


# ── Fixtures de mocking (para tests que no requieren AWS) ────────────────────

@pytest.fixture
def mock_env_credentials(monkeypatch):
    """Mock de credenciales AWS para tests sin conexión real."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    monkeypatch.setenv("AWS_REGION", "us-east-2")
