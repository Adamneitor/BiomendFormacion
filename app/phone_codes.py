"""
Prefijos telefónicos internacionales (UIT-T E.164) con longitud del número nacional.
Fuente de referencia: Anexo Wikipedia de prefijos mundiales + longitudes típicas NSN.
El máximo E.164 total es 15 dígitos (código país + número nacional).
"""

from __future__ import annotations

# code: dígitos del país | label: visible | nsn_min/nsn_max: dígitos del número NACIONAL (sin el +código)
# Orden: América primero (público BIOMEND), luego resto alfabético por etiqueta.

PHONE_COUNTRY_CODES: list[dict] = [
    # --- América / Caribe (NANP +1: 10 dígitos nacionales, ej. 809-000-0000) ---
    {"code": "1", "label": "+1 · RD / USA / CA / PR / Caribe NANP", "nsn_min": 10, "nsn_max": 10, "placeholder": "809-000-0000"},
    {"code": "52", "label": "+52 · México", "nsn_min": 10, "nsn_max": 10, "placeholder": "55-0000-0000"},
    {"code": "501", "label": "+501 · Belice", "nsn_min": 7, "nsn_max": 7, "placeholder": "600-0000"},
    {"code": "502", "label": "+502 · Guatemala", "nsn_min": 8, "nsn_max": 8, "placeholder": "5000-0000"},
    {"code": "503", "label": "+503 · El Salvador", "nsn_min": 8, "nsn_max": 8, "placeholder": "7000-0000"},
    {"code": "504", "label": "+504 · Honduras", "nsn_min": 8, "nsn_max": 8, "placeholder": "9000-0000"},
    {"code": "505", "label": "+505 · Nicaragua", "nsn_min": 8, "nsn_max": 8, "placeholder": "8000-0000"},
    {"code": "506", "label": "+506 · Costa Rica", "nsn_min": 8, "nsn_max": 8, "placeholder": "8000-0000"},
    {"code": "507", "label": "+507 · Panamá", "nsn_min": 7, "nsn_max": 8, "placeholder": "6000-0000"},
    {"code": "509", "label": "+509 · Haití", "nsn_min": 8, "nsn_max": 8, "placeholder": "3000-0000"},
    {"code": "53", "label": "+53 · Cuba", "nsn_min": 8, "nsn_max": 8, "placeholder": "5000-0000"},
    {"code": "51", "label": "+51 · Perú", "nsn_min": 9, "nsn_max": 9, "placeholder": "900-000-000"},
    {"code": "54", "label": "+54 · Argentina", "nsn_min": 10, "nsn_max": 10, "placeholder": "11-0000-0000"},
    {"code": "55", "label": "+55 · Brasil", "nsn_min": 10, "nsn_max": 11, "placeholder": "11-90000-0000"},
    {"code": "56", "label": "+56 · Chile", "nsn_min": 9, "nsn_max": 9, "placeholder": "9-0000-0000"},
    {"code": "57", "label": "+57 · Colombia", "nsn_min": 10, "nsn_max": 10, "placeholder": "300-000-0000"},
    {"code": "58", "label": "+58 · Venezuela", "nsn_min": 10, "nsn_max": 10, "placeholder": "412-0000000"},
    {"code": "591", "label": "+591 · Bolivia", "nsn_min": 8, "nsn_max": 8, "placeholder": "70000000"},
    {"code": "592", "label": "+592 · Guyana", "nsn_min": 7, "nsn_max": 7, "placeholder": "6000000"},
    {"code": "593", "label": "+593 · Ecuador", "nsn_min": 9, "nsn_max": 9, "placeholder": "99-000-0000"},
    {"code": "595", "label": "+595 · Paraguay", "nsn_min": 9, "nsn_max": 9, "placeholder": "981-000000"},
    {"code": "597", "label": "+597 · Surinam", "nsn_min": 6, "nsn_max": 7, "placeholder": "7000000"},
    {"code": "598", "label": "+598 · Uruguay", "nsn_min": 8, "nsn_max": 8, "placeholder": "99-000-000"},
    # --- Europa ---
    {"code": "34", "label": "+34 · España", "nsn_min": 9, "nsn_max": 9, "placeholder": "600-000-000"},
    {"code": "33", "label": "+33 · Francia", "nsn_min": 9, "nsn_max": 9, "placeholder": "6-00-00-00-00"},
    {"code": "39", "label": "+39 · Italia", "nsn_min": 9, "nsn_max": 10, "placeholder": "300-0000000"},
    {"code": "44", "label": "+44 · Reino Unido", "nsn_min": 10, "nsn_max": 10, "placeholder": "7400-000000"},
    {"code": "49", "label": "+49 · Alemania", "nsn_min": 10, "nsn_max": 11, "placeholder": "151-00000000"},
    {"code": "351", "label": "+351 · Portugal", "nsn_min": 9, "nsn_max": 9, "placeholder": "900-000-000"},
    {"code": "31", "label": "+31 · Países Bajos", "nsn_min": 9, "nsn_max": 9, "placeholder": "6-00000000"},
    {"code": "32", "label": "+32 · Bélgica", "nsn_min": 8, "nsn_max": 9, "placeholder": "470-00-00-00"},
    {"code": "41", "label": "+41 · Suiza", "nsn_min": 9, "nsn_max": 9, "placeholder": "78-000-00-00"},
    {"code": "43", "label": "+43 · Austria", "nsn_min": 10, "nsn_max": 13, "placeholder": "664-0000000"},
    {"code": "46", "label": "+46 · Suecia", "nsn_min": 9, "nsn_max": 9, "placeholder": "70-000-00-00"},
    {"code": "47", "label": "+47 · Noruega", "nsn_min": 8, "nsn_max": 8, "placeholder": "400-00-000"},
    {"code": "45", "label": "+45 · Dinamarca", "nsn_min": 8, "nsn_max": 8, "placeholder": "20-00-00-00"},
    {"code": "48", "label": "+48 · Polonia", "nsn_min": 9, "nsn_max": 9, "placeholder": "500-000-000"},
    {"code": "7", "label": "+7 · Rusia / Kazajistán", "nsn_min": 10, "nsn_max": 10, "placeholder": "900-000-00-00"},
    # --- Asia / Oceanía / África (principales) ---
    {"code": "91", "label": "+91 · India", "nsn_min": 10, "nsn_max": 10, "placeholder": "90000-00000"},
    {"code": "86", "label": "+86 · China", "nsn_min": 11, "nsn_max": 11, "placeholder": "130-0000-0000"},
    {"code": "81", "label": "+81 · Japón", "nsn_min": 10, "nsn_max": 10, "placeholder": "90-0000-0000"},
    {"code": "82", "label": "+82 · Corea del Sur", "nsn_min": 9, "nsn_max": 10, "placeholder": "10-0000-0000"},
    {"code": "971", "label": "+971 · EAU", "nsn_min": 9, "nsn_max": 9, "placeholder": "50-000-0000"},
    {"code": "966", "label": "+966 · Arabia Saudita", "nsn_min": 9, "nsn_max": 9, "placeholder": "50-000-0000"},
    {"code": "90", "label": "+90 · Turquía", "nsn_min": 10, "nsn_max": 10, "placeholder": "500-000-0000"},
    {"code": "61", "label": "+61 · Australia", "nsn_min": 9, "nsn_max": 9, "placeholder": "400-000-000"},
    {"code": "64", "label": "+64 · Nueva Zelanda", "nsn_min": 8, "nsn_max": 10, "placeholder": "21-000-0000"},
    {"code": "27", "label": "+27 · Sudáfrica", "nsn_min": 9, "nsn_max": 9, "placeholder": "82-000-0000"},
    {"code": "234", "label": "+234 · Nigeria", "nsn_min": 8, "nsn_max": 10, "placeholder": "801-000-0000"},
    {"code": "20", "label": "+20 · Egipto", "nsn_min": 9, "nsn_max": 10, "placeholder": "100-000-0000"},
]

PHONE_BY_CODE: dict[str, dict] = {c["code"]: c for c in PHONE_COUNTRY_CODES}


def phone_meta(codigo_pais: str) -> dict | None:
    code = "".join(ch for ch in (codigo_pais or "") if ch.isdigit())
    return PHONE_BY_CODE.get(code)


def validate_national_number(codigo_pais: str, telefono_nacional: str) -> tuple[bool, str]:
    """
    Valida número nacional según país.
    Retorna (ok, telefono_e164_sin_plus) p.ej. '18098970000'.
    """
    import re

    meta = phone_meta(codigo_pais)
    if meta is None:
        return False, ""
    national = re.sub(r"\D+", "", telefono_nacional or "")
    nmin = int(meta["nsn_min"])
    nmax = int(meta["nsn_max"])
    # Tope E.164: código + nacional <= 15
    e164_cap = 15 - len(meta["code"])
    nmax = min(nmax, e164_cap)
    if not (nmin <= len(national) <= nmax):
        return False, ""
    return True, f"{meta['code']}{national}"
