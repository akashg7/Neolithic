"""FPO lot aggregation (`POST /api/v1/pools/aggregate`). Owner: Pranay.

The old implementation here read `lot.crop`, `lot.quantity_kg` and
`price_*_paise_per_qtl`, which do not exist on the `Lot` model, so every call
crashed. The logic now lives in `LotPoolService` (shared with the new
`POST /api/v1/fpo/lots/pool`). This function stays so any older caller keeps
working.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.fpo_repository import SQLAlchemyFpoRepository
from app.repositories.lot_repository import SQLAlchemyLotRepository
from app.schemas.lot import BatchLotOut
from app.services.lot_pool_service import LotPoolService


async def aggregate_lots(db: AsyncSession, user: User, lot_ids: list[int]) -> BatchLotOut:
    service = LotPoolService(SQLAlchemyLotRepository(db), SQLAlchemyFpoRepository(db))
    return await service.pool(user, lot_ids)
