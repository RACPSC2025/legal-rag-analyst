#!/usr/bin/env python3
"""
Script de prueba detallado para diagnosticar problemas de la API
"""

import socket
import time
import sys
from pathlib import Path

def check_socket(host='127.0.0.1', port=8000, timeout=5):
    """Verificar si un socket está escuchando"""
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

def test_uvicorn_directly():
    """Probar uvicorn directamente"""
    import subprocess
    import threading
    import queue
    
    def read_output(pipe, queue):
        """Leer output de un pipe"""
        try:
            for line in iter(pipe.readline, ''):
                queue.put(line.strip())
        except:
            pass
    
    print("\n🔧 Probando uvicorn directamente...")
    
    # Comando para ejecutar uvicorn
    cmd = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"]
    
    try:
        # Ejecutar proceso
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Leer output en threads separados
        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()
        
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, stdout_queue))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, stderr_queue))
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Esperar un poco y verificar
        print("   Esperando 5 segundos para inicio del servidor...")
        time.sleep(5)
        
        # Verificar socket
        socket_ok, socket_msg = check_socket()
        print(f"   {socket_msg}")
        
        # Terminar proceso
        process.terminate()
        process.wait(timeout=2)
        
        # Leer cualquier output pendiente
        stdout_lines = []
        while not stdout_queue.empty():
            stdout_lines.append(stdout_queue.get())
        
        stderr_lines = []
        while not stderr_queue.empty():
            stderr_lines.append(stderr_queue.get())
        
        if stderr_lines:
            print(f"\n   📋 Salida de error:")
            for line in stderr_lines[:10]:  # Mostrar primeros 10 errores
                print(f"      {line}")
        
        if stdout_lines:
            print(f"\n   📋 Salida estándar (últimas líneas):")
            for line in stdout_lines[-5:]:  # Mostrar últimas 5 líneas
                print(f"      {line}")
        
        return socket_ok
        
    except Exception as e:
        print(f"   ❌ Error ejecutando uvicorn: {e}")
        return False

def main():
    print("=" * 70)
    print("  DIAGNÓSTICO DETALLADO API RAG LEGAL")
    print("=" * 70)
    
    # 1. Verificar Python y entorno
    print("\n1. Verificando entorno Python...")
    print(f"   Python executable: {sys.executable}")
    print(f"   Python version: {sys.version}")
    print(f"   Working directory: {Path.cwd()}")
    
    # 2. Verificar imports críticos
    print("\n2. Verificando imports críticos...")
    
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
    
    # 3. Verificar socket
    print("\n3. Verificando socket 127.0.0.1:8000...")
    socket_ok, socket_msg = check_socket(timeout=2)
    print(f"   {socket_msg}")
    
    # 4. Probar uvicorn directamente si el socket no está activo
    if not socket_ok:
        test_uvicorn_directly()
    
    # 5. Problemas comunes de Windows
    print("\n5. Problemas comunes de Windows:")
    print("   • Firewall bloqueando Python.exe")
    print("   • Proxy configurado (netsh winhttp show proxy)")
    print("   • Puerto ocupado por otro proceso")
    print("   • Permisos de red para Python")
    
    # 6. Soluciones
    print("\n6. Soluciones sugeridas:")
    print("   a) Verificar firewall:")
    print("      Get-NetFirewallRule | Where {$_.DisplayName -like '*Python*'}")
    print("   b) Verificar proxy:")
    print("      netsh winhttp show proxy")
    print("   c) Probar puerto diferente:")
    print("      uvicorn api.main:app --host 127.0.0.1 --port 8001")
    print("   d) Ejecutar como administrador")
    print("   e) Verificar que .venv\\Scripts\\python.exe tiene permisos de red")
    
    print("\n" + "=" * 70)
    print("  DIAGNÓSTICO COMPLETADO")
    print("=" * 70)

if __name__ == "__main__":
    main()