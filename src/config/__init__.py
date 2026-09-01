from pathlib import Path
from typing import List, Optional, Dict

from config.parameter_config import PARAMETER_CONFIG

# ============================================================
# DIRECTORIOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

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
    },
    {
        "url": "https://qacore-rummi.gse.com.co/trading/api-docs/",
        "section_name": "Rummi Blockchain Trading API",
        "filter_paths": ["/trading"],
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
