"""HTTP access to the farmer agent tools — for Track C's loop, the app and testing.

    GET  /api/v1/agent/tools          → JSON schemas of every tool (hand these to the LLM)
    POST /api/v1/agent/tools/{name}   → run one tool

Identity is the request's JWT (optional: guests get the read tools). A tool's
own failure (`NEEDS_INPUT`, `NO_DATA`, ...) is a normal 200 with `ok: false` —
it is information for the agent, not a transport error. Write tools only ever
return CONFIRM_ACTION cards, so nothing here changes data.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import TOOL_REGISTRY, ToolContext, run_tool, tool_schemas
from app.database import get_db
from app.dependencies.auth import get_optional_user
from app.models.user import User

router = APIRouter()


class ScreenContext(BaseModel):
    current_screen: str | None = None
    active_commodity_id: str | None = None
    active_market_id: str | None = None
    active_lot_id: str | None = None


class ToolRunReq(BaseModel):
    args: dict[str, Any] = Field(default_factory=dict)
    locale: Literal["mr", "hi", "en"] = "mr"
    screen_context: ScreenContext = Field(default_factory=ScreenContext)


@router.get("")
async def list_tools() -> dict:
    return {"tools": [
        {**t.schema(), "kind": t.kind, "requires_login": t.requires_login}
        for t in TOOL_REGISTRY.values()
    ]}


@router.post("/{name}")
async def call_tool(
    name: str,
    req: ToolRunReq,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    if name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"No tool named {name!r}")
    ctx = ToolContext(db=db, user=user, locale=req.locale,
                      screen=req.screen_context.model_dump(exclude_none=True))
    return await run_tool(name, ctx, req.args)


__all__ = ["router", "tool_schemas"]
