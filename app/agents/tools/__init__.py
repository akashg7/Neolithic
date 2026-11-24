"""Farmer-side agent tools (Track B). Importing this package registers them all.

    from app.agents.tools import TOOL_REGISTRY, ToolContext, run_tool, tool_schemas

Wave 1 (demo path): resolve_place_or_crop, get_mandi_price, get_price_forecast,
get_sale_window, draft_lot, create_lot, run_quality_check, get_lot_price_band,
open_screen.
"""

from app.agents.tools.base import (  # noqa: F401
    TOOL_REGISTRY, Tool, ToolContext, ToolFailure, ToolResult, run_tool, tool_schemas,
)
from app.agents.tools import market, decision, lots, navigation  # noqa: F401,E402  (registers)
