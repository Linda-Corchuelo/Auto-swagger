import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from config import WORD_TEMPLATE, PARAMETER_CONFIG


# ============================================================
# DICCIONARIO DE DESCRIPCIONES DE CÓDIGOS DE ESTADO
# ============================================================

STANDARD_STATUS_CODES: Dict[str, str] = {
    "200": "La solicitud fue procesada correctamente.",
    "201": "El recurso fue creado exitosamente.",
    "204": "Petición procesada correctamente sin contenido de respuesta.",
    "400": "La solicitud contiene datos inválidos o incompletos.",
    "401": "No autorizado o token de sesión inválido / expirado.",
    "403": "Acceso denegado / permisos insuficientes.",
    "404": "El recurso solicitado no fue encontrado.",
    "422": "Error por parte del usuario o datos no procesables.",
    "500": "Error interno en el servidor.",
}

# MEDIDAS ESTÁNDAR DE TABLAS 
# ============================================================
# Nombre (3.57 cm), Tipo (3.10 cm), Tamaño (3.11 cm), Obligatorio (3.57 cm), Descripción (3.65 cm)
TABLE_5_COL_WIDTHS = [
    3.57 / 2.54,
    3.30 / 2.54,
    3.57 / 2.54,
    4.00 / 2.54,
    4.50 / 2.54,
]
# ============================================================
# CONFIGURACIÓN DE ESTILOS DEL DOCUMENTO
# ============================================================

def _configure_document_styles(document) -> None:
    """
    Configura tipografía Arial, interlineado 1.15 y espaciado
    de 6pt después de cada párrafo para todo el documento.
    """
    styles = document.styles

    # ── Estilo Normal (base de todo el documento)
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)
    pf = normal.paragraph_format
    pf.line_spacing = 1.15
    pf.space_after = Pt(6)
    pf.space_before = Pt(0)

    # ── Estilos de encabezado heredan Arial
    for level in range(1, 5):
        style_name = f"Heading {level}"
        if style_name in styles:
            heading = styles[style_name]
            heading.font.name = "Arial"
            heading.paragraph_format.line_spacing = 1.15
            heading.paragraph_format.space_after = Pt(6)
            heading.paragraph_format.space_before = Pt(12)


# ============================================================
# UTILIDADES DE FORMATO WORD
# ============================================================

def set_cell_shading(cell, fill_hex: str) -> None:
    """Aplica color de fondo hexadecimal a una celda de tabla."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill_hex.replace("#", ""))
    tc_pr.append(shd)


def set_cell_text_bold(cell) -> None:
    """Pone en negrita todo el texto de los párrafos dentro de una celda."""
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True


def set_cell_width(cell, width_inches: float) -> None:
    """Establece el ancho exacto de una celda en pulgadas."""
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width_inches * 1440)))
    tc_w.set(qn("w:type"), "dxa")


def set_table_col_widths(table, widths_inches: List[float]) -> None:
    """
    Aplica anchos predefinidos a cada columna desactivando el reajuste
    automático de Microsoft Word para forzar el tamaño exacto.
    """
    # 1. Desactivar autofit en la tabla
    table.autofit = False
    
    # 2. Configurar layout de tabla 'fixed' a nivel de XML
    tblPr = table._tbl.tblPr
    layout = tblPr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tblPr.append(layout)
    layout.set(qn("w:type"), "fixed")

    # 3. Aplicar anchos celda por celda y a nivel de fila (cantSplit / cantSplit)
    for row in table.rows:
        # Evitar que la fila se rompa entre páginas si se desea consistencia
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        
        for i, width in enumerate(widths_inches):
            if i < len(row.cells):
                cell = row.cells[i]
                set_cell_width(cell, width)

def format_type_display(raw_type: Optional[str]) -> str:
    """Formatea el tipo OpenAPI a la nomenclatura corporativa (String, Number, Object, Array, Boolean)."""
    if not raw_type:
        return "String"
    t = str(raw_type).strip().lower()
    if "int" in t or t in ("integer", "number", "float", "double"):
        return "Number"
    if t == "string":
        return "String"
    if t in ("boolean", "bool"):
        return "Boolean"
    if t == "array":
        return "Array"
    if t == "object":
        return "Object"
    return str(raw_type).capitalize()


def format_size_display(prop: Any) -> str:
    """
    Calcula el tamaño del parámetro o propiedad siguiendo
    la prioridad:

    1. Si PARAMETER_CONFIG define "size" fijo → usarlo (ej. X-Ct → Variable)
    2. Si el $ref contiene "encrypted" → "Variable"
    3. Si Swagger tiene minLength/maxLength → usar Swagger
    4. Si PARAMETER_CONFIG tiene min/max → usar config
    5. Si no existe en ninguno → "No especificado"
    """
    if not prop:
        return "No especificado"

    param_name = getattr(prop, "name", "")

    # ========================================================
    # PARAMETER INFO
    # ========================================================
    schema = getattr(prop, "schema", None)
    if isinstance(schema, dict):

        # 0. Config con tamaño fijo (ej. X-Ct → Variable)
        config = PARAMETER_CONFIG.get(param_name)
        if config and "size" in config:
            return config["size"]

        # 1. Detectar encrypted desde $ref
        ref = getattr(prop, "reference", None) or ""
        if "encrypted" in ref.lower():
            return "Variable"

        # 2. Swagger minLength / maxLength
        min_l = schema.get("minLength")
        max_l = schema.get("maxLength")
        if min_l is not None or max_l is not None:
            if min_l is not None and max_l is not None:
                return f"{min_l} - {max_l}"
            if max_l is not None:
                return str(max_l)
            if min_l is not None:
                return f"Mín. {min_l}"

        # 3. PARAMETER_CONFIG min/max
        if config:
            return f"{config['min']} - {config['max']}"

        # 4. No especificado
        return "No especificado"

    # ========================================================
    # SCHEMA PROPERTY
    # ========================================================

    # 0. Config con tamaño fijo
    config = PARAMETER_CONFIG.get(param_name)
    if config and "size" in config:
        return config["size"]

    # 1. Detectar encrypted desde reference o is_encrypted
    prop_ref = getattr(prop, "reference", None) or ""
    if "encrypted" in prop_ref.lower():
        return "Variable"
    if getattr(prop, "is_encrypted", False):
        return "Variable"

    # 2. Swagger minLength / maxLength (propiedad directa)
    min_l = getattr(prop, "min_length", None)
    max_l = getattr(prop, "max_length", None)
    if min_l is not None or max_l is not None:
        if min_l is not None and max_l is not None:
            return f"{min_l} - {max_l}"
        if max_l is not None:
            return str(max_l)
        if min_l is not None:
            return f"Mín. {min_l}"

    # 3. PARAMETER_CONFIG min/max
    if config:
        return f"{config['min']} - {config['max']}"

    # 4. No especificado
    return "No especificado"


def generate_sample_json(schema_or_prop: Any) -> Any:
    """
    Construye un payload JSON realista a partir del schema OpenAPI.

    Prioridad:
      1. `example` explícito en el schema raíz (más específico).
      2. Recorre cada propiedad recursivamente usando su propio `example`.
      3. Si la propiedad tampoco tiene `example`, usa inferencia por nombre/tipo.
    """
    if not schema_or_prop:
        return None

    # ── 1. Ejemplo explícito a nivel de schema raíz
    explicit_example = getattr(schema_or_prop, "example", None)
    if explicit_example is not None:
        return explicit_example

    prop_type = getattr(schema_or_prop, "type", "object")
    prop_name = getattr(schema_or_prop, "name", "").lower()

    # ── 2. Objeto: recorrer propiedades recursivamente
    if prop_type == "object":
        properties = getattr(schema_or_prop, "properties", [])
        if not properties:
            return {}
        result = {}
        for prop in properties:
            result[prop.name] = generate_sample_json(prop)
        return result

    # ── 3. Array: generar un elemento del array
    elif prop_type == "array":
        items = getattr(schema_or_prop, "items", None)
        if items:
            return [generate_sample_json(items)]
        return []

    # ── 4. Tipos escalares: usar inferencia contextual solo si no hay example
    elif prop_type == "string":
        fmt = str(getattr(schema_or_prop, "format", "") or "").lower()
        enum_vals = getattr(schema_or_prop, "enum", [])
        if enum_vals:
            return enum_vals[0]
        if "documenttype" in prop_name:
            return "CC"
        if "documentnumber" in prop_name:
            return "1098596254"
        if "email" in prop_name or fmt == "email":
            return "usuario@dominio.com"
        if "phone" in prop_name:
            return "+573001234567"
        if "username" in prop_name or fmt == "uuid":
            return "8468e428-8041-7053-0e44-215f7f112030"
        if "country" in prop_name:
            return "CO"
        if "firstname" in prop_name or "first_name" in prop_name:
            return "Juan"
        if "lastname" in prop_name or "last_name" in prop_name:
            return "Pérez"
        if "nickname" in prop_name:
            return "juanp"
        if "password" in prop_name:
            return "P@ssw0rd123"
        if "code" in prop_name:
            return "US01"
        if "message" in prop_name:
            return "Operación procesada correctamente"
        if "status" in prop_name:
            return "active"
        if fmt == "date-time":
            return "2026-08-24T12:00:00Z"
        if fmt == "date":
            return "2026-08-24"
        if fmt == "byte" or fmt == "binary" or "encoded" in prop_name or "base64" in prop_name:
            return "U2FsdGVkX19v8+3mN3kL9y2y9..."
        if "iv" in prop_name:
            return "dGhpcyBpcyBhbiBpdiA="
        return "string"

    elif prop_type in ("integer", "number"):
        if "statuscode" in prop_name:
            return 200
        if "biocode" in prop_name or "bio_code" in prop_name:
            return 30185
        return 1

    elif prop_type == "boolean":
        return True

    return "string"



# ============================================================
# COMPONENTES DE DOCUMENTO WORD
# ============================================================

def add_code_block(document, code_data: Any) -> None:
    """
    Inserta un bloque de código estilizado (caja con fondo gris claro,
    borde sutil y fuente Consolas).
    """
    if code_data is None:
        return

    if isinstance(code_data, (dict, list)):
        code_text = json.dumps(code_data, ensure_ascii=False, indent=2)
    else:
        code_text = str(code_data).strip()

    if not code_text:
        return

    table = document.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    cell = table.rows[0].cells[0]
    set_cell_shading(cell, "F8F9FA")
    set_cell_width(cell, 6.5)

    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for b_name in ("top", "left", "bottom", "right"):
        border = OxmlElement(f"w:{b_name}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "4")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "D0D5DD")
        borders.append(border)
    tc_pr.append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15

    run = p.add_run(code_text)
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(40, 40, 40)

    document.add_paragraph()


def add_parameters_table(document, parameters: List[Any]) -> None:
    """Genera la tabla de 5 columnas para parámetros de consulta, ruta o cabecera."""
    if not parameters:
        return

    table = document.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Nombre", "Tipo", "Tamaño", "Obligatorio", "Descripción"]
    widths = TABLE_5_COL_WIDTHS

    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
        set_cell_text_bold(cell)
        set_cell_shading(cell, "000000")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.color.rgb = RGBColor(255, 255, 255)
    for parameter in parameters:
        row = table.add_row().cells
        row[0].text = parameter.name
        row[1].text = format_type_display(parameter.type)
        row[2].text = format_size_display(parameter)
        row[3].text = "Sí" if parameter.required else "No"
        desc = parameter.description or f"Parámetro {parameter.location} de la petición."
        row[4].text = desc

    set_table_col_widths(table, widths)
    document.add_paragraph()


def collect_schema_rows(properties: List[Any], prefix: str = "") -> List[Dict[str, str]]:
    """Extrae filas aplanadas con nombres jerárquicos y atributos para tablas de schema."""
    rows = []
    for prop in properties:
        full_name = f"{prefix}.{prop.name}" if prefix else prop.name
        desc = prop.description
        if not desc:
            p_lower = prop.name.lower()
            if "statuscode" in p_lower:
                desc = "Código de estado HTTP de la operación."
            elif "message" in p_lower:
                desc = "Mensaje descriptivo del resultado de la operación."
            elif "code" in p_lower:
                desc = "Código interno de respuesta del servicio."
            elif "users" in p_lower:
                desc = "Lista de usuarios."
            elif "user" in p_lower:
                desc = "Objeto con los datos del usuario."
            elif "data" in p_lower:
                desc = "Objeto con la información registrada/actualizada"
            elif "email" in p_lower:
                desc = "Correo electrónico registrado del usuario."
            elif "phone" in p_lower:
                desc = "Número de teléfono en formato internacional (E.164)."
            elif "document" in p_lower:
                desc = "Número o tipo de documento del usuario."
            elif "username" in p_lower:
                desc = "Identificador único del usuario (UUID)."
            else:
                desc = "Sin descripción"

        rows.append({
            "name": full_name,
            "type": format_type_display(prop.type),
            "size": format_size_display(prop),
            "required": "Sí" if prop.required else "No",
            "description": desc,
        })

        if prop.properties:
            rows.extend(collect_schema_rows(prop.properties, full_name))
        elif prop.items and getattr(prop.items, "properties", None):
            rows.extend(collect_schema_rows(prop.items.properties, f"{full_name}[]"))
    return rows


def add_schema_properties_table(document, schema: Any) -> None:
    """Genera la tabla con las propiedades de un schema OpenAPI (5 columnas)."""
    if not schema:
        return

    properties = getattr(schema, "properties", [])
    if not properties:
        return

    rows_data = collect_schema_rows(properties)
    if not rows_data:
        return

    table = document.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Nombre", "Tipo", "Tamaño", "Obligatorio", "Descripción"]
    widths = TABLE_5_COL_WIDTHS

    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
        set_cell_text_bold(cell)
        set_cell_shading(cell, "000000")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.color.rgb = RGBColor(255, 255, 255)
    for row_info in rows_data:
        row = table.add_row().cells
        row[0].text = row_info["name"]
        row[1].text = row_info["type"]
        row[2].text = row_info["size"]
        row[3].text = row_info["required"]
        row[4].text = row_info["description"]

    set_table_col_widths(table, widths)
    document.add_paragraph()


def add_status_code_table(document, responses: List[Any]) -> None:
    """Genera la tabla de códigos de estado HTTP (statusCode) con descripciones completas."""
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Código", "Descripción"]
    widths = [1.2, 5.3]

    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
        set_cell_text_bold(cell)
        set_cell_shading(cell, "000000")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.color.rgb = RGBColor(255, 255, 255)
    # Extraer códigos definidos en el Swagger
    rendered_codes = {}
    for resp in (responses or []):
        code_str = str(resp.status_code)
        desc = resp.description or STANDARD_STATUS_CODES.get(code_str, "Respuesta de la operación.")
        rendered_codes[code_str] = desc

    # Asegurar códigos estándar comunes (200, 400, 404, 500, 422)
    for code, default_desc in STANDARD_STATUS_CODES.items():
        if code in ("200", "400", "404", "500", "422") and code not in rendered_codes:
            rendered_codes[code] = default_desc

    # Ordenar códigos numéricamente
    sorted_codes = sorted(
        rendered_codes.items(),
        key=lambda item: int(item[0]) if item[0].isdigit() else 999
    )

    for code_str, desc_text in sorted_codes:
        row = table.add_row().cells
        row[0].text = code_str
        row[1].text = desc_text

    set_table_col_widths(table, widths)
    document.add_paragraph()


# ============================================================
# GENERACIÓN DE ENDPOINT SEGÚN ESTRUCTURA CORPORATIVA
# ============================================================

def add_endpoint_section(
    document,
    endpoint: Any,
    index: int,
    base_url: str = "",
    is_template: bool = True,
) -> None:
    """
    Agrega la documentación detallada de un endpoint siguiendo
    la estructura y redacción del estándar corporativo institucional.

    NOTA: Los encabezados NO llevan prefijo numérico manual porque el
    estilo 'Heading 2'/'Heading 3' de la plantilla ya tiene numeración
    automática (numId=10) que genera '3.1', '3.1.1', etc.
    Si se usa modo standalone (is_template=False) sí se incluye prefijo
    porque ese documento no tiene numeración automática configurada.
    """
    endpoint_slug = endpoint.path.strip("/")
    endpoint_summary = endpoint.summary or endpoint_slug

    if is_template:
        h2_title = f"Endpoint {endpoint_slug} ({endpoint_summary})"
        h3_params       = "Parámetros de entrada"
        h3_ejemplo_in   = "Ejemplo JSON de entrada"
        h3_ejemplo_out  = "Ejemplo JSON de salida"
        h3_respuesta    = "Respuesta"
        h3_status       = "Valores para el atributo de statusCode"
    else:
        chapter_prefix = "1"
        h2_title        = f"{chapter_prefix}.{index} Endpoint {endpoint_slug} ({endpoint_summary})"
        h3_params       = f"{chapter_prefix}.{index}.1 Parámetros de entrada"
        h3_ejemplo_in   = f"{chapter_prefix}.{index}.2 Ejemplo JSON de entrada"
        h3_ejemplo_out  = f"{chapter_prefix}.{index}.3 Ejemplo JSON de salida"
        h3_respuesta    = f"{chapter_prefix}.{index}.4 Respuesta"
        h3_status       = f"{chapter_prefix}.{index}.5 Valores para el atributo de statusCode"


    # ── Título del Endpoint (Heading 2)
    document.add_heading(h2_title, level=2)

    # ── Objetivo
    p_obj = document.add_paragraph()
    r_obj_title = p_obj.add_run("Objetivo: ")
    r_obj_title.bold = True
    obj_text = endpoint.description or f"Petición encargada de realizar las acciones de {endpoint_summary.lower()}."
    p_obj.add_run(obj_text)

    # ── Método
    p_met = document.add_paragraph()
    r_met_title = p_met.add_run("Método: ")
    r_met_title.bold = True
    p_met.add_run(
        f"se utiliza el método {endpoint.method}, este método realiza la transacción para "
        f"{endpoint_summary.lower()}."
    )

    # ── URL
    p_url = document.add_paragraph()
    r_url_title = p_url.add_run("URL: ")
    r_url_title.bold = True
    p_url.add_run(f"QA: {{{{baseUrl}}}}/{endpoint_slug}")

    # ── Parámetros de Entrada (Heading 3)
    has_rb = bool(endpoint.request_body and endpoint.request_body.content)
    has_params = bool(endpoint.parameters)

    document.add_heading(h3_params, level=3)

    if has_rb:
        p_intro = document.add_paragraph()
        p_intro.add_run("Los parámetros de entrada del objeto JSON deben cumplir con los siguientes atributos:")
        first_rb_content = next(iter(endpoint.request_body.content.values()))
        add_schema_properties_table(document, first_rb_content)

        if has_params:
            p_extra = document.add_paragraph()
            p_extra.add_run("Parámetros de cabecera / consulta requeridos:")
            add_parameters_table(document, endpoint.parameters)

    elif has_params:
        p_intro = document.add_paragraph()
        p_intro.add_run("Los parámetros de la petición deben cumplir con los siguientes atributos:")
        add_parameters_table(document, endpoint.parameters)
    else:
        p_intro = document.add_paragraph()
        p_intro.add_run("Este endpoint no requiere parámetros de entrada adicionales.")

    # ── Ejemplo JSON de entrada (Heading 3, solo si hay request body)
    if has_rb:
        document.add_heading(h3_ejemplo_in, level=3)
        document.add_paragraph("Ejemplo correspondiente al consumo del endpoint:")
        sample_input = generate_sample_json(first_rb_content)
        add_code_block(document, sample_input)

    # ── Respuesta: buscar schemas de éxito y error
    success_response = next(
        (r for r in endpoint.responses if r.status_code.startswith("2") and r.content),
        None,
    ) or next((r for r in endpoint.responses if r.content), None)

    resp_schema = None
    if success_response and success_response.content:
        resp_schema = next(iter(success_response.content.values()))

    error_response = next(
        (r for r in endpoint.responses if (r.status_code.startswith("4") or r.status_code.startswith("5")) and r.content),
        None,
    )

    # ── Ejemplo JSON de salida (Heading 3)
    if success_response and success_response.content:
        document.add_heading(h3_ejemplo_out, level=3)
        document.add_paragraph("Ejemplo de respuesta obtenida del endpoint:")
        sample_output = generate_sample_json(resp_schema)
        add_code_block(document, sample_output)

    # ── Respuesta (Heading 3)
    document.add_heading(h3_respuesta, level=3)
    document.add_paragraph("Información del JSON de respuesta correspondiente a la operación del endpoint:")

    if resp_schema:
        p_main = document.add_paragraph()
        r_bullet = p_main.add_run("· Respuesta exitosa")
        r_bullet.bold = True
        add_schema_properties_table(document, resp_schema)

    if error_response and error_response.content:
        p_err = document.add_paragraph()
        r_err_bullet = p_err.add_run("· En caso de error")
        r_err_bullet.bold = True
        err_schema = next(iter(error_response.content.values()))
        add_schema_properties_table(document, err_schema)

    # ── Valores para el atributo de statusCode (Heading 3)
    document.add_heading(h3_status, level=3)
    add_status_code_table(document, endpoint.responses)

    # Salto de página para el siguiente endpoint
    document.add_page_break()


# ============================================================
# LIMPIEZA DE PLANTILLA
# ============================================================

def clean_template_dummy_elements(document) -> None:
    """
    Elimina los endpoints de ejemplo preexistentes en la plantilla
    manteniendo la portada, control de cambios, índice, definiciones
    y el encabezado de 'Operaciones del servicio'.
    """
    target_idx = -1
    for i, child in enumerate(document._element.body):
        if child.tag.endswith("p"):
            p = document.paragraphs[0].__class__(child, document)
            if "A continuaci" in p.text and "operaciones disponibles" in p.text:
                target_idx = i
                break

    if target_idx == -1:
        return

    sect_pr = document._element.body.find(qn("w:sectPr"))
    elements_to_remove = []

    for i in range(target_idx + 1, len(document._element.body)):
        child = document._element.body[i]
        if child != sect_pr:
            elements_to_remove.append(child)

    for elem in elements_to_remove:
        document._element.body.remove(elem)


def update_template_metadata(document, document_data: Dict[str, Any]) -> None:
    """Actualiza títulos y referencias de API en la sección de Objetivo de la plantilla."""
    info = document_data.get("info", {})
    title = info.get("title", "la API")

    for p in document.paragraphs[:40]:
        if "Este documento pretende describir de manera" in p.text:
            p.text = (
                f"Este documento pretende describir de manera técnica y detallada "
                f"el consumo del servicio web de {title}."
            )
            break


# ============================================================
# FUNCIÓN PRINCIPAL DE GENERACIÓN
# ============================================================

def _set_update_fields_on_open(document) -> None:
    """
    Inserta <w:updateFields w:val='true'> en el settings.xml del documento
    para que Word actualice automáticamente todos los campos (incluida la
    Tabla de Contenido) la próxima vez que se abra el archivo.
    """
    try:
        settings = document.settings.element
        ns_w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        tag = f"{{{ns_w}}}updateFields"
        # Eliminar si ya existe
        for old in settings.findall(tag):
            settings.remove(old)
        upd = OxmlElement("w:updateFields")
        upd.set(qn("w:val"), "true")
        settings.append(upd)
    except Exception as e:
        print(f"[AVISO] No se pudo configurar updateFields: {e}")


def _update_toc_with_word(docx_path: Path) -> None:
    """
    Abre el documento con Microsoft Word via COM (win32com) para actualizar
    la Tabla de Contenido y luego lo guarda y cierra silenciosamente.
    Solo funciona en Windows con Word instalado.
    """
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        abs_path = str(docx_path.resolve())
        doc = word.Documents.Open(abs_path)
        doc.TablesOfContents(1).Update()
        doc.Save()
        doc.Close()
        word.Quit()
        pythoncom.CoUninitialize()
        print("Tabla de contenido actualizada exitosamente con Microsoft Word.")
    except ImportError:
        print("[INFO] pywin32 no instalado. La TOC se actualizará al abrir el archivo en Word (Ctrl+A → F9).")
    except Exception as e:
        print(f"[INFO] No se pudo actualizar la TOC automáticamente ({e}). Ábrela en Word y presiona Ctrl+A → F9.")


def generate_word(
    endpoints: List[Any],
    document_data: Dict[str, Any],
    output: Union[str, Path] = "output/documentacion_api.docx",
    template_path: Optional[Union[str, Path]] = None,
) -> None:
    """
    Genera la documentación Word (.docx).

    Si se proporciona una plantilla (o existe WORD_TEMPLATE), se basa
    en ella respetando los estándares institucionales de la empresa.
    En caso contrario, genera un documento independiente bien estructurado.
    """
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    template_file = Path(template_path) if template_path else Path(WORD_TEMPLATE)
    use_template = template_file.exists()

    servers = document_data.get("servers", [])
    base_url = servers[0].get("url", "") if servers else ""

    if use_template:
        print(f"Usando plantilla corporativa: {template_file}")
        document = Document(str(template_file))
        _configure_document_styles(document)
        update_template_metadata(document, document_data)
        clean_template_dummy_elements(document)

        for counter, endpoint in enumerate(endpoints, start=1):
            add_endpoint_section(
                document=document,
                endpoint=endpoint,
                index=counter,
                base_url=base_url,
                is_template=True,
            )
    else:
        print("Generando documento independiente desde cero...")
        document = Document()
        _configure_document_styles(document)

        section = document.sections[0]
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

        info = document_data.get("info", {})
        title_p = document.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_p.add_run(info.get("title", "Documentación de API"))
        run.bold = True
        run.font.size = Pt(20)

        document.add_heading("1. Información General", level=1)
        info_table = document.add_table(rows=3, cols=2)
        info_table.style = "Table Grid"
        info_data = [
            ("Título", info.get("title", "Sin información")),
            ("Versión", info.get("version", "1.0.0")),
            ("OpenAPI", document_data.get("openapi", "3.0.0")),
        ]
        for row, (k, v) in zip(info_table.rows, info_data):
            row.cells[0].text = k
            row.cells[1].text = str(v)
            set_cell_text_bold(row.cells[0])
            set_cell_shading(row.cells[0], "000000")
            for paragraph in row.cells[0].paragraphs:
                for run in paragraph.runs:
                    run.font.color.rgb = RGBColor(255, 255, 255)
        document.add_paragraph()

        document.add_heading("2. Operaciones del Servicio", level=1)
        for counter, endpoint in enumerate(endpoints, start=1):
            add_endpoint_section(
                document=document,
                endpoint=endpoint,
                index=counter,
                base_url=base_url,
                is_template=False,
            )

    # Forzar actualización de campos (TOC) al abrir el archivo en Word
    _set_update_fields_on_open(document)

    try:
        document.save(str(output_path))
        print(f"\nDocumento Word generado exitosamente en: {output_path}")
        # Intentar actualizar la TOC automáticamente vía COM (solo Windows + Word)
        _update_toc_with_word(output_path)
    except PermissionError:
        fallback_path = output_path.with_name(f"{output_path.stem}_nuevo{output_path.suffix}")
        _set_update_fields_on_open(document)
        document.save(str(fallback_path))
        print(f"\n[AVISO] El archivo original estaba abierto en Word. Se guardó exitosamente en: {fallback_path}")
        _update_toc_with_word(fallback_path)



