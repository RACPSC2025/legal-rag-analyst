"""
Script de Prueba de la API — RAG Legal Colombiano
──────────────────────────────────────────────────
Script para probar los endpoints de la API de forma rápida.

Uso:
    python api/test_api.py

Autor: Fenix Tech Líder
Fecha: 2026-04-27
"""

import httpx
import json
from typing import Dict, Any


# ── Configuración ────────────────────────────────────────────────────────────

API_BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0  # segundos


# ── Helper Functions ─────────────────────────────────────────────────────────

def print_section(title: str):
    """Imprime un separador de sección."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_response(response: httpx.Response):
    """Imprime una respuesta HTTP de forma legible."""
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    except Exception:
        print(f"Response (text):\n{response.text}")


# ── Test Functions ───────────────────────────────────────────────────────────

def test_root():
    """Test del endpoint raíz."""
    print_section("TEST 1: Root Endpoint")
    
    with httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
        response = client.get("/")
        print_response(response)
        
        assert response.status_code == 200
        print("\n✅ Test 1 PASSED")


def test_health():
    """Test de health check."""
    print_section("TEST 2: Health Check")
    
    with httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
        response = client.get("/health")
        print_response(response)
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        print("\n✅ Test 2 PASSED")


def test_query():
    """Test de consulta RAG."""
    print_section("TEST 3: Query RAG")
    
    request_data = {
        "question": "¿Qué es una licencia ambiental?",
        "top_k": 5,
        "use_cache": True,
        "stream": False
    }
    
    print(f"Request:\n{json.dumps(request_data, indent=2, ensure_ascii=False)}\n")
    
    with httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
        response = client.post("/api/v1/query", json=request_data)
        print_response(response)
        
        assert response.status_code == 200
        data = response.json()
        assert "query_id" in data
        assert "answer" in data
        assert "sources" in data
        print("\n✅ Test 3 PASSED")


def test_cache_stats():
    """Test de estadísticas de caché."""
    print_section("TEST 4: Cache Stats")
    
    with httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
        response = client.get("/api/v1/cache/stats")
        print_response(response)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "hit_rate" in data
        print("\n✅ Test 4 PASSED")


def test_validation_error():
    """Test de error de validación."""
    print_section("TEST 5: Validation Error")
    
    # Request inválido (question muy corta)
    request_data = {
        "question": "Hola",  # Menos de 10 caracteres
        "top_k": 5
    }
    
    print(f"Request (inválido):\n{json.dumps(request_data, indent=2, ensure_ascii=False)}\n")
    
    with httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
        response = client.post("/api/v1/query", json=request_data)
        print_response(response)
        
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "error" in data
        print("\n✅ Test 5 PASSED (error esperado)")


def test_batch_query():
    """Test de consultas en batch."""
    print_section("TEST 6: Batch Query")
    
    request_data = {
        "questions": [
            "¿Qué es una licencia ambiental?",
            "¿Cuáles son los requisitos para una concesión de aguas?",
            "¿Qué es el Decreto 1076 de 2015?"
        ],
        "top_k": 5,
        "use_cache": True
    }
    
    print(f"Request:\n{json.dumps(request_data, indent=2, ensure_ascii=False)}\n")
    
    with httpx.Client(base_url=API_BASE_URL, timeout=60.0) as client:
        response = client.post("/api/v1/query/batch", json=request_data)
        print_response(response)
        
        assert response.status_code == 200
        data = response.json()
        assert "batch_id" in data
        assert "total_questions" in data
        assert "results" in data
        assert len(data["results"]) == 3
        print("\n✅ Test 6 PASSED")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Ejecuta todos los tests."""
    print("\n" + "=" * 80)
    print("  🚀 INICIANDO TESTS DE LA API RAG LEGAL COLOMBIANO")
    print("=" * 80)
    
    try:
        # Verificar que el servidor esté corriendo
        print("\n🔍 Verificando que el servidor esté corriendo...")
        with httpx.Client(base_url=API_BASE_URL, timeout=5.0) as client:
            response = client.get("/")
            if response.status_code != 200:
                print("❌ El servidor no está respondiendo correctamente")
                return
        
        print("✅ Servidor corriendo correctamente\n")
        
        # Ejecutar tests
        test_root()
        test_health()
        test_query()
        test_cache_stats()
        test_validation_error()
        test_batch_query()
        
        # Resumen
        print_section("RESUMEN")
        print("✅ Todos los tests pasaron exitosamente!")
        print("\n📊 Tests ejecutados: 6")
        print("✅ Tests exitosos: 6")
        print("❌ Tests fallidos: 0")
        print("\n" + "=" * 80)
    
    except httpx.ConnectError:
        print("\n❌ ERROR: No se pudo conectar al servidor")
        print(f"   Asegúrate de que el servidor esté corriendo en {API_BASE_URL}")
        print("   Ejecuta: python api/main.py")
    
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
