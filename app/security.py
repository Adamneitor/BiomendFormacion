"""
Controles de ciberseguridad — BIOMEND Formación Continua.
Upload seguro, CSRF, rate limit, cabeceras HTTP.
"""

from __future__ import annotations

import os
import re
import secrets
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Deque, Optional

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

# --- Configuración -----------------------------------------------------------

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_UPLOAD_EXT = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
MAGIC_SIGNATURES = (
    (b"%PDF", ".pdf"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
)

FIELD_LIMITS = {
    "nombres": 120,
    "apellidos": 120,
    "correo": 254,
    "telefono": 32,
    "institucion": 200,
    "profesion": 200,
    "pais": 100,
    "ciudad": 120,
    "idioma": 40,
    "programa": 300,
    "certificado": 200,
}


def is_production() -> bool:
    return (os.getenv("APP_ENV") or "").strip().lower() in {"production", "prod"}


def get_secret_key() -> str:
    key = (os.getenv("SECRET_KEY") or "").strip()
    if key:
        return key
    if is_production():
        raise RuntimeError("SECRET_KEY es obligatorio en producción")
    # Solo desarrollo: clave efímera (sesiones no persisten entre reinicios)
    return "dev-only-" + secrets.token_hex(16)


def get_allowed_hosts() -> list[str]:
    raw = (os.getenv("ALLOWED_HOSTS") or "").strip()
    if raw:
        return [h.strip() for h in raw.split(",") if h.strip()]
    if is_production():
        # Dominio propio + hosts de Railway (ajustar ALLOWED_HOSTS en prod real)
        return [
            "biomendformacion.com",
            "www.biomendformacion.com",
            "*.up.railway.app",
            "*.railway.app",
        ]
    return ["*"]


# --- Rate limit en memoria (por IP) ------------------------------------------

class _RateBucket:
    def __init__(self) -> None:
        self.hits: Deque[float] = deque()


_rate_store: dict[str, _RateBucket] = defaultdict(_RateBucket)


def rate_limit_ok(key: str, limit: int = 8, window_seconds: int = 600) -> bool:
    """True si la petición está dentro del cupo."""
    now = time.time()
    bucket = _rate_store[key]
    while bucket.hits and bucket.hits[0] < now - window_seconds:
        bucket.hits.popleft()
    if len(bucket.hits) >= limit:
        return False
    bucket.hits.append(now)
    return True


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host
    return "unknown"


# --- CSRF --------------------------------------------------------------------

CSRF_SESSION_KEY = "csrf_token"


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf(request: Request, form_token: Optional[str]) -> bool:
    expected = request.session.get(CSRF_SESSION_KEY)
    if not expected or not form_token:
        return False
    return secrets.compare_digest(str(expected), str(form_token))


def validate_origin(request: Request) -> bool:
    """Rechaza POST cross-site evidentes por Origin/Referer."""
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    host = request.headers.get("host", "")
    if origin:
        # Origin: https://host[:port]
        return host in origin
    if referer:
        return host in referer
    # Sin Origin/Referer (algunos clientes): se apoya en CSRF token
    return True


# --- Uploads seguros ---------------------------------------------------------

def detect_extension(content: bytes) -> Optional[str]:
    for magic, ext in MAGIC_SIGNATURES:
        if content.startswith(magic):
            return ".jpg" if ext == ".jpg" else ext
    return None


async def read_upload_limited(upload, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    """Lee el upload en chunks y aborta si supera el límite (anti-DoS memoria)."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError("ARCHIVO_DEMASIADO_GRANDE")
        chunks.append(chunk)
    return b"".join(chunks)


def validate_upload_content(original_name: str, content: bytes) -> tuple[str, str]:
    """
    Valida extensión declarada + magic bytes.
    Retorna (ext_canonica, mime_detectado).
    """
    if not content:
        raise ValueError("ARCHIVO_VACIO")
    declared = Path(original_name or "").suffix.lower()
    if declared == ".jpeg":
        declared = ".jpg"
    detected = detect_extension(content)
    if detected is None:
        raise ValueError("TIPO_NO_PERMITIDO")
    if declared and declared not in ALLOWED_UPLOAD_EXT and declared != ".jpeg":
        raise ValueError("EXTENSION_NO_PERMITIDA")
    # Si declara extensión, debe coincidir con magic (jpeg/jpg equivalentes)
    if declared in {".jpg", ".jpeg"} and detected != ".jpg":
        raise ValueError("EXTENSION_NO_COINCIDE")
    if declared == ".png" and detected != ".png":
        raise ValueError("EXTENSION_NO_COINCIDE")
    if declared == ".pdf" and detected != ".pdf":
        raise ValueError("EXTENSION_NO_COINCIDE")
    mime = ALLOWED_UPLOAD_EXT[detected if detected != ".jpg" else ".jpg"]
    return detected, mime


def opaque_stored_name(ext: str) -> str:
    return f"{uuid.uuid4().hex}{ext}"


def sanitize_text(value: str, max_len: int) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", (value or "").strip())
    return cleaned[:max_len]


# --- Middleware cabeceras ----------------------------------------------------

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if is_production():
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        # No filtrar server version
        if "server" in response.headers:
            del response.headers["server"]
        return response
