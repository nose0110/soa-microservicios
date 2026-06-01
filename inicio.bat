@echo off
title SOA TecNM - Iniciando Servicios
color 0A

echo =====================================================
echo   SOA TecNM - INICIANDO SERVICIOS
echo =====================================================
echo.

:: Verificar carpeta
if not exist "auth\security.py" (
    echo Error: Ejecuta desde la carpeta "completo 1"
    pause
    exit /b 1
)

echo Iniciando servicios...
echo.

:: 1. CLIENTES - Puerto 8000
echo [1/6] Clientes en puerto 8000...
start "Clientes :8000" cmd /k "cd clientes && py -m uvicorn main:app --port 8000 --reload"
timeout /t 3 /nobreak >nul

:: 2. PRODUCTOS PYTHON - Puerto 8001
echo [2/6] Productos Python en puerto 8001...
start "Productos Py :8001" cmd /k "cd productos && py -m uvicorn main:app --port 8001 --reload"
timeout /t 3 /nobreak >nul

:: 3. PRODUCTOS NODE.JS - Puerto 8011
echo [3/6] Productos Node.js en puerto 8011...
start "Productos Node :8011" cmd /k "cd productos\productos_node && node server.js"
timeout /t 3 /nobreak >nul

:: 4. INVENTARIO - Puerto 8003
echo [4/6] Inventario en puerto 8003...
start "Inventario :8003" cmd /k "cd inventario && py -m uvicorn main:app --port 8003 --reload"
timeout /t 3 /nobreak >nul

:: 5. PEDIDOS - Puerto 8002
echo [5/6] Pedidos en puerto 8002...
start "Pedidos :8002" cmd /k "cd pedidos && py -m uvicorn main:app --port 8002 --reload"
timeout /t 3 /nobreak >nul

:: 6. WORKER RABBITMQ
echo [6/6] Worker RabbitMQ...
start "Worker RabbitMQ" cmd /k "cd pedidos && py worker.py"

echo.
echo =====================================================
echo   SERVICIOS INICIADOS
echo =====================================================
echo.
echo   Endpoints:
echo   - Clientes:     http://localhost:8000/docs
echo   - Productos Py: http://localhost:8001/docs
echo   - Productos Js: http://localhost:8011/
echo   - Inventario:   http://localhost:8003/docs
echo   - Pedidos:      http://localhost:8002/docs
echo   - RabbitMQ UI:  http://localhost:15672
echo.
echo   Usuarios: admin/admin123, usuario/usuario123
echo.
echo   Para detener: cierra cada ventana manualmente
echo.

timeout /t 2 /nobreak >nul
start http://localhost:8002/docs

exit /b 0