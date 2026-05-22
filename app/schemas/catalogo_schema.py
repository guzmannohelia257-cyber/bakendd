from pydantic import BaseModel, ConfigDict
from typing import Optional


class CategoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_categoria: int
    codigo: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    requiere_cotizacion: bool
    icono_url: Optional[str] = None
