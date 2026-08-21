from dataclasses import dataclass, field
from typing import Any


@dataclass
class SchemaProperty:
    """
    Representa una propiedad dentro de un schema OpenAPI.
    """
    name: str

    type: str = "object"

    description: str = ""

    required: bool = False

    format: str | None = None

    example: Any = None

    enum: list[Any] = field(
        default_factory=list
    )

    reference: str | None = None

    properties: list["SchemaProperty"] = field(
        default_factory=list
    )

    items: "SchemaProperty | None" = None


@dataclass
class ParsedSchema:
    """
    Representa un schema OpenAPI procesado.
    """

    name: str | None = None

    reference: str | None = None

    type: str = "object"

    description: str = ""

    properties: list[SchemaProperty] = field(
        default_factory=list
    )

    required: list[str] = field(
        default_factory=list
    )

    example: Any = None

    enum: list[Any] = field(
        default_factory=list
    )


def resolve_reference(
    document: dict[str, Any],
    reference: str,
) -> dict[str, Any] | None:
    """
    Resuelve una referencia interna de OpenAPI.

    Ejemplo:

        #/components/schemas/ApiResponse
    """

    if not reference.startswith("#/"):
        return None

    current: Any = document

    parts = reference[2:].split("/")

    for part in parts:

        if not isinstance(current, dict):
            return None

        current = current.get(part)

        if current is None:
            return None

    if isinstance(current, dict):
        return current

    return None


def get_reference_name(
    reference: str | None,
) -> str | None:
    """
    Obtiene el nombre de un $ref.

    Ejemplo:

        #/components/schemas/ApiResponse

    devuelve:

        ApiResponse
    """

    if not reference:
        return None

    return reference.split("/")[-1]


def parse_schema(
    document: dict[str, Any],
    schema: dict[str, Any] | None,
    name: str | None = None,
    reference: str | None = None,
) -> ParsedSchema:
    """
    Procesa un schema OpenAPI completo.
    """

    if not schema:
        return ParsedSchema(
            name=name,
            reference=reference,
        )

    # Resolver $ref
    if "$ref" in schema:

        reference = schema["$ref"]

        resolved_schema = resolve_reference(
            document,
            reference,
        )

        if resolved_schema is None:
            return ParsedSchema(
                name=get_reference_name(
                    reference
                ),
                reference=reference,
            )

        return parse_schema(
            document,
            resolved_schema,
            name=get_reference_name(
                reference
            ),
            reference=reference,
        )

    schema_type = schema.get(
        "type",
        "object",
    )

    required_fields = schema.get(
        "required",
        [],
    )

    properties = []

    for property_name, property_schema in (
        schema.get(
            "properties",
            {}
        ).items()
    ):

        property_info = parse_property(
            document,
            property_name,
            property_schema,
            required_fields,
        )

        properties.append(
            property_info
        )

    return ParsedSchema(
        name=name,
        reference=reference,
        type=schema_type,
        description=schema.get(
            "description",
            "",
        ),
        properties=properties,
        required=required_fields,
        example=schema.get(
            "example"
        ),
        enum=schema.get(
            "enum",
            [],
        ),
    )


def parse_property(
    document: dict[str, Any],
    property_name: str,
    property_schema: dict[str, Any],
    required_fields: list[str],
) -> SchemaProperty:
    """
    Procesa una propiedad de un schema.
    """

    required = property_name in required_fields

    reference = property_schema.get(
        "$ref"
    )

    # Propiedad basada en $ref
    if reference:

        resolved_schema = resolve_reference(
            document,
            reference,
        )

        if resolved_schema:

            nested_schema = parse_schema(
                document,
                resolved_schema,
                name=get_reference_name(
                    reference
                ),
                reference=reference,
            )

            return SchemaProperty(
                name=property_name,
                type=nested_schema.type,
                description=nested_schema.description,
                required=required,
                example=nested_schema.example,
                enum=nested_schema.enum,
                reference=reference,
                properties=nested_schema.properties,
            )

    property_type = property_schema.get(
        "type",
        "object",
    )

    properties = []

    # Objeto anidado
    if property_type == "object":

        for nested_name, nested_schema in (
            property_schema.get(
                "properties",
                {}
            ).items()
        ):

            properties.append(
                parse_property(
                    document,
                    nested_name,
                    nested_schema,
                    property_schema.get(
                        "required",
                        [],
                    ),
                )
            )

    # Array
    items = None

    if property_type == "array":

        items_schema = property_schema.get(
            "items"
        )

        if items_schema:

            items = parse_property(
                document,
                "items",
                items_schema,
                [],
            )

    return SchemaProperty(
        name=property_name,
        type=property_type,
        description=property_schema.get(
            "description",
            "",
        ),
        required=required,
        format=property_schema.get(
            "format"
        ),
        example=property_schema.get(
            "example"
        ),
        enum=property_schema.get(
            "enum",
            [],
        ),
        reference=reference,
        properties=properties,
        items=items,
    )


def flatten_schema(
    schema: ParsedSchema,
    prefix: str = "",
) -> list[SchemaProperty]:
    """
    Convierte un schema anidado en una lista plana.

    Esto será útil posteriormente para generar
    tablas de documentación.

    Ejemplo:

        data.code
        data.message
        data.user.name
    """

    result: list[SchemaProperty] = []

    for property_info in schema.properties:

        if prefix:
            property_name = (
                f"{prefix}.{property_info.name}"
            )
        else:
            property_name = property_info.name

        flattened_property = SchemaProperty(
            name=property_name,
            type=property_info.type,
            description=property_info.description,
            required=property_info.required,
            format=property_info.format,
            example=property_info.example,
            enum=property_info.enum,
            reference=property_info.reference,
            properties=property_info.properties,
            items=property_info.items,
        )

        result.append(
            flattened_property
        )

        if property_info.properties:

            nested_schema = ParsedSchema(
                properties=property_info.properties
            )

            result.extend(
                flatten_schema(
                    nested_schema,
                    property_name,
                )
            )

    return result

def print_schema_tree(
    schema: ParsedSchema,
    level: int = 0,
) -> None:
    """
    Imprime el árbol completo de un schema,
    soportando objetos y arrays anidados.
    """

    indent = "    " * level

    for prop in schema.properties:

        required = (
            "Sí"
            if prop.required
            else "No"
        )

        print(
            f"{indent}- {prop.name}"
            f" | tipo: {prop.type}"
            f" | requerido: {required}"
        )

        # ------------------------------------------
        # Objeto anidado
        # ------------------------------------------

        if prop.properties:

            print(
                f"{indent}  Propiedades:"
            )

            nested_schema = ParsedSchema(
                properties=prop.properties
            )

            print_schema_tree(
                nested_schema,
                level + 2,
            )

        # ------------------------------------------
        # Array
        # ------------------------------------------

        if prop.items:

            print(
                f"{indent}  Items:"
            )

            print(
                f"{indent}    - tipo: "
                f"{prop.items.type}"
            )

            if prop.items.properties:

                nested_schema = ParsedSchema(
                    properties=(
                        prop.items.properties
                    )
                )

                print_schema_tree(
                    nested_schema,
                    level + 3,
                )