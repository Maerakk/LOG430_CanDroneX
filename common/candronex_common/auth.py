import os
from functools import wraps

import jwt
from flask import current_app, g, request

from candronex_common import context
from candronex_common.errors import UnauthorizedError

JWKS_URL = "http://keycloak:8080/realms/candronex/protocol/openid-connect/certs"
ISSUER = "http://localhost:8081/realms/candronex"
AUDIENCE = "candronex-api"


class InvalidToken(Exception):
    pass


class TokenVerifier:
    def __init__(self, key=None):
        self.issuer = os.environ.get("JWT_ISSUER", ISSUER)
        self.audience = os.environ.get("JWT_AUDIENCE", AUDIENCE)
        self._key = key  # clé fixe pour les tests, sinon JWKS de Keycloak
        self._jwks = None if key else jwt.PyJWKClient(os.environ.get("JWT_JWKS_URL", JWKS_URL), lifespan=3600)

    def verify(self, authorization: str | None) -> dict:
        if not authorization or not authorization.startswith("Bearer "):
            raise InvalidToken("missing bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        try:
            key = self._key or self._jwks.get_signing_key_from_jwt(token).key
            return jwt.decode(token, key, algorithms=["RS256"], issuer=self.issuer, audience=self.audience,
                              options={"require": ["exp", "iss", "aud", "azp"]})
        except (jwt.PyJWTError, jwt.PyJWKClientError) as e:
            raise InvalidToken(str(e)) from e


def install(app, verifier: TokenVerifier) -> None:
    app.extensions["token_verifier"] = verifier


def requires_client(func):
    """L'identité du client est la claim azp du jeton vérifié, jamais un en-tête."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization")
        try:
            claims = current_app.extensions["token_verifier"].verify(header)
        except InvalidToken as e:
            raise UnauthorizedError("A valid bearer token is required.") from e
        g.client_id = claims["azp"]
        context.client_id.set(g.client_id)
        context.authorization.set(header)  # retransmis tel quel aux autres services
        return func(*args, **kwargs)
    return wrapper
