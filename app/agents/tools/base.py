"""Agent tool framework — the contract every farmer-side tool follows.

* Tools are thin wrappers over services (never over HTTP).
* Identity comes from `ToolContext.user` (the JWT), never from the LLM's args.
* Read tools return facts. Write tools never write: they return a
  `CONFIRM_ACTION` card carrying the exact REST request; the app's Confirm button
  sends it. The agent can propose; only the farmer's tap acts.
* Failures come back as structured errors (`NEEDS_INPUT`, `NOT_FOUND`, `NO_DATA`,
  ...) so the agent can ask a follow-up or say "I don't know" instead of guessing.

Track C's agent loop uses three things from here:
    TOOL_REGISTRY            name -> Tool
    tool_schemas()           JSON schemas to hand to the LLM
    run_tool(name, ctx, args)  -> dict (always; never raises)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.window_service import NoPriceDataError, WindowInputError
from app.utils.id_resolver import ResolveError

logger = logging.getLogger(__name__)

ToolKind = Literal["read", "write", "navigate"]
ErrorCode = Literal[
    "NEEDS_INPUT", "NEEDS_LOGIN", "NOT_ALLOWED", "NOT_FOUND", "AMBIGUOUS",
    "NO_DATA", "SERVICE_DOWN", "UNKNOWN_TOOL",
]


@dataclass
class ToolContext:
    """Built by the /agent router from the request — never from LLM output."""

    db: AsyncSession
    user: User | None = None
    locale: str = "mr"
    screen: dict[str, Any] = field(default_factory=dict)

    def screen_value(self, key: str) -> Any:
        v = (self.screen or {}).get(key)
        return v if v not in ("", None) else None

    def t(self, mr: str, hi: str, en: str) -> str:
        return {"mr": mr, "hi": hi}.get(self.locale, en)


@dataclass
class ToolResult:
    data: dict[str, Any]
    card: dict[str, Any] | None = None        # {"type": ..., "data": {...}}
    ui_action: dict[str, Any] | None = None   # {"type", "target_screen", "cta_label", "params"}
    citation: dict[str, Any] | None = None    # {"source": ..., "as_of"?: ...}


class ToolFailure(Exception):
    """Raise inside a tool to return a structured error."""

    def __init__(self, code: ErrorCode, message: str, *,
                 missing: list[str] | None = None, candidates: list[dict] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.missing = missing or []
        self.candidates = candidates or []


Handler = Callable[[ToolContext, Any], Awaitable[ToolResult]]


@dataclass
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    kind: ToolKind
    handler: Handler
    requires_login: bool = False

    def schema(self) -> dict:
        params = self.args_model.model_json_schema()
        params.pop("title", None)
        return {"name": self.name, "description": self.description, "parameters": params}


TOOL_REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, args: type[BaseModel], *,
         kind: ToolKind = "read", requires_login: bool = False):
    """Decorator: register an async handler `(ctx, args) -> ToolResult`."""

    def wrap(fn: Handler) -> Handler:
        if name in TOOL_REGISTRY:
            raise ValueError(f"duplicate tool name {name!r}")
        TOOL_REGISTRY[name] = Tool(name=name, description=description, args_model=args,
                                   kind=kind, handler=fn, requires_login=requires_login)
        return fn

    return wrap


def tool_schemas() -> list[dict]:
    return [t.schema() for t in TOOL_REGISTRY.values()]


def _error(name: str, code: str, message: str, *, missing=None, candidates=None) -> dict:
    return {"ok": False, "tool": name,
            "error": {"code": code, "message": message,
                      "missing": missing or [], "candidates": candidates or []}}


async def run_tool(name: str, ctx: ToolContext, args: dict | None) -> dict:
    """Validate args, run the tool, and return a JSON-safe dict. Never raises."""
    t = TOOL_REGISTRY.get(name)
    if t is None:
        return _error(name, "UNKNOWN_TOOL", f"No tool named {name!r}")
    if t.requires_login and ctx.user is None:
        return _error(name, "NEEDS_LOGIN", "This needs the farmer to be logged in.")

    try:
        parsed = t.args_model.model_validate(args or {})
    except ValidationError as exc:
        missing = [".".join(str(p) for p in e["loc"]) for e in exc.errors()]
        return _error(name, "NEEDS_INPUT", "Invalid or missing arguments: " + "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()), missing=missing)

    try:
        res = await t.handler(ctx, parsed)
    except ToolFailure as exc:
        return _error(name, exc.code, exc.message, missing=exc.missing, candidates=exc.candidates)
    except ResolveError as exc:
        if exc.ambiguous:
            return _error(name, "AMBIGUOUS", f"More than one {exc.kind} matches {exc.query!r}",
                          candidates=[c.as_dict() for c in exc.candidates[:5]])
        return _error(name, "NOT_FOUND", f"Unknown {exc.kind}: {exc.query!r}")
    except WindowInputError as exc:
        return _error(name, "NEEDS_INPUT", str(exc), missing=exc.missing)
    except NoPriceDataError as exc:
        return _error(name, "NO_DATA", str(exc))
    except HTTPException as exc:
        if exc.status_code == 404:
            return _error(name, "NOT_FOUND", str(exc.detail))
        if exc.status_code in (400, 422):
            return _error(name, "NEEDS_INPUT", str(exc.detail))
        logger.warning("tool %s: HTTP %s %s", name, exc.status_code, exc.detail)
        return _error(name, "SERVICE_DOWN", str(exc.detail))
    except Exception:  # pragma: no cover - logged, never leaked to the farmer
        logger.exception("tool %s failed", name)
        return _error(name, "SERVICE_DOWN", "This service is temporarily unavailable.")

    return {"ok": True, "tool": name, "kind": t.kind, "data": res.data,
            "card": res.card, "ui_action": res.ui_action, "citation": res.citation}


# ── helpers shared by tools ────────────────────────────────────────────────

def need(value: Any, field_name: str, message: str) -> Any:
    if value in (None, "", 0):
        raise ToolFailure("NEEDS_INPUT", message, missing=[field_name])
    return value


def confirm_card(ctx: ToolContext, *, action: str, summary: dict, method: str,
                 path: str, body: dict | None) -> dict:
    """A CONFIRM_ACTION card: the app shows `summary` and, only on the farmer's
    tap, sends exactly `request` with the farmer's own JWT."""
    return {
        "type": "CONFIRM_ACTION",
        "data": {
            "action": action,
            "summary": summary,
            "request": {"method": method, "path": path, "body": body},
            "confirm_label": ctx.t("पक्के करा", "पक्का करें", "Confirm"),
            "cancel_label": ctx.t("रद्द करा", "रद्द करें", "Cancel"),
        },
    }


def navigate(ctx: ToolContext, target_screen: str, params: dict | None = None,
             *, kind: str = "OFFER_NAVIGATION", label: tuple[str, str, str] | None = None) -> dict:
    mr, hi, en = label or ("पूर्ण तपशील पहा", "पूरी जानकारी देखें", "See full details")
    return {"type": kind, "target_screen": target_screen,
            "cta_label": ctx.t(mr, hi, en), "params": params or {}}
