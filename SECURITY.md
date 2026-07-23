# Seguridad — checklist pre-despliegue BIOMEND

## Controles implementados

| Control | Estado |
|---|---|
| Uploads fuera de `/static` (`storage/private/`) | OK |
| Nombres opacos (UUID) | OK |
| Magic bytes PDF/JPEG/PNG | OK |
| Lectura por chunks + tope 5 MB | OK |
| Rate limit POST /inscripcion | OK |
| CSRF + Origin/Referer | OK |
| Cabeceras CSP / XFO / nosniff / HSTS | OK |
| TrustedHost (prod) | OK |
| Fail-closed sin DATABASE_URL en prod | OK |
| OpenAPI/docs off en prod | OK |
| Lucide self-hosted (sin CDN @latest) | OK |
| Dependencies pineadas | OK |
| `.gitignore` PII / .env / storage | OK |
| Sin URL meet en el DOM | OK |
| Whitelist programa / longitudes | OK |
| Handlers de error sin stack al cliente | OK |

## Antes de subir a GitHub

1. Confirmar que **no** hay `.env` con secretos.
2. Confirmar que `storage/private/` está vacío (salvo `.gitkeep`).
3. Confirmar que no hay `*.tsv` con datos reales.
4. En producción definir: `APP_ENV=production`, `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`.

## Pendiente operativo (no bloquea el push)

- Panel admin autenticado para descargar documentos (hoy: solo filesystem privado en servidor).
- Object storage (S3) + URLs firmadas cuando escale.
- WAF / rate limit en reverse proxy (nginx/Cloudflare) además del in-app.
