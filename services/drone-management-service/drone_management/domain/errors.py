from candronex_common.errors import ConflictError, NotFoundError


class DroneAlreadyRegisteredError(ConflictError):
    pass


class NetworkIdentityUnavailableError(ConflictError):
    pass


class DroneNotFoundError(NotFoundError):
    pass
