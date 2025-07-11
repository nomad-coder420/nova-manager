from fastapi.responses import JSONResponse

from nova_manager.core.response_code import ErrorCode, ResponseCode


class BaseException(Exception):
    """The base exception class for Data Access Layer Exceptions."""

    error_code: str = "UNKNOWN_ERROR"
    status_code: int = 500
    message: str = "Unknown Error"
    meta_data: dict = {}

    def __repr__(self):
        return "{}(error_code: {}, status_code: {}, message: {}, meta_data: {})".format(
            self.__class__.__name__,
            self.error_code,
            self.status_code,
            self.message,
            self.meta_data,
        )

    def __str__(self):
        return "{}(error_code: {}, status_code: {}, message: {}, meta_data: {})".format(
            self.__class__.__name__,
            self.error_code,
            self.status_code,
            self.message,
            self.meta_data,
        )


def create_exception_response(execption: BaseException):
    error = {"error_code": execption.error_code, "message": execption.message}

    if execption.meta_data:
        error.update(execption.meta_data)

    return JSONResponse(
        status_code=execption.status_code,
        content={"detail": error},
    )


class RequestValidationException(BaseException):
    status_code = ResponseCode.VALIDATION_ERROR.value
    error_code = ErrorCode.REQUEST_VALIDATION_ERROR.name
    message = ErrorCode.REQUEST_VALIDATION_ERROR.value

    def __init__(self, errors=None):
        self.meta_data = {"errors": str(errors)}


class ValidationException(BaseException):
    status_code = ResponseCode.VALIDATION_ERROR.value
    error_code = ErrorCode.VALIDATION_ERROR.name
    message = ErrorCode.VALIDATION_ERROR.value

    def __init__(self, errors=None):
        self.meta_data = {"errors": str(errors)}
