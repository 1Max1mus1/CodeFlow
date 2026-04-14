"""Proxy router — forwards HTTP requests from the browser to the user's local app.

This sidesteps CORS: the browser calls Codeflow's backend (/proxy), and the
backend makes the actual request server-side, where CORS doesn't apply.
"""
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Any
from src.models.domain import CamelModel

router = APIRouter()


class ProxyRequest(CamelModel):
    url: str                             # full URL, e.g. http://localhost:8000/tasks
    method: str = "GET"                  # HTTP verb
    headers: dict[str, str] = {}
    body: Any = None                     # JSON-serialisable body (or None)


class ProxyResponse(CamelModel):
    status_code: int
    headers: dict[str, str]
    body: Any                            # parsed JSON or raw text


@router.post("")
async def proxy_request(req: ProxyRequest):
    """Forward a request to the user's app and return the response."""
    method = req.method.upper()
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
        raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=method,
                url=req.url,
                headers=req.headers or {},
                json=req.body if req.body is not None else None,
            )
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not connect to {req.url!r}. Is the server running?",
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Request timed out (30 s)") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Try to parse JSON response; fall back to raw text
    try:
        body = resp.json()
    except Exception:
        body = resp.text

    # Return only string-valued headers to keep the model clean
    safe_headers = {k: v for k, v in resp.headers.items() if isinstance(v, str)}

    result = ProxyResponse(
        status_code=resp.status_code,
        headers=safe_headers,
        body=body,
    )
    return JSONResponse(content=result.model_dump(by_alias=True))
