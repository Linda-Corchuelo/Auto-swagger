import os
from pathlib import Path
from typing import List, Optional, Dict
from dotenv import load_dotenv

from config.parameter_config import PARAMETER_CONFIG

# ============================================================
# VARIABLES DE ENTORNO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SWAGGER_AUTH_USERNAME: Optional[str] = os.environ.get("SWAGGER_AUTH_USERNAME")
SWAGGER_AUTH_PASSWORD: Optional[str] = os.environ.get("SWAGGER_AUTH_PASSWORD")

# ============================================================
# DIRECTORIOS
# ============================================================

TEMPLATE_DIR = BASE_DIR / "template"
OUTPUT_DIR = BASE_DIR / "output"

def ensure_directories() -> None:
    """Crea los directorios necesarios si no existen."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

# Crear directorios base automáticamente
ensure_directories()

# ============================================================
# PLANTILLA WORD
# ============================================================

WORD_TEMPLATE: Path = TEMPLATE_DIR / "IXV10 - acuerdo de interfaz.docx"

# ============================================================
# SERVICIOS SWAGGER / OPENAPI
# ============================================================
# Cada servicio define: url, section_name (nombre de la sección
# en el Word), y filter_paths (prefijos de paths a incluir).

SWAGGER_SERVICES: List[Dict] = [
    {
        "url": "https://qacore-rummi.gse.com.co/users/api-docs/",
        "section_name": "Rummi User Administration API",
        "filter_paths": ["/users"],
        "auth": None,
    },
    {
        "url": "https://qacore-rummi.gse.com.co/trading/api-docs/",
        "section_name": "Rummi Blockchain Trading API",
        "filter_paths": ["/trading"],
        "auth": {"username": SWAGGER_AUTH_USERNAME, "password": SWAGGER_AUTH_PASSWORD} if SWAGGER_AUTH_USERNAME and SWAGGER_AUTH_PASSWORD else None,
    },
    {
        "url": "https://qacore-rummi.gse.com.co/file-manager/api-docs/",
        "section_name": "File Manager Service",
        "filter_paths": ["/file-manager"],
        "auth": None,
    },
    {
        "url": "https://qacore-rummi.gse.com.co/events/api-docs/",
        "section_name": "Rummi Events API",
        "filter_paths": ["/events"],
        "auth": {"username": SWAGGER_AUTH_USERNAME, "password": SWAGGER_AUTH_PASSWORD} if SWAGGER_AUTH_USERNAME and SWAGGER_AUTH_PASSWORD else None,
    },
    {
        "url": "https://qacore-rummi.gse.com.co/wallet/api-docs/",
        "section_name": "Rummi Wallet API",
        "filter_paths": ["/wallet"],
        "auth": {"username": SWAGGER_AUTH_USERNAME, "password": SWAGGER_AUTH_PASSWORD} if SWAGGER_AUTH_USERNAME and SWAGGER_AUTH_PASSWORD else None,
    },
]

# ============================================================
# FUENTE SWAGGER / OPENAPI (compatibilidad hacia atrás)
# ============================================================

SWAGGER_URL: str = SWAGGER_SERVICES[0]["url"]

# ============================================================
# FILTROS DE ENDPOINTS (compatibilidad hacia atrás)
# ============================================================

ENDPOINTS_TO_DOCUMENT: Optional[List[str]] = SWAGGER_SERVICES[0]["filter_paths"]
