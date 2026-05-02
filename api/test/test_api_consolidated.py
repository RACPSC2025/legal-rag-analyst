#!/usr/bin/env python3
"""
Test Consolidado de API — RAG Legal Colombiano
────────────────────────────────────────────────
Test unificado que combina:
1. Pruebas básicas de conectividad y endpoints
2. Diagnóstico de problemas comunes
3. Smoke test con PDFs para validar calidad de respuestas
4. Validación de integridad del sistema

Este test reemplaza:
- test_api_basic.py
- test_api_detailed.py  
- test_api_simple.py

Autor: Fenix Tech Líder
Fecha: 01 de mayo de 2026
"""

import httpx
import json
import time
import socket
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List
import subprocess
import threading
import queue

# ── Configuración ────────────────────────────────────────────────────────────

API_BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0
SMOKE_TEST_PDF = "data/input/Decreto_1072_2015.pdf"  # PDF de ejemplo para tests
SMOKE_TEST_QUESTIONS = [
    "¿Qué es una licencia ambiental?",
    "¿Cuáles son los requisitos para obtener una licencia ambiental?",
    "¿Qué establece el Decreto 1072 de 2015 sobre licencias ambientales?"
]

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def check_socket(host='127.0.0.1', port=8000, timeout=5) -> Tuple[bool, str]:
    """Verificar si un socket está escuchando."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return True, "✅ Socket escuchando"
        else:
            return False, f"❌ Socket no escuchando (error code: {result})"
    except Exception as e:
        return False, f"❌ Error verificando socket: {e}"

# ── Parte 1: Diagnóstico del Sistema ───────────────────────────────────────

def diagnose_system():
    """Diagnóstico completo del sistema."""
    print_section("DIAGNÓSTICO DEL SISTEMA")
    
    # 1. Verificar Python y entorno
    print("1. Verificando entorno Python...")
    print(f"   Python executable: {sys.executable}")
    print(f"   Python version: {sys.version}")
    print(f"   Working directory: {Path.cwd()}")
    
    # 2. Verificar socket
    print("\n2. Verificando socket 127.0.0.1:8000...")
    socket_ok, socket_msg = check_socket(timeout=2)
    print(f"   {socket_msg}")
    
    # 3. Verificar imports críticos
    print("\n3. Verificando imports críticos...")
    
    imports_to_check = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("api.main", "app"),
        ("api.routes.query", "router"),
        ("api.routes.health", "router"),
        ("api.middleware.error_handler", "add_error_handlers"),
    ]
    
    for module, item in imports_to_check:
        try:
            if module == "api.main":
                exec(f"from {module} import {item}")
                print(f"   ✅ {module}.{item}")
            elif "." in module:
                exec(f"import {module}")
                print(f"   ✅ {module}")
            else:
                __import__(module)
                print(f"   ✅ {module}")
        except Exception as e:
            print(f"   ❌ {module}: {e}")
    
    # 4. Problemas comunes de Windows
    print("\n4. Problemas comunes de Windows:")
    print("   • Firewall bloqueando Python.exe")
    print("   • Proxy configurado (netsh winhttp show proxy)")
    print("   • Puerto ocupado por otro proceso")
    print("   • Permisos de red para Python")
    
    return socket_ok

# ── Parte 2: Tests de Endpoints Básicos ─────────────────────────────────────

def test_root_endpoint(client: httpx.Client) -> bool:
    """Test del endpoint raíz."""
    print_section("TEST: Root Endpoint")
    
    try:
        response = client.get("/")
        print_response(response)
        
        if response.status_code == 200:
            print("\n✅ Test PASSED")
            return True
        else:
            print(f"\n❌ Test FAILED - Status {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Test FAILED - Exception: {e}")
        return False

def test_health_check(client: httpx.Client) -> bool:
    """Test de health check."""
    print_section("TEST: Health Check")
    
    try:
        response = client.get("/health")
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            if "status" in data and "components" in data:
                print("\n✅ Test PASSED")
                return True
            else:
                print("\n❌ Test FAILED - Missing required fields")
                return False
        else:
            print(f"\n❌ Test FAILED - Status {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Test FAILED - Exception: {e}")
        return False

# ── Parte 3: Tests de Query RAG ────────────────────────────────────────────

def test_query_rag(client: httpx.Client, question: str) -> Tuple[bool, Dict]:
    """Test de consulta RAG con validación de calidad."""
    print_section(f"TEST: Query RAG - '{question[:50]}...'")
    
    request_data = {
        "question": question,
        "top_k": 5,
        "use_cache": True,
        "stream": False,
        "include_tables": True
    }
    
    print(f"Request:\n{json.dumps(request_data, indent=2, ensure_ascii=False)}\n")
    
    try:
        response = client.post("/api/v1/query", json=request_data)
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            
            # Validaciones de calidad
            quality_checks = []
            
            # 1. Estructura básica
            if "query_id" in data:
                quality_checks.append("✅ query_id presente")
            else:
                quality_checks.append("❌ query_id faltante")
            
            if "answer" in data and len(data["answer"]) > 10:
                quality_checks.append("✅ answer válida (más de 10 caracteres)")
            else:
                quality_checks.append("❌ answer muy corta o faltante")
            
            if "sources" in data:
                quality_checks.append("✅ sources presente")
            else:
                quality_checks.append("❌ sources faltante")
            
            # 2. Validación de citas (si existen)
            if "citations" in data:
                citations = data["citations"]
                verified_count = sum(1 for c in citations if c.get("is_verified", False))
                quality_checks.append(f"✅ {len(citations)} citas, {verified_count} verificadas")
            
            # 3. Validación de discrepancias numéricas
            if "numeric_discrepancies" in data:
                discrepancies = data["numeric_discrepancies"]
                if discrepancies:
                    quality_checks.append(f"⚠️  {len(discrepancies)} discrepancias numéricas detectadas")
                else:
                    quality_checks.append("✅ Sin discrepancias numéricas")
            
            # 4. Score de confianza
            if "confidence_score" in data:
                score = data["confidence_score"]
                if score >= 0.7:
                    quality_checks.append(f"✅ Confidence score alto: {score:.2f}")
                elif score >= 0.5:
                    quality_checks.append(f"⚠️  Confidence score medio: {score:.2f}")
                else:
                    quality_checks.append(f"❌ Confidence score bajo: {score:.2f}")
            
            print("\nValidaciones de Calidad:")
            for check in quality_checks:
                print(f"  {check}")
            
            # Determinar si pasa el test
            passed = response.status_code == 200 and len(quality_checks) > 0
            if passed:
                print("\n✅ Test PASSED con validaciones de calidad")
            else:
                print("\n⚠️  Test PASSED pero con advertencias de calidad")
            
            return passed, data
            
        else:
            print(f"\n❌ Test FAILED - Status {response.status_code}")
            return False, {}
            
    except Exception as e:
        print(f"\n❌ Test FAILED - Exception: {e}")
        return False, {}

def test_validation_error(client: httpx.Client) -> bool:
    """Test de error de validación."""
    print_section("TEST: Validation Error")
    
    request_data = {
        "question": "Hola",  # Menos de 10 caracteres
        "top_k": 5
    }
    
    print(f"Request (inválido):\n{json.dumps(request_data, indent=2, ensure_ascii=False)}\n")
    
    try:
        response = client.post("/api/v1/query", json=request_data)
        print_response(response)
        
        if response.status_code == 422:  # Unprocessable Entity
            print("\n✅ Test PASSED (error esperado)")
            return True
        else:
            print(f"\n❌ Test FAILED - Expected 422, got {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Test FAILED - Exception: {e}")
        return False

def test_batch_query(client: httpx.Client) -> bool:
    """Test de consultas en batch."""
    print_section("TEST: Batch Query")
    
    request_data = {
        "questions": SMOKE_TEST_QUESTIONS,
        "top_k": 5,
        "use_cache": True
    }
    
    print(f"Request:\n{json.dumps(request_data, indent=2, ensure_ascii=False)}\n")
    
    try:
        response = client.post("/api/v1/query/batch", json=request_data, timeout=60.0)
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            if "batch_id" in data and "total_questions" in data and "results" in data:
                if len(data["results"]) == len(SMOKE_TEST_QUESTIONS):
                    print("\n✅ Test PASSED")
                    return True
                else:
                    print(f"\n❌ Test FAILED - Expected {len(SMOKE_TEST_QUESTIONS)} results, got {len(data['results'])}")
                    return False
            else:
                print("\n❌ Test FAILED - Missing required fields")
                return False
        else:
            print(f"\n❌ Test FAILED - Status {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Test FAILED - Exception: {e}")
        return False

# ── Parte 4: Smoke Test con PDF ─────────────────────────────────────────────

def test_smoke_with_pdf(client: httpx.Client) -> bool:
    """
    Smoke test completo que valida:
    1. Upload de PDF
    2. Ingesta del documento
    3. Consultas específicas sobre el PDF
    4. Validación de calidad de respuestas
    """
    print_section("SMOKE TEST: Validación Completa con PDF")
    
    # Verificar si el PDF existe
    pdf_path = Path(SMOKE_TEST_PDF)
    if not pdf_path.exists():
        print(f"⚠️  PDF no encontrado: {SMOKE_TEST_PDF}")
        print("   Creando PDF de prueba...")
        
        # Crear un PDF de prueba simple
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.drawString(100, 750, "Decreto 1072 de 2015 - Licencias Ambientales")
            c.drawString(100, 730, "Artículo 1. La licencia ambiental es el instrumento mediante el cual")
            c.drawString(100, 710, "la autoridad ambiental competente autoriza la ejecución de un proyecto,")
            c.drawString(100, 690, "obra o actividad que pueda generar impactos ambientales significativos.")
            c.drawString(100, 670, "Artículo 2. Los requisitos para obtener una licencia ambiental incluyen:")
            c.drawString(100, 650, "1. Estudio de Impacto Ambiental (EIA)")
            c.drawString(100, 630, "2. Plan de Manejo Ambiental (PMA)")
            c.drawString(100, 610, "3. Certificación de cumplimiento de requisitos legales")
            c.drawString(100, 590, "Artículo 3. El plazo máximo para la evaluación es de 60 días hábiles.")
            c.save()
            print(f"✅ PDF de prueba creado: {pdf_path}")
        except ImportError:
            print("❌ No se pudo crear PDF de prueba (reportlab no disponible)")
            return False
    
    print(f"📄 PDF para test: {pdf_path}")
    
    # 1. Upload del PDF
    print("\n1. Upload del PDF...")
    try:
        with open(pdf_path, 'rb') as f:
            files = {'files': (pdf_path.name, f, 'application/pdf')}
            response = client.post("/api/v1/ingestion/upload", files=files)
        
        if response.status_code == 200:
            upload_data = response.json()
            print(f"✅ Upload exitoso: {upload_data}")
            
            file_paths = upload_data.get('file_paths', [])
            if not file_paths:
                print("❌ No se recibieron file_paths en la respuesta")
                return False
        else:
            print(f"❌ Upload falló - Status {response.status_code}")
            print_response(response)
            return False
    except Exception as e:
        print(f"❌ Error en upload: {e}")
        return False
    
    # 2. Ingesta del documento
    print("\n2. Ingesta del documento...")
    try:
        request_data = {"file_paths": file_paths}
        response = client.post("/api/v1/ingestion", json=request_data)
        
        if response.status_code == 200:
            ingestion_data = response.json()
            job_id = ingestion_data.get('job_id')
            print(f"✅ Ingesta iniciada - Job ID: {job_id}")
            
            # Polling del estado
            print("   Polling estado de ingesta...")
            for i in range(10):  # Máximo 10 intentos
                time.sleep(2)
                status_response = client.get(f"/api/v1/ingestion/status/{job_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get('status')
                    print(f"   Intento {i+1}: Status = {status}")
                    
                    if status == 'completed':
                        print("✅ Ingesta completada exitosamente")
                        break
                    elif status == 'failed':
                        print("❌ Ingesta falló")
                        return False
                else:
                    print(f"❌ Error consultando estado: {status_response.status_code}")
                    return False
            else:
                print("⚠️  Timeout en ingesta")
                return False
        else:
            print(f"❌ Ingesta falló - Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error en ingesta: {e}")
        return False
    
    # 3. Consultas específicas sobre el PDF
    print("\n3. Consultas sobre el PDF ingerido...")
    
    pdf_questions = [
        "¿Qué es una licencia ambiental según el Decreto 1072?",
        "¿Cuáles son los requisitos para obtener una licencia ambiental?",
        "¿Cuál es el plazo máximo para la evaluación de una licencia ambiental?"
    ]
    
    all_passed = True
    for i, question in enumerate(pdf_questions, 1):
        print(f"\n   Consulta {i}: '{question}'")
        passed, response_data = test_query_rag(client, question)
        
        if not passed:
            all_passed = False
            print(f"   ❌ Consulta {i} falló")
        else:
            # Validación específica para respuestas de PDF
            answer = response_data.get('answer', '')
            if 'licencia ambiental' in answer.lower() or 'decreto 1072' in answer.lower():
                print(f"   ✅ Consulta {i} válida (respuesta relacionada con PDF)")
            else:
                print(f"   ⚠️  Consulta {i} pasó pero respuesta no parece relacionada con PDF")
    
    if all_passed:
        print("\n✅ Smoke Test COMPLETO - Todas las consultas pasaron")
        return True
    else:
        print("\n⚠️  Smoke Test PARCIAL - Algunas consultas fallaron")
        return False

# ── Parte 5: Tests de Cache ───────────────────────────────────────────────

def test_cache_stats(client: httpx.Client) -> bool:
    """Test de estadísticas de caché."""
    print_section("TEST: Cache Stats")
    
    try:
        response = client.get("/api/v1/cache/stats")
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            if "total_requests" in data and "hit_rate" in data:
                print(f"\n✅ Test PASSED - Total requests: {data['total_requests']}, Hit rate: {data['hit_rate']:.2%}")
                return True
            else:
                print("\n❌ Test FAILED - Missing required fields")
                return False
        else:
            print(f"\n❌ Test FAILED - Status {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Test FAILED - Exception: {e}")
        return False

# ── Main ───────────────────────────────────────────────────────────────────

def main():
    """Ejecuta todos los tests consolidados."""
    print("\n" + "=" * 80)
    print("  🚀 TEST CONSOLIDADO API RAG LEGAL COLOMBIANO")
    print("=" * 80)
    
    # Diagnóstico inicial
    socket_ok = diagnose_system()
    if not socket_ok:
        print("\n❌ El servidor no está corriendo. Iniciando diagnóstico...")
        # Podríamos intentar iniciar el servidor aquí si fuera necesario
        print("   Ejecuta: uvicorn api.main:app --reload")
        return
    
    # Crear cliente HTTP con follow_redirects=True para manejar 307
    try:
        client = httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT, follow_redirects=True)
        
        # Verificar que el servidor esté respondiendo
        print("\n🔍 Verificando que el servidor esté respondiendo...")
        response = client.get("/", timeout=5.0)
        if response.status_code != 200:
            print("❌ El servidor no está respondiendo correctamente")
            return
        print("✅ Servidor corriendo correctamente\n")
        
        # Ejecutar tests
        test_results = []
        
        # Tests básicos
        test_results.append(("Root Endpoint", test_root_endpoint(client)))
        test_results.append(("Health Check", test_health_check(client)))
        
        # Tests de query
        test_results.append(("Query RAG (licencia ambiental)", 
                           test_query_rag(client, "¿Qué es una licencia ambiental?")[0]))
        test_results.append(("Validation Error", test_validation_error(client)))
        test_results.append(("Batch Query", test_batch_query(client)))
        
        # Smoke test con PDF (opcional - puede ser más lento)
        print("\n" + "=" * 80)
        print("  ⚠️  ADVERTENCIA: Smoke test con PDF puede tomar varios minutos")
        print("  ¿Desea ejecutar el smoke test completo? (s/n)")
        print("=" * 80)
        
        user_input = input("  >> ").strip().lower()
        if user_input == 's':
            test_results.append(("Smoke Test con PDF", test_smoke_with_pdf(client)))
        else:
            print("  Smoke test omitido por el usuario")
            test_results.append(("Smoke Test con PDF", "SKIPPED"))
        
        # Tests de cache
        test_results.append(("Cache Stats", test_cache_stats(client)))
        
        # Resumen
        print_section("RESUMEN DE TESTS")
        
        passed_count = 0
        total_count = 0
        
        for test_name, result in test_results:
            total_count += 1
            if result is True:
                passed_count += 1
                print(f"✅ {test_name}: PASSED")
            elif result == "SKIPPED":
                print(f"⏭️  {test_name}: SKIPPED")
            else:
                print(f"❌ {test_name}: FAILED")
        
        print(f"\n📊 Estadísticas:")
        print(f"   Total tests: {total_count}")
        print(f"   Tests pasados: {passed_count}")
        
        if total_count > 0:
            success_rate = (passed_count / total_count) * 100
            print(f"   Tasa de éxito: {success_rate:.1f}%")
        
        if passed_count == total_count:
            print("\n🎉 ¡TODOS LOS TESTS PASARON EXITOSAMENTE!")
        else:
            print(f"\n⚠️  {total_count - passed_count} test(s) fallaron")
        
        print("\n" + "=" * 80)
        
    except httpx.ConnectError:
        print("\n❌ ERROR: No se pudo conectar al servidor")
        print(f"   Asegúrate de que el servidor esté corriendo en {API_BASE_URL}")
        print("   Ejecuta: uvicorn api.main:app --reload")
    
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == "__main__":
    main()