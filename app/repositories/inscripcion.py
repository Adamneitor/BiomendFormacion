"""
Repositorio de inscripciones — hechos F_Inscripcion / F_Documento_Inscripcion.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


# Mapeo texto del formulario → Codigo_Preferencia
CERT_MAP = {
    "Sí, deseo recibir certificado": "SI",
    "No deseo recibir certificado": "NO",
    "Necesito más información sobre el certificado": "MAS_INFO",
}

IDIOMA_MAP = {
    "Español": "ES",
    "Inglés": "EN",
    "ES": "ES",
    "EN": "EN",
}


@dataclass
class DocumentoPayload:
    codigo_tipo: str  # CEDULA | GRADO
    nombre_original: str
    nombre_almacenado: str
    ruta_almacenamiento: str
    tipo_mime: Optional[str]
    tamano_bytes: int
    contenido: bytes


@dataclass
class InscripcionPayload:
    nombres: str
    apellidos: str
    correo: str
    telefono: str
    institucion: str
    profesion: str
    pais: str
    ciudad: str
    idioma: str
    nombre_programa: str
    slug_programa: Optional[str]
    certificado: str
    documentos: list[DocumentoPayload]
    ip_origen: Optional[str] = None
    user_agent: Optional[str] = None


def normalizar_correo(correo: str) -> str:
    return correo.strip().lower()


def normalizar_telefono(telefono: str) -> str:
    """Solo dígitos; si viene con 1 de país (+1), lo quita dejando 10 dígitos RD."""
    digits = re.sub(r"\D+", "", telefono or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def formatear_telefono(telefono: str) -> str:
    digits = normalizar_telefono(telefono)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return telefono or "—"


def formatear_fecha(value) -> str:
    if value is None:
        return "—"
    try:
        from zoneinfo import ZoneInfo
        dt = value
        if getattr(dt, "tzinfo", None) is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(ZoneInfo("America/Santo_Domingo"))
        return local.strftime("%d/%m/%Y · %H:%M")
    except Exception:
        return str(value)[:19]


def sha256_hex(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def _lookup_id(conn: Connection, sql: str, codigo: str) -> int:
    row = conn.execute(text(sql), {"codigo": codigo}).fetchone()
    if row is None:
        raise ValueError(f"No se encontró catálogo para código: {codigo}")
    return int(row[0])


def guardar_inscripcion(engine: Engine, payload: InscripcionPayload) -> int:
    """
    Inserta 1 F_Inscripcion + N F_Documento_Inscripcion.
    Retorna Id_Inscripcion.
    """
    correo = normalizar_correo(payload.correo)
    telefono = normalizar_telefono(payload.telefono)
    codigo_cert = CERT_MAP.get(payload.certificado.strip())
    if not codigo_cert:
        # Intento por coincidencia parcial
        lower = payload.certificado.lower()
        if "no deseo" in lower:
            codigo_cert = "NO"
        elif "más información" in lower or "mas informacion" in lower:
            codigo_cert = "MAS_INFO"
        else:
            codigo_cert = "SI"

    codigo_idioma = IDIOMA_MAP.get(payload.idioma.strip(), "ES")
    now = datetime.now(timezone.utc)
    enrollment_uuid = uuid.uuid4()

    with engine.begin() as conn:
        id_estado = _lookup_id(
            conn,
            'SELECT "Id_Estado_Inscripcion" FROM biomend."D_Estado_Inscripcion" WHERE "Codigo_Estado" = :codigo',
            "RECIBIDA",
        )
        id_pref = _lookup_id(
            conn,
            'SELECT "Id_Preferencia_Certificado" FROM biomend."D_Preferencia_Certificado" WHERE "Codigo_Preferencia" = :codigo',
            codigo_cert,
        )
        id_idioma = _lookup_id(
            conn,
            'SELECT "Id_Idioma" FROM biomend."D_Idioma" WHERE "Codigo_Idioma" = :codigo',
            codigo_idioma,
        )

        result = conn.execute(
            text(
                """
                INSERT INTO biomend."F_Inscripcion" (
                    "Uuid_Inscripcion",
                    "Id_Estado_Inscripcion",
                    "Id_Preferencia_Certificado",
                    "Id_Idioma",
                    "Nombres", "Apellidos", "Correo", "Telefono",
                    "Institucion", "Profesion", "Pais", "Ciudad",
                    "Slug_Programa", "Nombre_Programa",
                    "Fecha_Envio", "Ip_Origen", "User_Agent",
                    "Fecha_Creacion", "Fecha_Actualizacion"
                ) VALUES (
                    :uuid_inscripcion,
                    :id_estado, :id_pref, :id_idioma,
                    :nombres, :apellidos, :correo, :telefono,
                    :institucion, :profesion, :pais, :ciudad,
                    :slug_programa, :nombre_programa,
                    :fecha_envio, :ip_origen, :user_agent,
                    :fecha_creacion, :fecha_actualizacion
                )
                RETURNING "Id_Inscripcion"
                """
            ),
            {
                "uuid_inscripcion": str(enrollment_uuid),
                "id_estado": id_estado,
                "id_pref": id_pref,
                "id_idioma": id_idioma,
                "nombres": payload.nombres.strip(),
                "apellidos": payload.apellidos.strip(),
                "correo": correo,
                "telefono": telefono,
                "institucion": payload.institucion.strip(),
                "profesion": payload.profesion.strip(),
                "pais": payload.pais.strip(),
                "ciudad": payload.ciudad.strip(),
                "slug_programa": payload.slug_programa,
                "nombre_programa": payload.nombre_programa.strip(),
                "fecha_envio": now,
                "ip_origen": payload.ip_origen,
                "user_agent": payload.user_agent,
                "fecha_creacion": now,
                "fecha_actualizacion": now,
            },
        )
        id_inscripcion = int(result.scalar_one())

        for doc in payload.documentos:
            id_tipo = _lookup_id(
                conn,
                'SELECT "Id_Tipo_Documento" FROM biomend."D_Tipo_Documento" WHERE "Codigo_Tipo_Documento" = :codigo',
                doc.codigo_tipo,
            )
            conn.execute(
                text(
                    """
                    INSERT INTO biomend."F_Documento_Inscripcion" (
                        "Id_Inscripcion",
                        "Id_Tipo_Documento",
                        "Nombre_Original",
                        "Nombre_Almacenado",
                        "Ruta_Almacenamiento",
                        "Tipo_Mime",
                        "Tamano_Bytes",
                        "Hash_SHA256",
                        "Fecha_Carga"
                    ) VALUES (
                        :id_inscripcion, :id_tipo,
                        :nombre_original, :nombre_almacenado, :ruta,
                        :mime, :tamano, :hash_sha, :fecha_carga
                    )
                    """
                ),
                {
                    "id_inscripcion": id_inscripcion,
                    "id_tipo": id_tipo,
                    "nombre_original": doc.nombre_original[:260],
                    "nombre_almacenado": doc.nombre_almacenado[:260],
                    "ruta": doc.ruta_almacenamiento[:500],
                    "mime": (doc.tipo_mime or "")[:120] or None,
                    "tamano": doc.tamano_bytes,
                    "hash_sha": sha256_hex(doc.contenido),
                    "fecha_carga": now,
                },
            )

    return id_inscripcion


def listar_inscripciones(engine: Engine, limit: int = 200) -> list[dict]:
    """Lista inscripciones recientes para el panel admin."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    i."Id_Inscripcion",
                    i."Uuid_Inscripcion",
                    i."Fecha_Envio",
                    i."Nombres",
                    i."Apellidos",
                    i."Correo",
                    i."Telefono",
                    i."Institucion",
                    i."Profesion",
                    i."Pais",
                    i."Ciudad",
                    i."Nombre_Programa",
                    i."Slug_Programa",
                    e."Nombre_Estado",
                    p."Nombre_Preferencia",
                    lang."Nombre_Idioma",
                    (
                        SELECT COUNT(*)
                        FROM biomend."F_Documento_Inscripcion" d
                        WHERE d."Id_Inscripcion" = i."Id_Inscripcion"
                    ) AS "Cant_Documentos"
                FROM biomend."F_Inscripcion" i
                JOIN biomend."D_Estado_Inscripcion" e
                    ON e."Id_Estado_Inscripcion" = i."Id_Estado_Inscripcion"
                JOIN biomend."D_Preferencia_Certificado" p
                    ON p."Id_Preferencia_Certificado" = i."Id_Preferencia_Certificado"
                JOIN biomend."D_Idioma" lang
                    ON lang."Id_Idioma" = i."Id_Idioma"
                ORDER BY i."Fecha_Envio" DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        ).mappings().all()
        return [dict(r) for r in rows]


def obtener_inscripcion(engine: Engine, id_inscripcion: int) -> Optional[dict]:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    i.*,
                    e."Nombre_Estado",
                    p."Nombre_Preferencia",
                    lang."Nombre_Idioma"
                FROM biomend."F_Inscripcion" i
                JOIN biomend."D_Estado_Inscripcion" e
                    ON e."Id_Estado_Inscripcion" = i."Id_Estado_Inscripcion"
                JOIN biomend."D_Preferencia_Certificado" p
                    ON p."Id_Preferencia_Certificado" = i."Id_Preferencia_Certificado"
                JOIN biomend."D_Idioma" lang
                    ON lang."Id_Idioma" = i."Id_Idioma"
                WHERE i."Id_Inscripcion" = :id
                """
            ),
            {"id": id_inscripcion},
        ).mappings().fetchone()
        if not row:
            return None
        docs = conn.execute(
            text(
                """
                SELECT d.*, t."Nombre_Tipo_Documento"
                FROM biomend."F_Documento_Inscripcion" d
                JOIN biomend."D_Tipo_Documento" t
                    ON t."Id_Tipo_Documento" = d."Id_Tipo_Documento"
                WHERE d."Id_Inscripcion" = :id
                ORDER BY d."Id_Documento_Inscripcion"
                """
            ),
            {"id": id_inscripcion},
        ).mappings().all()
        data = dict(row)
        data["documentos"] = [dict(d) for d in docs]
        return data


def actualizar_estado_inscripcion(engine: Engine, id_inscripcion: int, codigo_estado: str) -> bool:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                'SELECT "Id_Estado_Inscripcion" FROM biomend."D_Estado_Inscripcion" WHERE "Codigo_Estado" = :c'
            ),
            {"c": codigo_estado},
        ).fetchone()
        if row is None:
            return False
        result = conn.execute(
            text(
                """
                UPDATE biomend."F_Inscripcion"
                SET "Id_Estado_Inscripcion" = :id_estado,
                    "Fecha_Actualizacion" = NOW()
                WHERE "Id_Inscripcion" = :id
                """
            ),
            {"id_estado": int(row[0]), "id": id_inscripcion},
        )
        return result.rowcount > 0


def resumen_inscripciones(engine: Engine) -> dict:
    """Indicadores para el dashboard admin."""
    with engine.connect() as conn:
        total = conn.execute(text('SELECT COUNT(*) FROM biomend."F_Inscripcion"')).scalar() or 0
        hoy = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM biomend."F_Inscripcion"
                WHERE ("Fecha_Envio" AT TIME ZONE 'America/Santo_Domingo')::date
                    = (NOW() AT TIME ZONE 'America/Santo_Domingo')::date
                """
            )
        ).scalar() or 0
        recibidas = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM biomend."F_Inscripcion" i
                JOIN biomend."D_Estado_Inscripcion" e ON e."Id_Estado_Inscripcion" = i."Id_Estado_Inscripcion"
                WHERE e."Codigo_Estado" = 'RECIBIDA'
                """
            )
        ).scalar() or 0
        acceso = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM biomend."F_Inscripcion" i
                JOIN biomend."D_Estado_Inscripcion" e ON e."Id_Estado_Inscripcion" = i."Id_Estado_Inscripcion"
                WHERE e."Codigo_Estado" = 'ACCESO_ENVIADO'
                """
            )
        ).scalar() or 0
        por_programa = conn.execute(
            text(
                """
                SELECT "Nombre_Programa", COUNT(*) AS c
                FROM biomend."F_Inscripcion"
                GROUP BY "Nombre_Programa"
                ORDER BY c DESC
                LIMIT 5
                """
            )
        ).mappings().all()
        return {
            "total": int(total),
            "hoy": int(hoy),
            "recibidas": int(recibidas),
            "acceso_enviado": int(acceso),
            "por_programa": [dict(r) for r in por_programa],
        }


def resolver_slug_programa(nombre_programa: str, programs: list[dict]) -> Optional[str]:
    target = (nombre_programa or "").strip().lower()
    for p in programs:
        if p.get("enroll_name", "").strip().lower() == target:
            return p.get("slug")
        if p.get("select_label", "").strip().lower() == target:
            return p.get("slug")
    return None
