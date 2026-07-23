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
from typing import Callable, Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import get_engine
from app.repositories.inscripcion import listar_inscripciones, obtener_inscripcion
from app.security import ensure_csrf_token, rate_limit_ok, validate_csrf

logger = logging.getLogger("biomend.admin")

router = APIRouter(prefix="/admin", tags=["admin"])

BASE_DIR = Path(__file__).resolve().parent
PRIVATE_UPLOAD_DIR = BASE_DIR.parent / "storage" / "private"
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.auto_reload = True


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
    # Rotar CSRF tras login
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    engine = get_engine()
    rows: list[dict] = []
    db_error = ""
    if engine is None:
        db_error = "DATABASE_URL no configurada."
    else:
        try:
            rows = listar_inscripciones(engine, limit=300)
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
            "db_error": db_error,
            "admin_user": request.session.get("admin_user", ""),
        },
    )


@router.get("/inscripcion/{id_inscripcion}", response_class=HTMLResponse)
async def admin_inscripcion_detail(request: Request, id_inscripcion: int):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    engine = get_engine()
    if engine is None:
        return RedirectResponse(url="/admin", status_code=303)
    data = obtener_inscripcion(engine, id_inscripcion)
    if not data:
        return RedirectResponse(url="/admin", status_code=303)

    return templates.TemplateResponse(
        request,
        "admin_detail.html",
        {
            "request": request,
            "csrf_token": ensure_csrf_token(request),
            "item": data,
            "admin_user": request.session.get("admin_user", ""),
        },
    )


@router.get("/documento/{id_inscripcion}/{nombre_almacenado}")
async def admin_download_doc(request: Request, id_inscripcion: int, nombre_almacenado: str):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    # Solo nombres opacos (hex + extensión)
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
