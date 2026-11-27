"""Direct Buyer <-> Farmer negotiation chat router (`/api/v1/chats/{thread_id}/messages`)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.chat import ThreadMessage
from app.models.lot import Lot
from app.models.offer import Offer
from app.models.user import User
from app.utils.spatial import is_postgres

router = APIRouter()

_TABLE_READY = False


async def _ensure_table(db: AsyncSession) -> None:
    global _TABLE_READY
    if _TABLE_READY or not hasattr(db, "connection"):
        return
    conn = await db.connection()
    await conn.run_sync(lambda sync_conn: ThreadMessage.__table__.create(sync_conn, checkfirst=True))
    _TABLE_READY = True


async def _resolve_thread_key_and_authorize(db: AsyncSession, user: User, thread_id: str) -> tuple[str, Optional[Offer]]:
    """Authorize actor on offer/lot threads and normalize offer threads to root offer id."""
    raw = (thread_id or "").strip()
    if not raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    offer_id: Optional[int] = None
    if raw.isdigit():
        offer_id = int(raw)
    elif raw.startswith("offer_") and raw[6:].isdigit():
        offer_id = int(raw[6:])

    if offer_id is not None:
        offer = await db.get(Offer, offer_id)
        if offer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
        if user.id not in (offer.buyer_id, offer.farmer_id) and (offer.farmer_id is not None or (user.role or "").upper() != "FARMER"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
        if is_postgres(db):
            anchor = select(Offer.id, Offer.parent_offer_id).where(Offer.id == offer_id).cte(
                name="chat_offer_ancestors", recursive=True
            )
            parent_q = select(Offer.id, Offer.parent_offer_id).join(
                anchor, Offer.id == anchor.c.parent_offer_id
            )
            cte = anchor.union_all(parent_q)
            root_offer = (
                await db.execute(
                    select(Offer)
                    .join(cte, Offer.id == cte.c.id)
                    .where(Offer.parent_offer_id.is_(None))
                    .limit(1)
                )
            ).scalar_one_or_none()
            cur = root_offer or offer
        else:
            cur = offer
            visited = {cur.id}
            while cur.parent_offer_id and cur.parent_offer_id not in visited:
                visited.add(cur.parent_offer_id)
                parent = await db.get(Offer, cur.parent_offer_id)
                if parent is None:
                    break
                cur = parent
        return f"offer:{cur.id}", cur

    if raw.startswith("lot_") and raw[4:].isdigit():
        lot = await db.get(Lot, int(raw[4:]))
        if lot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
        if lot.farmer_id != user.id:
            has_offer = (
                await db.execute(
                    select(Offer.id).where(Offer.buyer_id == user.id)
                )
            ).first()
            if not has_offer:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
        return f"lot:{lot.id}", None

    return f"thread:{raw}", None


class ChatMessageIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class ChatMessageOut(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    text: str
    created_at: str
    is_me: bool


def _serialize(row: ThreadMessage, viewer_id: int) -> ChatMessageOut:
    created = row.created_at or datetime.now(timezone.utc)
    return ChatMessageOut(
        id=str(row.id),
        sender_id=str(row.sender_id),
        sender_name=row.sender_name,
        text=row.text,
        created_at=created.isoformat(),
        is_me=(row.sender_id == viewer_id),
    )


@router.get("/{thread_id}/messages", response_model=list[ChatMessageOut])
async def get_thread_messages(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch persisted buyer-farmer messages for an offer/deal thread."""
    await _ensure_table(db)
    canonical_key, root_offer = await _resolve_thread_key_and_authorize(db, user, thread_id)
    rows = (
        await db.execute(
            select(ThreadMessage)
            .where(ThreadMessage.thread_id == canonical_key)
            .order_by(ThreadMessage.created_at.asc(), ThreadMessage.id.asc())
        )
    ).scalars().all()
    if not rows and root_offer is not None and root_offer.note:
        sender_uid = root_offer.buyer_id if (root_offer.initiator or "").upper() == "BUYER" else (root_offer.farmer_id or user.id)
        sender = await db.get(User, sender_uid)
        return [
            ChatMessageOut(
                id=f"offer_note_{root_offer.id}",
                sender_id=str(sender_uid),
                sender_name=sender.name if sender else ("Buyer" if sender_uid == root_offer.buyer_id else "Farmer"),
                text=root_offer.note,
                created_at=(root_offer.created_at or datetime.now(timezone.utc)).isoformat(),
                is_me=(sender_uid == user.id),
            )
        ]
    return [_serialize(r, user.id) for r in rows]


@router.post("/{thread_id}/messages", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
async def post_thread_message(
    thread_id: str,
    payload: ChatMessageIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist a direct buyer-farmer message on an offer/deal thread."""
    await _ensure_table(db)
    canonical_key, _ = await _resolve_thread_key_and_authorize(db, user, thread_id)
    msg = ThreadMessage(
        thread_id=canonical_key,
        sender_id=user.id,
        sender_name=user.name or ("Farmer" if (user.role or "").upper() == "FARMER" else "Buyer"),
        text=payload.text.strip(),
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return _serialize(msg, user.id)
