from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from fastapi.responses import JSONResponse
from starlette.requests import Request
from fastapi import HTTPException, status

from nova_manager.core.exceptions import BaseException, create_exception_response
from nova_manager.core.log import logger


class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            response = await call_next(request)

        except BaseException as e:
            logger.exception(e)
            response = create_exception_response(e)

        except HTTPException as e:
            logger.exception(e)
            response = JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
            )

        except Exception as e:
            logger.exception(e)
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": {
                        "error_code": "UNKNOWN_ERROR",
                        "message": "Unknown error",
                        "error": str(e),
                    }
                },
            )

        return response
