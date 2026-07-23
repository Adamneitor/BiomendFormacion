# Base de datos BIOMEND — Inscripciones (PostgreSQL)

Modelo dimensional en español:

| Prefijo | Tipo | Ejemplos |
|---|---|---|
| `D_` | Dimensión (catálogo) | `D_Estado_Inscripcion`, `D_Tipo_Documento` |
| `F_` | Hecho (transacción) | `F_Inscripcion`, `F_Documento_Inscripcion` |

- **Base:** `biomend_web`
- **Schema:** `biomend`

## 1. Crear la base

```bash
psql -U postgres -c "CREATE DATABASE biomend_web OWNER postgres ENCODING 'UTF8';"
```

## 2. Aplicar migración

Desde la carpeta `BiomendWeb`:

```bash
psql -U postgres -d biomend_web -f db/migrations/001_biomend_inscripciones.sql
```

Verifica:

```sql
SET search_path TO biomend;
SELECT * FROM "D_Estado_Inscripcion";
SELECT * FROM "D_Tipo_Documento";
SELECT * FROM "D_Preferencia_Certificado";
SELECT * FROM "D_Idioma";
```

## 3. Variables de entorno

Copia `.env.example` a `.env`:

```env
DATABASE_URL=postgresql+psycopg://usuario:clave@localhost:5432/biomend_web
```

- Con `DATABASE_URL` definida → las inscripciones van a `F_Inscripcion` + `F_Documento_Inscripcion`.
- Sin `DATABASE_URL` → fallback a `app/inscripciones.tsv` (solo desarrollo).

## 4. Dependencias Python

```bash
pip install -r requirements.txt
```

## Seguridad de archivos

Los documentos de inscripción **no** se guardan en `/static`.
Ruta privada: `storage/private/` (fuera del montaje de StaticFiles).

En producción (`APP_ENV=production`) es obligatorio:
- `DATABASE_URL`
- `SECRET_KEY`
- `ALLOWED_HOSTS` (dominios reales)

Controles activos en la app:
- Rate limit en `POST /inscripcion`
- Token CSRF + validación Origin/Referer
- Validación magic bytes (PDF/JPEG/PNG)
- Nombres de archivo opacos (UUID)
- Cabeceras: CSP, X-Frame-Options, nosniff, Referrer-Policy, HSTS (prod)
- Docs OpenAPI deshabilitados en producción


## Tablas

### Dimensiones
- `biomend.D_Estado_Inscripcion` — ciclo de vida (`RECIBIDA`, `EN_REVISION`, …)
- `biomend.D_Tipo_Documento` — `CEDULA`, `GRADO`
- `biomend.D_Preferencia_Certificado` — `SI`, `NO`, `MAS_INFO`
- `biomend.D_Idioma` — `ES`, `EN`

### Hechos
- `biomend.F_Inscripcion` — 1 fila por solicitud
- `biomend.F_Documento_Inscripcion` — 1 fila por archivo (ruta opaca en `storage/private/`, fuera de StaticFiles)

## Consulta de control

```sql
SELECT
    i."Id_Inscripcion",
    i."Fecha_Envio",
    i."Nombres",
    i."Apellidos",
    i."Correo",
    i."Nombre_Programa",
    e."Codigo_Estado",
    COUNT(d."Id_Documento_Inscripcion") AS docs
FROM biomend."F_Inscripcion" i
JOIN biomend."D_Estado_Inscripcion" e
  ON e."Id_Estado_Inscripcion" = i."Id_Estado_Inscripcion"
LEFT JOIN biomend."F_Documento_Inscripcion" d
  ON d."Id_Inscripcion" = i."Id_Inscripcion"
GROUP BY 1, 2, 3, 4, 5, 6, 7
ORDER BY i."Fecha_Envio" DESC;
```
