from config import SWAGGER_URL

from swagger.reader import load_from_url
from swagger.parser import parse_endpoints
from swagger.schema_parser import print_schema_tree
from swagger.exporter import export_endpoints
from generator.word_generator import generate_word


def print_endpoint_detail(endpoint):

    print("\n" + "=" * 70)
    print(f"{endpoint.method} {endpoint.path}")
    print("=" * 70)

    # ========================================================
    # INFORMACIÓN GENERAL
    # ========================================================

    print(f"Método: {endpoint.method}")
    print(f"Ruta: {endpoint.path}")
    print(f"Resumen: {endpoint.summary}")

    if endpoint.description:
        print(
            f"Descripción: {endpoint.description}"
        )

    # ========================================================
    # PARÁMETROS
    # ========================================================

    print("\nParámetros:")

    if endpoint.parameters:

        for parameter in endpoint.parameters:

            required = (
                "Sí"
                if parameter.required
                else "No"
            )

            print(
                f" - {parameter.name}"
                f" | ubicación: {parameter.location}"
                f" | requerido: {required}"
            )

            schema = getattr(
                parameter,
                "schema",
                {}
            )

            if isinstance(schema, dict):

                print(
                    f"   Tipo: "
                    f"{schema.get('type', 'string')}"
                )

                if schema.get("format"):
                    print(
                        f"   Formato: "
                        f"{schema.get('format')}"
                    )

                if schema.get("example") is not None:
                    print(
                        f"   Example: "
                        f"{schema.get('example')}"
                    )

                if schema.get("enum"):
                    print(
                        f"   Enum: "
                        f"{schema.get('enum')}"
                    )

            if parameter.description:

                print(
                    f"   Descripción: "
                    f"{parameter.description}"
                )

    else:

        print(
            " - No tiene parámetros"
        )

    # ========================================================
    # REQUEST BODY
    # ========================================================

    print("\nRequest Body:")

    if endpoint.request_body:

        required = (
            "Sí"
            if endpoint.request_body.required
            else "No"
        )

        print(
            f"Obligatorio: {required}"
        )

        for (
            content_type,
            schema
        ) in endpoint.request_body.content.items():

            print(
                f"\n - Content-Type: "
                f"{content_type}"
            )

            print(
                f"   Schema: "
                f"{schema.name}"
            )

            print(
                f"   Tipo: "
                f"{schema.type}"
            )

            print(
                f"   Referencia: "
                f"{schema.reference}"
            )

            if schema.description:

                print(
                    f"   Descripción: "
                    f"{schema.description}"
                )

            if schema.example is not None:

                print(
                    f"   Example: "
                    f"{schema.example}"
                )

            if schema.required:

                print(
                    f"   Required: "
                    f"{schema.required}"
                )

            if schema.enum:

                print(
                    f"   Enum: "
                    f"{schema.enum}"
                )

            print(
                "\n   Árbol del schema:"
            )

            print_schema_tree(
                schema,
                level=2
            )

    else:

        print(
            " - No tiene Request Body"
        )

    # ========================================================
    # RESPUESTAS
    # ========================================================

    print("\nRespuestas:")

    if endpoint.responses:

        for response in endpoint.responses:

            print(
                f"\n - {response.status_code}: "
                f"{response.description}"
            )

            if not response.content:

                print(
                    "   Sin contenido."
                )

                continue

            for (
                content_type,
                schema
            ) in response.content.items():

                print(
                    f"   Content-Type: "
                    f"{content_type}"
                )

                print(
                    f"   Schema: "
                    f"{schema.name}"
                )

                print(
                    f"   Tipo: "
                    f"{schema.type}"
                )

                print(
                    f"   Referencia: "
                    f"{schema.reference}"
                )

                if schema.description:

                    print(
                        f"   Descripción: "
                        f"{schema.description}"
                    )

                if schema.example is not None:

                    print(
                        f"   Example: "
                        f"{schema.example}"
                    )

                if schema.required:

                    print(
                        f"   Required: "
                        f"{schema.required}"
                    )

                if schema.enum:

                    print(
                        f"   Enum: "
                        f"{schema.enum}"
                    )

                print(
                    "\n   Árbol del schema:"
                )

                print_schema_tree(
                    schema,
                    level=2
                )

    else:

        print(
            " - No tiene respuestas definidas"
        )


def main():

    # ========================================================
    # 1. CARGAR SWAGGER
    # ========================================================

    print(
        "Cargando Swagger..."
    )

    print(
        f"URL: {SWAGGER_URL}"
    )

    document = load_from_url(
        SWAGGER_URL
    )

    print(
        "\nSwagger cargado correctamente."
    )

    # ========================================================
    # 2. INFORMACIÓN GENERAL
    # ========================================================

    info = document.get(
        "info",
        {}
    )

    print(
        "\nInformación general:"
    )

    print(
        f"Título: "
        f"{info.get('title')}"
    )

    print(
        f"Versión: "
        f"{info.get('version')}"
    )

    print(
        f"OpenAPI: "
        f"{document.get('openapi')}"
    )

    # ========================================================
    # 3. PARSEAR ENDPOINTS
    # ========================================================

    print(
        "\nParseando endpoints..."
    )

    endpoints = parse_endpoints(
        document
    )

    print(
        f"\nEndpoints encontrados: "
        f"{len(endpoints)}"
    )

    for endpoint in endpoints:

        print(
            f" - "
            f"{endpoint.method} "
            f"{endpoint.path}"
        )

    # ========================================================
    # 4. DETALLE DE TODOS LOS ENDPOINTS
    # ========================================================

    print(
        "\n" + "#" * 70
    )

    print(
        "# DETALLE DE TODOS LOS ENDPOINTS"
    )

    print(
        "#" * 70
    )

    for endpoint in endpoints:

        print_endpoint_detail(
            endpoint
        )

    # ========================================================
    # 5. EXPORTAR JSON
    # ========================================================

    print(
        "\n" + "#" * 70
    )

    print(
        "# EXPORTANDO JSON"
    )

    print(
        "#" * 70
    )

    export_endpoints(
        endpoints,
        document,
        "swagger_output.json"
    )

    # ========================================================
    # 6. GENERAR WORD
    # ========================================================

    print(
        "\n" + "#" * 70
    )

    print(
        "# GENERANDO DOCUMENTACIÓN WORD"
    )

    print(
        "#" * 70
    )

    generate_word(
        endpoints=endpoints,
        document_data=document,
        output="documentacion_api.docx"
    )

    print(
        "\nProceso terminado correctamente."
    )


if __name__ == "__main__":
    main()