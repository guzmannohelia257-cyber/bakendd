"""
Servicio de Notificaciones Push — Firebase Cloud Messaging (FCM).

Inicializa firebase-admin con las credenciales del entorno.
Si no hay credenciales configuradas, las operaciones de push se omiten
sin interrumpir el flujo de la aplicación (graceful degradation).
"""
import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from app.models.transaccional import Notificacion

logger = logging.getLogger("notificacion_service")

# Firebase Admin SDK (opcional)

_firebase_app = None


def _init_firebase():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    # Dos formas de proveer el service account de Firebase:
    #  - FIREBASE_CREDENTIALS_JSON: el JSON completo como variable de entorno
    #    (recomendado en Render: sin archivos en disco).
    #  - FIREBASE_CREDENTIALS_PATH: ruta a un archivo .json.
    creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    # En Render el Secret File se monta en /etc/secrets/. Si no se configuro
    # ninguna variable, usamos esa ruta por defecto cuando el archivo existe.
    if not creds_json and not creds_path:
        default_secret = "/etc/secrets/firebase-credentials.json"
        if os.path.exists(default_secret):
            creds_path = default_secret
    if not creds_json and not creds_path:
        logger.warning(
            "[FCM] Sin credenciales de Firebase (JSON / PATH / secret file) — push desactivado"
        )
        return None

    try:
        import json

        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
        else:
            if creds_json:
                cred = credentials.Certificate(json.loads(creds_json))
            else:
                cred = credentials.Certificate(creds_path)
            _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("[FCM] Firebase Admin SDK inicializado")
    except Exception as exc:
        logger.error(f"[FCM] Error al inicializar Firebase: {exc}")
        _firebase_app = None

    return _firebase_app


def _send_fcm(token: str, titulo: str, cuerpo: str, data: Optional[dict] = None) -> bool:
    """Envía una notificación push mediante FCM. Retorna True si fue exitoso."""
    app = _init_firebase()
    if app is None:
        return False

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=titulo, body=cuerpo),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        response = messaging.send(message)
        logger.info(f"[FCM] Mensaje enviado: {response}")
        return True
    except Exception as exc:
        logger.error(f"[FCM] Error al enviar push a token {token[:12]}...: {exc}")
        return False


# API pública

def crear_y_enviar_notificacion(
    db: Session,
    titulo: str,
    mensaje: str,
    *,
    id_usuario: Optional[int] = None,
    id_taller: Optional[int] = None,
    id_incidente: Optional[int] = None,
    push_token: Optional[str] = None,
    data: Optional[dict] = None,
) -> Notificacion:
    """
    Persiste una notificación en BD y, si hay token, envía push FCM.
    Exactamente uno de id_usuario o id_taller debe estar presente.
    """
    if (id_usuario is None) == (id_taller is None):
        raise ValueError("Exactamente uno de id_usuario o id_taller debe ser provisto")

    notif = Notificacion(
        id_usuario=id_usuario,
        id_taller=id_taller,
        id_incidente=id_incidente,
        titulo=titulo,
        mensaje=mensaje,
        enviado_push=False,
    )
    db.add(notif)
    db.flush()  # Obtener id_notificacion antes del commit

    if push_token:
        enviado = _send_fcm(push_token, titulo, mensaje, data=data)
        notif.enviado_push = enviado

    return notif
