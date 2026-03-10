from __future__ import annotations

from fastapi import HTTPException


def http_error(status_code: int, code: str, message: str, *, request_id: str | None = None, details: dict | None = None) -> HTTPException:
    payload = {
        "request_id": request_id,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }
    return HTTPException(status_code=status_code, detail=payload)
