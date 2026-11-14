"""Factory Method Pattern — polymorphic creation of role-specific user profiles.

Owner: Member 1 (LLD_MEMBER_1_AUTH_AND_REPOSITORY.md §4, Pattern 2).

`AuthService.register` never instantiates `Farmer` / `Buyer` directly; it asks
`UserFactory` for "the profile for this role". Each role has its own concrete
`ProfileCreator`, held in a registry, so a new role (e.g. a warehouse
inspector) is added by registering one more creator. The registration flow
stays the same (Open/Closed Principle).

Schema notes (the real tables in app/models/user.py):
  * `name`, `district_id`, `village` live on `users`, not on the profile.
  * `Buyer` stores only `gst_last4`. The full GSTIN is validated here and
    then dropped (we keep as little PII as possible).
  * `FPO_ADMIN` accounts get a `Farmer` profile. That profile's `fpo_id` is how
    an admin is linked to their FPO (used by /fpo/farmers and /pools).
"""
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping, Optional, Union

from app.models.user import Buyer, Farmer, User

Profile = Union[Farmer, Buyer]

# 15-char GSTIN: 2-digit state code, 10-char PAN, entity no., 'Z', checksum.
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


class ProfileCreator(ABC):
    """Abstract creator: builds the role-specific profile for a `User`."""

    @abstractmethod
    def create(self, user: User, payload: Mapping[str, Any]) -> Profile: ...


class FarmerProfileCreator(ProfileCreator):
    def create(self, user: User, payload: Mapping[str, Any]) -> Farmer:
        return Farmer(user_id=user.id, user=user, fpo_id=_optional_int(payload.get("fpo_id")))


class BuyerProfileCreator(ProfileCreator):
    def create(self, user: User, payload: Mapping[str, Any]) -> Buyer:
        gst_number = payload.get("gst_number")
        gst_last4: Optional[str] = None
        if gst_number:
            gst_number = str(gst_number).strip().upper()
            if not GSTIN_RE.match(gst_number):
                raise ValueError("Invalid GST number")
            gst_last4 = gst_number[-4:]
        return Buyer(
            user_id=user.id,
            user=user,
            company_name=payload.get("company_name") or payload.get("business_name"),
            gst_last4=gst_last4,
        )


class UserFactory:
    """Registry-backed factory that picks the right `ProfileCreator` for a role."""

    _creators: Dict[str, ProfileCreator] = {
        "FARMER": FarmerProfileCreator(),
        "FPO_ADMIN": FarmerProfileCreator(),
        "BUYER": BuyerProfileCreator(),
    }

    @classmethod
    def register(cls, role: str, creator: ProfileCreator) -> None:
        """Extension point (OCP): plug in a new role without editing callers."""
        cls._creators[role.strip().upper()] = creator

    @classmethod
    def supported_roles(cls) -> list[str]:
        return sorted(cls._creators)

    @classmethod
    def create_user_profile(cls, user: User, payload: Mapping[str, Any]) -> Profile:
        role = str(payload.get("role") or user.role or "").strip().upper()
        creator = cls._creators.get(role)
        if creator is None:
            raise ValueError(f"Invalid user role: {role or '<empty>'}")
        return creator.create(user, payload)


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)
