from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class InfluenceOSException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class InvalidCredentialsException(InfluenceOSException):
    def __init__(self, detail: str = "Invalid email or password"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(InfluenceOSException):
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class UserInactiveException(InfluenceOSException):
    def __init__(self, detail: str = "User account is inactive"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class DuplicateEmailException(InfluenceOSException):
    def __init__(self, detail: str = "An account with this email already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class NotFoundException(InfluenceOSException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class ForbiddenException(InfluenceOSException):
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ProviderNotConfiguredException(InfluenceOSException):
    """A required external data provider has no usable credentials."""

    def __init__(self, detail: str = "External data provider is not configured"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )


class ProviderQuotaExceededException(InfluenceOSException):
    """The external provider rejected the request because its quota is exhausted."""

    def __init__(self, detail: str = "External data provider quota exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )


class ProviderUnavailableException(InfluenceOSException):
    """The external provider failed in a way the user cannot fix."""

    def __init__(self, detail: str = "External data provider is currently unavailable"):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )


class InvalidRequestException(InfluenceOSException):
    def __init__(self, detail: str = "Invalid request"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class AINotConfiguredException(InfluenceOSException):
    """Grok/xAI credentials are missing or blank."""

    def __init__(self, detail: str = "AI provider is not configured"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )


class AIProviderException(InfluenceOSException):
    """Grok/xAI request failed after retries or returned an unusable response."""

    def __init__(self, detail: str = "AI provider request failed"):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )


class AgentValidationException(InfluenceOSException):
    """LLM output failed Pydantic or business-rule validation."""

    def __init__(self, detail: str = "Agent output failed validation"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class WorkflowStateException(InfluenceOSException):
    """Requested agent action is not allowed for the campaign's workflow state."""

    def __init__(self, detail: str = "Invalid workflow transition"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )
