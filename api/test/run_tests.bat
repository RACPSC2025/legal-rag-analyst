@echo off
echo ========================================
echo  Tests de API - RAG Legal Colombiano
echo ========================================
echo.

REM Verificar que estamos en el directorio correcto
if not exist "..\main.py" (
    echo ❌ Error: No se encuentra api/main.py
    echo    Ejecutar desde la raiz del proyecto
    pause
    exit /b 1
)

REM Verificar entorno virtual
if not exist "..\..\.venv\Scripts\python.exe" (
    echo ❌ Error: No se encuentra entorno virtual (.venv)
    echo    Crear entorno: python -m venv .venv
    pause
    exit /b 1
)

echo 1. Iniciando servidor en segundo plano...
start /B cmd /c "cd ..\.. && .venv\Scripts\python -m uvicorn api.main:app --host 127.0.0.1 --port 8000"
echo    Servidor iniciado (PID: %errorlevel%)

echo.
echo 2. Esperando 5 segundos para que el servidor esté listo...
timeout /t 5 /nobreak > nul

echo.
echo 3. Ejecutando test consolidado...
cd ..\..
.venv\Scripts\python api\test\test_api_consolidated.py

echo.
echo 4. Presiona cualquier tecla para terminar el servidor...
pause > nul

REM Terminar proceso del servidor (buscar por puerto 8000)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    taskkill /F /PID %%a
    echo Servidor terminado (PID: %%a)
)

echo.
echo ========================================
echo  Tests completados
echo ========================================
pause