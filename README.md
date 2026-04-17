# 🚗 API de Emergencias Vehiculares

Plataforma inteligente para reportar y gestionar emergencias vehiculares con IA.

## 📋 Requisitos Previos

- Python 3.10+ 
- PostgreSQL 12+
- Git

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone <repo-url>
cd Backend
```

### 2. Crear y activar Virtual Environment
```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crear archivo `.env` en la raíz del proyecto:
```env
DATABASE_URL=postgresql://postgres:12345678@localhost:5432/emergencias_vehiculares
SECRET_KEY=tu-clave-secreta-super-segura-min-32-caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_NAME=Emergencias Vehiculares API
DEBUG=True
```

### 5. Crear Base de Datos en PostgreSQL
```sql
CREATE DATABASE emergencias_vehiculares;
```

### 6. Ejecutar la aplicación
```bash
uvicorn app.main:app --reload
```

La API estará disponible en: http://localhost:8000

## 📚 Documentación Interactiva

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📁 Estructura del Proyecto

```
Backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Punto de entrada de FastAPI
│   ├── api/
│   │   ├── __init__.py
│   │   ├── users.py            # Endpoints de usuarios (CU-01)
│   │   ├── incidencias.py      # Endpoints de incidencias (CU-05)
│   │   └── talleres.py         # Endpoints de talleres
│   ├── models/
│   │   ├── __init__.py
│   │   └── user_model.py       # Modelos SQLAlchemy
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user_schema.py      # Esquemas Pydantic
│   ├── services/
│   │   ├── __init__.py
│   │   └── asignacion.py       # Lógica de negocio
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuración (variables de entorno)
│   │   └── security.py         # Funciones de seguridad (hash, JWT)
│   ├── db/
│   │   ├── __init__.py
│   │   └── session.py          # Configuración de SQLAlchemy
│   └── ai_modules/
│       ├── __init__.py
│       ├── audio.py            # Módulo de transcripción de audio
│       └── vision.py           # Módulo de visión artificial
├── requirements.txt            # Dependencias de Python
├── .env                        # Variables de entorno (gitignored)
├── .gitignore                  # Archivos ignorados por Git
└── README.md
```

## 🔐 Seguridad

- ✅ Contraseñas hasheadas con **bcrypt**
- ✅ Autenticación con **JWT tokens**
- ✅ Variables sensibles en `.env` (nunca en Git)
- ⚠️ En producción, cambiar `SECRET_KEY` y `DEBUG=False`

## 📡 Endpoints Principales

### Usuarios (CU-01)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/usuarios/registro` | Registrar nueva cuenta |
| POST | `/usuarios/login` | Autenticarse |
| GET | `/usuarios/{id}` | Obtener perfil |

### Incidencias (CU-05)

*Por implementar*

## 🧪 Testing

```bash
# Ejecutar tests
pytest

# Con cobertura
pytest --cov=app
```

## 🤝 Contribuir

1. Crear una rama: `git checkout -b feature/nueva-funcionalidad`
2. Hacer cambios y commit: `git commit -am 'Agregar nueva funcionalidad'`
3. Push a la rama: `git push origin feature/nueva-funcionalidad`
4. Abrir un Pull Request

## 📝 Licencia

Proyecto académico - 2026

---

**Estado**: En desarrollo 🚧

**Última actualización**: 15 de abril de 2026
