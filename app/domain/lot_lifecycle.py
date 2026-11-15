"""Lot status lifecycle. Owner: Pranay.

The DB keeps lowercase status strings. The LLD calls the first state
"available"; the live schema and seed data already call it "active", so that
name is kept.

    active ──► locked ──► sold
      │  ▲        │
      │  └────────┘   (offer rejected / expired → back to active)
      ├──► pooled     (merged into an FPO batch lot; final for the source lot)
      └──► cancelled

Only this module decides which moves are legal, so no service can push a lot
from "sold" back to "active" by accident.
"""

ACTIVE = "active"
LOCKED = "locked"
SOLD = "sold"
POOLED = "pooled"
CANCELLED = "cancelled"

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    ACTIVE: frozenset({LOCKED, POOLED, CANCELLED}),
    LOCKED: frozenset({ACTIVE, SOLD}),
    SOLD: frozenset(),
    POOLED: frozenset(),
    CANCELLED: frozenset(),
}


class InvalidLotTransition(ValueError):
    pass


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get((current or "").lower(), frozenset())


def transition(lot, target: str) -> None:
    """Move `lot.status` to `target`, or raise if that move is not allowed."""
    current = (lot.status or "").lower()
    if not can_transition(current, target):
        raise InvalidLotTransition(f"Lot {lot.id} cannot go from '{current}' to '{target}'.")
    lot.status = target
