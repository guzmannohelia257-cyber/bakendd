"""
Catalogos auxiliares: categoria_problema, prioridad, tipo_evidencia, metodo_pago.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.catalogos import (
    CategoriaProblema,
    MetodoPago,
    Prioridad,
    TipoEvidencia,
)
from SETT.config import CATEGORIAS, METODOS_PAGO, PRIORIDADES, TIPOS_EVIDENCIA
from SETT.utils import Ctx, logger


def run(db: Session, ctx: Ctx) -> None:
    db.add_all([
        CategoriaProblema(codigo=cod, nombre=n, descripcion=d, requiere_cotizacion=req)
        for cod, n, d, req in CATEGORIAS
    ])
    db.add_all([Prioridad(nivel=n, orden=o) for n, o in PRIORIDADES])
    db.add_all([TipoEvidencia(nombre=n) for n in TIPOS_EVIDENCIA])
    db.add_all([MetodoPago(nombre=n) for n in METODOS_PAGO])
    db.commit()

    for c in db.query(CategoriaProblema).all():
        ctx.categoria[c.nombre] = c
    for p in db.query(Prioridad).all():
        ctx.prioridad[p.nivel] = p
    for t in db.query(TipoEvidencia).all():
        ctx.tipo_evidencia[t.nombre] = t
    for m in db.query(MetodoPago).all():
        ctx.metodo_pago[m.nombre] = m

    logger.info(
        f"[catalogos] categorias={len(ctx.categoria)}, "
        f"prioridades={len(ctx.prioridad)}, "
        f"tipos_evidencia={len(ctx.tipo_evidencia)}, "
        f"metodos_pago={len(ctx.metodo_pago)}"
    )
