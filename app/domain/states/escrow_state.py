from abc import ABC, abstractmethod
from typing import Dict, Type
from fastapi import HTTPException, status


class IEscrowState(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the escrow state."""
        pass

    def deposit(self, context=None) -> "IEscrowState":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot deposit in state: {self.name}")

    def dispatch(self, context=None) -> "IEscrowState":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot dispatch goods in state: {self.name}")

    def inspect(self, context=None) -> "IEscrowState":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot inspect goods in state: {self.name}")

    def release(self, context=None) -> "IEscrowState":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot release funds in state: {self.name}")

    def dispute(self, context=None) -> "IEscrowState":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot dispute in state: {self.name}")

    def apply_action(self, action: str, context=None) -> "IEscrowState":
        action_clean = action.upper().strip()
        if action_clean in ("DEPOSIT", "DEPOSIT_PAID"):
            return self.deposit(context)
        elif action_clean in ("DISPATCH", "DISPATCHED"):
            return self.dispatch(context)
        elif action_clean in ("INSPECT", "INSPECTED", "INSPECTED_OK", "ARRIVED"):
            return self.inspect(context)
        elif action_clean in ("RELEASE", "FUNDS_RELEASED", "FUNDS_TRANSFER"):
            return self.release(context)
        elif action_clean in ("DISPUTE", "DISPUTED", "INSPECTED_REJECT", "NO_SHOW"):
            return self.dispute(context)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid action: {action}")


class CreatedState(IEscrowState):
    name = "CREATED"

    def deposit(self, context=None) -> IEscrowState:
        return DepositHeldState()


class DepositHeldState(IEscrowState):
    name = "DEPOSIT_HELD"

    def dispatch(self, context=None) -> IEscrowState:
        return InTransitState()


class InTransitState(IEscrowState):
    name = "IN_TRANSIT"

    def inspect(self, context=None) -> IEscrowState:
        return InspectedState()

    def dispute(self, context=None) -> IEscrowState:
        return DisputedState()


class InspectedState(IEscrowState):
    name = "INSPECTED"

    def release(self, context=None) -> IEscrowState:
        return FundsReleasedState()

    def dispute(self, context=None) -> IEscrowState:
        return DisputedState()


class FundsReleasedState(IEscrowState):
    name = "FUNDS_RELEASED"


class DisputedState(IEscrowState):
    name = "DISPUTED"

    def release(self, context=None) -> IEscrowState:
        """Allow resolution of dispute in favor of releasing funds to farmer."""
        return FundsReleasedState()


_STATE_MAP: Dict[str, Type[IEscrowState]] = {
    "CREATED": CreatedState,
    "PENDING_BUYER_DEPOSIT": CreatedState,
    "DEPOSIT_HELD": DepositHeldState,
    "ESCROW_HELD": DepositHeldState,
    "IN_TRANSIT": InTransitState,
    "DISPATCHED": InTransitState,
    "ARRIVED_PENDING_INSPECTION": InTransitState,
    "INSPECTED": InspectedState,
    "INSPECTION_PASSED": InspectedState,
    "DELIVERED": InspectedState,
    "FUNDS_RELEASED": FundsReleasedState,
    "RELEASED": FundsReleasedState,
    "DISPUTED": DisputedState,
    "DISPUTED_QUALITY": DisputedState,
    "DISPUTED_NO_SHOW": DisputedState,
}


def get_state(state_name: str) -> IEscrowState:
    state_cls = _STATE_MAP.get(state_name.upper() if state_name else "")
    if not state_cls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown escrow state: {state_name}"
        )
    return state_cls()

