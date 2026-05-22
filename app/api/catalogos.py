"""Endpoints de catalogos publicos: categorias, prioridades, estados."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.catalogos import CategoriaProblema
from app.schemas.catalogo_schema import CategoriaResponse


router = APIRouter(tags=["Catalogos"])


@router.get(
    "/categorias",
    response_model=List[CategoriaResponse],
    summary="Listar las 7 categorias oficiales de incidente",
)
def listar_categorias(db: Session = Depends(get_db)):
    """
    Publico. Devuelve todas las categorias con su codigo, nombre, descripcion
    y flag `requiere_cotizacion`. Lo consumen tanto Flutter (al reportar
    incidente) como Angular (al declarar servicios del taller).
    """
    return db.query(CategoriaProblema).order_by(CategoriaProblema.nombre).all()
