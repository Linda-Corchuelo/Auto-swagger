from docx import Document

from docx.enum.table import (
    WD_CELL_VERTICAL_ALIGNMENT,
    WD_TABLE_ALIGNMENT,
)

from docx.enum.text import WD_ALIGN_PARAGRAPH

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from docx.shared import Inches, Pt

import json


# ============================================================
# UTILIDADES
# ============================================================

def set_cell_shading(cell, fill):
    """
    Cambia el color de fondo de una celda.
    """
    tc_pr = cell._tc.get_or_add_tcPr()

    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)

    tc_pr.append(shd)


def set_cell_text_bold(cell):
    """
    Pone en negrita el contenido de una celda.
    """
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True


def set_cell_width(cell, width_inches):
    """
    Establece el ancho aproximado de una celda.
    """
    tc = cell._tc

    tc_pr = tc.get_or_add_tcPr()

    tc_w = tc_pr.find(qn("w:tcW"))

    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)

    tc_w.set(
        qn("w:w"),
        str(int(width_inches * 1440))
    )

    tc_w.set(
        qn("w:type"),
        "dxa"
    )


def format_value(value):
    """
    Convierte valores Python complejos en texto legible.
    """

    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (dict, list)):

        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                indent=2
            )

        except Exception:
            return str(value)

    return str(value)


# ============================================================
# TAMAÑO
# ============================================================

def get_property_size(prop):
    """
    Obtiene el tamaño de una propiedad Swagger/OpenAPI.

    Prioridad:

    1. maxLength
    2. minLength + maxLength
    3. maxItems
    4. minItems + maxItems
    5. maximum
    6. minimum

    Si no existe información de tamaño:
        -

    Ejemplos:

        maxLength: 50
            -> 50

        minLength: 3, maxLength: 50
            -> 3 - 50

        maxItems: 10
            -> 10

        minimum: 1, maximum: 100
            -> 1 - 100
    """

    # --------------------------------------------------------
    # Obtener atributos
    # --------------------------------------------------------

    max_length = getattr(
        prop,
        "max_length",
        None
    )

    min_length = getattr(
        prop,
        "min_length",
        None
    )

    max_items = getattr(
        prop,
        "max_items",
        None
    )

    min_items = getattr(
        prop,
        "min_items",
        None
    )

    maximum = getattr(
        prop,
        "maximum",
        None
    )

    minimum = getattr(
        prop,
        "minimum",
        None
    )

    # --------------------------------------------------------
    # Si el parser guarda los valores en atributos diferentes
    # --------------------------------------------------------

    if isinstance(prop, dict):

        max_length = prop.get(
            "maxLength",
            max_length
        )

        min_length = prop.get(
            "minLength",
            min_length
        )

        max_items = prop.get(
            "maxItems",
            max_items
        )

        min_items = prop.get(
            "minItems",
            min_items
        )

        maximum = prop.get(
            "maximum",
            maximum
        )

        minimum = prop.get(
            "minimum",
            minimum
        )

    # --------------------------------------------------------
    # Longitud
    # --------------------------------------------------------

    if (
        min_length is not None
        and max_length is not None
    ):
        return f"{min_length} - {max_length}"

    if max_length is not None:
        return str(max_length)

    if min_length is not None:
        return f"{min_length} -"

    # --------------------------------------------------------
    # Arrays
    # --------------------------------------------------------

    if (
        min_items is not None
        and max_items is not None
    ):
        return f"{min_items} - {max_items}"

    if max_items is not None:
        return str(max_items)

    if min_items is not None:
        return f"{min_items} -"

    # --------------------------------------------------------
    # Valores numéricos
    # --------------------------------------------------------

    if (
        minimum is not None
        and maximum is not None
    ):
        return f"{minimum} - {maximum}"

    if maximum is not None:
        return str(maximum)

    if minimum is not None:
        return f"{minimum} -"

    return "-"


# ============================================================
# TÍTULO
# ============================================================

def add_title(document, title):
    """
    Agrega el título principal.
    """

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    run = paragraph.add_run(title)

    run.bold = True
    run.font.size = Pt(20)


# ============================================================
# INFORMACIÓN GENERAL
# ============================================================

def add_general_information(
    document,
    document_data
):
    """
    Agrega la información general del API.
    """

    document.add_heading(
        "1. Información general",
        level=1
    )

    info = document_data.get(
        "info",
        {}
    )

    table = document.add_table(
        rows=4,
        cols=2
    )

    table.alignment = (
        WD_TABLE_ALIGNMENT.CENTER
    )

    table.style = "Table Grid"

    data = [
        (
            "Nombre",
            info.get(
                "title",
                "Sin información"
            )
        ),
        (
            "Versión",
            info.get(
                "version",
                "Sin información"
            )
        ),
        (
            "OpenAPI",
            document_data.get(
                "openapi",
                "Sin información"
            )
        ),
        (
            "Descripción",
            info.get(
                "description",
                "Sin información"
            )
        ),
    ]

    for row, (label, value) in zip(
        table.rows,
        data
    ):

        row.cells[0].text = str(label)

        row.cells[1].text = format_value(
            value
        )

        set_cell_text_bold(
            row.cells[0]
        )

        set_cell_shading(
            row.cells[0],
            "D9EAF7"
        )

    document.add_paragraph()


# ============================================================
# RESUMEN DE ENDPOINTS
# ============================================================

def add_endpoint_summary(
    document,
    endpoints
):
    """
    Agrega un resumen de los endpoints.

    Esta tabla es únicamente de navegación/resumen,
    no de campos de Request/Response.
    """

    document.add_heading(
        "2. Resumen de endpoints",
        level=1
    )

    table = document.add_table(
        rows=1,
        cols=4
    )

    table.style = "Table Grid"

    table.alignment = (
        WD_TABLE_ALIGNMENT.CENTER
    )

    headers = [
        "Método",
        "Endpoint",
        "Resumen",
        "Descripción",
    ]

    for cell, header in zip(
        table.rows[0].cells,
        headers
    ):

        cell.text = header

        set_cell_text_bold(
            cell
        )

        set_cell_shading(
            cell,
            "D9EAF7"
        )

        cell.vertical_alignment = (
            WD_CELL_VERTICAL_ALIGNMENT.CENTER
        )

    for endpoint in endpoints:

        row = table.add_row().cells

        row[0].text = str(
            endpoint.method
        ).upper()

        row[1].text = str(
            endpoint.path
        )

        row[2].text = str(
            endpoint.summary
            or "Sin resumen"
        )

        row[3].text = str(
            endpoint.description
            or "Sin descripción"
        )

    document.add_paragraph()


# ============================================================
# TABLA ESTÁNDAR DE CAMPOS
# ============================================================

def create_fields_table(
    document,
    properties
):
    """
    Crea la tabla estándar de campos.

    COLUMNAS OBLIGATORIAS:

        Nombre
        Tipo
        Tamaño
        Obligatorio
        Descripción
    """

    table = document.add_table(
        rows=1,
        cols=5
    )

    table.style = "Table Grid"

    table.alignment = (
        WD_TABLE_ALIGNMENT.CENTER
    )

    headers = [
        "Nombre",
        "Tipo",
        "Tamaño",
        "Obligatorio",
        "Descripción",
    ]

    # --------------------------------------------------------
    # Encabezados
    # --------------------------------------------------------

    for cell, header in zip(
        table.rows[0].cells,
        headers
    ):

        cell.text = header

        set_cell_text_bold(
            cell
        )

        set_cell_shading(
            cell,
            "EAF2F8"
        )

        cell.vertical_alignment = (
            WD_CELL_VERTICAL_ALIGNMENT.CENTER
        )

    # --------------------------------------------------------
    # Ancho de columnas
    # --------------------------------------------------------

    widths = [
        1.8,
        1.0,
        1.0,
        1.1,
        3.2,
    ]

    for cell, width in zip(
        table.rows[0].cells,
        widths
    ):
        set_cell_width(
            cell,
            width
        )

    # --------------------------------------------------------
    # Filas
    # --------------------------------------------------------

    for prop in properties:

        row = table.add_row().cells

        # Nombre
        row[0].text = str(
            getattr(
                prop,
                "name",
                ""
            )
        )

        # Tipo
        row[1].text = str(
            getattr(
                prop,
                "type",
                "object"
            )
        )

        # Tamaño
        row[2].text = get_property_size(
            prop
        )

        # Obligatorio
        row[3].text = (
            "Sí"
            if getattr(
                prop,
                "required",
                False
            )
            else "No"
        )

        # Descripción
        row[4].text = str(
            getattr(
                prop,
                "description",
                ""
            )
            or ""
        )

        # Alineación vertical
        for cell in row:

            cell.vertical_alignment = (
                WD_CELL_VERTICAL_ALIGNMENT.CENTER
            )

        # Anchos
        for cell, width in zip(
            row,
            widths
        ):

            set_cell_width(
                cell,
                width
            )

    return table


# ============================================================
# PROPIEDADES ANIDADAS
# ============================================================

def collect_nested_properties(
    properties,
    prefix=""
):
    """
    Convierte propiedades anidadas en una lista plana.

    Ejemplo:

        user
          name
          address
            city

    Se documentará como:

        user
        user.name
        user.address
        user.address.city
    """

    result = []

    for prop in properties:

        name = getattr(
            prop,
            "name",
            ""
        )

        full_name = (
            f"{prefix}.{name}"
            if prefix
            else name
        )

        result.append(
            (
                full_name,
                prop
            )
        )

        children = getattr(
            prop,
            "properties",
            []
        )

        if children:

            result.extend(
                collect_nested_properties(
                    children,
                    full_name
                )
            )

        items = getattr(
            prop,
            "items",
            None
        )

        if items:

            item_name = (
                f"{full_name}[]"
            )

            result.append(
                (
                    item_name,
                    items
                )
            )

            item_children = getattr(
                items,
                "properties",
                []
            )

            if item_children:

                result.extend(
                    collect_nested_properties(
                        item_children,
                        item_name
                    )
                )

    return result


# ============================================================
# TABLA DE SCHEMA
# ============================================================

def add_schema_properties_table(
    document,
    schema,
    title="Campos"
):
    """
    Agrega una tabla con las propiedades del schema.

    La tabla contiene únicamente:

        Nombre
        Tipo
        Tamaño
        Obligatorio
        Descripción
    """

    if not schema:
        return

    properties = getattr(
        schema,
        "properties",
        []
    )

    if not properties:
        return

    document.add_heading(
        title,
        level=3
    )

    # --------------------------------------------------------
    # Propiedades principales + anidadas
    # --------------------------------------------------------

    flattened = collect_nested_properties(
        properties
    )

    # --------------------------------------------------------
    # Crear una copia de propiedades modificando solamente
    # el nombre mostrado.
    # --------------------------------------------------------

    table_properties = []

    for full_name, prop in flattened:

        class PropertyWrapper:

            pass

        wrapper = PropertyWrapper()

        wrapper.name = full_name
        wrapper.type = getattr(
            prop,
            "type",
            "object"
        )

        wrapper.required = getattr(
            prop,
            "required",
            False
        )

        wrapper.description = getattr(
            prop,
            "description",
            ""
        )

        wrapper.format = getattr(
            prop,
            "format",
            None
        )

        wrapper.example = getattr(
            prop,
            "example",
            None
        )

        wrapper.enum = getattr(
            prop,
            "enum",
            []
        )

        wrapper.reference = getattr(
            prop,
            "reference",
            None
        )

        # Intentamos copiar información de tamaño
        wrapper.max_length = getattr(
            prop,
            "max_length",
            None
        )

        wrapper.min_length = getattr(
            prop,
            "min_length",
            None
        )

        wrapper.max_items = getattr(
            prop,
            "max_items",
            None
        )

        wrapper.min_items = getattr(
            prop,
            "min_items",
            None
        )

        wrapper.maximum = getattr(
            prop,
            "maximum",
            None
        )

        wrapper.minimum = getattr(
            prop,
            "minimum",
            None
        )

        table_properties.append(
            wrapper
        )

    create_fields_table(
        document,
        table_properties
    )


# ============================================================
# DETALLE DEL SCHEMA
# ============================================================

def add_schema_detail(
    document,
    schema,
    title="Schema"
):
    """
    Agrega información básica del schema
    y la tabla de campos.
    """

    if not schema:
        return

    document.add_heading(
        title,
        level=3
    )

    name = getattr(
        schema,
        "name",
        None
    )

    schema_type = getattr(
        schema,
        "type",
        None
    )

    description = getattr(
        schema,
        "description",
        None
    )

    reference = getattr(
        schema,
        "reference",
        None
    )

    if name:

        document.add_paragraph(
            f"Nombre: {name}"
        )

    if schema_type:

        document.add_paragraph(
            f"Tipo: {schema_type}"
        )

    if reference:

        document.add_paragraph(
            f"Referencia: {reference}"
        )

    if description:

        document.add_paragraph(
            f"Descripción: {description}"
        )

    # --------------------------------------------------------
    # Ejemplo
    # --------------------------------------------------------

    example = getattr(
        schema,
        "example",
        None
    )

    if example is not None:

        document.add_paragraph(
            "Ejemplo:"
        )

        example_paragraph = (
            document.add_paragraph()
        )

        run = example_paragraph.add_run(
            format_value(example)
        )

        run.font.name = "Consolas"
        run.font.size = Pt(9)

    # --------------------------------------------------------
    # Tabla de campos
    # --------------------------------------------------------

    add_schema_properties_table(
        document,
        schema,
        title="Campos"
    )


# ============================================================
# PARÁMETROS
# ============================================================

def add_parameters(
    document,
    parameters
):
    """
    Agrega los parámetros del endpoint.

    COLUMNAS:

        Nombre
        Tipo
        Tamaño
        Obligatorio
        Descripción
    """

    document.add_heading(
        "Parámetros",
        level=2
    )

    if not parameters:

        document.add_paragraph(
            "No tiene parámetros."
        )

        return

    properties = []

    for parameter in parameters:

        class ParameterWrapper:

            pass

        wrapper = ParameterWrapper()

        wrapper.name = getattr(
            parameter,
            "name",
            ""
        )

        wrapper.required = getattr(
            parameter,
            "required",
            False
        )

        wrapper.description = getattr(
            parameter,
            "description",
            ""
        )

        schema = getattr(
            parameter,
            "schema",
            {}
        )

        if not isinstance(
            schema,
            dict
        ):
            schema = {}

        wrapper.type = schema.get(
            "type",
            "string"
        )

        wrapper.max_length = schema.get(
            "maxLength"
        )

        wrapper.min_length = schema.get(
            "minLength"
        )

        wrapper.max_items = schema.get(
            "maxItems"
        )

        wrapper.min_items = schema.get(
            "minItems"
        )

        wrapper.maximum = schema.get(
            "maximum"
        )

        wrapper.minimum = schema.get(
            "minimum"
        )

        properties.append(
            wrapper
        )

    create_fields_table(
        document,
        properties
    )


# ============================================================
# REQUEST BODY
# ============================================================

def add_request_body(
    document,
    request_body
):
    """
    Documenta el Request Body.
    """

    if not request_body:
        return

    document.add_heading(
        "Request Body",
        level=2
    )

    required = (
        "Sí"
        if getattr(
            request_body,
            "required",
            False
        )
        else "No"
    )

    document.add_paragraph(
        f"Obligatorio: {required}"
    )

    content = getattr(
        request_body,
        "content",
        {}
    )

    if not content:

        document.add_paragraph(
            "No tiene contenido definido."
        )

        return

    for content_type, schema in content.items():

        document.add_heading(
            f"Content-Type: {content_type}",
            level=3
        )

        add_schema_detail(
            document,
            schema,
            title="Campos del Request Body"
        )


# ============================================================
# RESPUESTAS
# ============================================================

def add_responses(
    document,
    responses
):
    """
    Documenta las respuestas del endpoint.

    Las tablas de campos utilizan:

        Nombre
        Tipo
        Tamaño
        Obligatorio
        Descripción
    """

    document.add_heading(
        "Respuestas",
        level=2
    )

    if not responses:

        document.add_paragraph(
            "No tiene respuestas definidas."
        )

        return

    for response in responses:

        status_code = getattr(
            response,
            "status_code",
            ""
        )

        description = getattr(
            response,
            "description",
            ""
        )

        document.add_heading(
            f"HTTP {status_code}",
            level=3
        )

        document.add_paragraph(
            "Descripción: "
            + (
                description
                or "Sin descripción"
            )
        )

        content = getattr(
            response,
            "content",
            {}
        )

        if not content:

            document.add_paragraph(
                "Sin contenido."
            )

            continue

        for content_type, schema in content.items():

            document.add_heading(
                f"Content-Type: {content_type}",
                level=4
            )

            add_schema_detail(
                document,
                schema,
                title="Campos de respuesta"
            )


# ============================================================
# DETALLE DEL ENDPOINT
# ============================================================

def add_endpoint_detail(
    document,
    number,
    endpoint
):
    """
    Agrega toda la documentación de un endpoint.
    """

    document.add_heading(
        f"{number}. "
        f"{str(endpoint.method).upper()} "
        f"{endpoint.path}",
        level=1
    )

    # --------------------------------------------------------
    # Información general
    # --------------------------------------------------------

    summary = (
        endpoint.summary
        or "Sin resumen"
    )

    description = (
        endpoint.description
        or "Sin descripción"
    )

    document.add_paragraph(
        f"Resumen: {summary}"
    )

    document.add_paragraph(
        f"Descripción: {description}"
    )

    # --------------------------------------------------------
    # Parámetros
    # --------------------------------------------------------

    add_parameters(
        document,
        getattr(
            endpoint,
            "parameters",
            []
        )
    )

    # --------------------------------------------------------
    # Request Body
    # --------------------------------------------------------

    add_request_body(
        document,
        getattr(
            endpoint,
            "request_body",
            None
        )
    )

    # --------------------------------------------------------
    # Responses
    # --------------------------------------------------------

    add_responses(
        document,
        getattr(
            endpoint,
            "responses",
            []
        )
    )

    document.add_paragraph()


# ============================================================
# GENERAR WORD
# ============================================================

def generate_word(
    endpoints,
    document_data,
    output="documentacion_api.docx"
):
    """
    Genera el documento Word completo.

    Parámetros:

        endpoints:
            Lista de objetos Endpoint.

        document_data:
            Documento Swagger/OpenAPI original.

        output:
            Nombre/ruta del archivo Word.
    """

    document = Document()

    # ========================================================
    # CONFIGURACIÓN DE PÁGINA
    # ========================================================

    section = document.sections[0]

    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)

    # ========================================================
    # TÍTULO
    # ========================================================

    info = document_data.get(
        "info",
        {}
    )

    add_title(
        document,
        info.get(
            "title",
            "Documentación API"
        )
    )

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    paragraph.add_run(
        "Documentación generada automáticamente "
        "a partir de Swagger / OpenAPI."
    )

    # ========================================================
    # INFORMACIÓN GENERAL
    # ========================================================

    add_general_information(
        document,
        document_data
    )

    # ========================================================
    # RESUMEN
    # ========================================================

    add_endpoint_summary(
        document,
        endpoints
    )

    # ========================================================
    # DOCUMENTACIÓN DE ENDPOINTS
    # ========================================================

    document.add_heading(
        "3. Documentación de endpoints",
        level=1
    )

    for counter, endpoint in enumerate(
        endpoints,
        start=1
    ):

        add_endpoint_detail(
            document=document,
            number=counter,
            endpoint=endpoint
        )

    # ========================================================
    # GUARDAR
    # ========================================================

    document.save(
        output
    )

    print(
        f"\nWord generado correctamente: {output}"
    )