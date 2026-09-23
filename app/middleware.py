import logging
import time
import uuid

from fastapi import Request

from app.logging_config import request_id_ctx

logger = logging.getLogger("case_pp")


async def log_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_ctx.set(request_id)
    start = time.perf_counter()
    try:
        logger.info(f"{request.method} {request.url.path} - started")
        response = await call_next(request)
    except Exception:
        logger.exception(f"{request.method} {request.url.path} - unhandled error")
        raise
    else:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(f"{request.method} {request.url.path} - {response.status_code} ({duration_ms:.1f}ms)")
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token)
