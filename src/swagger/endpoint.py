from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================
# PARAMETER
# ============================================================

@dataclass
class ParameterInfo:
    """
    Representa un parámetro de un endpoint OpenAPI.

    Ejemplos:

        query
        header
        path
        cookie
    """

    name: str
    location: str

    required: bool = False

    description: str = ""

    schema: Optional[Dict[str, Any]] = None

    @property
    def type(self) -> Optional[str]:
        """
        Obtiene el tipo definido en el schema
        del parámetro.
        """

        if not self.schema:
            return None

        return self.schema.get(
            "type"
        )

    @property
    def format(self) -> Optional[str]:
        """
        Obtiene el formato definido en el schema
        del parámetro.
        """

        if not self.schema:
            return None

        return self.schema.get(
            "format"
        )

    @property
    def example(self) -> Any:
        """
        Obtiene el ejemplo del parámetro.
        """

        if not self.schema:
            return None

        return self.schema.get(
            "example"
        )

    @property
    def enum(self) -> List[Any]:
        """
        Obtiene los valores permitidos
        del parámetro.
        """

        if not self.schema:
            return []

        return self.schema.get(
            "enum",
            []
        )


# ============================================================
# SCHEMA PROPERTY
# ============================================================

@dataclass
class SchemaProperty:
    """
    Representa una propiedad dentro
    de un schema OpenAPI.

    Ejemplo:

        data
            ├── code
            └── message
    """

    name: str

    type: str = "object"

    required: bool = False

    description: str = ""

    format: Optional[str] = None

    example: Any = None

    enum: List[Any] = field(
        default_factory=list
    )

    reference: Optional[str] = None

    properties: List["SchemaProperty"] = field(
        default_factory=list
    )

    items: Optional["SchemaProperty"] = None


# ============================================================
# SCHEMA INFO
# ============================================================

@dataclass
class SchemaInfo:
    """
    Representa un schema completo
    de OpenAPI.

    Ejemplo:

        ApiResponse

        {
            "type": "object",
            "properties": {
                ...
            }
        }
    """

    name: str

    reference: Optional[str] = None

    # --------------------------------------------------------
    # Tipo principal del schema
    #
    # object
    # array
    # string
    # integer
    # boolean
    # etc.
    # --------------------------------------------------------

    type: str = "object"

    # --------------------------------------------------------
    # Descripción del schema
    # --------------------------------------------------------

    description: str = ""

    # --------------------------------------------------------
    # Ejemplo completo del schema
    # --------------------------------------------------------

    example: Any = None

    # --------------------------------------------------------
    # Valores enum del schema
    # --------------------------------------------------------

    enum: List[Any] = field(
        default_factory=list
    )

    # --------------------------------------------------------
    # Propiedades del schema
    # --------------------------------------------------------

    properties: List[SchemaProperty] = field(
        default_factory=list
    )

    # --------------------------------------------------------
    # Campos requeridos
    # --------------------------------------------------------

    required: List[str] = field(
        default_factory=list
    )


# ============================================================
# REQUEST BODY
# ============================================================

@dataclass
class RequestBodyInfo:
    """
    Representa el cuerpo de una petición.
    """

    required: bool = False

    content: Dict[str, SchemaInfo] = field(
        default_factory=dict
    )


# ============================================================
# RESPONSE
# ============================================================

@dataclass
class ResponseInfo:
    """
    Representa una respuesta HTTP
    de un endpoint.
    """

    status_code: str

    description: str = ""

    content: Dict[str, SchemaInfo] = field(
        default_factory=dict
    )


# ============================================================
# ENDPOINT
# ============================================================

@dataclass
class Endpoint:
    """
    Representa un endpoint completo
    de la API.
    """

    method: str

    path: str

    summary: str = ""

    description: str = ""

    parameters: List[ParameterInfo] = field(
        default_factory=list
    )

    request_body: Optional[RequestBodyInfo] = None

    responses: List[ResponseInfo] = field(
        default_factory=list
    )

    def __post_init__(self):
        """
        Normaliza el método HTTP.
        """

        self.method = self.method.upper()

    @property
    def name(self) -> str:
        """
        Nombre completo del endpoint.

        Ejemplo:

            GET /users
        """

        return (
            f"{self.method} "
            f"{self.path}"
        )

    @property
    def has_request_body(self) -> bool:
        """
        Indica si el endpoint tiene Request Body.
        """

        return (
            self.request_body
            is not None
        )

    @property
    def required_parameters(
        self,
    ) -> List[ParameterInfo]:
        """
        Obtiene únicamente
        los parámetros requeridos.
        """

        return [
            parameter
            for parameter in self.parameters
            if parameter.required
        ]

    @property
    def optional_parameters(
        self,
    ) -> List[ParameterInfo]:
        """
        Obtiene únicamente
        los parámetros opcionales.
        """

        return [
            parameter
            for parameter in self.parameters
            if not parameter.required
        ]

    @property
    def response_codes(
        self,
    ) -> List[str]:
        """
        Obtiene todos los códigos
        de respuesta del endpoint.
        """

        return [
            response.status_code
            for response in self.responses
        ]

    def __str__(self) -> str:
        """
        Representación legible
        del endpoint.
        """

        return self.name