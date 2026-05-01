"""
Debug Swagger UI — API RAG Legal
────────────────────────────────
Script para depurar problemas con Swagger UI (/docs).

Problemas comunes:
1. OpenAPI schema no se genera
2. Errores en los schemas Pydantic
3. Rutas mal definidas
4. Middleware que bloquea /docs
5. CORS mal configurado

Uso:
    python api/debug_swagger.py

Autor: Fenix Tech Líder
Fecha: 2026-04-28
"""

import sys
import json
from pathlib import Path

# Añadir raíz del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("  DEBUG SWAGGER UI — API RAG LEGAL")
print("=" * 80)

# ── Test 1: Verificar OpenAPI schema ────────────────────────────────────────
print("\n" + "-" * 80)
print("TEST 1: Generar OpenAPI schema")
print("-" * 80)

try:
    from api.main import app
    
    # Intentar generar el schema OpenAPI
    openapi_schema = app.openapi()
    
    print("✅ OpenAPI schema generado correctamente")
    print(f"   Versión OpenAPI: {openapi_schema.get('openapi', 'N/A')}")
    print(f"   Título: {openapi_schema.get('info', {}).get('title', 'N/A')}")
    print(f"   Paths definidos: {len(openapi_schema.get('paths', {}))}")
    
    # Verificar que /docs está en los paths
    if 'paths' in openapi_schema:
        print("\n📋 Paths disponibles:")
        for path in list(openapi_schema['paths'].keys())[:10]:  # Mostrar primeros 10
            print(f"   • {path}")
        
        if len(openapi_schema['paths']) > 10:
            print(f"   ... y {len(openapi_schema['paths']) - 10} paths más")
    
except Exception as e:
    print(f"❌ Error generando OpenAPI schema: {e}")
    import traceback
    traceback.print_exc()

# ── Test 2: Verificar schemas Pydantic ─────────────────────────────────────
print("\n" + "-" * 80)
print("TEST 2: Verificar schemas Pydantic")
print("-" * 80)

try:
    from api.schemas.request_models import QueryRequest, BatchQueryRequest
    from api.schemas.response_models import QueryResponse, ErrorResponse
    
    print("✅ Schemas Pydantic importados correctamente")
    
    # Verificar que los schemas tienen schema_json
    for name, schema in [
        ("QueryRequest", QueryRequest),
        ("QueryResponse", QueryResponse),
        ("ErrorResponse", ErrorResponse)
    ]:
        try:
            json_schema = schema.model_json_schema()
            print(f"   • {name}: ✅ Schema JSON disponible")
        except Exception as e:
            print(f"   • {name}: ❌ Error en schema: {e}")
    
except Exception as e:
    print(f"❌ Error verificando schemas Pydantic: {e}")
    import traceback
    traceback.print_exc()

# ── Test 3: Verificar rutas de documentación ──────────────────────────────
print("\n" + "-" * 80)
print("TEST 3: Verificar rutas de documentación")
print("-" * 80)

try:
    from api.main import app
    
    print("📋 Rutas de documentación configuradas:")
    print(f"   • app.docs_url = {app.docs_url}")
    print(f"   • app.redoc_url = {app.redoc_url}")
    print(f"   • app.openapi_url = {app.openapi_url}")
    
    # Verificar que las rutas están registradas
    docs_routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            if route.path in [app.docs_url, app.redoc_url, app.openapi_url]:
                docs_routes.append(route.path)
    
    if docs_routes:
        print(f"\n✅ Rutas de documentación registradas: {docs_routes}")
    else:
        print("\n⚠️  Rutas de documentación NO registradas")
        print("   FastAPI debería registrarlas automáticamente")
    
except Exception as e:
    print(f"❌ Error verificando rutas: {e}")

# ── Test 4: Verificar CORS para Swagger ────────────────────────────────────
print("\n" + "-" * 80)
print("TEST 4: Verificar CORS para Swagger")
print("-" * 80)

try:
    from api.main import app
    
    # Buscar middleware CORS
    cors_middleware = None
    for mw in app.user_middleware:
        if "CORSMiddleware" in str(mw.cls):
            cors_middleware = mw
            break
    
    if cors_middleware:
        print("✅ Middleware CORS encontrado")
        
        # Extraer configuraciones CORS
        from fastapi.middleware.cors import CORSMiddleware
        
        # Verificar allow_origins
        for option in ["allow_origins", "allow_credentials", "allow_methods", "allow_headers"]:
            if hasattr(cors_middleware, "options"):
                value = cors_middleware.options.get(option, "N/A")
                print(f"   • {option}: {value}")
    else:
        print("⚠️  Middleware CORS NO encontrado")
        print("   Swagger UI puede necesitar CORS para cargar recursos")
    
except Exception as e:
    print(f"❌ Error verificando CORS: {e}")

# ── Test 5: Probar endpoint raíz ───────────────────────────────────────────
print("\n" + "-" * 80)
print("TEST 5: Probar endpoint raíz")
print("-" * 80)

try:
    from api.main import app
    
    # Crear cliente de test
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # Probar endpoint raíz
    response = client.get("/")
    print(f"✅ Endpoint raíz responde: HTTP {response.status_code}")
    print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Respuesta: {json.dumps(data, indent=2)[:200]}...")
    else:
        print(f"   Error: {response.text[:200]}")
    
except Exception as e:
    print(f"❌ Error probando endpoint raíz: {e}")

# ── Test 6: Probar endpoint /openapi.json ─────────────────────────────────
print("\n" + "-" * 80)
print("TEST 6: Probar endpoint /openapi.json")
print("-" * 80)

try:
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    
    print(f"✅ OpenAPI endpoint: HTTP {response.status_code}")
    print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Schema generado: {len(json.dumps(data))} bytes")
        
        # Verificar estructura básica
        required_keys = ["openapi", "info", "paths"]
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            print(f"⚠️  Faltan keys en schema: {missing_keys}")
        else:
            print(f"✅ Estructura OpenAPI completa")
            
    else:
        print(f"❌ Error en /openapi.json: {response.text[:200]}")
    
except Exception as e:
    print(f"❌ Error probando /openapi.json: {e}")
    import traceback
    traceback.print_exc()

# ── Test 7: Verificar problemas comunes ─────────────────────────────────────
print("\n" + "-" * 80)
print("TEST 7: Verificar problemas comunes")
print("-" * 80)

print("🔍 Problemas comunes con Swagger UI:")
print("\n1. **Schemas Pydantic con referencias circulares**")
print("   • Verificar que no hay imports circulares en schemas")
print("   • Usar `from __future__ import annotations`")

print("\n2. **OpenAPI schema demasiado grande**")
print("   • Puede causar timeout en el navegador")
print("   • Verificar con: curl http://127.0.0.1:8000/openapi.json | wc -c")

print("\n3. **CORS bloqueando recursos de Swagger**")
print("   • Swagger UI carga recursos desde CDN")
print("   • Verificar que CORS permite todos los orígenes")

print("\n4. **Middleware que modifica respuestas**")
print("   • Algunos middleware pueden romper JSON responses")
print("   • Verificar logging middleware, auth middleware")

print("\n5. **Problemas de importación silenciosos**")
print("   • FastAPI puede fallar silenciosamente al generar schema")
print("   • Verificar logs de uvicorn con --log-level debug")

# ── Soluciones ─────────────────────────────────────────────────────────────
print("\n" + "-" * 80)
print("SOLUCIONES SUGERIDAS")
print("-" * 80)

print("\n1. **Ejecutar con logging detallado:**")
print("   .venv\\Scripts\\python.exe -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 --log-level debug")

print("\n2. **Probar endpoint /openapi.json directamente:**")
print("   curl http://127.0.0.1:8000/openapi.json | python -m json.tool | head -100")

print("\n3. **Simplificar temporalmente:**")
print("   • Comentar middleware problemático")
print("   • Simplificar schemas complejos")
print("   • Probar con app mínima")

print("\n4. **Verificar navegador:**")
print("   • Probar en modo incógnito (sin extensiones)")
print("   • Probar con Firefox/Chrome/Edge")
print("   • Verificar consola del navegador (F12)")

print("\n5. **Probar endpoint alternativo:**")
print("   http://127.0.0.1:8000/redoc (ReDoc)")
print("   http://127.0.0.1:8000/ (endpoint raíz)")

print("\n" + "=" * 80)
print("  DIAGNÓSTICO COMPLETADO")
print("=" * 80)

print("\n📋 Pasos siguientes:")
print("1. Ejecutar servidor con logging detallado")
print("2. Visitar http://127.0.0.1:8000/openapi.json directamente")
print("3. Verificar consola del navegador para errores")
print("4. Probar en navegador diferente/modo incógnito")

print("\nSi /openapi.json carga pero /docs no:")
print("• Problema probablemente en el navegador")
print("• Swagger UI CDN bloqueado")
print("• JavaScript deshabilitado")

print("\nSi /openapi.json NO carga:")
print("• Problema en generación del schema")
print("• Error en schemas Pydantic")
print("• Importación circular")
