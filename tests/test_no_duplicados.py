"""
Pruebas de la lógica de secciones en la generación de endpoints.

Reglas cubiertas:

  A) "Ejemplo JSON de entrada" se imprime SIEMPRE después de los
     parámetros de entrada (si existe contenido: requestBody o ejemplo
     desencriptado). Nunca se emite el heading sin contenido.
  B) No se imprimen dos tablas de estructura de respuesta idénticas:
     se conserva "Respuesta exitosa".
  C) "Estructura del JSON de salida desencriptado" solo se imprime en
     endpoints CIFRADOS.
  D) Ningún subtítulo se imprime sin contenido debajo.

Ejecución:
    python tests/test_no_duplicados.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docx import Document  # noqa: E402
from docx.table import Table  # noqa: E402
from docx.text.paragraph import Paragraph  # noqa: E402

from generator.word_generator import (  # noqa: E402
    _rows_are_equal,
    _schema_rows,
    add_endpoint_section,
    classify_endpoints,
)
from swagger.endpoint import SchemaInfo, SchemaProperty  # noqa: E402
from swagger.parser import parse_endpoints  # noqa: E402


# ============================================================
# ESQUEMAS DE PRUEBA (crudos, tal como los aporta OpenAPI)
# ============================================================

RESPONSE_SPEC = {
    "type": "object",
    "required": ["statusCode"],
    "properties": {
        "statusCode": {"type": "integer"},
        "data": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
        },
    },
}

BODY_SPEC = {
    "type": "object",
    "required": ["userName", "email", "profile"],
    "properties": {
        "userName": {"type": "string"},
        "email": {"type": "string"},
        "profile": {
            "type": "object",
            "properties": {
                "firstName": {"type": "string"},
                "address": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                },
            },
        },
    },
}


def response_schema():
    """SchemaInfo equivalente a RESPONSE_SPEC (para probar los helpers)."""
    return SchemaInfo(
        name="ApiResponse",
        type="object",
        properties=[
            SchemaProperty(name="statusCode", type="integer", required=True),
            SchemaProperty(
                name="data",
                type="object",
                properties=[SchemaProperty(name="message", type="string")],
            ),
        ],
    )


# ============================================================
# UTILIDADES DE PRUEBA
# ============================================================

def doc_items(document):
    """Secuencia de (tipo, estilo/nºfilas, texto/cabecera) del documento."""
    items = []
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, document)
            items.append(("p", paragraph.style.name, paragraph.text.strip()))
        elif child.tag.endswith("}tbl"):
            table = Table(child, document)
            header = [cell.text.strip() for cell in table.rows[0].cells]
            items.append(("t", len(table.rows), header))
    return items


def render(document_spec):
    """Parsea, clasifica y renderiza como lo hace generate_word."""
    endpoints = parse_endpoints(document_spec)
    document = Document()
    groups = classify_endpoints(endpoints)

    for endpoint in groups["encrypted"]:
        add_endpoint_section(
            document, endpoint, index=1, is_template=True, is_encrypted=True
        )
    for endpoint in groups["not_encrypted"]:
        add_endpoint_section(
            document, endpoint, index=1, is_template=True, is_encrypted=False
        )
    return document


def paragraph_texts(document, style=None):
    return [
        text
        for kind, item_style, text in doc_items(document)
        if kind == "p" and (style is None or item_style == style) and text
    ]


def has_paragraph(document, text):
    return text in paragraph_texts(document)


def has_heading(document, text, level=3):
    return any(
        kind == "p" and style == f"Heading {level}" and value == text
        for kind, style, value in doc_items(document)
    )


def structure_tables(document):
    """Tablas de 5 columnas (Nombre/Tipo/Tamaño/Obligatorio/Descripción)."""
    return [
        item
        for item in doc_items(document)
        if item[0] == "t"
        and item[2]
        and item[2][0] == "Nombre"
        and item[2][1] == "Tipo"
    ]


def json_blocks(document):
    """Bloques de código (tablas de 1 fila)."""
    return [item for item in doc_items(document) if item[0] == "t" and item[1] == 1]


def openapi(description, *, rb=None, params=None, responses=None):
    operation = {
        "summary": "Operacion de prueba",
        "description": description,
        "responses": responses or {
            "200": {
                "description": "OK",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/R"}}},
            }
        },
    }
    if rb is not None:
        operation["requestBody"] = {
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/B"}}}
        }
    if params:
        operation["parameters"] = params

    return {
        "openapi": "3.0.0",
        "info": {"title": "API de prueba", "version": "1.0.0"},
        "paths": {"/demo": {"post": operation}},
        "components": {"schemas": {"B": rb or {}, "R": RESPONSE_SPEC}},
    }


# ============================================================
# HELPERS
# ============================================================

def test_schema_rows_vacio():
    assert _schema_rows(None) == []
    assert _schema_rows(SchemaInfo(name="X", type="object", properties=[])) == []

    rows = _schema_rows(response_schema())
    assert [row["name"] for row in rows] == ["statusCode", "data", "data.message"]


def test_rows_are_equal():
    rows = _schema_rows(response_schema())
    assert _rows_are_equal(rows, [dict(row) for row in rows]) is True
    assert _rows_are_equal(rows, []) is False
    assert _rows_are_equal([], rows) is False
    assert _rows_are_equal(rows, rows[:-1]) is False


# ============================================================
# ESCENARIOS
# ============================================================

def test_sin_cifrado_imprime_ejemplo_json_de_entrada():
    """Escenario 1: sin cifrado -> ejemplo de entrada + sin sección desencriptada."""
    spec = openapi(
        "Crea un usuario nuevo. No usa cifrado.",
        rb=BODY_SPEC,
        params=[
            {"name": "X-Ct", "in": "header", "required": False,
             "schema": {"type": "string"}}
        ],
    )
    document = render(spec)

    # A) El ejemplo JSON de entrada se restablece después de los parámetros
    assert has_heading(document, "Ejemplo JSON de entrada"), (
        "Debe imprimirse el ejemplo JSON de entrada"
    )

    # Etiqueta dinámica: sin "encriptado" en endpoints sin cifrado
    texts = paragraph_texts(document)
    idx = texts.index("Ejemplo JSON de entrada")
    assert texts[idx + 1] == "Ejemplo JSON de entrada:", (
        f"Etiqueta inesperada: {texts[idx + 1]!r}"
    )
    assert len(json_blocks(document)) >= 1, "Debe imprimirse el bloque JSON"

    # C) Sin sección de salida desencriptada
    assert not has_paragraph(document, "Estructura del JSON de salida desencriptado"), (
        "Los endpoints sin cifrado no muestran estructura desencriptada"
    )

    # B) Se conserva "Respuesta exitosa" como única tabla de estructura
    assert has_paragraph(document, "Respuesta exitosa"), (
        "Se conserva el subtítulo 'Respuesta exitosa'"
    )

    # Tablas de estructura: body + cabecera/consulta + respuesta
    assert len(structure_tables(document)) == 3, (
        f"Se esperaban 3 tablas (body, cabecera, respuesta), hay "
        f"{len(structure_tables(document))}"
    )

    # El ejemplo de salida y la tabla de statusCode se conservan
    assert has_heading(document, "Ejemplo JSON de salida")
    assert has_heading(document, "Valores para el atributo de statusCode")


def test_ejemplo_json_de_entrada_va_despues_de_parametros():
    """El ejemplo de entrada se imprime inmediatamente tras la tabla de parámetros."""
    spec = openapi("Confirma el registro. No usa cifrado.", rb=BODY_SPEC)
    document = render(spec)
    items = doc_items(document)

    def heading_index(text):
        return next(
            i for i, (kind, style, value) in enumerate(items)
            if kind == "p" and style == "Heading 3" and value == text
        )

    i_params = heading_index("Parámetros de entrada")
    i_example = heading_index("Ejemplo JSON de entrada")
    i_response = heading_index("Respuesta")

    assert i_params < i_example < i_response, (
        "El ejemplo de entrada debe ir entre parámetros y respuesta"
    )

    # Entre "Parámetros de entrada" y el ejemplo no puede haber otro heading
    middle = items[i_params + 1:i_example]
    assert not any(
        kind == "p" and style.startswith("Heading")
        for kind, style, _ in middle
    ), "No debe haber otro heading intermedio"

    # Justo después del heading: la etiqueta y el bloque JSON
    following = items[i_example + 1:i_example + 3]
    assert following[0] == ("p", "Normal", "Ejemplo JSON de entrada:")
    assert following[1][0] == "t" and following[1][1] == 1, (
        "Falta el bloque de código con el JSON de ejemplo"
    )


def test_con_cifrado_conserva_todas_las_secciones():
    """Escenario 4: los endpoints cifrados conservan su documentación actual."""
    description = (
        "Envia la notificacion al usuario. Requiere cifrado en transporte.\n"
        "Estructura del JSON de entrada desencriptado:\n"
        '{\n  "userId": "u1"\n}\n'
        "Estructura del JSON de salida desencriptado:\n"
        '{\n  "statusCode": 200,\n  "code": "ES01"\n}'
    )
    spec = openapi(description, rb=BODY_SPEC)
    document = render(spec)

    # Entrada desencriptada
    assert has_paragraph(document, "Estructura de JSON de entrada desencriptado")
    assert has_paragraph(document, "Ejemplo de JSON de entrada desencriptado:")

    # Ejemplo de entrada encriptado (etiqueta original conservada)
    assert has_heading(document, "Ejemplo JSON de entrada")
    texts = paragraph_texts(document)
    idx = texts.index("Ejemplo JSON de entrada")
    assert texts[idx + 1] == "Ejemplo JSON de entrada encriptado:"

    # Respuesta y salida desencriptada (contenido distinto -> se imprime)
    assert has_paragraph(document, "Respuesta exitosa")
    assert has_paragraph(document, "Estructura del JSON de salida desencriptado")

    # Ejemplo de salida y statusCode
    assert has_heading(document, "Ejemplo JSON de salida")
    assert has_heading(document, "Valores para el atributo de statusCode")

    # Tablas: body + entrada desencriptada + respuesta + salida desencriptada
    assert len(structure_tables(document)) == 4, (
        f"Se esperaban 4 tablas (body, entrada desencriptada, respuesta, "
        f"salida desencriptada), hay {len(structure_tables(document))}"
    )


def test_con_cifrado_sin_salida_desencriptada_no_duplica_tabla():
    """Escenario B: cifrado sin JSON de salida -> no repite la tabla idéntica."""
    spec = openapi("Opera el recurso sin marcadores de desencriptado.", rb=BODY_SPEC)
    document = render(spec)

    assert has_paragraph(document, "Respuesta exitosa"), (
        "Se conserva la única tabla de estructura"
    )
    assert not has_paragraph(document, "Estructura del JSON de salida desencriptado"), (
        "No debe duplicarse una tabla idéntica"
    )
    # Se mantiene el comportamiento existente de los endpoints cifrados:
    # "Estructura de JSON de entrada desencriptado" sigue imprimiéndose.
    assert has_paragraph(document, "Estructura de JSON de entrada desencriptado")
    assert len(structure_tables(document)) == 3, (
        f"Se esperaban 3 tablas (body, entrada desencriptada, respuesta), "
        f"hay {len(structure_tables(document))}"
    )


def test_sin_request_body_no_imprime_titulo_vacio():
    """Escenario 3: sin ejemplo de entrada -> no queda el heading vacío."""
    spec = openapi(
        "Suscripcion SSE. No usa cifrado.",
        params=[
            {"name": "userId", "in": "query", "required": True,
             "schema": {"type": "string"}}
        ],
    )
    document = render(spec)

    assert not has_heading(document, "Ejemplo JSON de entrada"), (
        "El heading no debe existir si no hay contenido"
    )
    assert has_paragraph(document, "Respuesta exitosa")
    assert not has_paragraph(document, "Estructura del JSON de salida desencriptado")
    assert len(structure_tables(document)) == 2, (
        f"Se esperaban 2 tablas (parámetros + respuesta), hay "
        f"{len(structure_tables(document))}"
    )


def test_respuesta_sin_contenido_no_imprime_subtitulos():
    """Escenario 5: respuestas sin contenido -> sin subtítulos ni secciones vacías."""
    spec = openapi(
        "Endpoint sin cuerpo de respuesta. No usa cifrado.",
        rb=BODY_SPEC,
        responses={
            "204": {"description": "Sin contenido"},
            "404": {"description": "No encontrado"},
        },
    )
    document = render(spec)

    assert not has_paragraph(document, "Respuesta exitosa")
    assert not has_paragraph(document, "Estructura del JSON de salida desencriptado")
    assert not has_heading(document, "Ejemplo JSON de salida")

    # La tabla de statusCode siempre tiene contenido que mostrar
    assert has_heading(document, "Valores para el atributo de statusCode")


def test_todos_los_subtitulos_tienen_contenido():
    """Ningún subtítulo en negrita puede quedar sin tabla debajo."""
    spec = openapi("Crea un usuario nuevo. No usa cifrado.", rb=BODY_SPEC)
    document = render(spec)
    items = doc_items(document)

    bold_titles = {
        "Respuesta exitosa",
        "Estructura del JSON de salida desencriptado",
        "Estructura de JSON de entrada desencriptado",
    }

    for position, (kind, _style, text) in enumerate(items):
        if kind == "p" and text in bold_titles:
            following = items[position + 1:position + 3]
            assert any(
                entry[0] == "t" and entry[1] > 1 and entry[2] and entry[2][0] == "Nombre"
                for entry in following
            ), f"El subtítulo {text!r} no tiene tabla debajo"


# ============================================================
# Runner
# ============================================================

def main():
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]

    failures = []

    for test in tests:
        try:
            test()
        except Exception as error:  # noqa: BLE001
            failures.append((test.__name__, error))
            print(f"[FALLO] {test.__name__}: {type(error).__name__}: {error}")
        else:
            print(f"[ OK ] {test.__name__}")

    print("-" * 60)
    print(
        f"Pruebas: {len(tests)} | OK: {len(tests) - len(failures)} | "
        f"Fallos: {len(failures)}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
