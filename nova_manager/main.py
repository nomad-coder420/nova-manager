from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from nova_manager.core.exceptions import (
    RequestValidationException,
    ValidationException,
    create_exception_response,
)
from nova_manager.core.log import configure_logging
from nova_manager.middlewares.exceptions import ExceptionMiddleware


configure_logging()
app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return create_exception_response(RequestValidationException(exc.errors()))


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    return create_exception_response(ValidationException(exc.errors()))


app.add_middleware(ExceptionMiddleware)
