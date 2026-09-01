from config import (
    SWAGGER_SERVICES,
    OUTPUT_DIR,
    WORD_TEMPLATE,
)

from swagger.reader import load_document
from swagger.parser import parse_endpoints, print_schema_tree
from swagger.exporter import export_endpoints
from generator.word_generator import generate_word, classify_endpoints


def print_endpoint_detail(endpoint):

    print("\n" + "=" * 70)
    print(f"{endpoint.method} {endpoint.path}")
    print("=" * 70)
    
    # INFORMACIÓN GENERAL
    
    print(f"Método: {endpoint.method}")
    print(f"Ruta: {endpoint.path}")
    print(f"Resumen: {endpoint.summary}")

    if endpoint.description:
        print( f"Descripción: {endpoint.description}")
        
    # PARÁMETROS
    
    print("\nParámetros:")

    if endpoint.parameters:

        for parameter in endpoint.parameters:

            required = (
                "Sí"
                if parameter.required
                else "No")

            print(
                f" - {parameter.name}"
                f" | ubicación: {parameter.location}"
                f" | requerido: {required}")

            schema = getattr(
                parameter,
                "schema",
                {})

            if isinstance(schema, dict):

                print(
                    f"   Tipo: "
                    f"{schema.get('type', 'string')}" )

                if schema.get("format"):
                    print(
                        f"   Formato: "
                        f"{schema.get('format')}" )

                if schema.get("example") is not None:
                    print(
                        f"   Example: "
                        f"{schema.get('example')}" )

                if schema.get("enum"):
                    print(
                        f"   Enum: "
                        f"{schema.get('enum')}" )

            if parameter.description:

                print(
                    f"   Descripción: "
                    f"{parameter.description}" )

    else:

        print( " - No tiene parámetros" )
        
    # REQUEST BODY
    
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

        print(" - No tiene respuestas definidas" )


def main():

    services = []

    for service_config in SWAGGER_SERVICES:
        swagger_url = service_config["url"]
        section_name = service_config["section_name"]
        filter_paths = service_config["filter_paths"]

        print("=" * 70)
        print(f"SERVICIO: {section_name}")
        print("=" * 70)
        print(f"Origen: {swagger_url}")

        # 1. CARGAR SWAGGER / OPENAPI
        document = load_document(swagger_url)

        print("\nEspecificación OpenAPI cargada correctamente.")

        # 2. INFORMACIÓN GENERAL
        info = document.get("info", {})
        print(f"\nTítulo: {info.get('title')}")
        print(f"Versión: {info.get('version')}")
        print(f"OpenAPI: {document.get('openapi')}")

        # 3. PARSEAR ENDPOINTS
        print("\nParseando endpoints...")
        if filter_paths:
            print(f"Filtro activo de endpoints: {filter_paths}")

        endpoints = parse_endpoints(
            document,
            filter_paths=filter_paths,
        )

        print(f"\nEndpoints encontrados: {len(endpoints)}")

        # 3.1 CLASIFICAR ENDPOINTS
        groups = classify_endpoints(endpoints)
        print(f"\nClasificación:")
        print(f"  Cifrados: {len(groups['encrypted'])}")
        print(f"  No cifrados: {len(groups['not_encrypted'])}")

        # 4. EXPORTAR JSON
        output_json_path = OUTPUT_DIR / f"swagger_output_{section_name.replace(' ', '_').lower()}.json"
        print(f"\nExportando JSON a: {output_json_path}")

        export_endpoints(
            endpoints,
            document,
            output_file=str(output_json_path),
        )

        services.append({
            "section_name": section_name,
            "endpoints": endpoints,
            "document_data": document,
        })

    # 5. GENERAR WORD
    output_docx_path = OUTPUT_DIR / "documentacion_api.docx"

    print("\n" + "=" * 70)
    print("GENERANDO DOCUMENTACIÓN WORD")
    print("=" * 70)

    generate_word(
        services=services,
        output=str(output_docx_path),
    )

    print("\nProceso terminado correctamente.")

if __name__ == "__main__":
    main()
