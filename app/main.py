"""
BIOMEND Formación Continua - Aplicación web multipágina con FastAPI.
Pestañas: Inicio, Nosotros, Programas, Inscripción, FAQ, Contacto
+ formulario de inscripción con documentos requeridos.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.admin import router as admin_router
from app.db import get_engine
from app.db_migrate import apply_migrations
from app.email_service import notify_inscripcion
from app.repositories.inscripcion import (
    DocumentoPayload,
    InscripcionPayload,
    guardar_inscripcion,
    resolver_slug_programa,
)
from app.security import (
    FIELD_LIMITS,
    MAX_UPLOAD_BYTES,
    SecurityHeadersMiddleware,
    client_ip,
    ensure_csrf_token,
    get_allowed_hosts,
    get_secret_key,
    is_production,
    opaque_stored_name,
    rate_limit_ok,
    read_upload_limited,
    sanitize_text,
    validate_csrf,
    validate_origin,
    validate_upload_content,
)

BASE_DIR = Path(__file__).resolve().parent
# Almacenamiento PRIVADO (fuera de /static — no se sirve públicamente)
PRIVATE_UPLOAD_DIR = BASE_DIR.parent / "storage" / "private"
PRIVATE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INSCRIPTIONS_FILE = BASE_DIR / "inscripciones.tsv"

logger = logging.getLogger("biomend")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    engine = get_engine()
    if engine is not None:
        try:
            apply_migrations(engine)
            logger.info("Migraciones de esquema verificadas/aplicadas")
        except Exception:
            logger.exception("Fallo al aplicar migraciones — revisa DATABASE_URL y permisos")
    else:
        logger.warning("Sin DATABASE_URL — omitiendo migraciones")
    yield


_docs_enabled = not is_production()
app = FastAPI(
    title="BIOMEND Formación Continua",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
    lifespan=lifespan,
)

# Orden: ProxyHeaders → TrustedHost → Session → Security headers
# Railway termina TLS; X-Forwarded-Proto debe llegar a Starlette/url_for
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
_hosts = get_allowed_hosts()
if _hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_hosts)
app.add_middleware(SessionMiddleware, secret_key=get_secret_key(), same_site="lax", https_only=is_production())
app.add_middleware(SecurityHeadersMiddleware)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(admin_router)
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.auto_reload = True
templates.env.cache = None
ASSET_VERSION = "20260723a"


def static_url(path: str) -> str:
    """Ruta relativa HTTPS-safe (evita mixed content detrás del proxy de Railway)."""
    clean = str(path or "").lstrip("/")
    return f"/static/{clean}?v={ASSET_VERSION}"


templates.env.globals["static_url"] = static_url

# ----------------------------------------------------------------------------
# Datos de marca
# ----------------------------------------------------------------------------
BRAND = {
    "name": "BIOMEND",
    "full_name": "BIOMEND Formación Continua",
    "tagline": "Capacitación y actualización profesional para el área de la salud.",
    "whatsapp_primary": "18098970552",
    "whatsapp_primary_label": "809-897-0552",
    "whatsapp_secondary": "18293380552",
    "whatsapp_secondary_label": "829-338-0552",
    "email": "info@biomendformacion.com",
    "website": "https://www.biomendformacion.com",
    "website_label": "www.biomendformacion.com",
    "instagram_user": "biomendformacion",
    "instagram_url": "https://www.instagram.com/biomendformacion",
    "facebook_label": "Biomend Formación",
    "facebook_url": "https://www.facebook.com/BiomendFormacion",
    "wa_message": "Hola, me gustaría recibir información sobre los programas de BIOMEND",
}

# ----------------------------------------------------------------------------
# Contenido — estadísticas, modalidades, beneficios
# ----------------------------------------------------------------------------
HERO_STATS = [
    {"value": "3", "label": "Programas abiertos"},
    {"value": "100%", "label": "Enfoque práctico"},
    {"value": "RD", "label": "República Dominicana"},
]

# Fotos reales de egresados / cohorts BIOMEND (static/img/egresados).
GRADUATES = [
    {
        "src": "img/egresados/egresados-01.png",
        "alt": "Egresados BIOMEND con certificados de formación continua",
        "caption": "Cohorte certificada · Formación continua",
    },
    {
        "src": "img/egresados/egresados-02.png",
        "alt": "Participantes BIOMEND en bata blanca con sus diplomas",
        "caption": "Profesionales de la salud · República Dominicana",
    },
    {
        "src": "img/egresados/egresados-03.png",
        "alt": "Grupo de egresados BIOMEND celebrando su certificación",
        "caption": "Comunidad académica BIOMEND",
    },
    {
        "src": "img/egresados/egresados-04.png",
        "alt": "Egresados frente al banner de BIOMEND Formación Continua",
        "caption": "Formación continua en el área de la salud",
    },
]

# Imágenes editoriales (formación médica / laboratorio / práctica clínica).
SITE_IMAGES = {
    "hero": "https://images.unsplash.com/photo-1527613426441-4da17471b66d?w=900&h=1000&fit=crop&auto=format&q=80",
    "hero_alt": "Estudiantes y profesionales latinos de ciencias de la salud en formación universitaria",
    "about": "img/egresados/egresados-01.png",
    "about_alt": "Participantes certificados de programas BIOMEND",
    "classroom": "https://images.unsplash.com/photo-1527613426441-4da17471b66d?w=900&h=700&fit=crop&auto=format&q=80",
    "lab": "https://images.unsplash.com/photo-1579154204601-01588f351e67?w=900&h=700&fit=crop&auto=format&q=80",
    "practice": "https://images.unsplash.com/photo-1551076805-e1869033e561?w=900&h=700&fit=crop&auto=format&q=80",
}

MODALITIES = [
    {"icon": "graduation-cap", "title": "Diplomados", "description": "Programas de especialización profesional"},
    {"icon": "users", "title": "Simposios", "description": "Encuentros con expertos del sector"},
    {"icon": "book-open", "title": "Seminarios", "description": "Actualización en temáticas clínicas"},
    {"icon": "mic", "title": "Conferencias / Charlas", "description": "Ponencias de referentes médicos"},
    {"icon": "microscope", "title": "Jornadas Científicas", "description": "Divulgación e investigación"},
    {"icon": "layers", "title": "Cursos / Talleres", "description": "Capacitaciones prácticas"},
]

BENEFITS = [
    {"icon": "stethoscope", "title": "Formación especializada", "description": "Contenidos enfocados 100% en el área de la salud."},
    {"icon": "user-check", "title": "Docentes calificados", "description": "Facilitadores con experiencia clínica comprobada."},
    {"icon": "calendar-clock", "title": "Modalidad flexible", "description": "Presencial, virtual en vivo y semipresencial."},
    {"icon": "flask-conical", "title": "Enfoque teórico-práctico", "description": "Aprende haciendo, con práctica supervisada."},
    {"icon": "refresh-cw", "title": "Programas actualizados", "description": "Contenidos alineados a la práctica actual."},
    {"icon": "headset", "title": "Atención personalizada", "description": "Acompañamiento durante todo el proceso."},
    {"icon": "clipboard-check", "title": "Inscripción sencilla", "description": "Proceso claro, rápido y en línea."},
    {"icon": "award", "title": "Certificación", "description": "Certificado sujeto al cumplimiento de requisitos."},
]

# ----------------------------------------------------------------------------
# Programas disponibles (oferta actual)
# ----------------------------------------------------------------------------
PROGRAMS = [
    {
        "slug": "biomarcadores-modernos",
        "kicker": "Conferencia",
        "title": "Biomarcadores Modernos en la Evaluación Integral del Organismo Humano",
        "select_label": "Conferencia: Biomarcadores Modernos en la Evaluación Integral del Organismo Humano",
        "enroll_name": "Conferencia: Biomarcadores Modernos en la Evaluación Integral del Organismo Humano",
        "card_date": "Viernes 24/07/2026 · 7:00 pm",
        "image": "/static/img/avales/kenia-mendez.png",
        "image_alt": "Licda. Kenia Méndez, MA. — Bioanalista, ponente de la conferencia",
        "badge_label": "Virtual · Gratis",
        "badge_icon": "video",
        "badge_bg": "#E7F0FB",
        "badge_color": "#2560B8",
        "desc": (
            "Conferencia virtual “…Más allá de lo Tradicional” sobre cómo los biomarcadores modernos "
            "están revolucionando la medicina y el laboratorio clínico. Descubrirás qué son y cómo "
            "interpretar sus resultados para una evaluación más precisa del estado de salud del paciente. "
            "Libre de costo · Plataforma Zoom."
        ),
        "has_instructor": True,
        "instr_initials": "KM",
        "instr_name": "Licda. Kenia Méndez, MA.",
        "instr_role": "Bioanalista",
        "meta": [
            {"icon": "calendar", "text": "Viernes 24/07/2026"},
            {"icon": "clock", "text": "7:00 pm"},
            {"icon": "badge-dollar-sign", "text": "Libre de costo"},
            {"icon": "video", "text": "Virtual · Zoom"},
        ],
        "has_learn": True,
        "learn_title": "¿Qué aprenderás en esta conferencia?",
        "learn_intro": (
            "Biomarcadores modernos en la evaluación integral del organismo humano. "
            "En esta conferencia descubrirás cómo los biomarcadores modernos están revolucionando "
            "la medicina y el laboratorio clínico. Aprenderás qué son, y cómo interpretar sus "
            "resultados para hacer una evaluación más precisa del estado de salud del paciente."
        ),
        "learn": [
            "Detección temprana de enfermedades",
            "Diagnóstico y pronóstico",
            "Monitoreo y seguimiento de tratamientos",
        ],
        "wa_href": (
            "https://wa.me/18098970552?text=Hola,%20deseo%20información%20sobre%20la%20"
            "Conferencia%20de%20Biomarcadores%20Modernos"
        ),
    },
    {
        "slug": "toma-muestra-sanguinea",
        "kicker": "Curso avanzado",
        "title": "Toma de Muestra Sanguínea y Canalización",
        "select_label": "Curso Avanzado en Toma de Muestra Sanguínea y Canalización",
        "enroll_name": "Curso Avanzado en Toma de Muestra Sanguínea y Canalización",
        "card_date": "7, 8 y 9 de agosto de 2026",
        "image": "https://images.unsplash.com/photo-1615461066841-6116e61058f4?w=760&h=860&fit=crop&auto=format&q=80",
        "image_alt": "Toma de muestra sanguínea y venopunción",
        "badge_label": "Semipresencial",
        "badge_icon": "map-pin",
        "badge_bg": "#EAF4F5",
        "badge_color": "#1E7A82",
        "desc": (
            "Programa teórico-práctico dirigido a participantes interesados en fortalecer "
            "sus competencias para realizar una toma de muestra sanguínea segura y aplicar "
            "correctamente las técnicas de canalización venosa periférica."
        ),
        "has_instructor": False,
        "instr_initials": "",
        "instr_name": "",
        "instr_role": "",
        "meta": [
            {"icon": "calendar", "text": "7, 8 y 9 de agosto de 2026"},
            {"icon": "layers", "text": "Semipresencial"},
            {"icon": "flask-conical", "text": "Teórico-práctico"},
            {"icon": "package", "text": "Material de apoyo y gastable"},
        ],
        "has_learn": True,
        "learn_title": "Aprenderás",
        "learn_intro": "",
        "learn": [
            "Técnicas actuales de toma de muestra sanguínea",
            "Canalización venosa periférica segura y eficaz",
            "Buenas prácticas y bioseguridad",
            "Aplicación teórica con práctica supervisada",
        ],
        "wa_href": (
            "https://wa.me/18098970552?text=Hola,%20deseo%20información%20sobre%20el%20"
            "Curso%20de%20Toma%20de%20Muestra%20Sanguínea"
        ),
    },
    {
        "slug": "fenotipo-rh-kell",
        "kicker": "Seminario",
        "title": "Determinación e importancia clínica del Fenotipo Rh y Kell",
        "select_label": "Seminario: Fenotipo Rh y Kell",
        "enroll_name": "Seminario: Determinación e importancia clínica del Fenotipo Rh y Kell",
        "card_date": "Viernes 28/08/2026 · 7:00 pm",
        "image": "https://images.unsplash.com/photo-1579154204601-01588f351e67?w=760&h=860&fit=crop&auto=format&q=80",
        "image_alt": "Laboratorio de inmunohematología y fenotipado sanguíneo",
        "badge_label": "Virtual en vivo",
        "badge_icon": "video",
        "badge_bg": "#E7F0FB",
        "badge_color": "#2560B8",
        "desc": (
            "Seminario especializado enfocado en la determinación y la importancia clínica del "
            "fenotipo Rh y Kell, abordando su relevancia en inmunohematología, hemoterapia y "
            "práctica clínica."
        ),
        "has_instructor": True,
        "instr_initials": "IS",
        "instr_name": "Licda. Isabel Santamaría",
        "instr_role": "Especialista en Hemoterapia",
        "meta": [
            {"icon": "calendar", "text": "Viernes 28/08/2026"},
            {"icon": "clock", "text": "7:00 pm"},
            {"icon": "video", "text": "Virtual en vivo"},
            {"icon": "building-2", "text": "Patrocina: UTESUR"},
        ],
        "has_learn": False,
        "learn_title": "",
        "learn_intro": "",
        "learn": [],
        "wa_href": (
            "https://wa.me/18098970552?text=Hola,%20deseo%20información%20sobre%20el%20"
            "Seminario%20de%20Fenotipo%20Rh%20y%20Kell"
        ),
    },
]

PROGRAMS_BY_SLUG = {p["slug"]: p for p in PROGRAMS}

# ----------------------------------------------------------------------------
# Preguntas frecuentes
# ----------------------------------------------------------------------------
FAQS = [
    {
        "question": "¿A quiénes están dirigidos los programas?",
        "answer": (
            "Están dirigidos a profesionales y estudiantes del área de la salud interesados en "
            "fortalecer sus conocimientos y competencias mediante formación teórica y práctica."
        ),
    },
    {
        "question": "¿El curso de toma de muestra incluye práctica?",
        "answer": (
            "Sí. Es un programa teórico-práctico que incluye práctica supervisada, además de "
            "material de apoyo y material gastable."
        ),
    },
    {
        "question": "¿Qué documentos necesito para inscribirme?",
        "answer": (
            "Cédula de identidad, recibo o comprobante de pago y documento del grado de estudio, "
            "en formato PDF, JPG o PNG (máximo 5 MB por archivo)."
        ),
    },
    {
        "question": "¿Cómo recibiré el enlace de acceso?",
        "answer": (
            "Una vez validada tu inscripción, recibirás el enlace de acceso al programa por correo "
            "electrónico y por WhatsApp."
        ),
    },
    {
        "question": "¿El seminario será en vivo?",
        "answer": (
            "Sí. El seminario de Fenotipo Rh y Kell será virtual en vivo el viernes 28/08/2026 a "
            "las 7:00 pm."
        ),
    },
    {
        "question": "¿La conferencia de biomarcadores tiene costo?",
        "answer": (
            "No. La conferencia “Biomarcadores Modernos en la Evaluación Integral del Organismo "
            "Humano” es libre de costo, virtual por Zoom, el viernes 24/07/2026 a las 7:00 pm, "
            "con la Licda. Kenia Méndez, MA. (Bioanalista)."
        ),
    },
    {
        "question": "¿Puedo recibir certificado?",
        "answer": (
            "Sí. La emisión del certificado está sujeta al cumplimiento de los requisitos "
            "establecidos para cada programa."
        ),
    },
    {
        "question": "¿Cómo puedo solicitar más información?",
        "answer": (
            "Puedes escribirnos por WhatsApp al 809-897-0552 o 829-338-0552, o a través de "
            "nuestras redes sociales."
        ),
    },
]

# ----------------------------------------------------------------------------
# Formulario de inscripción
# ----------------------------------------------------------------------------
ENROLL_FIELDS = [
    {"label": "Nombres", "name": "nombres", "type": "text", "placeholder": "Tus nombres"},
    {"label": "Apellidos", "name": "apellidos", "type": "text", "placeholder": "Tus apellidos"},
    {"label": "Correo electrónico", "name": "correo", "type": "email", "placeholder": "tucorreo@ejemplo.com"},
    {"label": "Teléfono / WhatsApp", "name": "telefono", "type": "tel", "placeholder": "809-000-0000"},
    {"label": "Institución", "name": "institucion", "type": "text", "placeholder": "Institución donde laboras/estudias"},
    {"label": "Profesión, cargo o nivel académico", "name": "profesion", "type": "text", "placeholder": "Ej. Bioanalista, estudiante…"},
    {"label": "País", "name": "pais", "type": "text", "placeholder": "República Dominicana"},
    {"label": "Provincia o ciudad", "name": "ciudad", "type": "text", "placeholder": "Santo Domingo"},
]

ENROLL_DOCS = [
    {"label": "Cédula de identidad", "name": "doc_cedula", "icon": "id-card"},
    {"label": "Documento del grado de estudio", "name": "doc_grado", "icon": "graduation-cap"},
]

CERT_OPTIONS = [
    "Sí, deseo recibir certificado",
    "No deseo recibir certificado",
    "Necesito más información sobre el certificado",
]

CONTACTS = [
    {"icon": "message-circle", "title": "WhatsApp", "value": "809-897-0552", "href": "https://wa.me/18098970552"},
    {"icon": "message-circle", "title": "WhatsApp", "value": "829-338-0552", "href": "https://wa.me/18293380552"},
    {"icon": "globe", "title": "Sitio web", "value": "biomendformacion.com", "href": "https://www.biomendformacion.com"},
    {"icon": "at-sign", "title": "Redes", "value": "@biomendformacion", "href": "https://www.instagram.com/biomendformacion"},
]

ACCESS_LINK = ""  # No exponer URL de meet en el DOM hasta validación admin


def base_context(request: Request, active: str) -> dict:
    """Contexto común a todas las páginas."""
    return {
        "request": request,
        "brand": BRAND,
        "active_page": active,
        "year": datetime.now().year,
        "asset_version": ASSET_VERSION,
        "graduates": GRADUATES,
        "site_images": SITE_IMAGES,
        "csrf_token": ensure_csrf_token(request),
        "nav_links": [
            ("inicio", "Inicio", "/"),
            ("nosotros", "Nosotros", "/nosotros"),
            ("programas", "Programas", "/programas"),
            ("faq", "Preguntas frecuentes", "/faq"),
            ("contacto", "Contacto", "/contacto"),
        ],
    }


# ----------------------------------------------------------------------------
# Rutas de páginas
# ----------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Healthcheck para Railway / load balancers."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    ctx = base_context(request, "inicio")
    ctx.update({
        "programs": PROGRAMS,
        "hero_stats": HERO_STATS,
        "faqs_home": FAQS[:4],
        "benefits": BENEFITS,
    })
    return templates.TemplateResponse(request, "index.html", ctx)


@app.get("/nosotros", response_class=HTMLResponse)
def nosotros(request: Request):
    ctx = base_context(request, "nosotros")
    ctx.update({
        "modalities": MODALITIES,
        "benefits": BENEFITS,
        "hero_stats": HERO_STATS,
    })
    return templates.TemplateResponse(request, "nosotros.html", ctx)


@app.get("/programas", response_class=HTMLResponse)
def programas(request: Request):
    ctx = base_context(request, "programas")
    ctx.update({"programs": PROGRAMS})
    return templates.TemplateResponse(request, "programas.html", ctx)


@app.get("/inscripcion", response_class=HTMLResponse)
def inscripcion(request: Request, programa: str = "", ok: int = 0, err: str = ""):
    ctx = base_context(request, "inscripcion")
    # Sanitizar query programa (solo whitelist)
    allowed_names = {p["enroll_name"] for p in PROGRAMS}
    if programa and programa not in allowed_names:
        programa = ""
    ctx.update({
        "programs": PROGRAMS,
        "fields": ENROLL_FIELDS,
        "docs": ENROLL_DOCS,
        "cert_options": CERT_OPTIONS,
        "access_link": "",  # nunca filtrar URL real al cliente
        "programa": programa,
        "submitted": ok == 1,
        "form_error": err,
    })
    return templates.TemplateResponse(request, "inscripcion.html", ctx)


@app.post("/inscripcion")
async def inscripcion_submit(
    request: Request,
    csrf_token: str = Form(...),
    nombres: str = Form(...),
    apellidos: str = Form(...),
    correo: str = Form(...),
    telefono: str = Form(...),
    institucion: str = Form(...),
    profesion: str = Form(...),
    pais: str = Form(...),
    ciudad: str = Form(...),
    idioma: str = Form(...),
    programa: str = Form(...),
    certificado: str = Form(...),
    consentimiento_datos: str = Form(...),
    consentimiento_veracidad: str = Form(...),
    doc_cedula: UploadFile = File(...),
    doc_grado: UploadFile = File(...),
):
    ip = client_ip(request)
    if not rate_limit_ok(f"inscripcion:{ip}", limit=8, window_seconds=600):
        return RedirectResponse(url="/inscripcion?err=rate", status_code=303)

    if not validate_csrf(request, csrf_token) or not validate_origin(request):
        return RedirectResponse(url="/inscripcion?err=csrf", status_code=303)

    # Fail-closed en producción sin BDD
    engine = get_engine()
    if is_production() and engine is None:
        logger.error("DATABASE_URL ausente en producción — inscripción rechazada")
        return RedirectResponse(url="/inscripcion?err=config", status_code=303)

    # Validación de longitudes y whitelist
    try:
        nombres = sanitize_text(nombres, FIELD_LIMITS["nombres"])
        apellidos = sanitize_text(apellidos, FIELD_LIMITS["apellidos"])
        correo = sanitize_text(correo, FIELD_LIMITS["correo"]).lower()
        telefono = sanitize_text(telefono, FIELD_LIMITS["telefono"])
        institucion = sanitize_text(institucion, FIELD_LIMITS["institucion"])
        profesion = sanitize_text(profesion, FIELD_LIMITS["profesion"])
        pais = sanitize_text(pais, FIELD_LIMITS["pais"])
        ciudad = sanitize_text(ciudad, FIELD_LIMITS["ciudad"])
        idioma = sanitize_text(idioma, FIELD_LIMITS["idioma"])
        programa = sanitize_text(programa, FIELD_LIMITS["programa"])
        certificado = sanitize_text(certificado, FIELD_LIMITS["certificado"])
    except Exception:
        return RedirectResponse(url="/inscripcion?err=validacion", status_code=303)

    allowed_programs = {p["enroll_name"] for p in PROGRAMS}
    if programa not in allowed_programs:
        return RedirectResponse(url="/inscripcion?err=programa", status_code=303)
    if certificado not in CERT_OPTIONS:
        return RedirectResponse(url="/inscripcion?err=validacion", status_code=303)
    if idioma not in {"Español", "Inglés"}:
        return RedirectResponse(url="/inscripcion?err=validacion", status_code=303)
    if "@" not in correo or "." not in correo.split("@")[-1]:
        return RedirectResponse(url="/inscripcion?err=validacion", status_code=303)

    saved_meta: list[tuple[str, str, str, bytes, str, int]] = []
    # (codigo_tipo, stored_name, original_name, content, mime, size)
    written_paths: list[Path] = []

    try:
        for codigo, upload in (("CEDULA", doc_cedula), ("GRADO", doc_grado)):
            original = Path(upload.filename or f"{codigo}.bin").name
            content = await read_upload_limited(upload, MAX_UPLOAD_BYTES)
            ext, mime = validate_upload_content(original, content)
            stored = opaque_stored_name(ext)
            destination = PRIVATE_UPLOAD_DIR / stored
            # Guardrail path traversal
            destination.resolve().relative_to(PRIVATE_UPLOAD_DIR.resolve())
            destination.write_bytes(content)
            written_paths.append(destination)
            saved_meta.append((codigo, stored, original[:260], content, mime, len(content)))
    except ValueError:
        for p in written_paths:
            p.unlink(missing_ok=True)
        return RedirectResponse(url="/inscripcion?err=archivo", status_code=303)
    except Exception:
        for p in written_paths:
            p.unlink(missing_ok=True)
        logger.exception("Error al procesar uploads")
        return RedirectResponse(url="/inscripcion?err=archivo", status_code=303)

    def clean(value: str) -> str:
        return value.replace("\t", " ").replace("\n", " ").strip()

    slug = resolver_slug_programa(programa, PROGRAMS)
    user_agent = (request.headers.get("user-agent") or "")[:500]

    id_inscripcion = None
    try:
        if engine is not None:
            docs = [
                DocumentoPayload(
                    codigo_tipo=codigo,
                    nombre_original=original,
                    nombre_almacenado=stored,
                    ruta_almacenamiento=f"storage/private/{stored}",
                    tipo_mime=mime,
                    tamano_bytes=size,
                    contenido=content,
                )
                for codigo, stored, original, content, mime, size in saved_meta
            ]
            id_inscripcion = guardar_inscripcion(
                engine,
                InscripcionPayload(
                    nombres=nombres,
                    apellidos=apellidos,
                    correo=correo,
                    telefono=telefono,
                    institucion=institucion,
                    profesion=profesion,
                    pais=pais,
                    ciudad=ciudad,
                    idioma=idioma,
                    nombre_programa=programa,
                    slug_programa=slug,
                    certificado=certificado,
                    documentos=docs,
                    ip_origen=ip if ip != "unknown" else None,
                    user_agent=user_agent or None,
                ),
            )
        else:
            # Solo desarrollo: TSV (nunca en producción — ya bloqueado arriba)
            row = "\t".join([
                datetime.now().isoformat(timespec="seconds"),
                clean(nombres), clean(apellidos), clean(correo), clean(telefono),
                clean(institucion), clean(profesion), clean(pais), clean(ciudad),
                clean(idioma), clean(programa), clean(certificado),
                " | ".join(m[1] for m in saved_meta),
            ]) + "\n"
            with INSCRIPTIONS_FILE.open("a", encoding="utf-8") as fh:
                fh.write(row)
    except Exception:
        for p in written_paths:
            p.unlink(missing_ok=True)
        logger.exception("Error al persistir inscripción")
        return RedirectResponse(url="/inscripcion?err=guardar", status_code=303)

    # Correos: estudiante + clienta (no bloquea la inscripción si SMTP falla)
    try:
        attachments = [
            (original, content, mime)
            for _codigo, _stored, original, content, mime, _size in saved_meta
        ]
        notify_inscripcion(
            estudiante_nombre=f"{nombres} {apellidos}".strip(),
            estudiante_correo=correo,
            telefono=telefono,
            institucion=institucion,
            profesion=profesion,
            pais=pais,
            ciudad=ciudad,
            idioma=idioma,
            programa=programa,
            certificado=certificado,
            id_inscripcion=id_inscripcion,
            attachments=attachments,
        )
    except Exception:
        logger.exception("Error enviando correos de inscripción")

    return RedirectResponse(url="/inscripcion?ok=1", status_code=303)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return PlainTextResponse("No encontrado", status_code=404)
    return PlainTextResponse("Error", status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path == "/inscripcion" and request.method == "POST":
        return RedirectResponse(url="/inscripcion?err=validacion", status_code=303)
    return PlainTextResponse("Solicitud inválida", status_code=422)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Error no controlado en %s", request.url.path)
    return PlainTextResponse("Error interno", status_code=500)


@app.get("/faq", response_class=HTMLResponse)
def faq(request: Request):
    ctx = base_context(request, "faq")
    ctx.update({"faqs": FAQS})
    return templates.TemplateResponse(request, "faq.html", ctx)


@app.get("/contacto", response_class=HTMLResponse)
def contacto(request: Request):
    ctx = base_context(request, "contacto")
    ctx.update({"contacts": CONTACTS})
    return templates.TemplateResponse(request, "contacto.html", ctx)


# ----------------------------------------------------------------------------
# Compatibilidad con rutas antiguas
# ----------------------------------------------------------------------------
@app.get("/cursos", response_class=HTMLResponse)
def cursos_redir():
    return RedirectResponse(url="/programas", status_code=303)


@app.get("/cursos/{slug}", response_class=HTMLResponse)
def curso_detalle_redir(slug: str):
    return RedirectResponse(url="/programas", status_code=303)


@app.get("/programas/{slug}", response_class=HTMLResponse)
def programa_detalle_redir(slug: str):
    program = PROGRAMS_BY_SLUG.get(slug)
    if program is None:
        return RedirectResponse(url="/programas", status_code=303)
    from urllib.parse import quote
    return RedirectResponse(url=f"/inscripcion?programa={quote(program['enroll_name'])}", status_code=303)
