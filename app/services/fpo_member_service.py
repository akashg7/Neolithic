"""FPO membership directory: which farmers belong to an FPO. Owner: Member 1.

(Lot pooling/aggregation for FPOs lives in fpo_service.py and is not part of
this module.)
"""
from fastapi import Depends, HTTPException, status

from app.dependencies.repositories import get_fpo_repository
from app.models.user import User
from app.repositories.fpo_repository import IFpoRepository
from app.schemas.user import FarmerOut


class FpoMemberService:
    def __init__(self, fpo_repo: IFpoRepository):
        self.fpo_repo = fpo_repo

    async def list_farmers_for_admin(self, admin: User) -> list[FarmerOut]:
        """Farmers in the admin's own FPO. The FPO comes from the admin's
        identity, never from a client-supplied parameter."""
        fpo_id = await self.fpo_repo.get_fpo_id_for_user(admin.id)
        if fpo_id is None:
            # 404 (not 403): don't reveal anything to an admin without an FPO.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FPO not found")

        farmers = await self.fpo_repo.list_farmers(fpo_id)
        return [
            FarmerOut(
                user_id=f.user_id,
                name=f.user.name,
                phone=f.user.phone,
                district_id=f.user.district_id,
                village=f.user.village,
                fpo_id=f.fpo_id,
                verified=bool(f.user.verified),
            )
            for f in farmers
            # The admin's own Farmer row (it links them to the FPO) is not a member farmer.
            if f.user_id != admin.id
        ]


def get_fpo_member_service(fpo_repo: IFpoRepository = Depends(get_fpo_repository)) -> FpoMemberService:
    return FpoMemberService(fpo_repo)
