@echo off
echo ========================================
echo  API RAG Legal - Modo Debug
echo ========================================
echo.
echo Este script inicia la API con logging detallado
echo y verifica la conectividad antes de iniciar.
echo.

REM Verificar que el entorno virtual existe
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Entorno virtual .venv no encontrado!
    echo Ejecuta: python -m venv .venv
    pause
    exit /b 1
)

REM Verificar que el puerto 8000 está disponible
echo Verificando puerto 8000...
netstat -ano | find ":8000" > nul
if %errorlevel% equ 0 (
    echo ADVERTENCIA: Puerto 8000 ya está en uso!
    echo.
    echo Opciones:
    echo 1. Matar proceso que usa puerto 8000
    echo 2. Usar puerto diferente (ej: 8001)
    echo 3. Continuar de todos modos
    echo.
    set /p choice="Selecciona opción (1-3): "
    
    if "%choice%"=="1" (
        echo Buscando PID del proceso en puerto 8000...
        for /f "tokens=5" %%a in ('netstat -ano ^| find ":8000" ^| find "LISTENING"') do (
            echo Matando proceso PID: %%a
            taskkill /PID %%a /F
        )
    ) else if "%choice%"=="2" (
        set /p newport="Nuevo puerto (ej: 8001): "
        set PORT=%newport%
    ) else (
        set PORT=8000
    )
) else (
    set PORT=8000
)

REM Verificar conectividad básica
echo.
echo Verificando conectividad de red...
ping -n 1 127.0.0.1 > nul
if %errorlevel% neq 0 (
    echo ERROR: No hay conectividad de loopback!
    echo Verifica tu configuración de red.
    pause
    exit /b 1
)

REM Iniciar API con logging detallado
echo.
echo ========================================
echo Iniciando API en puerto %PORT%...
echo ========================================
echo.
echo URLs importantes:
echo   Swagger UI:    http://127.0.0.1:%PORT%/docs
echo   ReDoc:         http://127.0.0.1:%PORT%/redoc
echo   API Root:      http://127.0.0.1:%PORT%/
echo   OpenAPI JSON:  http://127.0.0.1:%PORT%/openapi.json
echo   Test HTML:     http://127.0.0.1:%PORT%/test_swagger.html
echo.
echo Presiona Ctrl+C para detener el servidor.
echo.

.venv\Scripts\python.exe -m uvicorn api.main:app --reload --host 127.0.0.1 --port %PORT% --log-level debug