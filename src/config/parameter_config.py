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
        "max": 35,
    },
    "userName": {
        "type": "string",
        "min": 1,
        "max": 36,
    },
    "statusCode": {
        "type": "number",
        "size": "3 dígitos",
    },
    "code": {
        "type": "string",
        "min": 1,
        "max": 5,
    },
    "data": {
        "type": "object",
        "size": "---",
    },
    "message": {
        "type": "string",
        "min": 1,
        "max": 50,
    },
    "users": {
        "type": "array",
        "min": 0,
        "max": 100,
    },
    "user": {
        "type": "object",
        "size": "---",
     },
    "userAttributes": {
        "type": "object",
        "size": "---",
     },
    "profilePictureUrl": {
        "type": "string",
        "min": 1,
        "max": 100,
    },
    "presignedPostProfileImage": {
        "type": "object",
        "size": "---",
        },
    "password": {
        "type": "string",
        "min": 8,
        "max": 20,
    },
    "newPassword": {
        "type": "string",
        "min": 8,
        "max": 20,
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
        "max": 25,
    },
    "documentNumber": {
        "type": "string",
        "min": 5,
        "max": 20,
    },
    "role": {
        "type": "string",
        "min": 1,
        "max": 25,
    },
    "userRole": {
        "type": "string",
        "min": 1,
        "max": 50,
    },
    "bio_code": {
        "type": "string",
        "min": 1,
        "max": 20,
    },
    "bio_status": {
        "type": "string",
        "min": 1,
        "max": 15,
    },
    "kyc_level": {
        "type": "string",
        "min": 1,
        "max": 25,
    },
    "isAcceptATDP": {
        "type": "boolean",
        "size": "----",
    },
    "lastKey": {
        "type": "string",
        "min": 1,
        "max": 25,
    },
    "phone_number": {
    "type": "string",
    "min": 1,
    "max": 15,
    },
    "custom_documentNumber": {
        "type": "string",
        "min": 1,
        "max": 20,
    },
    "custom_documentType": {
        "type": "string",
        "min": 1,
        "max": 20,
    },
    "custom_firstName": {
        "type": "string",
        "min": 1,
        "max": 25,
    },
    "custom_lastName": {
        "type": "string",
        "min": 1,
        "max": 25,
    },
    "custom_nickname": {
        "type": "string",
        "min": 1,
        "max": 25,
    },
    "custom_country": {
        "type": "string",
        "min": 1,
        "max": 25,
    },
    "custom_documentCountry": {
        "type": "string",
        "min": 1,
        "max": 20,
    },
    "amount": {
        "type": "number",
        "size": "Variable"
    },
    "buyer": {
        "type": "string",
        "min": 1,
        "max": 25
    },
    "seller": {
        "type": "string",
        "min": 1,
        "max": 25
    },
    "atdpType": {
        "type": "string",
        "min": 1,
        "max": 10
    },
    "idTemplate": {
        "type": "string",
        "size": "Variable"
    },
    "pin": {
        "type": "string",
        "min": 4,
        "max": 6
    },
    "hash": {
        "type": "string",
        "size": "Variable",
        },
    "enabled": {
        "type": "boolean",
        "size": "----",
    },
    "url": {
        "type": "string",
        "size": "Variable",
    },
    # ============================================================
    # MICROSERVICIO EVENTS
    # ============================================================
    "userId": {
        "type": "string",
        "min": 1,
        "max": 36,
    },
    "username": {
        "type": "string",
        "min": 1,
        "max": 36,
    },
    "payload": {
        "type": "object",
        "size": "---",
    },
    "title": {
        "type": "string",
        "min": 1,
        "max": 50,
    },
    "link": {
        "type": "string",
        "size": "Variable",
    },
    "type": {
        "type": "string",
        "min": 1,
        "max": 20,
    },
    "notificationId": {
        "type": "string",
        "min": 1,
        "max": 50,
    },
    "notification": {
        "type": "object",
        "size": "---",
    },
    "id": {
        "type": "string",
        "min": 1,
        "max": 50,
    },
    "read": {
        "type": "boolean",
        "size": "----",
    },
    "timestamp": {
        "type": "string",
        "size": "Variable",
    },
    "success": {
        "type": "boolean",
        "size": "----",
    },
    "redirectTo": {
        "type": "string",
        "size": "Variable",
    },
    # ============================================================
    # MICROSERVICIO WALLET
    # ============================================================
    "balances": {
        "type": "array",
        "min": 0,
        "max": 100,
    },
    "detailTokens": {
        "type": "array",
        "min": 0,
        "max": 100,
    },
    "symbol": {
        "type": "string",
        "min": 1,
        "max": 10,
    },
    "stablecoin": {
        "type": "string",
        "min": 1,
        "max": 10,
    },
    "country": {
        "type": "string",
        "min": 1,
        "max": 3,
    },
    "status": {
        "type": "string",
        "min": 1,
        "max": 10,
    },
    "balancePol": {
        "type": "object",
        "size": "---",
    },
    "features": {
        "type": "object",
        "size": "---",
    },
    "balance": {
        "type": "number",
        "size": "Variable",
    },
    "tokensBalance": {
        "type": "number",
        "size": "Variable",
    },
    "totalTokens": {
        "type": "number",
        "size": "Variable",
    },
    "tokenPriceInUSD": {
        "type": "number",
        "size": "Variable",
    },
    "walletAddress": {
        "type": "string",
        "size": "Variable",
    },
    "address": {
        "type": "string",
        "size": "Variable",
    }
}
