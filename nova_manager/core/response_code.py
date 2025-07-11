from enum import Enum


class ErrorCode(Enum):
    BAD_REQUEST = "Bad Request"
    PERMISSION_DENIED = "Permission denied"
    METHOD_NOT_ALLOWED = "Method not allowed"
    TIMEOUT = "Timeout"
    VALIDATION_ERROR = "Validation error"
    REQUEST_VALIDATION_ERROR = "Request validation error"
    INTERNAL_SERVER_ERROR = "Internal server error"
    EXTERNAL_API_ERROR = "External API error"
    API_REQUEST_EXCEPTION = "API Request exception"
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded"
    DB_CONNECTION_NOT_FOUND = "Database connection not found"
    UNKNOWN_ERROR = "Unknown error"


class ResponseCode(Enum):
    BAD_REQUEST = 400
    PERMISSION_DENIED = 403
    METHOD_NOT_ALLOWED = 405
    TIMEOUT = 408
    VALIDATION_ERROR = 422
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
