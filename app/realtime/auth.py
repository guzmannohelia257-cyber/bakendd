"""
Auth para WebSocket: extrae JWT del query string `?token=...`
y devuelve identidad + canales a los que el cliente puede suscribirse.
"""
from typing import Optional

from fastapi import WebSocket, status

from app.core.security import verify_token


class WSIdentity:
    def __init__(self, tipo: str, sub_id: int, id_tenant: Optional[int] = None) -> None:
        self.tipo = tipo
        self.sub_id = sub_id
        self.id_tenant = id_tenant

    @property
    def base_channels(self) -> list[str]:
        if self.tipo == "taller":
            ch = [f"taller:{self.sub_id}"]
            if self.id_tenant:
                ch.append(f"tenant:{self.id_tenant}")
            return ch
        if self.tipo == "usuario":
            return [f"usuario:{self.sub_id}"]
        if self.tipo == "tecnico":
            ch = [f"usuario:{self.sub_id}"]
            if self.id_tenant:
                ch.append(f"tenant:{self.id_tenant}")
            return ch
        return []


async def authenticate_ws(ws: WebSocket) -> Optional[WSIdentity]:
    """
    Valida el token del query string. Si invalido, cierra el WS con 1008.
    """
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Falta token")
        return None

    payload = verify_token(token)
    if not payload:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token invalido")
        return None

    tipo = payload.get("tipo")
    sub = payload.get("sub")
    tid = payload.get("id_tenant")
    if tipo not in ("usuario", "taller", "tecnico") or sub is None:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Claims invalidos")
        return None

    try:
        sub_id = int(sub)
        tid_int = int(tid) if tid is not None else None
    except (TypeError, ValueError):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Claims malformados")
        return None

    return WSIdentity(tipo=tipo, sub_id=sub_id, id_tenant=tid_int)
