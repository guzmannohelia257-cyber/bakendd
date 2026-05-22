"""
Esquemas Pydantic de la aplicación
"""
from app.schemas.user_schema import (
    UsuarioCreate,
    UsuarioResponse,
    UsuarioDetailResponse,
    UsuarioUpdate,
    LoginRequest,
    TokenResponse,
    RolResponse,
    MensajeResponse,
)
from app.schemas.taller_schema import (
    TallerLoginRequest,
    TallerUpdate,
    TallerResponse,
    TallerTokenResponse,
    TecnicoCreate,
    TecnicoUpdate,
    TecnicoResponse,
    TallerServicioCreate,
    TallerServicioResponse,
    TallerConServicios,
    ActualizarServiciosTallerRequest,
    TallerCompatibleResponse,
)
from app.schemas.catalogo_schema import CategoriaResponse
from app.schemas.cotizacion_schema import (
    SolicitarCotizacionesRequest,
    ResponderCotizacionRequest,
    CotizacionResponse,
    CotizacionesSolicitadasResponse,
)
from app.schemas.cancelacion_schema import (
    CancelarAsignacionRequest,
    CancelacionResponse,
    TarifaTrasladoUpdate,
)
from app.schemas.tracking_schema import UbicacionPing, EtaResponse, UbicacionResponse
from app.schemas.kpi_schema import CategoriaCount, KpiResumen, TallerRanking

__all__ = [
    # Usuario
    "UsuarioCreate",
    "UsuarioResponse",
    "UsuarioDetailResponse",
    "UsuarioUpdate",
    "LoginRequest",
    "TokenResponse",
    "RolResponse",
    "MensajeResponse",
    # Taller
    "TallerLoginRequest",
    "TallerUpdate",
    "TallerResponse",
    "TallerTokenResponse",
    "TecnicoCreate",
    "TecnicoUpdate",
    "TecnicoResponse",
    "TallerServicioCreate",
    "TallerServicioResponse",
    "TallerConServicios",
    "ActualizarServiciosTallerRequest",
    "TallerCompatibleResponse",
    "CategoriaResponse",
    "SolicitarCotizacionesRequest",
    "ResponderCotizacionRequest",
    "CotizacionResponse",
    "CotizacionesSolicitadasResponse",
    "CancelarAsignacionRequest",
    "CancelacionResponse",
    "TarifaTrasladoUpdate",
    "UbicacionPing",
    "EtaResponse",
    "UbicacionResponse",
    "CategoriaCount",
    "KpiResumen",
    "TallerRanking",
]
