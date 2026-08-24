# Swagger / OpenAPI Document Generator

Generador automático de documentación técnica y acuerdos de interfaz para APIs REST a partir de especificaciones Swagger / OpenAPI 3.0+.

## Características

- 🌐 **Lector Universal OpenAPI / Swagger**: Soporta URLs de Swagger UI HTML, URLs directas JSON/YAML (`/v3/api-docs`, `/openapi.json`, etc.) y archivos locales (`.json`, `.yaml`, `.yml`).
- 🧩 **Modelado Tipado y Jerárquico**: Resuelve referencias internas (`$ref`), parámetros (query, path, header), cuerpos de petición (request body) y respuestas HTTP con esquemas anidados.
- 🎯 **Filtro de Endpoints**: Permite documentar toda la API o filtrar por prefijos de rutas específicas (ej. solo `["/users"]`).
- 📄 **Exportación Intermedia JSON**: Genera un archivo `swagger_output.json` normalizado y estructurado.
- 📝 **Acuerdo de Interfaz Institucional en Word (.docx)**: Produce un documento Word basado en la plantilla corporativa oficial (`template/IXV10 - acuerdo de interfaz.docx`) o en modo independiente, con tablas estilizadas y cajas de código JSON formateadas.

---

## Estructura del Proyecto

```
swagger-doc-generator/
├── src/
│   ├── config.py              # Configuración central (URL, rutas de salida, filtros)
│   ├── main.py                # Punto de entrada y orquestador del flujo
│   ├── swagger/
│   │   ├── endpoint.py        # Dataclasses tipadas (Endpoint, SchemaInfo, ParameterInfo, etc.)
│   │   ├── reader.py          # Lector y extractor de Swagger UI / OpenAPI
│   │   ├── parser.py          # Parseo de endpoints, schemas y resolución de $ref
│   │   └── exporter.py        # Serialización y exportación a JSON
│   └── generator/
│       └── word_generator.py  # Generador de documentos Word con python-docx
├── template/
│   └── IXV10 - acuerdo de interfaz.docx # Plantilla base de acuerdo de interfaz
├── output/                    # Carpeta donde se generan los archivos de salida
├── requirements.txt           # Dependencias de Python
└── README.md                  # Documentación del proyecto
```

---

## Instalación

1. Crear y activar un entorno virtual:
```bash
python -m venv .venv
# En Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# En Linux / Mac:
source .venv/bin/activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

---

## Uso

1. Configurar la URL del Swagger y las opciones en [`src/config.py`](file:///c:/Users/home/swagger-doc-generator/src/config.py):
```python
SWAGGER_URL = "https://qacore-rummi.gse.com.co/users/api-docs/"
ENDPOINTS_TO_DOCUMENT = ["/users"]  # Dejar en [] para documentar todos
```

2. Ejecutar el generador:
```bash
python src/main.py
```

3. Los resultados se guardarán automáticamente en la carpeta `output/`:
   - `output/swagger_output.json`
   - `output/documentacion_api.docx`
