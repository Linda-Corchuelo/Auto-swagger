from swagger.endpoint import (
    Endpoint,
    ParameterInfo,
    RequestBodyInfo,
    ResponseInfo,
    SchemaInfo,
    SchemaProperty,
)


HTTP_METHODS = {
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "options",
    "head",
}


# ============================================================
# RESOLVER $REF
# ============================================================

def resolve_reference(document, reference):
    """
    Resuelve una referencia local de Swagger/OpenAPI.

    Ejemplo:

        #/components/schemas/User

    se convierte en:

        document["components"]["schemas"]["User"]
    """

    if not reference:
        return None

    if not reference.startswith("#/"):
        return None

    parts = reference[2:].split("/")

    current = document

    for part in parts:

        if not isinstance(current, dict):
            return None

        current = current.get(part)

        if current is None:
            return None

    return current

 
# NOMBRE DEL $REF


def get_reference_name(reference):
    """
    Obtiene el nombre de un schema a partir de un $ref.

    Ejemplo:

        #/components/schemas/ApiResponse

    devuelve:

        ApiResponse
    """

    if not reference:
        return None

    return reference.split("/")[-1]


# ============================================================
# NORMALIZAR SCHEMA
# ============================================================

def normalize_schema(schema):
    """
    Normaliza un schema para trabajar de forma segura.

    Evita modificar directamente el documento Swagger.
    """

    if not isinstance(schema, dict):
        return {}

    return dict(schema)


# ============================================================
# EXTRAER EXAMPLE
# ============================================================

def extract_example(data):
    """
    Obtiene el example de una estructura OpenAPI.

    Soporta:

        example

    y:

        examples:
          ejemplo:
            value: ...

    También soporta examples como lista.
    """

    if not isinstance(data, dict):
        return None
    
    if "example" in data:
        return data["example"]
    
    examples = data.get("examples")

    if isinstance(examples, dict) and examples:

        first_example = next(
            iter(examples.values())
        )

        if isinstance(first_example, dict):

            if "value" in first_example:
                return first_example["value"]

            if "externalValue" in first_example:
                return first_example["externalValue"]

        return first_example

    # --------------------------------------------------------
    # examples como lista
    # --------------------------------------------------------

    if isinstance(examples, list) and examples:

        first_example = examples[0]

        if isinstance(first_example, dict):

            if "value" in first_example:
                return first_example["value"]

            if "externalValue" in first_example:
                return first_example["externalValue"]

        return first_example

    return None


# ============================================================
# PARSE PROPERTY
# ============================================================

def parse_property(
    name,
    schema,
    required=False,
    document=None,
    visited_refs=None,
    is_encrypted=False,
):
    """
    Convierte una propiedad Swagger/OpenAPI
    en SchemaProperty.

    Soporta:

    - tipos básicos
    - example
    - examples
    - enum
    - format
    - objetos anidados
    - arrays
    - $ref

    Además evita ciclos infinitos provocados
    por referencias circulares.

    Si is_encrypted es True (o el $ref contiene "encrypted"),
    todas las propiedades hijas se marcan como encriptadas.
    """

    if schema is None:
        schema = {}

    schema = normalize_schema(schema)

    if visited_refs is None:
        visited_refs = set()
        
    reference = schema.get("$ref")

    if reference and "encrypted" in reference.lower():
        is_encrypted = True

    resolved_schema = schema

    if reference and document:
        
        # Evitar ciclos
        
        if reference in visited_refs:

            return SchemaProperty(
                name=name,
                type="object",
                required=required,
                reference=reference,
            )

        visited_refs = set(visited_refs)
        visited_refs.add(reference)

        resolved = resolve_reference(
            document,
            reference,
        )

        if resolved:

            resolved_schema = dict(
                resolved
            )
            
            for key, value in schema.items():

                if key != "$ref":
                    resolved_schema[key] = value
                    
    # Tipo
    
    property_type = resolved_schema.get(
        "type",
        "object",
    )

    # --------------------------------------------------------
    # Example
    # --------------------------------------------------------

    example = extract_example(
        resolved_schema
    )

    # --------------------------------------------------------
    # Crear propiedad
    # --------------------------------------------------------

    property_info = SchemaProperty(

        name=name,

        type=property_type,

        required=required,

        description=resolved_schema.get(
            "description",
            "",
        ),

        format=resolved_schema.get(
            "format"
        ),

        min_length=resolved_schema.get(
            "minLength"
        ),

        max_length=resolved_schema.get(
            "maxLength"
        ),

        minimum=resolved_schema.get(
            "minimum"
        ),

        maximum=resolved_schema.get(
            "maximum"
        ),

        example=example,

        enum=resolved_schema.get(
            "enum",
            [],
        ),

        reference=reference,

        is_encrypted=is_encrypted,
    )

    properties = resolved_schema.get(
        "properties",
        {},
    )

    required_properties = set(
        resolved_schema.get(
            "required",
            [],
        )
    )

    if isinstance(properties, dict):

        for child_name, child_schema in properties.items():

            child = parse_property(

                name=child_name,

                schema=child_schema,

                required=(
                    child_name
                    in required_properties
                ),

                document=document,

                visited_refs=visited_refs,

                is_encrypted=is_encrypted,
            )

            property_info.properties.append(
                child
            )

    # ========================================================
    # ARRAY ITEMS
    # ========================================================

    if property_type == "array":

        items_schema = resolved_schema.get(
            "items"
        )

        if items_schema:

            property_info.items = parse_property(

                name="items",

                schema=items_schema,

                required=False,

                document=document,

                visited_refs=visited_refs,

                is_encrypted=is_encrypted,
            )

    return property_info


# ============================================================
# PARSE SCHEMA
# ============================================================

def parse_schema(
    name,
    schema,
    document,
    reference=None,
):
    """
    Convierte un schema completo de OpenAPI
    en SchemaInfo.

    Detecta automáticamente si el $ref contiene "encrypted"
    y propaga is_encrypted a todas las propiedades hijas.

    Conserva:

    - name
    - reference
    - type
    - description
    - example
    - enum
    - required
    - properties
    """

    if schema is None:
        schema = {}

    schema = normalize_schema(
        schema
    )

    # --------------------------------------------------------
    # Resolver referencia
    # --------------------------------------------------------

    schema_reference = (
        reference
        or schema.get("$ref")
    )

    is_encrypted = bool(
        schema_reference
        and "encrypted" in schema_reference.lower()
    )

    resolved_schema = schema

    if schema_reference:

        resolved = resolve_reference(
            document,
            schema_reference,
        )

        if resolved:

            resolved_schema = dict(
                resolved
            )

            # ------------------------------------------------
            # Mantener propiedades adicionales
            # ------------------------------------------------

            for key, value in schema.items():

                if key != "$ref":
                    resolved_schema[key] = value

    # --------------------------------------------------------
    # Required
    # --------------------------------------------------------

    required_properties = list(
        resolved_schema.get(
            "required",
            [],
        )
    )

    # --------------------------------------------------------
    # Properties
    # --------------------------------------------------------

    properties = []

    schema_properties = resolved_schema.get(
        "properties",
        {},
    )

    if isinstance(
        schema_properties,
        dict,
    ):

        for property_name, property_schema in (
            schema_properties.items()
        ):

            property_info = parse_property(

                name=property_name,

                schema=property_schema,

                required=(
                    property_name
                    in required_properties
                ),

                document=document,

                is_encrypted=is_encrypted,
            )

            properties.append(
                property_info
            )

    # --------------------------------------------------------
    # Crear SchemaInfo
    # --------------------------------------------------------

    return SchemaInfo(

        name=(
            name
            or get_reference_name(
                schema_reference
            )
        ),

        reference=schema_reference,

        type=resolved_schema.get(
            "type",
            "object",
        ),

        description=resolved_schema.get(
            "description",
            "",
        ),

        example=extract_example(
            resolved_schema
        ),

        enum=resolved_schema.get(
            "enum",
            [],
        ),

        properties=properties,

        required=required_properties,
    )


# ============================================================
# PARSE CONTENT
# ============================================================

def parse_content_schema(
    content,
    document,
):
    """
    Convierte el content de Request/Response
    en SchemaInfo.

    Soporta:

        application/json
        application/xml
        etc.

    También conserva examples definidos
    directamente en Media Type.
    """

    result = {}

    if not isinstance(
        content,
        dict,
    ):
        return result

    for content_type, media_type in content.items():

        if not isinstance(
            media_type,
            dict,
        ):
            continue

        schema = media_type.get(
            "schema",
            {},
        )

        if not isinstance(
            schema,
            dict,
        ):
            schema = {}

        reference = schema.get(
            "$ref"
        )

        schema_name = (
            get_reference_name(
                reference
            )
            if reference
            else "AnonymousSchema"
        )

        parsed_schema = parse_schema(

            name=schema_name,

            schema=schema,

            document=document,

            reference=reference,
        )

        # ----------------------------------------------------
        # Example del Media Type
        # ----------------------------------------------------

        media_example = extract_example(
            media_type
        )

        if media_example is not None:

            parsed_schema.example = (
                media_example
            )

        result[content_type] = (
            parsed_schema
        )

    return result


# ============================================================
# PARSE PARAMETERS
# ============================================================

def parse_parameters(
    parameters,
    document,
):
    """
    Convierte los parámetros OpenAPI
    en ParameterInfo.

    Conserva:

    - name
    - in
    - required
    - description
    - type
    - format
    - example
    - enum
    """

    result = []

    if not isinstance(
        parameters,
        list,
    ):
        return result

    for parameter in parameters:

        if not isinstance(
            parameter,
            dict,
        ):
            continue

        # ----------------------------------------------------
        # Resolver $ref
        # ----------------------------------------------------

        if "$ref" in parameter:

            resolved_parameter = (
                resolve_reference(
                    document,
                    parameter["$ref"],
                )
            )

            if resolved_parameter:

                parameter = dict(
                    resolved_parameter
                )

        # ----------------------------------------------------
        # Schema
        # ----------------------------------------------------

        parameter_schema = parameter.get(
            "schema",
            {},
        )

        if not isinstance(
            parameter_schema,
            dict,
        ):
            parameter_schema = {}

        parameter_schema = dict(
            parameter_schema
        )

        # ----------------------------------------------------
        # Example directo
        #
        # OpenAPI puede tener:
        #
        # "example": "Admin"
        #
        # directamente en el parámetro.
        # ----------------------------------------------------

        parameter_example = extract_example(
            parameter
        )

        if (
            parameter_example is not None
            and "example"
            not in parameter_schema
        ):

            parameter_schema["example"] = (
                parameter_example
            )

        # ----------------------------------------------------
        # Enum directo
        # ----------------------------------------------------

        if (
            "enum" in parameter
            and "enum"
            not in parameter_schema
        ):

            parameter_schema["enum"] = (
                parameter["enum"]
            )

        # ----------------------------------------------------
        # Type directo
        # ----------------------------------------------------

        if (
            "type" in parameter
            and "type"
            not in parameter_schema
        ):

            parameter_schema["type"] = (
                parameter["type"]
            )

        # ----------------------------------------------------
        # Format directo
        # ----------------------------------------------------

        if (
            "format" in parameter
            and "format"
            not in parameter_schema
        ):

            parameter_schema["format"] = (
                parameter["format"]
            )

        # ----------------------------------------------------
        # Crear ParameterInfo
        # ----------------------------------------------------

        parameter_schema_ref = parameter_schema.get(
            "$ref"
        )

        parameter_info = ParameterInfo(

            name=parameter.get(
                "name",
                "",
            ),

            location=parameter.get(
                "in",
                "",
            ),

            required=parameter.get(
                "required",
                False,
            ),

            description=parameter.get(
                "description",
                "",
            ),

            schema=parameter_schema,

            reference=parameter_schema_ref,
        )

        result.append(
            parameter_info
        )

    return result


# ============================================================
# PARSE ENDPOINTS
# ============================================================

def parse_endpoints(document, filter_paths=None):
    """
    Convierte los paths del Swagger en objetos Endpoint.

    Si se proporciona `filter_paths`, solo se incluirán los endpoints
    cuyo path coincida exactamente o sea un subpath de los indicados.
    """

    endpoints = []

    paths = document.get(
        "paths",
        {},
    )

    if not isinstance(
        paths,
        dict,
    ):
        return endpoints

    # ========================================================
    # PATHS
    # ========================================================

    for path, path_item in paths.items():

        if not isinstance(
            path_item,
            dict,
        ):
            continue

        # Filtrar por paths configurados si aplica
        if filter_paths:
            matches = any(
                path == fp or path.startswith(fp.rstrip("/") + "/")
                for fp in filter_paths
            )
            if not matches:
                continue

        # ====================================================
        # METHODS
        # ====================================================

        for method, operation in path_item.items():

            method_lower = method.lower()

            if method_lower not in HTTP_METHODS:
                continue

            if not isinstance(
                operation,
                dict,
            ):
                continue

            # =================================================
            # ENDPOINT
            # =================================================

            endpoint = Endpoint(

                method=method.upper(),

                path=path,

                summary=operation.get(
                    "summary",
                    "",
                ),

                description=operation.get(
                    "description",
                    "",
                ),
            )

            # =================================================
            # PARAMETERS
            # =================================================

            operation_parameters = (
                operation.get(
                    "parameters",
                    [],
                )
            )

            endpoint.parameters.extend(

                parse_parameters(
                    operation_parameters,
                    document,
                )
            )

            # =================================================
            # REQUEST BODY
            # =================================================

            request_body_data = (
                operation.get(
                    "requestBody"
                )
            )

            if request_body_data:

                # ---------------------------------------------
                # Resolver RequestBody $ref
                # ---------------------------------------------

                if "$ref" in request_body_data:

                    resolved_request_body = (
                        resolve_reference(
                            document,
                            request_body_data[
                                "$ref"
                            ],
                        )
                    )

                    if resolved_request_body:

                        request_body_data = (
                            resolved_request_body
                        )

                request_body = RequestBodyInfo(

                    required=request_body_data.get(
                        "required",
                        False,
                    )
                )

                request_body.content = (
                    parse_content_schema(

                        request_body_data.get(
                            "content",
                            {},
                        ),

                        document,
                    )
                )

                endpoint.request_body = (
                    request_body
                )

            # =================================================
            # RESPONSES
            # =================================================

            responses = operation.get(
                "responses",
                {},
            )

            if isinstance(
                responses,
                dict,
            ):

                for (
                    status_code,
                    response_data,
                ) in responses.items():

                    if not isinstance(
                        response_data,
                        dict,
                    ):
                        continue

                    # -----------------------------------------
                    # Resolver Response $ref
                    # -----------------------------------------

                    if "$ref" in response_data:

                        resolved_response = (
                            resolve_reference(
                                document,
                                response_data[
                                    "$ref"
                                ],
                            )
                        )

                        if resolved_response:

                            response_data = (
                                resolved_response
                            )

                    # -----------------------------------------
                    # ResponseInfo
                    # -----------------------------------------

                    response_info = ResponseInfo(

                        status_code=str(
                            status_code
                        ),

                        description=response_data.get(
                            "description",
                            "",
                        ),
                    )

                    # -----------------------------------------
                    # Response Content
                    # -----------------------------------------

                    response_info.content = (
                        parse_content_schema(

                            response_data.get(
                                "content",
                                {},
                            ),

                            document,
                        )
                    )

                    endpoint.responses.append(
                        response_info
                    )

            # =================================================
            # AGREGAR ENDPOINT
            # =================================================

            endpoints.append(
                endpoint
            )

    return endpoints


# ============================================================
# UTILIDADES DE SCHEMA
# ============================================================

def flatten_schema(schema, prefix=""):
    """
    Convierte un schema anidado en una lista plana de propiedades.

    Útil para generar tablas o reportes lineales.
    """
    result = []
    properties = getattr(schema, "properties", [])

    for prop in properties:
        prop_name = f"{prefix}.{prop.name}" if prefix else prop.name

        flattened_prop = SchemaProperty(
            name=prop_name,
            type=prop.type,
            required=prop.required,
            description=getattr(prop, "description", ""),
            format=getattr(prop, "format", None),
            min_length=getattr(prop, "min_length", None),
            max_length=getattr(prop, "max_length", None),
            minimum=getattr(prop, "minimum", None),
            maximum=getattr(prop, "maximum", None),
            example=getattr(prop, "example", None),
            enum=getattr(prop, "enum", []),
            reference=getattr(prop, "reference", None),
            properties=getattr(prop, "properties", []),
            items=getattr(prop, "items", None),
        )
        result.append(flattened_prop)


        if getattr(prop, "properties", None):
            result.extend(flatten_schema(prop, prop_name))

    return result


def print_schema_tree(schema, level=0):
    """
    Imprime el árbol jerárquico de un schema en consola,
    soportando objetos y arrays anidados.
    """
    indent = "    " * level
    properties = getattr(schema, "properties", [])

    for prop in properties:
        required = "Sí" if prop.required else "No"
        print(f"{indent}- {prop.name} | tipo: {prop.type} | requerido: {required}")

        if getattr(prop, "properties", None):
            print(f"{indent}  Propiedades:")
            print_schema_tree(prop, level + 2)

        if getattr(prop, "items", None):
            print(f"{indent}  Items:")
            item_type = getattr(prop.items, "type", "object")
            print(f"{indent}    - tipo: {item_type}")
            if getattr(prop.items, "properties", None):
                print_schema_tree(prop.items, level + 3)