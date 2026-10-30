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
from swagger.endpoint import SchemaInfo, SchemaProperty


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


def _infer_type_from_value(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def generate_schema_from_json(json_data: Any, name: str = "response") -> SchemaInfo:
    """
    Convierte un objeto JSON en un SchemaInfo con properties,
    para poder generar la tabla de estructura con add_schema_properties_table.
    """
    if isinstance(json_data, dict):
        properties = []
        for key, value in json_data.items():
            properties.append(_json_value_to_schema_property(key, value))
        return SchemaInfo(name=name, type="object", properties=properties)
    elif isinstance(json_data, list) and json_data:
        item_prop = _json_value_to_schema_property("items", json_data[0])
        return SchemaInfo(name=name, type="array", items=item_prop)
    else:
        return SchemaInfo(name=name, type=_infer_type_from_value(json_data))


def _json_value_to_schema_property(name: str, value: Any) -> SchemaProperty:
    prop_type = _infer_type_from_value(value)

    if prop_type == "object":
        nested_props = []
        for k, v in value.items():
            nested_props.append(_json_value_to_schema_property(k, v))
        return SchemaProperty(name=name, type="object", properties=nested_props, required=True)

    if prop_type == "array":
        if value and isinstance(value[0], (dict, list)):
            items = _json_value_to_schema_property("items", value[0])
        else:
            items = SchemaProperty(name="items", type=_infer_type_from_value(value[0]) if value else "string")
        return SchemaProperty(name=name, type="array", items=items, required=True)

    return SchemaProperty(name=name, type=prop_type, required=True)


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


def add_parameters_table(document, parameters: List[Any], required_only: bool = False) -> None:
    """Genera la tabla de 5 columnas para parámetros de consulta, ruta o cabecera."""
    if not parameters:
        return

    if required_only:
        parameters = [p for p in parameters if p.required]

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
            elif "profilepictureurl" in p_lower:
                desc = "URL de la imagen de perfil del usuario."
            elif "presignedpostprofileimage" in p_lower:
                desc = "Datos necesarios para cargar la imagen de perfil."
            elif "message" in p_lower:
                desc = "Mensaje descriptivo del resultado de la operación."
            elif "phone_number" in p_lower:
                desc = "Número de teléfono en formato internacional (E.164)."
            elif "custom_documentnumber" in p_lower:
                desc = "Número de documento de identificación del usuario."
            elif "custom_documenttype" in p_lower:
                desc = "Tipo de documento de identificación del usuario."
            elif "custom_firstname" in p_lower:
                desc = "Nombre del usuario."
            elif "custom_lastname" in p_lower:
                desc = "Apellido del usuario."
            elif "custom_nickname" in p_lower:
                desc = "Nombre o alias utilizado para identificar al usuario."
            elif "custom_country" in p_lower:
                desc = "País asociado al usuario."
            elif "custom_documentcountry" in p_lower:
                desc = "País de emisión del documento de identificación del usuario."
            elif "code" in p_lower:
                desc = "Código interno de respuesta del servicio."
            elif "users" in p_lower:
                desc = "Lista de usuarios."
            elif "userrole" in p_lower:
                desc = "Objeto con los datos del usuario."
            elif "userid" in p_lower:
                desc = "Identificador único del usuario."
            elif "username" in p_lower:
                desc = "Identificador único del usuario."
            elif "user" in p_lower:
                desc = "Objeto con los datos del usuario."
            elif "amount" in p_lower:
                desc = "Valor o monto de la transacción."
            elif "buyer" in p_lower:
                desc = "Identificador o información del comprador asociado a la transacción."
            elif "seller" in p_lower:
                desc = "Identificador o información del vendedor asociado a la transacción."
            elif "pin" in p_lower:
                desc = "Código PIN utilizado para la validación o autenticación de la operación."
            elif "data" in p_lower:
                desc = "Objeto con la información registrada o actualizada."
            elif "email" in p_lower:
                desc = "Correo electrónico registrado del usuario."
            elif "phone" in p_lower:
                desc = "Número de teléfono en formato internacional (E.164)."
            elif "document" in p_lower:
                desc = "Número de documento del usuario."
            elif "role" in p_lower:
                desc = "Rol del usuario."
            elif "name" in p_lower:
                desc = "Nombre del usuario."
            elif "lastkey" in p_lower:
                desc = "Clave para paginación o siguiente bloque de resultados."
            elif "enabled" in p_lower:
                desc = "Indicador de estado del usuario."
            elif "newpassword" in p_lower:
                desc = "Nueva contraseña del usuario."
            elif "password" in p_lower:
                desc = "Contraseña de acceso del usuario."
            elif "url" in p_lower:
                desc = "URL del presigned post para la imagen de perfil."
            elif "hash" in p_lower:
                desc = "Identificador criptográfico de la transacción u operación realizada en la red blockchain."
            elif "kyc_level" in p_lower:
                desc = "Nivel de verificación de identidad (KYC)."
            elif "isacceptatdp" in p_lower:
                desc = "Indicador de aceptación de los términos y condiciones."
            elif "bio_status" in p_lower:
                desc = "Estado del perfil biométrico del usuario."
            elif "atdptype" in p_lower:
                desc = "Tipo de plantilla de verificación de identidad (ATDP)."
            elif "idtemplate" in p_lower:
                desc = "Identificador del usuario firmante de la plantilla (ATDP)."
            elif "notificationid" in p_lower:
                desc = "Identificador de la notificación."
            elif "notification" in p_lower:
                desc = "Objeto con la notificación registrada."
            elif "payload" in p_lower:
                desc = "Objeto con el contenido de la notificación."
            elif "title" in p_lower:
                desc = "Título de la notificación."
            elif "link" in p_lower:
                desc = "Enlace o URL incluido en la notificación."
            elif "read" in p_lower:
                desc = "Indicador de si la notificación fue leída."
            elif "timestamp" in p_lower:
                desc = "Fecha y hora del evento en formato ISO 8601."
            elif "success" in p_lower:
                desc = "Indicador de si la operación fue exitosa."
            elif "redirectto" in p_lower:
                desc = "Ruta de redirección después de la autenticación."
            elif "otp" in p_lower:
                desc = "Código de verificación de un solo uso (OTP)."
            elif "walletaddress" in p_lower:
                desc = "Dirección pública de la wallet en la red blockchain."
            elif "balancepol" in p_lower:
                desc = "Balance de la criptomoneda nativa POL."
            elif "balances" in p_lower:
                desc = "Lista de balances por símbolo."
            elif "tokensbalance" in p_lower:
                desc = "Cantidad total de tokens poseídos."
            elif "balance" in p_lower:
                desc = "Monto disponible del activo."
            elif "symbol" in p_lower:
                desc = "Símbolo o ticker del activo."
            elif "stablecoin" in p_lower:
                desc = "Stablecoin asociada al token."
            elif "tokenpriceinusd" in p_lower:
                desc = "Precio del token en dólares (USD)."
            elif "totaltokens" in p_lower:
                desc = "Total de tokens disponibles."
            elif "detailtokens" in p_lower:
                desc = "Detalle de los tokens (vaults) del usuario."
            elif "features" in p_lower:
                desc = "Características adicionales del token."
            elif "address" in p_lower:
                desc = "Dirección del contrato del token o vault."
            elif "country" in p_lower:
                desc = "Código de país (ISO 3166-1 alfa-2)."
            elif "status" in p_lower:
                desc = "Estado actual del recurso."
            elif "type" in p_lower:
                desc = "Tipo de wallet o clasificación del recurso."
            elif "id" in p_lower:
                desc = "Identificador único del registro."
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


def _schema_rows(schema: Any) -> List[Dict[str, str]]:
    """
    Devuelve las filas que renderizaría la tabla de un schema.

    Retorna una lista vacía cuando no hay propiedades, de modo que
    las secciones puedan comprobar si hay contenido real antes de
    imprimir un subtítulo (evita subtítulos y tablas vacías).
    """
    if not schema:
        return []

    properties = getattr(schema, "properties", [])

    if not properties:
        return []

    return collect_schema_rows(properties)


def _rows_are_equal(rows_a: List[Dict[str, str]],
                    rows_b: List[Dict[str, str]]) -> bool:
    """
    Compara dos tablas por su contenido completo (nombre, tipo,
    tamaño, obligatorio y descripción).

    Se usa para detectar duplicidad exacta entre la tabla de
    "Respuesta exitosa" y la de "Estructura del JSON de salida
    desencriptado" antes de imprimirlas dos veces.
    """
    if not rows_a or not rows_b:
        return False

    def key(row):
        return (
            row.get("name"),
            row.get("type"),
            row.get("size"),
            row.get("required"),
            row.get("description"),
        )

    return [key(row) for row in rows_a] == [key(row) for row in rows_b]


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
# PARSING DE DESCRIPCION DE ENDPOINT
# ============================================================

def parse_endpoint_description(description: str) -> dict:
    """
    Extrae 4 partes de la descripción de un endpoint:

    1. objetivo → texto hasta el primer punto.
    2. body_desencriptado → contenido después de
       "Estructura del Body desencriptado".
    3. json_entrada_desencriptado → contenido después de
       "Ejemplo de entrada desencriptado".
    4. json_salida_desencriptado → contenido después de
       "Estructura del JSON de salida desencriptado".

    Retorna dict con las 4 claves. Si una parte no existe,
    su valor es string vacío.
    """
    result = {
        "objetivo": "",
        "body_desencriptado": "",
        "json_entrada_desencriptado": "",
        "json_salida_desencriptado": "",
    }

    if not description:
        result["objetivo"] = (
            "Petición encargada de realizar la operación."
        )
        return result

    # ── 1. Objetivo: texto hasta el primer punto
    first_period = description.find(".")
    if first_period != -1:
        result["objetivo"] = description[:first_period + 1].strip()
        remaining = description[first_period + 1:].strip()
    else:
        result["objetivo"] = description.strip()
        return result

    if not remaining:
        return result

    # ── 2, 3 y 4. Buscar encabezados en el texto restante
    lower_remaining = remaining.lower()

    body_marker = "estructura del body desencriptado"
    entrada_marker = "estructura del json de entrada desencriptado"
    json_marker = "estructura del json de salida desencriptado"

    body_pos = lower_remaining.find(body_marker)
    entrada_pos = lower_remaining.find(entrada_marker)
    json_pos = lower_remaining.find(json_marker)

    def _extract_block(text: str, marker: str) -> str:
        """Extrae contenido después del marker, ignorando
        '(referencia):**' u otros sufijos de la línea.
        Busca desde el fin de la línea del marker hasta el
        siguiente '**' o fin de texto."""
        lower_text = text.lower()
        start = lower_text.find(marker)
        if start == -1:
            return ""
        after = text[start + len(marker):]
        # Saltar hasta fin de línea del marker
        newline = after.find("\n")
        if newline == -1:
            return after.strip()
        content = after[newline + 1:]
        # Buscar fin del bloque: línea que empiece con '**' o fin
        lines = content.split("\n")
        result_lines = []
        for line in lines:
            if line.strip().startswith("**") and result_lines:
                break
            result_lines.append(line)
        return "\n".join(result_lines).strip()

    def _strip_code_fences(text: str) -> str:
        """Elimina fences markdown ```json ... ``` del contenido.

        Se eliminan TODOS los fences sobrantes (algunas descripciones
        cierran con doble fence: "```\\n```"), ya que un fence residual
        rompe el json.loads posterior.
        """
        stripped = text.strip()

        # Quitar fence(s) inicial(es): ```json o ```
        while stripped.startswith("```"):
            first_nl = stripped.find("\n")
            if first_nl == -1:
                return ""
            stripped = stripped[first_nl + 1:].lstrip("\n")

        # Quitar fence(s) de cierre sobrantes
        while stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3].rstrip()

        return stripped

    def _clean_json_trailing_commas(text: str) -> str:
        """Elimina comas trailing de JSON (válido en JSON5 pero no en JSON estándar)."""
        import re
        # Eliminar coma antes de } o ]
        cleaned = re.sub(r',\s*([}\]])', r'\1', text)
        return cleaned

    def _fix_json_missing_braces(text: str) -> str:
        """Agrega llaves de cierre faltantes para JSONs incompletos."""
        text = text.strip()
        opens = text.count('{') - text.count('}')
        if opens > 0:
            text += '\n' + '}' * opens
        return text

    # ── Extraer bloques ordenados por posición
    markers = [
        (body_pos, body_marker, "body_desencriptado"),
        (entrada_pos, entrada_marker, "json_entrada_desencriptado"),
        (json_pos, json_marker, "json_salida_desencriptado"),
    ]
    # Filtrar solo los que existen y ordenar por posición
    found = [(pos, marker, key) for pos, marker, key in markers if pos != -1]
    found.sort(key=lambda x: x[0])

    for i, (pos, marker, key) in enumerate(found):
        # El límite superior es el inicio del siguiente marker, o fin de texto
        end = found[i + 1][0] if i + 1 < len(found) else len(remaining)
        result[key] = _fix_json_missing_braces(
            _clean_json_trailing_commas(
                _strip_code_fences(
                    _extract_block(remaining[pos:end], marker)
                )
            )
        )

    return result


# ============================================================
# CLASIFICACION DE ENDPOINTS
# ============================================================

def classify_endpoints(endpoints: List[Any]) -> dict:
    """
    Clasifica endpoints en dos grupos basándose en su descripción (objetivo).

    Si la descripción contiene "no usa cifrado" (case-insensitive) → no cifrado.
    Si NO contiene → cifrado.

    Retorna dict con:
        "encrypted": [...]
        "not_encrypted": [...]
    """
    encrypted = []
    not_encrypted = []

    for endpoint in endpoints:
        description = (endpoint.description or "").lower()
        if "no usa cifrado" in description:
            not_encrypted.append(endpoint)
        else:
            encrypted.append(endpoint)

    return {
        "encrypted": encrypted,
        "not_encrypted": not_encrypted,
    }


# ============================================================
# GENERACIÓN DE ENDPOINT SEGÚN ESTRUCTURA CORPORATIVA
# ============================================================

def add_endpoint_section(
    document,
    endpoint: Any,
    index: int,
    base_url: str = "",
    is_template: bool = True,
    is_encrypted: bool = True,
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
        # La plantilla corporativa numera automáticamente los encabezados:
        # Heading 2 -> "3.1", "3.2" ...  Heading 3 -> "3.1.1", "3.1.2" ...
        # Solo ponemos el texto limpio SIN prefijo numérico.
        h2_title = f"Endpoint {endpoint_slug} ({endpoint_summary})"
        h3_params       = "Parámetros de entrada"
        h3_ejemplo_in   = "Ejemplo JSON de entrada"
        h3_respuesta    = "Respuesta"
        h3_ejemplo_out  = "Ejemplo JSON de salida"
        h3_status       = "Valores para el atributo de statusCode"
    else:
        # Documento standalone: numeramos manualmente con prefijo "1.x"
        chapter_prefix = "1"
        h2_title        = f"{chapter_prefix}.{index} Endpoint {endpoint_slug} ({endpoint_summary})"
        h3_params       = f"{chapter_prefix}.{index}.1 Parámetros de entrada"
        h3_ejemplo_in   = f"{chapter_prefix}.{index}.2 Ejemplo JSON de entrada"
        h3_respuesta    = f"{chapter_prefix}.{index}.3 Respuesta"
        h3_ejemplo_out  = f"{chapter_prefix}.{index}.4 Ejemplo JSON de salida"
        h3_status       = f"{chapter_prefix}.{index}.5 Valores para el atributo de statusCode"

    # ── Título del Endpoint (Heading 2)
    document.add_heading(h2_title, level=2)

    # ── Objetivo
    p_obj = document.add_paragraph()
    r_obj_title = p_obj.add_run("Objetivo: ")
    r_obj_title.bold = True

    if endpoint.description:
        parsed = parse_endpoint_description(endpoint.description)
        obj_text = parsed["objetivo"]
        body_desencriptado = parsed["body_desencriptado"]
        json_entrada_desencriptado = parsed["json_entrada_desencriptado"]
        json_salida_desencriptado = parsed["json_salida_desencriptado"]
    else:
        obj_text = (
            f"Petición encargada de realizar las acciones de "
            f"{endpoint_summary.lower()}."
        )
        body_desencriptado = ""
        json_entrada_desencriptado = ""
        json_salida_desencriptado = ""

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
    is_get_users = endpoint.method.lower() == "get" and endpoint.path == "/users"

    document.add_heading(h3_params, level=3)

    if has_rb:
        p_intro = document.add_paragraph()
        p_intro.add_run("Los parámetros de entrada del objeto JSON deben cumplir con los siguientes atributos:")
        first_rb_content = next(iter(endpoint.request_body.content.values()))
        add_schema_properties_table(document, first_rb_content)

        if has_params:
            p_extra = document.add_paragraph()
            p_extra.add_run("Parámetros de cabecera / consulta requeridos:")
            add_parameters_table(document, endpoint.parameters, required_only=is_get_users)

    elif has_params:
        # ── Endpoints cifrados sin requestBody (típicamente GET) ─────────
        # Los parámetros de consulta del Swagger son los mismos campos
        # desencriptados que se documentan más abajo en la sección
        # "Estructura de JSON de entrada desencriptado". Para evitar
        # duplicarlos, aquí solo se listan los parámetros de cabecera
        # (ej. X-Ct) y de ruta, y los campos de negocio quedan
        # exclusivamente en la tabla desencriptada.
        header_path_params = [
            p for p in endpoint.parameters
            if p.location in ("header", "path")
        ]
        has_query_params = any(
            p.location == "query" for p in endpoint.parameters
        )

        if is_encrypted and json_entrada_desencriptado and has_query_params:
            if header_path_params:
                p_intro = document.add_paragraph()
                p_intro.add_run(
                    "Los parámetros de cabecera / ruta de la petición deben cumplir con los siguientes atributos:"
                )
                add_parameters_table(document, header_path_params)
            # Los campos de consulta NO se listan aquí: ya aparecen
            # en la tabla "Estructura de JSON de entrada desencriptado".
        else:
            p_intro = document.add_paragraph()
            p_intro.add_run("Los parámetros de la petición deben cumplir con los siguientes atributos:")
            add_parameters_table(document, endpoint.parameters, required_only=is_get_users)
    else:
        p_intro = document.add_paragraph()
        p_intro.add_run("Este endpoint no requiere parámetros de entrada adicionales.")

    # ── Estructura de JSON de entrada desencriptado (ANTES del heading de ejemplo)
    # Solo se imprime si realmente hay contenido que mostrar.
    if is_encrypted and (json_entrada_desencriptado or has_rb):
        p_entrada_struct = document.add_paragraph()
        r_entrada_struct = p_entrada_struct.add_run("Estructura de JSON de entrada desencriptado")
        r_entrada_struct.bold = True
        if json_entrada_desencriptado:
            try:
                entrada_json = json.loads(json_entrada_desencriptado)
                entrada_schema = generate_schema_from_json(entrada_json)
                add_schema_properties_table(document, entrada_schema)
            except json.JSONDecodeError:
                pass
        elif has_rb:
            add_schema_properties_table(document, first_rb_content)

    # ── Ejemplo JSON de entrada (Heading 3) ─────────────────────────────
    #
    # La sección se imprime justo después de los parámetros de entrada,
    # siempre que exista contenido real:
    #
    #   - Ejemplo del requestBody: valores de ejemplo de los campos.
    #   - Ejemplo desencriptado: además, cuando existe en la descripción
    #     (aporta información propia de los endpoints cifrados).
    #
    # Si no hay contenido (sin requestBody y sin ejemplo desencriptado)
    # no se imprime el heading, para evitar subtítulos vacíos.
    sample_input = (
        generate_sample_json(first_rb_content)
        if has_rb
        else None
    )

    show_input_sample = bool(sample_input)
    show_decrypted_input_sample = bool(json_entrada_desencriptado)

    if show_input_sample or show_decrypted_input_sample:

        document.add_heading(h3_ejemplo_in, level=3)

        if show_input_sample:
            document.add_paragraph(
                "Ejemplo JSON de entrada encriptado:"
                if is_encrypted
                else "Ejemplo JSON de entrada:"
            )
            add_code_block(document, sample_input)

        if show_decrypted_input_sample:
            document.add_paragraph("Ejemplo de JSON de entrada desencriptado:")
            add_code_block(document, json_entrada_desencriptado)

    # ── Ejemplo Body desencriptado (solo si existe en la descripción)
    #if body_desencriptado:
     #   document.add_heading("Ejemplo de Body desencriptado", level=3)
      #  document.add_paragraph(body_desencriptado)

    # ── Respuesta (Heading 3)
    document.add_heading(h3_respuesta, level=3)
    document.add_paragraph("Información del JSON de respuesta correspondiente a la operación del endpoint:")

    success_response = next(
        (r for r in endpoint.responses if r.status_code.startswith("2") and r.content),
        None,
    ) or next((r for r in endpoint.responses if r.content), None)

    # ── Respuesta exitosa (subtítulo + tabla de estructura) ─────────────
    # Solo se imprime si la tabla tendrá filas reales: evita el
    # subtítulo en negrita sin contenido debajo.
    resp_schema = None
    resp_rows: List[Dict[str, str]] = []

    if success_response and success_response.content:
        resp_schema = next(iter(success_response.content.values()))
        resp_rows = _schema_rows(resp_schema)

    if resp_rows:
        p_main = document.add_paragraph()
        r_bullet = p_main.add_run("Respuesta exitosa")
        r_bullet.bold = True
        add_schema_properties_table(document, resp_schema)

    # ── Estructura del JSON de salida desencriptado ─────────────────────
    # Condiciones dinámicas:
    #   1. Únicamente endpoints CIFRADOS: la salida desencriptada solo
    #      aplica a servicios que implementan cifrado/descifrado.
    #   2. Únicamente si su contenido difiere de la tabla anterior:
    #      evita imprimir dos tablas con exactamente la misma
    #      información (en ese caso se conserva "Respuesta exitosa").
    if is_encrypted and resp_rows:

        if json_salida_desencriptado:
            try:
                output_json = json.loads(json_salida_desencriptado)
                output_schema = generate_schema_from_json(output_json)
            except json.JSONDecodeError:
                # Si el JSON desencriptado viene corrupto en el Swagger,
                # se usa el schema de la respuesta para no detener la
                # generación del documento.
                print(
                    f"[AVISO] JSON de salida inválido en "
                    f"{endpoint.method} {endpoint.path}. "
                    f"Se usa el schema de la respuesta."
                )
                output_schema = resp_schema
        else:
            output_schema = resp_schema

        output_rows = _schema_rows(output_schema)

        if output_rows and not _rows_are_equal(output_rows, resp_rows):
            p_output = document.add_paragraph()
            r_output = p_output.add_run(
                "Estructura del JSON de salida desencriptado"
            )
            r_output.bold = True
            add_schema_properties_table(document, output_schema)

    # ── Ejemplo JSON de salida (desencriptado desde Swagger o generado)
    if json_salida_desencriptado:
        document.add_heading(h3_ejemplo_out, level=3)
        document.add_paragraph("Ejemplo de respuesta JSON desencriptado obtenida del endpoint:")
        add_code_block(document, json_salida_desencriptado)
    elif resp_schema is not None:
        sample_output = generate_sample_json(resp_schema)
        if sample_output:
            document.add_heading(h3_ejemplo_out, level=3)
            document.add_paragraph("Ejemplo de respuesta JSON desencriptado obtenida del endpoint:")
            add_code_block(document, sample_output)

    # ── Valores para el atributo de statusCode (Heading 3)
    document.add_heading(h3_status, level=3)
    add_status_code_table(document, endpoint.responses)

    # Salto de página para el siguiente endpoint
    #document.add_page_break()
    
# ============================================================
# METADATOS DE PLANTILLA
# ============================================================

def update_template_metadata(
    document,
    services_or_data=None,
    document_data: Dict[str, Any] = None,
) -> None:
    """
    Actualiza títulos y referencias de API en la sección de Objetivo
    de la plantilla.

    Acepta:
        - services: lista de dicts con section_name (nuevo formato)
        - document_data: dict del Swagger (formato anterior, un solo servicio)
    """
    # Compatibilidad: si se pasa document_data directamente (formato anterior)
    if document_data is not None:
        services_list = [{"document_data": document_data}]
    elif isinstance(services_or_data, list):
        services_list = services_or_data
    elif isinstance(services_or_data, dict):
        services_list = [{"document_data": services_or_data}]
    else:
        services_list = []

    # Construir texto con todos los nombres de API
    api_names = []
    for svc in services_list:
        svc_data = svc.get("document_data", {})
        info = svc_data.get("info", {})
        title = info.get("title", "la API")
        if title not in api_names:
            api_names.append(title)

    if len(api_names) == 1:
        api_text = api_names[0]
    elif len(api_names) == 2:
        api_text = f"{api_names[0]} y {api_names[1]}"
    else:
        api_text = ", ".join(api_names[:-1]) + f" y {api_names[-1]}"

    for p in document.paragraphs[:50]:
        if "Este documento pretende describir de manera" in p.text:
            p.text = (
                f"Este documento pretende describir de manera técnica y detallada "
                f"el consumo del servicio web de Rummi.")
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

        if doc.TablesOfContents.Count > 0:
            doc.TablesOfContents(1).Update()
            print("Tabla de contenido actualizada exitosamente con Microsoft Word.")
        else:
            print("[INFO] El documento no contiene Tabla de Contenido. Se omite la actualización.")

        doc.Save()
        doc.Close()
        word.Quit()
        pythoncom.CoUninitialize()
    except ImportError:
        print("[INFO] pywin32 no instalado. La TOC se actualizara al abrir el archivo en Word (Ctrl+A -> F9).")
    except Exception as e:
        print(f"[INFO] No se pudo actualizar la TOC automaticamente ({e}). Abrirla en Word y presionar Ctrl+A -> F9.")


def _add_service_info_block(document, doc_data: Dict[str, Any]) -> None:
    """
    Agrega un bloque de información general del microservicio
    debajo del Heading 1, extrayendo la description
    directamente del Swagger/OpenAPI.
    """
    info = doc_data.get("info", {})
    description = info.get("description", "")

    if description:
        p_desc = document.add_paragraph()
        p_desc.add_run(description)

def _render_service_endpoints(
    document,
    endpoints,
    base_url,
    is_template,
):
    """
    Agrega los endpoints de un servicio al documento, agrupados
    por clasificación (cifrados / no cifrados).

    Los grupos usan Heading 2 con numId=0 para no consumir
    numeración de la secuencia de endpoints.
    """
    groups = classify_endpoints(endpoints)
    counter = 1

    if groups["encrypted"]:
        h = document.add_heading("Endpoints cifrados", level=2)
        document.add_paragraph("En esta sección se describen los endpoints del microservicio que utilizan comunicación cifrada, Todos los endpoints cifrados manejan la misma estructura general."
                               " Los siguientes endpoints utilizan comunicación cifrada; sin embargo, para facilitar su comprensión, los ejemplos de entrada y salida se muestran en formato descifrado.")
        for endpoint in groups["encrypted"]:
            add_endpoint_section(
                document=document,
                endpoint=endpoint,
                index=counter,
                base_url=base_url,
                is_template=is_template,
                is_encrypted=True,
            )
            counter += 1

    if groups["not_encrypted"]:
        h = document.add_heading("Endpoints no cifrados", level=2)
        document.add_paragraph("En esta sección se describen los endpoints del microservicio que no utilizan comunicación cifrada, Todos los endpoints no cifrados manejan la siguiente estructura general de entrada y salida:")
        for endpoint in groups["not_encrypted"]:
            add_endpoint_section(
                document=document,
                endpoint=endpoint,
                index=counter,
                base_url=base_url,
                is_template=is_template,
                is_encrypted=False,
            )
            counter += 1


def _set_heading_no_numbering(heading) -> None:
    """
    Configura un heading para que no consuma numeración
    automática (numId=0). Esto permite que los endpoints
    mantengan numeración continua sin saltos.
    """
    pPr = heading._element.get_or_add_pPr()
    # Remover numPr existente del estilo
    for old in pPr.findall(qn("w:numPr")):
        pPr.remove(old)
    # Agregar numPr con numId=0 (sin numeración)
    numPr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "1")
    numId = OxmlElement("w:numId")
    numId.set(qn("w:val"), "0")
    numPr.append(ilvl)
    numPr.append(numId)
    pPr.append(numPr)


def generate_word(
    services: List[Dict[str, Any]],
    output: Union[str, Path] = "output/documentacion_api.docx",
    template_path: Optional[Union[str, Path]] = None,
) -> None:
    """
    Genera la documentación Word (.docx).

    Parámetros:
        services: Lista de dicts con keys:
            - section_name: nombre de la sección (e.g. "Rummi User Administration API")
            - endpoints: lista de objetos Endpoint
            - document_data: dict del Swagger/OpenAPI
    """
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    template_file = Path(template_path) if template_path else Path(WORD_TEMPLATE)
    use_template = template_file.exists()

    if use_template:
        print(f"Usando plantilla corporativa: {template_file}")

        # Usar el document_data del primer servicio para el template
        first_doc_data = services[0]["document_data"]
        servers = first_doc_data.get("servers", [])
        base_url = servers[0].get("url", "") if servers else ""

        document = Document(str(template_file))
        _configure_document_styles(document)
        update_template_metadata(document, services)

        for service_idx, service in enumerate(services):
            section_name = service["section_name"]
            svc_endpoints = service["endpoints"]
            svc_doc_data = service["document_data"]

            svc_servers = svc_doc_data.get("servers", [])
            svc_base_url = svc_servers[0].get("url", "") if svc_servers else base_url

            print(f"\nGenerando sección: {section_name} ({len(svc_endpoints)} endpoints)")

            # Agregar Heading 1 con nombre del microservicio
            document.add_heading(section_name, level=1)

            # Agregar información general del microservicio desde el Swagger
            _add_service_info_block(document, svc_doc_data)

            _render_service_endpoints(
                document=document,
                endpoints=svc_endpoints,
                base_url=svc_base_url,
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

        first_doc_data = services[0]["document_data"]
        info = first_doc_data.get("info", {})
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
            ("OpenAPI", first_doc_data.get("openapi", "3.0.0")),
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

        doc_counter = 2
        for service in services:
            section_name = service["section_name"]
            svc_endpoints = service["endpoints"]
            svc_doc_data = service["document_data"]

            svc_servers = svc_doc_data.get("servers", [])
            svc_base_url = svc_servers[0].get("url", "") if svc_servers else ""

            document.add_heading(
                f"{doc_counter}. {section_name}", level=1
            )
            _render_service_endpoints(
                document=document,
                endpoints=svc_endpoints,
                base_url=svc_base_url,
                is_template=False,
            )
            doc_counter += 1

    # Forzar actualización de campos (TOC) al abrir el archivo en Word
    _set_update_fields_on_open(document)

    try:
        document.save(str(output_path))
        print(f"\nDocumento Word generado exitosamente en: {output_path}")
        
        _update_toc_with_word(output_path)
    except PermissionError:
        fallback_path = output_path.with_name(
            f"{output_path.stem}_nuevo{output_path.suffix}"
        )
        _set_update_fields_on_open(document)
        document.save(str(fallback_path))
        print(f"\n[AVISO] El archivo original estaba abierto en Word. Se guardó en: {fallback_path}")
        _update_toc_with_word(fallback_path)
        