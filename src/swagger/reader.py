import json
import re
from urllib.parse import urljoin

import requests


def extract_swagger_doc(js_content):
    """
    Extrae el objeto swaggerDoc desde swagger-ui-init.js.
    """

    marker = '"swaggerDoc"'

    position = js_content.find(marker)

    if position == -1:
        raise ValueError(
            "No se encontró 'swaggerDoc' dentro de swagger-ui-init.js"
        )

    # Buscar la primera llave después de "swaggerDoc":
    start = js_content.find("{", position)

    if start == -1:
        raise ValueError(
            "No se encontró el inicio del objeto swaggerDoc."
        )

    depth = 0
    in_string = False
    escaped = False

    for i in range(start, len(js_content)):
        char = js_content[i]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False

            continue

        if char == '"':
            in_string = True

        elif char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                swagger_json = js_content[start:i + 1]

                try:
                    return json.loads(swagger_json)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"swaggerDoc no es un JSON válido: {error}"
                    ) from error

    raise ValueError(
        "No se encontró el cierre del objeto swaggerDoc."
    )

def normalize_swagger_document(document):
    """
    Limpia entradas que no corresponden a endpoints dentro de paths.
    """

    paths = document.get("paths", {})

    invalid_path_keys = {
        "openapi",
        "info",
        "servers",
    }

    for key in invalid_path_keys:
        paths.pop(key, None)

    document["paths"] = paths

    return document

def load_from_url(url):
    print("Cargando Swagger...")
    print(f"URL: {url}")

    # ---------------------------------------------------------
    # 1. Descargar Swagger UI
    # ---------------------------------------------------------

    response = requests.get(url, timeout=30)

    print(f"STATUS: {response.status_code}")
    print(f"CONTENT-TYPE: {response.headers.get('content-type')}")
    print(f"URL FINAL: {response.url}")

    response.raise_for_status()

    # ---------------------------------------------------------
    # 2. Construir URL de swagger-ui-init.js
    # ---------------------------------------------------------

    init_js_url = urljoin(
        response.url,
        "swagger-ui-init.js"
    )

    print(f"Swagger Init JS: {init_js_url}")

    # ---------------------------------------------------------
    # 3. Descargar swagger-ui-init.js
    # ---------------------------------------------------------

    init_response = requests.get(
        init_js_url,
        timeout=30
    )

    print(
        f"INIT STATUS: {init_response.status_code}"
    )

    print(
        f"INIT CONTENT-TYPE: "
        f"{init_response.headers.get('content-type')}"
    )

    init_response.raise_for_status()

    # ---------------------------------------------------------
    # 4. Extraer swaggerDoc
    # ---------------------------------------------------------

    document = extract_swagger_doc(
    init_response.text
    )

    document = normalize_swagger_document(document)

    # ---------------------------------------------------------
    # 5. Validar documento
    # ---------------------------------------------------------

    print("Swagger extraído correctamente.")
    print(
        f"OpenAPI: "
        f"{document.get('openapi')}"
    )

    print(
        f"Título: "
        f"{document.get('info', {}).get('title')}"
    )

    print(
        f"Paths encontrados: "
        f"{len(document.get('paths', {}))}"
    )

    return document