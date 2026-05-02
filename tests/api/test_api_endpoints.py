"""
Tests de API Endpoints — RAG Legal Colombiano
─────────────────────────────────────────────
Tests de integración para los endpoints de la API REST.

IMPORTANTE: Estos tests requieren que el servidor esté corriendo.
Ejecutar: uvicorn api.main:app --reload

Autor: Fenix Tech Líder
Fecha: 2026-04-28
Migrado desde: api/test_api.py
"""

import pytest
import httpx
import json
from typing import Generator
import logging

logger = logging.getLogger(__name__)

# ── Configuración ────────────────────────────────────────────────────────────

API_BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_client() -> Generator[httpx.Client, None, None]:
    """
    Cliente HTTP para tests de API.
    
    Scope: module - Se crea una vez por módulo de tests.
    follow_redirects=True para manejar 307 de FastAPI (trailing slash).
    """
    logger.info(f"Creando cliente HTTP para {API_BASE_URL}")
    with httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT, follow_redirects=True) as client:
        yield client
    logger.info("Cliente HTTP cerrado")


@pytest.fixture(scope="module", autouse=True)
def check_server_running(api_client: httpx.Client):
    """
    Verifica que el servidor esté corriendo antes de ejecutar tests.
    
    autouse=True: Se ejecuta automáticamente antes de todos los tests.
    """
    logger.info("Verificando que el servidor esté corriendo...")
    try:
        response = api_client.get("/", timeout=5.0)
        if response.status_code != 200:
            pytest.skip("El servidor no está respondiendo correctamente")
        logger.info("✅ Servidor corriendo correctamente")
    except httpx.ConnectError:
        pytest.skip(
            f"No se pudo conectar al servidor en {API_BASE_URL}. "
            "Asegúrate de que esté corriendo: uvicorn api.main:app --reload"
        )


# ── Tests de Endpoints Básicos ──────────────────────────────────────────────

class TestBasicEndpoints:
    """Tests de endpoints básicos (root, health)."""
    
    def test_root_endpoint(self, api_client: httpx.Client):
        """Test del endpoint raíz."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Root Endpoint")
        logger.info("="*80)
        
        response = api_client.get("/")
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {response.json()}")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data or "message" in data
        
        logger.info("✅ Test PASSED\n")
    
    def test_health_check(self, api_client: httpx.Client):
        """Test de health check."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Health Check")
        logger.info("="*80)
        
        response = api_client.get("/health")
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        
        logger.info("✅ Test PASSED\n")


# ── Tests de Query RAG ───────────────────────────────────────────────────────

class TestQueryEndpoints:
    """Tests de endpoints de consulta RAG."""
    
    def test_query_rag_basic(self, api_client: httpx.Client):
        """Test de consulta RAG básica."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Query RAG")
        logger.info("="*80)
        
        request_data = {
            "question": "¿Qué es una licencia ambiental?",
            "top_k": 5,
            "use_cache": True,
            "stream": False
        }
        
        logger.info(f"Request: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
        
        response = api_client.post("/api/v1/query", json=request_data)
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        assert response.status_code == 200
        data = response.json()
        assert "query_id" in data
        assert "answer" in data
        assert "sources" in data
        
        logger.info("✅ Test PASSED\n")
    
    def test_query_validation_error(self, api_client: httpx.Client):
        """Test de error de validación (question muy corta)."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Validation Error")
        logger.info("="*80)
        
        request_data = {
            "question": "Hola",  # Menos de 10 caracteres
            "top_k": 5
        }
        
        logger.info(f"Request (inválido): {json.dumps(request_data, indent=2)}")
        
        response = api_client.post("/api/v1/query", json=request_data)
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "error" in data or "detail" in data
        
        logger.info("✅ Test PASSED (error esperado)\n")
    
    def test_batch_query(self, api_client: httpx.Client):
        """Test de consultas en batch."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Batch Query")
        logger.info("="*80)
        
        request_data = {
            "questions": [
                "¿Qué es una licencia ambiental?",
                "¿Cuáles son los requisitos para una concesión de aguas?",
                "¿Qué es el Decreto 1076 de 2015?"
            ],
            "top_k": 5,
            "use_cache": True
        }
        
        logger.info(f"Request: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
        
        response = api_client.post("/api/v1/query/batch", json=request_data, timeout=60.0)
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        assert response.status_code == 200
        data = response.json()
        assert "batch_id" in data
        assert "total_questions" in data
        assert "results" in data
        assert len(data["results"]) == 3
        
        logger.info("✅ Test PASSED\n")


# ── Tests de Cache ───────────────────────────────────────────────────────────

class TestCacheEndpoints:
    """Tests de endpoints de caché."""
    
    def test_cache_stats(self, api_client: httpx.Client):
        """Test de estadísticas de caché."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Cache Stats")
        logger.info("="*80)
        
        response = api_client.get("/api/v1/cache/stats")
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "hit_rate" in data
        
        logger.info("✅ Test PASSED\n")


# ── Markers para Ejecución Selectiva ────────────────────────────────────────

# Marcar todos los tests como "api" para poder ejecutarlos selectivamente
pytestmark = pytest.mark.api

# Para ejecutar solo estos tests:
# pytest tests/api/test_api_endpoints.py -v
# pytest -m api -v
# pytest tests/api/ -v
