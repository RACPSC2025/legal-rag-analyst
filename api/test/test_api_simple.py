#!/usr/bin/env python3
"""
Script de prueba simple para la API RAG Legal
"""

import subprocess
import time
import requests
import sys
from pathlib import Path

def check_port(port=8000):
    """Verificar si el puerto está en uso"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def test_endpoint(url):
    """Probar un endpoint HTTP"""
    try:
        response = requests.get(url, timeout=5)
        return response.status_code, response.headers.get('content-type', 'N/A')
    except Exception as e:
        return None, str(e)

def main():
    print("=" * 60)
    print("  PRUEBA DE CONECTIVIDAD API RAG LEGAL")
    print("=" * 60)
    
    # Verificar puerto
    print("\n1. Verificando puerto 8000...")
    if check_port(8000):
        print("   ✅ Puerto 8000 está en uso")
    else:
        print("   ❌ Puerto 8000 NO está en uso")
        print("   La API no se está ejecutando")
        return
    
    # Probar endpoints
    print("\n2. Probando endpoints...")
    
    endpoints = [
        ("/", "Endpoint raíz"),
        ("/openapi.json", "OpenAPI JSON"),
        ("/docs", "Swagger UI"),
        ("/health", "Health check"),
    ]
    
    for endpoint, description in endpoints:
        url = f"http://127.0.0.1:8000{endpoint}"
        print(f"\n   {description} ({url}):")
        status, content_type = test_endpoint(url)
        
        if status:
            print(f"      ✅ Status: {status}")
            print(f"      Content-Type: {content_type}")
            
            if status == 200:
                print("      ✅ ÉXITO: Endpoint responde correctamente")
            else:
                print(f"      ⚠️  ADVERTENCIA: Status {status} (esperado 200)")
        else:
            print(f"      ❌ ERROR: {content_type}")
    
    # Verificar problemas comunes
    print("\n3. Diagnóstico de problemas comunes...")
    
    # Verificar firewall
    print("\n   🔍 Problemas comunes de Windows:")
    print("   • Firewall bloqueando Python")
    print("   • Proxy configurado incorrectamente")
    print("   • Navegador con extensiones que bloquean")
    print("   • Puerto bloqueado por otro proceso")
    
    # Soluciones
    print("\n   🛠️ Soluciones sugeridas:")
    print("   1. Ejecutar en modo incógnito (Ctrl+Shift+N)")
    print("   2. Verificar Firewall de Windows")
    print("   3. Probar con otro navegador (Chrome/Firefox/Edge)")
    print("   4. Ejecutar: netsh winhttp show proxy")
    print("   5. Ejecutar: Get-NetFirewallRule | Where {$_.DisplayName -like '*Python*'}")
    
    print("\n" + "=" * 60)
    print("  DIAGNÓSTICO COMPLETADO")
    print("=" * 60)

if __name__ == "__main__":
    main()