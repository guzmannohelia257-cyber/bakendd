"""Configuracion global de la plataforma (singleton id=1).

Garantiza que exista la fila unica de ConfiguracionPlataforma con los valores
por defecto (penalizacion SLA 15%, tolerancia 20 min). Es idempotente: si la
fila ya existe no la duplica. La tabla no se trunca en el reseed, por lo que
normalmente este paso solo crea la fila la primera vez.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.configuracion import ConfiguracionPlataforma
from SETT.utils import Ctx, logger


def run(db: Session, ctx: Ctx) -> None:
    config = db.query(ConfiguracionPlataforma).first()
    if config is None:
        config = ConfiguracionPlataforma(
            sla_penalizacion_pct=15,
            sla_tolerancia_min=20,
        )
        db.add(config)
        db.commit()
        logger.info("[catalogos] configuracion_plataforma creada (15% / 20 min)")
    else:
        logger.info("[catalogos] configuracion_plataforma ya existe")
