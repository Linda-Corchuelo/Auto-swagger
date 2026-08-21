from pathlib import Path


# ============================================================
# DIRECTORIOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATE_DIR = BASE_DIR / "template"
OUTPUT_DIR = BASE_DIR / "output"


# ============================================================
# PLANTILLA WORD
# ============================================================

WORD_TEMPLATE = (
    TEMPLATE_DIR / "IXV10 - acuerdo de interfaz.docx"
)


# ============================================================
# SWAGGER
# ============================================================

SWAGGER_URL = (
    "https://qacore-rummi.gse.com.co/users/api-docs/"
)


# ============================================================
# ENDPOINTS A DOCUMENTAR
# ============================================================

ENDPOINTS_TO_DOCUMENT = [
    "/users",
]