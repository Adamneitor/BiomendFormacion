"""
Panel administrador — autenticación por sesión + listado de inscripciones.
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
from functools import wraps
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from fastapi import APIRouter, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import get_engine
from app.email_service import send_acceso_meet
from app.repositories.inscripcion import (
    actualizar_estado_inscripcion,
    formatear_fecha,
    formatear_telefono,
    listar_inscripciones,
    normalizar_telefono,
    obtener_inscripcion,
    resumen_inscripciones,
)
from app.security import ensure_csrf_token, rate_limit_ok, validate_csrf

logger = logging.getLogger("biomend.admin")

router = APIRouter(prefix="/admin", tags=["admin"])

BASE_DIR = Path(__file__).resolve().parent
PRIVATE_UPLOAD_DIR = BASE_DIR.parent / "storage" / "private"
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.auto_reload = True
templates.env.globals["fmt_fecha"] = formatear_fecha
templates.env.globals["fmt_tel"] = formatear_telefono


def get_admin_credentials() -> tuple[str, str]:
    user = (os.getenv("ADMIN_USERNAME") or "").strip()
    password = (os.getenv("ADMIN_PASSWORD") or "").strip()
    return user, password


def admin_configured() -> bool:
    user, password = get_admin_credentials()
    return bool(user and password)


def is_admin(request: Request) -> bool:
    return bool(request.session.get("admin_auth") is True)


def require_admin(view: Callable):
    @wraps(view)
    async def wrapper(request: Request, *args, **kwargs):
        if not is_admin(request):
            return RedirectResponse(url="/admin/login", status_code=303)
        return await view(request, *args, **kwargs)

    return wrapper


def whatsapp_href(telefono: str, nombre: str = "", programa: str = "") -> str:
    digits = normalizar_telefono(telefono)
    if len(digits) == 10:
        digits = "1" + digits
    msg = (
        f"Hola {nombre}, te escribimos de BIOMEND Formación Continua"
        + (f" sobre tu inscripción a «{programa}»." if programa else ".")
    )
    from urllib.parse import quote
    return f"https://wa.me/{digits}?text={quote(msg)}"


def valid_meet_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"https", "http"}:
            return False
        host = (parsed.hostname or "").lower()
        return bool(host) and ("." in host)
    except Exception:
        return False


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, err: str = ""):
    if is_admin(request):
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin_login.html",
        {
            "request": request,
            "csrf_token": ensure_csrf_token(request),
            "error": err,
            "configured": admin_configured(),
        },
    )


@router.post("/login")
async def admin_login_submit(
    request: Request,
    csrf_token: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
):
    ip = request.client.host if request.client else "unknown"
    if not rate_limit_ok(f"admin-login:{ip}", limit=10, window_seconds=600):
        return RedirectResponse(url="/admin/login?err=rate", status_code=303)
    if not validate_csrf(request, csrf_token):
        return RedirectResponse(url="/admin/login?err=csrf", status_code=303)

    expected_user, expected_pass = get_admin_credentials()
    if not expected_user or not expected_pass:
        return RedirectResponse(url="/admin/login?err=config", status_code=303)

    user_ok = hmac.compare_digest(username.strip(), expected_user)
    pass_ok = hmac.compare_digest(password, expected_pass)
    if not (user_ok and pass_ok):
        return RedirectResponse(url="/admin/login?err=creds", status_code=303)

    request.session["admin_auth"] = True
    request.session["admin_user"] = expected_user
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, msg: str = ""):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    engine = get_engine()
    rows: list[dict] = []
    stats = {"total": 0, "hoy": 0, "recibidas": 0, "acceso_enviado": 0, "por_programa": []}
    db_error = ""
    if engine is None:
        db_error = "DATABASE_URL no configurada."
    else:
        try:
            rows = listar_inscripciones(engine, limit=300)
            stats = resumen_inscripciones(engine)
            for r in rows:
                r["wa_href"] = whatsapp_href(
                    r.get("Telefono") or "",
                    f"{r.get('Nombres', '')} {r.get('Apellidos', '')}".strip(),
                    r.get("Nombre_Programa") or "",
                )
        except Exception:
            logger.exception("Error listando inscripciones")
            db_error = "No se pudieron leer las inscripciones. ¿Se aplicó la migración?"

    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "request": request,
            "csrf_token": ensure_csrf_token(request),
            "rows": rows,
            "stats": stats,
            "db_error": db_error,
            "flash": msg,
            "admin_user": request.session.get("admin_user", ""),
        },
    )


@router.get("/inscripcion/{id_inscripcion}", response_class=HTMLResponse)
async def admin_inscripcion_detail(request: Request, id_inscripcion: int, msg: str = "", err: str = ""):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    engine = get_engine()
    if engine is None:
        return RedirectResponse(url="/admin", status_code=303)
    data = obtener_inscripcion(engine, id_inscripcion)
    if not data:
        return RedirectResponse(url="/admin", status_code=303)

    data["wa_href"] = whatsapp_href(
        data.get("Telefono") or "",
        f"{data.get('Nombres', '')} {data.get('Apellidos', '')}".strip(),
        data.get("Nombre_Programa") or "",
    )

    return templates.TemplateResponse(
        request,
        "admin_detail.html",
        {
            "request": request,
            "csrf_token": ensure_csrf_token(request),
            "item": data,
            "flash": msg,
            "error": err,
            "admin_user": request.session.get("admin_user", ""),
        },
    )


@router.post("/inscripcion/{id_inscripcion}/enviar-acceso")
async def admin_enviar_acceso(
    request: Request,
    id_inscripcion: int,
    csrf_token: str = Form(...),
    meet_link: str = Form(...),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    if not validate_csrf(request, csrf_token):
        return RedirectResponse(
            url=f"/admin/inscripcion/{id_inscripcion}?err=csrf",
            status_code=303,
        )

    link = (meet_link or "").strip()
    if not valid_meet_url(link):
        return RedirectResponse(
            url=f"/admin/inscripcion/{id_inscripcion}?err=meet",
            status_code=303,
        )

    engine = get_engine()
    if engine is None:
        return RedirectResponse(url="/admin", status_code=303)
    data = obtener_inscripcion(engine, id_inscripcion)
    if not data:
        return RedirectResponse(url="/admin", status_code=303)

    ok = send_acceso_meet(
        estudiante_nombre=f"{data['Nombres']} {data['Apellidos']}".strip(),
        estudiante_correo=data["Correo"],
        programa=data["Nombre_Programa"],
        meet_link=link,
    )
    if not ok:
        return RedirectResponse(
            url=f"/admin/inscripcion/{id_inscripcion}?err=smtp",
            status_code=303,
        )

    try:
        actualizar_estado_inscripcion(engine, id_inscripcion, "ACCESO_ENVIADO")
    except Exception:
        logger.exception("No se pudo actualizar estado a ACCESO_ENVIADO")

    return RedirectResponse(
        url=f"/admin/inscripcion/{id_inscripcion}?msg=acceso",
        status_code=303,
    )


@router.get("/documento/{id_inscripcion}/{nombre_almacenado}")
async def admin_download_doc(request: Request, id_inscripcion: int, nombre_almacenado: str):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    safe = Path(nombre_almacenado).name
    if ".." in safe or "/" in safe or "\\" in safe:
        return RedirectResponse(url="/admin", status_code=303)

    engine = get_engine()
    if engine is None:
        return RedirectResponse(url="/admin", status_code=303)
    data = obtener_inscripcion(engine, id_inscripcion)
    if not data:
        return RedirectResponse(url="/admin", status_code=303)

    allowed = {d["Nombre_Almacenado"] for d in data.get("documentos", [])}
    if safe not in allowed:
        return RedirectResponse(url="/admin", status_code=303)

    path = (PRIVATE_UPLOAD_DIR / safe).resolve()
    try:
        path.relative_to(PRIVATE_UPLOAD_DIR.resolve())
    except ValueError:
        return RedirectResponse(url="/admin", status_code=303)
    if not path.is_file():
        return HTMLResponse("Archivo no disponible en este servidor (disco efímero).", status_code=404)

    original = next(
        (d["Nombre_Original"] for d in data["documentos"] if d["Nombre_Almacenado"] == safe),
        safe,
    )
    return FileResponse(path, filename=original)
