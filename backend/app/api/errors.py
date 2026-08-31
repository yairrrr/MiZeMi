"""§17 error responses for REST endpoints.

Reuses the shared error-payload models (one §17 shape everywhere — the same
models serve the realtime ``error`` event).
"""

from fastapi.responses import JSONResponse

from app.realtime.errors import ErrorCode, ErrorDetail, ErrorPayload


def error_response(status_code: int, code: ErrorCode, message: str) -> JSONResponse:
    payload = ErrorPayload(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))
