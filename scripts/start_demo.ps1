Write-Host "== 1. Levantando Redis =="
docker compose up -d redis
docker exec yary-redis redis-cli ping
if (-not $?) { Write-Error "Redis no responde"; exit 1 }

Write-Host "== 2. Verificando Postgres =="
$env:PGPASSWORD = "12345678"
psql -h localhost -U postgres -d emergencias_vehiculares -c "SELECT 1"
if (-not $?) { Write-Error "Postgres no responde"; exit 1 }

Write-Host "== 3. Aplicando migraciones =="
.\venv\Scripts\alembic.exe upgrade head
if (-not $?) { Write-Error "Fallo al aplicar migraciones"; exit 1 }

Write-Host "== 4. Cargando datos demo =="
.\venv\Scripts\python.exe -m scripts.seed_demo
if (-not $?) { Write-Error "Fallo al cargar datos demo"; exit 1 }

Write-Host "== 5. Arrancando backend =="
Start-Process -NoNewWindow -FilePath ".\venv\Scripts\python.exe" `
    -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"

Write-Host "LISTO. Acceder a http://localhost:8000/docs"
