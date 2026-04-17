@echo off
REM Script para poblar usuarios en Windows PowerShell
REM

echo.
echo ============================================================
echo POBLANDO USUARIOS DE EJEMPLO...
echo ============================================================
echo.

REM Ejecutar el script Python
.\venv\Scripts\python.exe -m scripts.seed_usuarios

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo LISTO! Ahora abre Swagger en: http://localhost:8000/docs
    echo ============================================================
) else (
    echo.
    echo ERROR: El script no se ejecutó correctamente
    echo.
)

pause
