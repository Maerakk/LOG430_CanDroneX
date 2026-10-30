"""Une paire de clés RSA remplace Keycloak dans les tests."""
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from candronex_common.auth import AUDIENCE, ISSUER, TokenVerifier

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def token(client_id: str = "inspectra-demo", key=KEY, **claims) -> str:
    c = {"iss": ISSUER, "aud": [AUDIENCE], "azp": client_id, "exp": int(time.time()) + 300}
    c.update(claims)
    return "Bearer " + jwt.encode({k: v for k, v in c.items() if v is not None}, key, algorithm="RS256")


def auth_headers(client_id: str = "inspectra-demo", **extra) -> dict:
    return {"Authorization": token(client_id), **extra}


def verifier() -> TokenVerifier:
    return TokenVerifier(key=KEY.public_key())
