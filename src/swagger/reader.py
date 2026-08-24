import json
from pathlib import Path
from typing import Any, Dict, Union
from urllib.parse import urljoin

import requests
import yaml


def extract_swagger_doc(js_content: str) -> Dict[str, Any]:
    """
    Extrae el objeto JSON swaggerDoc desde el archivo swagger-ui-init.js.
    """
    marker = '"swaggerDoc"'
    position = js_content.find(marker)

    if position == -1:
        # Intentar también con comillas simples o sin comillas si aplica
        marker = "swaggerDoc"
        position = js_content.find(marker)

    if position == -1:
        raise ValueError("No se encontró 'swaggerDoc' dentro de swagger-ui-init.js")

    # Buscar la primera llave '{' después de "swaggerDoc"
    start = js_content.find("{", position)
    if start == -1:
        raise ValueError("No se encontró el inicio del objeto swaggerDoc.")

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
                swagger_json = js_content[start : i + 1]
                try:
                    return json.loads(swagger_json)
                except json.JSONDecodeError as error:
                    raise ValueError(f"swaggerDoc no es un JSON válido: {error}") from error

    raise ValueError("No se encontró el cierre del objeto swaggerDoc.")


def normalize_swagger_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Limpia entradas que no corresponden a endpoints dentro de paths
    y asegura que la estructura básica esté presente.
    """
    if not isinstance(document, dict):
        raise ValueError("La especificación OpenAPI debe ser un objeto/diccionario.")

    paths = document.get("paths", {})
    if isinstance(paths, dict):
        invalid_path_keys = {"openapi", "info", "servers", "components", "security"}
        for key in invalid_path_keys:
            paths.pop(key, None)
        document["paths"] = paths
    else:
        document["paths"] = {}

    return document


def load_from_local_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Carga una especificación OpenAPI desde un archivo local (.json, .yaml o .yml).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo local de Swagger: {path}")

    print(f"Cargando especificación desde archivo local: {path}")
    content = path.read_text(encoding="utf-8")

    if path.suffix.lower() in (".yaml", ".yml"):
        document = yaml.safe_load(content)
    else:
        try:
            document = json.loads(content)
        except json.JSONDecodeError:
            # Si falla como JSON, intentar como YAML
            document = yaml.safe_load(content)

    return normalize_swagger_document(document)


def load_from_url(url: str) -> Dict[str, Any]:
    """
    Carga y procesa una especificación OpenAPI desde una URL.

    Soporta automáticamente:
    1. URLs directas de JSON (e.g. /v3/api-docs, /openapi.json, /swagger.json).
    2. URLs directas de YAML (e.g. /openapi.yaml).
    3. Interfaces interactivas Swagger UI HTML (extrayendo swaggerDoc desde swagger-ui-init.js).
    """
    print("Cargando Swagger / OpenAPI...")
    print(f"URL: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, application/yaml, text/yaml, text/html, */*",
    }

    response = requests.get(url, headers=headers, timeout=30)
    print(f"STATUS: {response.status_code}")
    print(f"CONTENT-TYPE: {response.headers.get('content-type')}")
    print(f"URL FINAL: {response.url}")

    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    text = response.text.strip()

    # ---------------------------------------------------------
    # CASO 1: Respuesta directa en formato JSON
    # ---------------------------------------------------------
    if "json" in content_type or text.startswith("{"):
        try:
            document = response.json()
            if isinstance(document, dict) and ("openapi" in document or "swagger" in document or "paths" in document):
                print("Especificación OpenAPI detectada directamente como JSON.")
                return normalize_swagger_document(document)
        except Exception:
            pass

    # ---------------------------------------------------------
    # CASO 2: Respuesta directa en formato YAML
    # ---------------------------------------------------------
    if "yaml" in content_type or url.endswith((".yaml", ".yml")):
        try:
            document = yaml.safe_load(text)
            if isinstance(document, dict) and ("openapi" in document or "swagger" in document or "paths" in document):
                print("Especificación OpenAPI detectada directamente como YAML.")
                return normalize_swagger_document(document)
        except Exception:
            pass

    # ---------------------------------------------------------
    # CASO 3: Interfaz gráfica Swagger UI HTML
    # ---------------------------------------------------------
    print("Detectada interfaz Swagger UI HTML. Extrayendo especificación interna...")

    # Intentar descargar swagger-ui-init.js
    init_js_url = urljoin(response.url, "swagger-ui-init.js")
    print(f"Descargando script: {init_js_url}")

    init_response = requests.get(init_js_url, headers=headers, timeout=30)
    init_response.raise_for_status()

    document = extract_swagger_doc(init_response.text)
    document = normalize_swagger_document(document)

    print("Swagger extraído correctamente.")
    print(f"OpenAPI: {document.get('openapi')}")
    print(f"Título: {document.get('info', {}).get('title')}")
    print(f"Paths encontrados: {len(document.get('paths', {}))}")

    return document


def load_document(source: Union[str, Path]) -> Dict[str, Any]:
    """
    Función de entrada unificada: determina automáticamente si `source`
    es un archivo local en disco o una URL de red, y procesa la especificación.
    """
    source_str = str(source).strip()

    if source_str.startswith(("http://", "https://")):
        return load_from_url(source_str)

    local_path = Path(source_str)
    if local_path.exists():
        return load_from_local_file(local_path)

    # Si no tiene http:// pero tampoco existe como ruta local, asumir URL
    return load_from_url(source_str)