-- =============================================================================
-- BIOMEND Formación Continua — Migración 001
-- Schema dimensional: dimensiones (D_) + hechos (F_)
-- Motor: PostgreSQL
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS biomend;

-- ---------------------------------------------------------------------------
-- Dimensiones
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS biomend."D_Estado_Inscripcion" (
    "Id_Estado_Inscripcion"   SMALLSERIAL PRIMARY KEY,
    "Codigo_Estado"           VARCHAR(32)  NOT NULL,
    "Nombre_Estado"           VARCHAR(120) NOT NULL,
    "Es_Activo"               BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT "UQ_D_Estado_Inscripcion_Codigo" UNIQUE ("Codigo_Estado")
);

CREATE TABLE IF NOT EXISTS biomend."D_Tipo_Documento" (
    "Id_Tipo_Documento"       SMALLSERIAL PRIMARY KEY,
    "Codigo_Tipo_Documento"   VARCHAR(32)  NOT NULL,
    "Nombre_Tipo_Documento"   VARCHAR(120) NOT NULL,
    "Es_Activo"               BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT "UQ_D_Tipo_Documento_Codigo" UNIQUE ("Codigo_Tipo_Documento")
);

CREATE TABLE IF NOT EXISTS biomend."D_Preferencia_Certificado" (
    "Id_Preferencia_Certificado" SMALLSERIAL PRIMARY KEY,
    "Codigo_Preferencia"         VARCHAR(32)  NOT NULL,
    "Nombre_Preferencia"         VARCHAR(200) NOT NULL,
    "Es_Activo"                  BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT "UQ_D_Preferencia_Certificado_Codigo" UNIQUE ("Codigo_Preferencia")
);

CREATE TABLE IF NOT EXISTS biomend."D_Idioma" (
    "Id_Idioma"               SMALLSERIAL PRIMARY KEY,
    "Codigo_Idioma"           VARCHAR(8)   NOT NULL,
    "Nombre_Idioma"           VARCHAR(80)  NOT NULL,
    "Es_Activo"               BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT "UQ_D_Idioma_Codigo" UNIQUE ("Codigo_Idioma")
);

-- ---------------------------------------------------------------------------
-- Hechos
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS biomend."F_Inscripcion" (
    "Id_Inscripcion"              BIGSERIAL PRIMARY KEY,
    "Uuid_Inscripcion"            UUID         NOT NULL DEFAULT gen_random_uuid(),
    "Id_Estado_Inscripcion"       SMALLINT     NOT NULL,
    "Id_Preferencia_Certificado"  SMALLINT     NOT NULL,
    "Id_Idioma"                   SMALLINT     NOT NULL,
    "Nombres"                     VARCHAR(120) NOT NULL,
    "Apellidos"                   VARCHAR(120) NOT NULL,
    "Correo"                      VARCHAR(254) NOT NULL,
    "Telefono"                    VARCHAR(32)  NOT NULL,
    "Institucion"                 VARCHAR(200) NOT NULL,
    "Profesion"                   VARCHAR(200) NOT NULL,
    "Pais"                        VARCHAR(100) NOT NULL,
    "Ciudad"                      VARCHAR(120) NOT NULL,
    "Slug_Programa"               VARCHAR(120) NULL,
    "Nombre_Programa"             VARCHAR(300) NOT NULL,
    "Fecha_Envio"                 TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    "Ip_Origen"                   INET         NULL,
    "User_Agent"                  TEXT         NULL,
    "Fecha_Creacion"              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    "Fecha_Actualizacion"         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT "UQ_F_Inscripcion_Uuid" UNIQUE ("Uuid_Inscripcion"),
    CONSTRAINT "FK_F_Inscripcion_D_Estado"
        FOREIGN KEY ("Id_Estado_Inscripcion")
        REFERENCES biomend."D_Estado_Inscripcion" ("Id_Estado_Inscripcion"),
    CONSTRAINT "FK_F_Inscripcion_D_Preferencia"
        FOREIGN KEY ("Id_Preferencia_Certificado")
        REFERENCES biomend."D_Preferencia_Certificado" ("Id_Preferencia_Certificado"),
    CONSTRAINT "FK_F_Inscripcion_D_Idioma"
        FOREIGN KEY ("Id_Idioma")
        REFERENCES biomend."D_Idioma" ("Id_Idioma")
);

CREATE TABLE IF NOT EXISTS biomend."F_Documento_Inscripcion" (
    "Id_Documento_Inscripcion" BIGSERIAL PRIMARY KEY,
    "Id_Inscripcion"           BIGINT       NOT NULL,
    "Id_Tipo_Documento"        SMALLINT     NOT NULL,
    "Nombre_Original"          VARCHAR(260) NOT NULL,
    "Nombre_Almacenado"        VARCHAR(260) NOT NULL,
    "Ruta_Almacenamiento"      VARCHAR(500) NOT NULL,
    "Tipo_Mime"                VARCHAR(120) NULL,
    "Tamano_Bytes"             INTEGER      NOT NULL CHECK ("Tamano_Bytes" >= 0),
    "Hash_SHA256"              CHAR(64)     NULL,
    "Fecha_Carga"              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT "FK_F_Documento_F_Inscripcion"
        FOREIGN KEY ("Id_Inscripcion")
        REFERENCES biomend."F_Inscripcion" ("Id_Inscripcion")
        ON DELETE CASCADE,
    CONSTRAINT "FK_F_Documento_D_Tipo"
        FOREIGN KEY ("Id_Tipo_Documento")
        REFERENCES biomend."D_Tipo_Documento" ("Id_Tipo_Documento")
);

-- ---------------------------------------------------------------------------
-- Índices
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS "IX_F_Inscripcion_Fecha_Envio"
    ON biomend."F_Inscripcion" ("Fecha_Envio" DESC);

CREATE INDEX IF NOT EXISTS "IX_F_Inscripcion_Correo"
    ON biomend."F_Inscripcion" ("Correo");

CREATE INDEX IF NOT EXISTS "IX_F_Inscripcion_Id_Estado"
    ON biomend."F_Inscripcion" ("Id_Estado_Inscripcion");

CREATE INDEX IF NOT EXISTS "IX_F_Inscripcion_Slug_Programa"
    ON biomend."F_Inscripcion" ("Slug_Programa");

CREATE INDEX IF NOT EXISTS "IX_F_Documento_Id_Inscripcion"
    ON biomend."F_Documento_Inscripcion" ("Id_Inscripcion");

-- ---------------------------------------------------------------------------
-- Seeds — dimensiones
-- ---------------------------------------------------------------------------

INSERT INTO biomend."D_Estado_Inscripcion" ("Codigo_Estado", "Nombre_Estado")
VALUES
    ('RECIBIDA', 'Recibida'),
    ('EN_REVISION', 'En revisión'),
    ('APROBADA', 'Aprobada'),
    ('RECHAZADA', 'Rechazada'),
    ('ACCESO_ENVIADO', 'Acceso enviado'),
    ('CANCELADA', 'Cancelada')
ON CONFLICT ("Codigo_Estado") DO NOTHING;

INSERT INTO biomend."D_Tipo_Documento" ("Codigo_Tipo_Documento", "Nombre_Tipo_Documento")
VALUES
    ('CEDULA', 'Cédula de identidad'),
    ('GRADO', 'Documento del grado de estudio')
ON CONFLICT ("Codigo_Tipo_Documento") DO NOTHING;

INSERT INTO biomend."D_Preferencia_Certificado" ("Codigo_Preferencia", "Nombre_Preferencia")
VALUES
    ('SI', 'Sí, deseo recibir certificado'),
    ('NO', 'No deseo recibir certificado'),
    ('MAS_INFO', 'Necesito más información sobre el certificado')
ON CONFLICT ("Codigo_Preferencia") DO NOTHING;

INSERT INTO biomend."D_Idioma" ("Codigo_Idioma", "Nombre_Idioma")
VALUES
    ('ES', 'Español'),
    ('EN', 'Inglés')
ON CONFLICT ("Codigo_Idioma") DO NOTHING;
