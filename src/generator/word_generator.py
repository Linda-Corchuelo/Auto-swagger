import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from config import WORD_TEMPLATE


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
    """Aplica anchos predefinidos a cada columna de la tabla."""
    for row in table.rows:
        for i, width in enumerate(widths_inches):
            if i < len(row.cells):
                set_cell_width(row.cells[i], width)


def format_value(value: Any) -> str:
    """Convierte cualquier valor u objeto Python a string legible."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False, indent=2)
        except Exception:
            return str(value)
    return str(value)


def generate_sample_json(schema_or_prop: Any) -> Any:
    """
    Construye un diccionario/valor JSON representativo a partir
    del schema o propiedad OpenAPI cuando no hay example explícito.
    """
    if not schema_or_prop:
        return None

    explicit_example = getattr(schema_or_prop, "example", None)
    if explicit_example is not None:
        return explicit_example

    prop_type = getattr(schema_or_prop, "type", "object")

    if prop_type == "object":
        properties = getattr(schema_or_prop, "properties", [])
        if not properties:
            return {}
        result = {}
        for prop in properties:
            result[prop.name] = generate_sample_json(prop)
        return result

    elif prop_type == "array":
        items = getattr(schema_or_prop, "items", None)
        if items:
            return [generate_sample_json(items)]
        return []

    elif prop_type == "string":
        fmt = getattr(schema_or_prop, "format", "")
        enum_vals = getattr(schema_or_prop, "enum", [])
        if enum_vals:
            return enum_vals[0]
        if fmt == "date-time":
            return "2026-08-24T12:00:00Z"
        elif fmt == "date":
            return "2026-08-24"
        elif fmt == "email":
            return "usuario@ejemplo.com"
        elif fmt == "uuid":
            return "123e4567-e89b-12d3-a456-426614174000"
        return "string"

    elif prop_type in ("integer", "number"):
        fmt = getattr(schema_or_prop, "format", "")
        if fmt == "int64":
            return 1001
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

    # Bordes finos de la celda
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
    """Genera la tabla de parámetros de consulta, ruta o cabecera."""
    if not parameters:
        return

    table = document.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Nombre", "Ubicación", "Tipo", "Obligatorio", "Descripción"]
    widths = [1.5, 1.0, 1.0, 0.9, 2.1]

    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
        set_cell_text_bold(cell)
        set_cell_shading(cell, "D9EAF7")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    for parameter in parameters:
        row = table.add_row().cells
        row[0].text = parameter.name
        row[1].text = parameter.location
        row[2].text = parameter.type or "string"
        row[3].text = "Sí" if parameter.required else "No"
        row[4].text = parameter.description or "Sin descripción"

    set_table_col_widths(table, widths)
    document.add_paragraph()


def collect_schema_rows(properties: List[Any], prefix: str = "") -> List[Dict[str, str]]:
    """Extrae filas aplanadas con nombres jerárquicos para tablas de schema."""
    rows = []
    for prop in properties:
        full_name = f"{prefix}.{prop.name}" if prefix else prop.name
        rows.append({
            "name": full_name,
            "type": prop.type or "object",
            "format": prop.format or "-",
            "required": "Sí" if prop.required else "No",
            "description": prop.description or "-",
        })

        if prop.properties:
            rows.extend(collect_schema_rows(prop.properties, full_name))
        elif prop.items and getattr(prop.items, "properties", None):
            rows.extend(collect_schema_rows(prop.items.properties, f"{full_name}[]"))
    return rows


def add_schema_properties_table(document, schema: Any) -> None:
    """Genera la tabla con las propiedades de un schema OpenAPI."""
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

    headers = ["Nombre", "Tipo", "Formato / Tamaño", "Obligatorio", "Descripción"]
    widths = [1.8, 1.0, 1.0, 0.9, 1.8]

    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
        set_cell_text_bold(cell)
        set_cell_shading(cell, "D9EAF7")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    for row_info in rows_data:
        row = table.add_row().cells
        row[0].text = row_info["name"]
        row[1].text = row_info["type"]
        row[2].text = row_info["format"]
        row[3].text = row_info["required"]
        row[4].text = row_info["description"]

    set_table_col_widths(table, widths)
    document.add_paragraph()


def add_status_code_table(document, responses: List[Any]) -> None:
    """Genera la tabla de códigos de estado HTTP (statusCode)."""
    if not responses:
        return

    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Código", "Descripción"]
    widths = [1.2, 5.3]

    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
        set_cell_text_bold(cell)
        set_cell_shading(cell, "D9EAF7")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    for resp in responses:
        row = table.add_row().cells
        row[0].text = str(resp.status_code)
        row[1].text = resp.description or "Sin descripción"

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
    la estructura del Acuerdo de Interfaz institucional.
    """
    endpoint_name = endpoint.summary or endpoint.path
    heading_title = f"4.{index} Endpoint {endpoint_name}" if is_template else f"{index}. {endpoint.method} {endpoint.path}"

    document.add_heading(heading_title, level=2)

    # 1. Descripción general y verbo
    p_desc = document.add_paragraph()
    desc_text = endpoint.description or endpoint.summary or f"Operación {endpoint.method} para {endpoint.path}"
    p_desc.add_run(f"Descripción: {desc_text}\n")
    p_desc.add_run(
        f"Para la invocación del endpoint se debe realizar una petición de tipo "
        f"{endpoint.method} al servicio web con la siguiente ruta:"
    )

    # 2. URL de Pruebas
    p_url = document.add_paragraph()
    full_url = f"{base_url.rstrip('/')}{endpoint.path}" if base_url else endpoint.path
    run_url_title = p_url.add_run("URL Pruebas:\n")
    run_url_title.bold = True
    p_url.add_run(f"QA: {full_url}")

    # 3. Parámetros de Petición (Query, Path, Header)
    if endpoint.parameters:
        document.add_heading("Parámetros", level=3)
        p_param = document.add_paragraph()
        p_param.add_run("A continuación se describen los parámetros de la petición:")
        add_parameters_table(document, endpoint.parameters)

    # 4. Request Body
    if endpoint.request_body and endpoint.request_body.content:
        document.add_heading("Parámetros del Request Body", level=3)
        p_rb = document.add_paragraph()
        p_rb.add_run("Describa los parámetros del Objeto JSON que debe cumplir con los siguientes atributos:")

        # Tomar el schema principal (normalmente application/json)
        first_content = next(iter(endpoint.request_body.content.values()))
        add_schema_properties_table(document, first_content)

        document.add_heading("Ejemplo JSON de entrada", level=3)
        document.add_paragraph("Ejemplo de carga útil (payload) correspondiente al consumo del endpoint:")
        sample_input = generate_sample_json(first_content)
        add_code_block(document, sample_input)

    # 5. Respuestas del Servicio
    if endpoint.responses:
        document.add_heading("Respuesta", level=3)
        document.add_paragraph("Estructura de datos retornada por la operación del endpoint:")

        # Buscar la primera respuesta con schema (preferentemente 200 o 201)
        success_response = next(
            (r for r in endpoint.responses if r.status_code.startswith("2") and r.content),
            None,
        ) or next((r for r in endpoint.responses if r.content), None)

        if success_response and success_response.content:
            resp_schema = next(iter(success_response.content.values()))
            add_schema_properties_table(document, resp_schema)

            document.add_heading("Ejemplo JSON de salida", level=3)
            document.add_paragraph(f"Ejemplo de la respuesta obtenida (HTTP {success_response.status_code}):")
            sample_output = generate_sample_json(resp_schema)
            add_code_block(document, sample_output)

        # 6. Tabla de códigos de estado HTTP
        document.add_heading("Valores para el atributo de statusCode", level=3)
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

        # Configurar márgenes
        section = document.sections[0]
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

        # Título
        info = document_data.get("info", {})
        title_p = document.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_p.add_run(info.get("title", "Documentación de API"))
        run.bold = True
        run.font.size = Pt(20)

        # Resumen general
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
            set_cell_shading(row.cells[0], "D9EAF7")
        document.add_paragraph()

        # Endpoints
        document.add_heading("2. Operaciones del Servicio", level=1)
        for counter, endpoint in enumerate(endpoints, start=1):
            add_endpoint_section(
                document=document,
                endpoint=endpoint,
                index=counter,
                base_url=base_url,
                is_template=False,
            )

    document.save(str(output_path))
    print(f"\nDocumento Word generado exitosamente en: {output_path}")