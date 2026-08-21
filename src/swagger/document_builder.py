from typing import Any


def schema_to_dict(schema) -> dict[str, Any]:
    """
    Convierte un SchemaInfo en un diccionario serializable.
    Incluye propiedades anidadas e items de arrays.
    """

    result = {
        "name": schema.name,
        "reference": schema.reference,
        "type": getattr(schema, "type", None),
        "properties": []
    }

    for prop in schema.properties:

        property_data = {
            "name": prop.name,
            "type": prop.type,
            "required": prop.required,
            "description": getattr(
                prop,
                "description",
                None
            ),
            "properties": []
        }

        # --------------------------------------------------------
        # Propiedades anidadas
        # --------------------------------------------------------

        if prop.properties:

            property_data["properties"] = [
                property_to_dict(nested)
                for nested in prop.properties
            ]

        # --------------------------------------------------------
        # Items de arrays
        # --------------------------------------------------------

        if getattr(prop, "items", None):

            property_data["items"] = {
                "type": getattr(
                    prop.items,
                    "type",
                    None
                )
            }

        result["properties"].append(
            property_data
        )

    return result


def property_to_dict(prop) -> dict[str, Any]:
    """
    Convierte una propiedad de schema a diccionario.
    Permite propiedades anidadas recursivamente.
    """

    result = {
        "name": prop.name,
        "type": prop.type,
        "required": prop.required,
        "description": getattr(
            prop,
            "description",
            None
        ),
        "properties": []
    }

    # ------------------------------------------------------------
    # Propiedades anidadas
    # ------------------------------------------------------------

    if prop.properties:

        result["properties"] = [
            property_to_dict(nested)
            for nested in prop.properties
        ]

    # ------------------------------------------------------------
    # Items de arrays
    # ------------------------------------------------------------

    if getattr(prop, "items", None):

        result["items"] = {
            "type": getattr(
                prop.items,
                "type",
                None
            )
        }

    return result


def response_to_dict(response) -> dict[str, Any]:
    """
    Convierte una respuesta de endpoint a diccionario.
    """

    result = {
        "statusCode": response.status_code,
        "description": response.description,
        "content": []
    }

    for content_type, schema in response.content.items():

        result["content"].append(
            {
                "contentType": content_type,
                "schema": schema_to_dict(schema)
            }
        )

    return result


def endpoint_to_dict(endpoint) -> dict[str, Any]:
    """
    Convierte un EndpointInfo completo
    en una estructura serializable.
    """

    result = {
        "method": endpoint.method,
        "path": endpoint.path,
        "summary": endpoint.summary,
        "description": endpoint.description,
        "parameters": [],
        "requestBody": None,
        "responses": []
    }

    # ============================================================
    # PARÁMETROS
    # ============================================================

    for parameter in endpoint.parameters:

        result["parameters"].append(
            {
                "name": parameter.name,
                "location": parameter.location,
                "required": parameter.required,
                "description": getattr(
                    parameter,
                    "description",
                    None
                )
            }
        )

    # ============================================================
    # REQUEST BODY
    # ============================================================

    if endpoint.request_body:

        request_body = {
            "required": endpoint.request_body.required,
            "content": []
        }

        for content_type, schema in (
            endpoint.request_body.content.items()
        ):

            request_body["content"].append(
                {
                    "contentType": content_type,
                    "schema": schema_to_dict(schema)
                }
            )

        result["requestBody"] = request_body

    # ============================================================
    # RESPUESTAS
    # ============================================================

    for response in endpoint.responses:

        result["responses"].append(
            response_to_dict(response)
        )

    return result


def build_document(document, endpoints) -> dict[str, Any]:
    """
    Construye la documentación completa de la API.
    """

    info = document.get(
        "info",
        {}
    )

    return {
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
                "description"
            )
        },
        "servers": document.get(
            "servers",
            []
        ),
        "endpoints": [
            endpoint_to_dict(endpoint)
            for endpoint in endpoints
        ]
    }