# Guia de despliegue en Render

Esta guia resume los pasos para desplegar el backend en Render.

## 1) Requisitos
- Proyecto con dependencias en requirements.txt.
- Archivo render.yaml en la raiz del proyecto.
- Variables de entorno definidas en Render.

## 2) Crear servicio en Render
1. En Render: New + > Web Service.
2. Conecta el repositorio y selecciona la rama.
3. Render detectara render.yaml y usara:
   - buildCommand: pip install -r requirements.txt
   - startCommand: gunicorn -k uvicorn.workers.UvicornWorker app.main:app
4. Espera a que termine el build.

## 3) Variables de entorno obligatorias
Configura estas variables en Render (secrets):
- DATABASE_URL
- SECRET_KEY
- CLOUDINARY_CLOUD_NAME
- CLOUDINARY_API_KEY
- CLOUDINARY_API_SECRET

Opcionales segun uso:
- GEMINI_API_KEY
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET

## 4) Configuracion recomendada
- AUTO_CREATE_TABLES=false (usar migraciones en produccion)
- DEBUG=false

## 5) Health check
Render usara /health. Verifica que responda 200.

## 6) Despliegue inicial
1. Haz push al repositorio.
2. Render hace build y despliega automaticamente.
3. Valida endpoints:
   - GET /
   - GET /health

## 7) Notas
- Si necesitas crear tablas automaticamente, cambia AUTO_CREATE_TABLES a true.
- Para problemas de CORS, restringe allow_origins a tu dominio en produccion.
