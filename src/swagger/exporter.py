import json


# ============================================================
# PROPERTY
# ============================================================

def property_to_dict(prop):
    """
    Convierte una SchemaProperty a diccionario.

    Conserva:

    - nombre
    - tipo
    - requerido
    - descripción
    - formato
    - ejemplo
    - enum
    - referencia
    - propiedades anidadas
    - items de arrays
    """

    result = {
        "name": getattr(
            prop,
            "name",
            None
        ),

        "type": getattr(
            prop,
            "type",
            None
        ),

        "required": getattr(
            prop,
            "required",
            False
        ),

        "description": getattr(
            prop,
            "description",
            ""
        ) or "",

        "format": getattr(
            prop,
            "format",
            None
        ),

        "example": getattr(
            prop,
            "example",
            None
        ),

        "enum": getattr(
            prop,
            "enum",
            []
        ) or [],

        "reference": getattr(
            prop,
            "reference",
            None
        ),

        "properties": [
            property_to_dict(nested)
            for nested in getattr(
                prop,
                "properties",
                []
            )
        ],
    }

    # ========================================================
    # ITEMS DE ARRAY
    # ========================================================

    items = getattr(
        prop,
        "items",
        None
    )

    if items:

        result["items"] = property_to_dict(
            items
        )

    return result


# ============================================================
# SCHEMA
# ============================================================

def schema_to_dict(schema):
    """
    Convierte un SchemaInfo a diccionario.

    Conserva la información completa del schema:

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
        return None

    return {
        "name": getattr(
            schema,
            "name",
            None
        ),

        "reference": getattr(
            schema,
            "reference",
            None
        ),

        "type": getattr(
            schema,
            "type",
            None
        ),

        "description": getattr(
            schema,
            "description",
            ""
        ) or "",

        "example": getattr(
            schema,
            "example",
            None
        ),

        "enum": getattr(
            schema,
            "enum",
            []
        ) or [],

        "required": getattr(
            schema,
            "required",
            []
        ) or [],

        "properties": [
            property_to_dict(prop)
            for prop in getattr(
                schema,
                "properties",
                []
            )
        ],
    }


# ============================================================
# PARAMETER
# ============================================================

def parameter_to_dict(parameter):
    """
    Convierte un ParameterInfo a diccionario.

    Conserva:

    - name
    - location
    - required
    - description
    - type
    - format
    - example
    - enum
    """

    return {
        "name": parameter.name,

        "location": parameter.location,

        "required": parameter.required,

        "description": (
            parameter.description
            or ""
        ),

        "type": getattr(
            parameter,
            "type",
            None
        ),

        "format": getattr(
            parameter,
            "format",
            None
        ),

        "example": getattr(
            parameter,
            "example",
            None
        ),

        "enum": getattr(
            parameter,
            "enum",
            []
        ) or [],
    }


# ============================================================
# CONTENT
# ============================================================

def content_to_dict(content):
    """
    Convierte el contenido de Request/Response.

    Ejemplo:

    application/json
        -> schema
        -> properties
        -> examples
    """

    result = []

    if not content:
        return result

    for content_type, schema in content.items():

        result.append(
            {
                "contentType": content_type,

                "schema": schema_to_dict(
                    schema
                ),
            }
        )

    return result


# ============================================================
# REQUEST BODY
# ============================================================

def request_body_to_dict(request_body):
    """
    Convierte RequestBodyInfo.
    """

    if not request_body:
        return None

    return {
        "required": request_body.required,

        "content": content_to_dict(
            request_body.content
        ),
    }


# ============================================================
# RESPONSE
# ============================================================

def response_to_dict(response):
    """
    Convierte ResponseInfo.
    """

    return {
        "statusCode": str(
            response.status_code
        ),

        "description": (
            response.description
            or ""
        ),

        "content": content_to_dict(
            response.content
        ),
    }


# ============================================================
# ENDPOINT
# ============================================================

def endpoint_to_dict(endpoint):
    """
    Convierte un Endpoint completo
    a un diccionario serializable.
    """

    return {
        "method": endpoint.method,

        "path": endpoint.path,

        "summary": (
            endpoint.summary
            or ""
        ),

        "description": (
            endpoint.description
            or ""
        ),

        "parameters": [
            parameter_to_dict(
                parameter
            )
            for parameter in endpoint.parameters
        ],

        "requestBody": request_body_to_dict(
            endpoint.request_body
        ),

        "responses": [
            response_to_dict(
                response
            )
            for response in endpoint.responses
        ],
    }


# ============================================================
# EXPORT
# ============================================================

def export_endpoints(
    endpoints,
    document,
    output_file="swagger_output.json",
):
    """
    Exporta todos los endpoints parseados
    junto con la información general de Swagger.

    El objetivo es generar una estructura intermedia
    que posteriormente será utilizada para generar
    la documentación Word.
    """

    info = document.get(
        "info",
        {}
    )

    output = {

        "openapi": document.get(
            "openapi"
        ),

        "info": {

            "title": info.get(
                "title"
            ),

            "version": info.get(
                "version"
            ),

            "description": info.get(
                "description",
                ""
            ),
        },

        "endpoints": [
            endpoint_to_dict(
                endpoint
            )
            for endpoint in endpoints
        ],
    }

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        "\nDocumentación exportada correctamente:"
        f" {output_file}"
    )