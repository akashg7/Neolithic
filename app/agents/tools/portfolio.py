"""Farmer portfolio tool: active lots, open offers, and escrow transactions."""
from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import or_, select

from app.agents.tools.base import ToolContext, ToolFailure, ToolResult, navigate, tool
from app.models.lot import Lot
from app.models.offer import Offer
from app.models.transaction import Transaction
from app.utils.id_resolver import load_catalog


class PortfolioArgs(BaseModel):
    """Takes no identity parameters — farmer identity comes strictly from JWT."""


@tool(
    "get_farmer_portfolio",
    "Fetch the logged-in farmer's active lots, open offers, and escrow transaction statuses.",
    PortfolioArgs,
    requires_login=True,
)
async def get_farmer_portfolio(ctx: ToolContext, args: PortfolioArgs) -> ToolResult:
    if ctx.user is None:
        raise ToolFailure("NEEDS_LOGIN", "Log in to view your lots, offers, and escrow deals.")

    catalog = await load_catalog(ctx.db)

    lots = (
        await ctx.db.execute(
            select(Lot)
            .where(Lot.farmer_id == ctx.user.id)
            .order_by(Lot.created_at.desc())
            .limit(20)
        )
    ).scalars().all()

    offers = (
        await ctx.db.execute(
            select(Offer)
            .where(or_(Offer.farmer_id == ctx.user.id, Offer.buyer_id == ctx.user.id))
            .order_by(Offer.created_at.desc())
            .limit(20)
        )
    ).scalars().all()

    txns = (
        await ctx.db.execute(
            select(Transaction)
            .where(or_(Transaction.farmer_id == ctx.user.id, Transaction.buyer_id == ctx.user.id))
            .order_by(Transaction.created_at.desc())
            .limit(20)
        )
    ).scalars().all()

    lot_items = []
    for lot in lots:
        comm = catalog.get("commodity", lot.commodity_id)
        mkt = catalog.get("market", lot.market_id) if lot.market_id else None
        lot_items.append(
            {
                "lot_id": str(lot.id),
                "commodity": comm.name if comm else str(lot.commodity_id),
                "commodity_slug": comm.slug if comm else None,
                "mandi": mkt.name if mkt else None,
                "quantity_kg": int(lot.quantity_qtl) * 100,
                "expected_price_paise_per_qtl": lot.expected_price_paise,
                "grade": lot.grade,
                "status": lot.status,
            }
        )

    offer_items = [
        {
            "offer_id": str(o.id),
            "price_paise_per_qtl": o.price_paise_per_qtl,
            "qty_kg": o.qty_kg,
            "round": o.round,
            "initiator": o.initiator,
            "status": o.status,
        }
        for o in offers
    ]

    txn_items = [
        {
            "transaction_id": str(t.id),
            "offer_id": str(t.offer_id),
            "amount_paise": t.amount_paise,
            "status": t.status,
        }
        for t in txns
    ]

    active_lots = [l for l in lot_items if (l.get("status") or "").lower() == "active"]
    open_offers = [o for o in offer_items if (o.get("status") or "").upper() == "OPEN"]

    target = "S31_DealsList" if txn_items and not open_offers and not active_lots else "S15_MyLots"
    label = (
        ("माझे व्यवहार पहा", "मेरे सौदे देखें", "View my deals")
        if target == "S31_DealsList"
        else ("माझे लॉट पहा", "मेरे लॉट देखें", "View my lots")
    )

    return ToolResult(
        data={
            "summary": {
                "active_lot_count": len(active_lots),
                "total_lot_count": len(lot_items),
                "open_offer_count": len(open_offers),
                "transaction_count": len(txn_items),
            },
            "active_lots": active_lots,
            "lots": lot_items,
            "open_offers": open_offers,
            "transactions": txn_items,
        },
        ui_action=navigate(ctx, target, label=label),
        citation={"source": "krishi_mitr_db"},
    )
