from pathlib import Path
from typing import List, Optional

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
# FUENTE SWAGGER / OPENAPI
# ============================================================

SWAGGER_URL: str = "https://qacore-rummi.gse.com.co/users/api-docs/"

# ============================================================
# FILTROS DE ENDPOINTS
# ============================================================
# Si la lista contiene elementos (e.g. ["/users"]), solo se documentarán
# los endpoints que comiencen o coincidan con dichas rutas.
# Si se deja vacía ([]), se documentarán todos los endpoints encontrados.

ENDPOINTS_TO_DOCUMENT: Optional[List[str]] = ["/users"]
