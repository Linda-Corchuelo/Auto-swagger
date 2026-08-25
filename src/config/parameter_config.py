# ============================================================
# CONFIGURACION DE PARAMETROS
# ============================================================
#
# Define el tamaño del valor DESENCRIPTADO / valor de negocio
# para cada parámetro cuando Swagger no proporciona
# minLength y maxLength.
#
# Cuando el $ref del schema contiene "encrypted", el tamaño
# se muestra como "Variable" sin importar estos valores.
#
# Excepción: X-Ct siempre es "Variable" sin importar
# el estado de encriptación del request.
# ============================================================

PARAMETER_CONFIG = {
    "X-Ct": {
        "type": "string",
        "size": "Variable",
    },
    "email": {
        "type": "string",
        "min": 1,
        "max": 100,
    },
    "userName": {
        "type": "string",
        "min": 1,
        "max": 36,
    },
    "statusCode": {
        "type": "number",
        "size": "3 digitos",
    },
    "code": {
        "type": "string",
        "min": 1,
        "max": 50,
    },
    "data": {
        "type": "object",
        "size": "---",
    },
    "message": {
        "type": "string",
        "min": 1,
        "max": 200,
    },
    "users": {
        "type": "array",
        "min": 0,
        "max": 100,
    },
    "profilePictureUrl": {
        "type": "string",
        "min": 1,
        "max": 204,
    },
    "password": {
        "type": "string",
        "min": 8,
        "max": 100,
    },
    "newPassword": {
        "type": "string",
        "min": 8,
        "max": 100,
    },
    "confirmationCode": {
        "type": "string",
        "min": 6,
        "max": 6,
    },
    "otp": {
        "type": "string",
        "min": 6,
        "max": 6,
    },
    "phone": {
        "type": "string",
        "min": 1,
        "max": 15,
    },
    "name": {
        "type": "string",
        "min": 1,
        "max": 100,
    },
    "documentNumber": {
        "type": "string",
        "min": 5,
        "max": 20,
    },
    "role": {
        "type": "string",
        "min": 1,
        "max": 50,
    },
    "bio_code": {
        "type": "string",
        "min": 1,
        "max": 100,
    },
    "lastKey": {
        "type": "string",
        "min": 1,
        "max": 100,
    },
}
