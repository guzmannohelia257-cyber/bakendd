"""
Configuración centralizada de la aplicación
Lee variables del archivo .env
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Settings que se leen desde el archivo .env
    Pydantic se encarga de las validaciones de tipos
    """
    
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # App
    APP_NAME: str = "Emergencias Vehiculares API"
    DEBUG: bool = False

    # Database
    AUTO_CREATE_TABLES: bool = False

    # Cloudinary (almacenamiento de evidencias)
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # AWS Bedrock (en espera de aumento de cuota)
    AWS_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = "us.amazon.nova-pro-v1:0"

    # Google Gemini (IA activa)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3-flash-preview"

    # Firebase Cloud Messaging
    FIREBASE_CREDENTIALS_PATH: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    class Config:
        # El archivo .env está en la raíz del proyecto Backend
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instancia única de settings (se carga una sola vez)
@lru_cache()
def get_settings() -> Settings:
    """
    Retorna las settings cacheadas
    Se recomienda usar esto en lugar de Settings() directamente
    """
    return Settings()
