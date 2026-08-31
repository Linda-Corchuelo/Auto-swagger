from config import (
    SWAGGER_URL,
    OUTPUT_DIR,
    ENDPOINTS_TO_DOCUMENT,
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

    # 1. CARGAR SWAGGER / OPENAPI
    print("Cargando especificación...")
    print(f"Origen: {SWAGGER_URL}")

    document = load_document(SWAGGER_URL)
    
    print("\nEspecificación OpenAPI cargada correctamente.")

    # 2. INFORMACIÓN GENERAL
    
    info = document.get(
        "info",
        {}
    )

    print("\nInformación general:")

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
    
    # 3. PARSEAR ENDPOINTS
    
    print("\nParseando endpoints...")
    if ENDPOINTS_TO_DOCUMENT:
        print(
            f"Filtro activo de endpoints: "
            f"{ENDPOINTS_TO_DOCUMENT}"
        )

    endpoints = parse_endpoints(
        document,
        filter_paths=ENDPOINTS_TO_DOCUMENT
    )

    print(
        f"\nEndpoints encontrados: "
        f"{len(endpoints)}"
    )

    # 3.1 CLASIFICAR ENDPOINTS
    groups = classify_endpoints(endpoints)
    print(f"\nClasificación:")
    print(f"  Cifrados: {len(groups['encrypted'])}")
    print(f"  No cifrados: {len(groups['not_encrypted'])}")

    # 4. EXPORTAR JSON
    output_json_path = OUTPUT_DIR / "swagger_output.json"

    print("# EXPORTANDO JSON")

    export_endpoints(
        endpoints,
        document,
        output_file=str(output_json_path)
    )

    # 5. GENERAR WORD
    output_docx_path = OUTPUT_DIR / "documentacion_api.docx"

    print("# GENERANDO DOCUMENTACIÓN WORD")

    generate_word(
        endpoints=endpoints,
        document_data=document,
        output=str(output_docx_path)
    )

    print("\nProceso terminado correctamente.")

if __name__ == "__main__":
    main()
