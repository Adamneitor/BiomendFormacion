# BIOMEND Formación Continua

Sitio web FastAPI + Jinja2 para inscripción a programas de formación continua.

## Stack

- Python 3.11+ / FastAPI / Uvicorn
- PostgreSQL (`biomend` schema — ver `db/`)
- Despliegue: Railway

## Desarrollo local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar SECRET_KEY y DATABASE_URL si usas Postgres
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Railway

1. Conectar el repo `Adamneitor/BiomendFormacion`.
2. Añadir plugin **PostgreSQL**.
3. Variables de entorno:

| Variable | Valor |
|---|---|
| `APP_ENV` | `production` |
| `SECRET_KEY` | cadena aleatoria fuerte |
| `DATABASE_URL` | (la inyecta Railway al vincular Postgres) |
| `ALLOWED_HOSTS` | tu dominio Railway y/o dominio propio, separados por coma |

4. Ejecutar la migración SQL una vez: `db/migrations/001_biomend_inscripciones.sql` contra la BD de Railway.
5. Start command (ya en `railway.toml` / `Procfile`):  
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Healthcheck: `GET /health`

## Estructura de base de datos

Al arrancar la app aplica automáticamente `db/migrations/*.sql` (tabla de control `biomend_schema_migrations`).

En Railway, tras el primer deploy con `DATABASE_URL`, recarga el servicio y en Data verás el schema `biomend` con:
- Dimensiones: `D_Estado_Inscripcion`, `D_Tipo_Documento`, `D_Preferencia_Certificado`, `D_Idioma`
- Hechos: `F_Inscripcion`, `F_Documento_Inscripcion`

Si la pestaña Data no muestra schemas, ejecuta en Query:
```sql
SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema = 'biomend';
```

## Variables Railway adicionales

| Variable | Uso |
|---|---|
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Acceso a `/admin` |
| `NOTIFY_EMAIL` | Correo de la clienta (cada inscripción) |
| `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASSWORD` `SMTP_FROM` | Envío de correos |

Panel: `https://biomendformacion.com/admin`

