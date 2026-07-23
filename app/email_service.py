"""
Envío de correos de inscripción (estudiante + notificación a clienta).
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

logger = logging.getLogger("biomend.email")


def _smtp_configured() -> bool:
    return bool((os.getenv("SMTP_HOST") or "").strip() and (os.getenv("SMTP_FROM") or "").strip())


def get_notify_email() -> str:
    """Destinatario de notificaciones de inscripción (clienta / admin)."""
    configured = (os.getenv("NOTIFY_EMAIL") or os.getenv("CLIENT_NOTIFY_EMAIL") or "").strip()
    return configured or "adamsanchezp@gmail.com"


def send_email(
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    attachments: Optional[list[tuple[str, bytes, str]]] = None,
) -> bool:
    """
    attachments: lista de (filename, content, mime)
    """
    if not _smtp_configured():
        logger.warning("SMTP no configurado — correo no enviado a %s", to)
        return False

    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT") or "587")
    user = (os.getenv("SMTP_USER") or "").strip()
    password = (os.getenv("SMTP_PASSWORD") or "").strip()
    from_addr = (os.getenv("SMTP_FROM") or "").strip()
    use_tls = (os.getenv("SMTP_TLS") or "true").strip().lower() in {"1", "true", "yes"}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    for filename, content, mime in attachments or []:
        maintype, _, subtype = (mime or "application/octet-stream").partition("/")
        if not subtype:
            maintype, subtype = "application", "octet-stream"
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if use_tls:
                smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
        logger.info("Correo enviado a %s — %s", to, subject)
        return True
    except Exception:
        logger.exception("Error enviando correo a %s", to)
        return False


def notify_inscripcion(
    *,
    estudiante_nombre: str,
    estudiante_correo: str,
    telefono: str,
    institucion: str,
    profesion: str,
    pais: str,
    ciudad: str,
    idioma: str,
    programa: str,
    certificado: str,
    id_inscripcion: Optional[int],
    attachments: Optional[list[tuple[str, bytes, str]]] = None,
) -> None:
    """Envía confirmación al estudiante y detalle completo a la clienta."""
    notify_to = get_notify_email()

    student_subject = f"Inscripción recibida — {programa}"
    student_body = (
        f"Hola {estudiante_nombre},\n\n"
        f"Recibimos tu inscripción a:\n"
        f"  {programa}\n\n"
        f"Nuestro equipo revisará tu solicitud y te contactará por correo o WhatsApp "
        f"con los siguientes pasos.\n\n"
        f"Si tienes dudas, escríbenos al 809-897-0552 o 829-338-0552.\n\n"
        f"Saludos,\n"
        f"BIOMEND Formación Continua\n"
        f"https://biomendformacion.com\n"
    )
    student_html = f"""
    <p>Hola <strong>{estudiante_nombre}</strong>,</p>
    <p>Recibimos tu inscripción a:</p>
    <p><strong>{programa}</strong></p>
    <p>Nuestro equipo revisará tu solicitud y te contactará por correo o WhatsApp con los siguientes pasos.</p>
    <p>WhatsApp: 809-897-0552 / 829-338-0552</p>
    <p>Saludos,<br/>BIOMEND Formación Continua</p>
    """
    send_email(
        to=estudiante_correo,
        subject=student_subject,
        body_text=student_body,
        body_html=student_html,
    )

    if not notify_to:
        logger.warning("NOTIFY_EMAIL no definido — no se notifica a la clienta")
        return

    ref = f"#{id_inscripcion}" if id_inscripcion else "(sin ID)"
    admin_subject = f"Nueva inscripción {ref} — {programa}"
    admin_body = (
        f"Nueva inscripción en biomendformacion.com\n\n"
        f"ID: {ref}\n"
        f"Programa: {programa}\n"
        f"Nombre: {estudiante_nombre}\n"
        f"Correo: {estudiante_correo}\n"
        f"Teléfono: {telefono}\n"
        f"Institución: {institucion}\n"
        f"Profesión: {profesion}\n"
        f"País / Ciudad: {pais} / {ciudad}\n"
        f"Idioma: {idioma}\n"
        f"Certificado: {certificado}\n\n"
        f"Documentos adjuntos (si SMTP lo permite).\n"
        f"También puedes verlas en /admin\n"
    )
    admin_html = f"""
    <h2>Nueva inscripción {ref}</h2>
    <table cellpadding="6">
      <tr><td><strong>Programa</strong></td><td>{programa}</td></tr>
      <tr><td><strong>Nombre</strong></td><td>{estudiante_nombre}</td></tr>
      <tr><td><strong>Correo</strong></td><td>{estudiante_correo}</td></tr>
      <tr><td><strong>Teléfono</strong></td><td>{telefono}</td></tr>
      <tr><td><strong>Institución</strong></td><td>{institucion}</td></tr>
      <tr><td><strong>Profesión</strong></td><td>{profesion}</td></tr>
      <tr><td><strong>País / Ciudad</strong></td><td>{pais} / {ciudad}</td></tr>
      <tr><td><strong>Idioma</strong></td><td>{idioma}</td></tr>
      <tr><td><strong>Certificado</strong></td><td>{certificado}</td></tr>
    </table>
    <p>Consulta el panel: <a href="https://biomendformacion.com/admin">/admin</a></p>
    """
    send_email(
        to=notify_to,
        subject=admin_subject,
        body_text=admin_body,
        body_html=admin_html,
        attachments=attachments,
    )


def send_acceso_meet(
    *,
    estudiante_nombre: str,
    estudiante_correo: str,
    programa: str,
    meet_link: str,
) -> bool:
    """Envía al estudiante el enlace de acceso (Meet/Zoom)."""
    subject = f"Enlace de acceso — {programa}"
    body = (
        f"Hola {estudiante_nombre},\n\n"
        f"Tu inscripción a «{programa}» fue validada.\n\n"
        f"Enlace de acceso:\n{meet_link}\n\n"
        f"Te esperamos.\n\n"
        f"BIOMEND Formación Continua\n"
        f"WhatsApp: 809-897-0552 / 829-338-0552\n"
    )
    html = f"""
    <p>Hola <strong>{estudiante_nombre}</strong>,</p>
    <p>Tu inscripción a <strong>{programa}</strong> fue validada.</p>
    <p><a href="{meet_link}" style="display:inline-block;padding:12px 18px;background:#2C9BA5;color:#fff;text-decoration:none;border-radius:8px;font-weight:700">Entrar a la sesión</a></p>
    <p style="word-break:break-all;color:#456">{meet_link}</p>
    <p>BIOMEND Formación Continua<br/>WhatsApp: 809-897-0552 / 829-338-0552</p>
    """
    return send_email(to=estudiante_correo, subject=subject, body_text=body, body_html=html)
