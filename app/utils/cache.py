"""Resilient Redis HTTP response cache decorator built over FastAPICache (DB 1).

Fixes two pitfalls of raw `@fastapi_cache.decorator.cache`:
1. Excludes non-serializable DI objects (`AsyncSession`, `User`) from keys by
   keying strictly on `(method, path, sorted query params[, user_id])`.
2. Degrades cleanly when `FastAPICache` is uninitialized (unit tests without
   lifespan) or when Redis is unreachable, instead of failing requests.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional

from fastapi.encoders import jsonable_encoder
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import _augment_signature
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("krishi.cache")


def request_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    args: tuple[Any, ...] = (),
    kwargs: Optional[dict[str, Any]] = None,
    user_scoped: bool = False,
) -> str:
    """Build deterministic cache key from HTTP path + sorted query params (+ optional user_id)."""
    kw = kwargs or {}
    parts: list[str] = [namespace or "default"]
    if request is not None:
        query_items = sorted(request.query_params.multi_items())
        parts.append(request.method)
        parts.append(request.url.path)
        parts.append(json.dumps(query_items, separators=(",", ":")))
    else:
        safe_kw = {
            k: v
            for k, v in sorted(kw.items())
            if k not in ("db", "session", "user", "request", "response")
        }
        parts.append(f"{func.__module__}.{func.__qualname__}")
        parts.append(json.dumps(safe_kw, default=str, separators=(",", ":")))

    if user_scoped:
        user = kw.get("user")
        uid = getattr(user, "id", None) if user is not None else None
        parts.append(f"uid={uid if uid is not None else 'anon'}")

    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]
    prefix = FastAPICache.get_prefix() if FastAPICache._init else "agrisense-cache"
    ns = f":{namespace}" if namespace else ""
    return f"{prefix}{ns}:{digest}"


def safe_cache(
    *,
    expire: int = 300,
    namespace: str = "",
    user_scoped: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Cache GET JSON responses in Redis when FastAPICache is initialized."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(func)
        req_param = next(
            (p for p in sig.parameters.values() if p.annotation is Request),
            None,
        )
        resp_param = next(
            (p for p in sig.parameters.values() if p.annotation is Response),
            None,
        )
        to_inject: list[inspect.Parameter] = []
        if req_param is None:
            req_param = inspect.Parameter(
                "_cache_request",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Request,
            )
            to_inject.append(req_param)
        if resp_param is None:
            resp_param = inspect.Parameter(
                "_cache_response",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Response,
            )
            to_inject.append(resp_param)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            copy_kwargs = kwargs.copy()
            request: Optional[Request] = copy_kwargs.pop(req_param.name, None)
            response: Optional[Response] = copy_kwargs.pop(resp_param.name, None)

            async def call_inner() -> Any:
                inner_kw = dict(kwargs)
                if req_param.name not in sig.parameters:
                    inner_kw.pop(req_param.name, None)
                if resp_param.name not in sig.parameters:
                    inner_kw.pop(resp_param.name, None)
                return await func(*args, **inner_kw)

            # Skip HTTP caching when called directly in unit tests or when FastAPICache isn't initialized.
            if (
                request is None
                or request.method != "GET"
                or not FastAPICache._init
                or not FastAPICache.get_enable()
            ):
                return await call_inner()

            backend = FastAPICache._backend
            if backend is None:
                return await call_inner()

            cache_header = FastAPICache.get_cache_status_header()
            bypass = request.headers.get("Cache-Control", "").lower() == "no-cache"
            cache_key = request_key_builder(
                func,
                namespace=namespace,
                request=request,
                response=response,
                args=args,
                kwargs=copy_kwargs,
                user_scoped=user_scoped,
            )

            if not bypass:
                try:
                    ttl, cached = await backend.get_with_ttl(cache_key)
                except Exception as exc:
                    logger.debug("Redis cache read skipped (%s): %s", cache_key, exc)
                    ttl, cached = 0, None

                if cached is not None:
                    headers = {
                        "Cache-Control": f"public, max-age={max(0, int(ttl or expire))}",
                        cache_header: "HIT",
                    }
                    return Response(
                        content=cached,
                        media_type="application/json",
                        headers=headers,
                    )

            result = await call_inner()
            try:
                encoded = json.dumps(
                    jsonable_encoder(result),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                await backend.set(cache_key, encoded, expire)
            except Exception as exc:
                logger.debug("Redis cache write skipped (%s): %s", cache_key, exc)

            if response is not None:
                response.headers["Cache-Control"] = f"public, max-age={expire}"
                response.headers[cache_header] = "MISS"
            return result

        if to_inject:
            wrapper.__signature__ = _augment_signature(sig, *to_inject)  # type: ignore[attr-defined]
        return wrapper

    return decorator


async def clear_http_cache() -> int:
    """Clear HTTP cache keys in FastAPICache / Redis DB 1 (best-effort)."""
    if FastAPICache._init and FastAPICache._backend is not None:
        try:
            return await FastAPICache.clear()
        except Exception:
            pass
    try:
        from redis import asyncio as aioredis
        from app.config import settings

        r = aioredis.from_url(settings.REDIS_URL)
        try:
            keys = await r.keys("agrisense-cache:*")
            if keys:
                return int(await r.delete(*keys))
            return 0
        finally:
            await r.close()
    except Exception:
        return 0
