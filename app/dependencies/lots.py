"""FastAPI providers for Pranay's lot grading and pooling (DIP).

Interfaces are bound to concrete SQLAlchemy classes here and nowhere else.
Tests replace any of these with `app.dependency_overrides[...]`.
Owner: Pranay.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.repositories import get_fpo_repository
from app.engines.strategies.grading_strategy import GradingStrategyRegistry, build_default_registry
from app.repositories.fpo_repository import IFpoRepository
from app.repositories.lot_repository import (
    ICommodityRepository,
    ILotRepository,
    SQLAlchemyCommodityRepository,
    SQLAlchemyLotRepository,
)
from app.services.lot_grading_service import LotGradingService
from app.services.lot_pool_service import LotPoolService

_registry = build_default_registry()


def get_lot_repository(db: AsyncSession = Depends(get_db)) -> ILotRepository:
    return SQLAlchemyLotRepository(db)


def get_commodity_repository(db: AsyncSession = Depends(get_db)) -> ICommodityRepository:
    return SQLAlchemyCommodityRepository(db)


def get_grading_registry() -> GradingStrategyRegistry:
    return _registry


def get_lot_grading_service(
    lot_repo: ILotRepository = Depends(get_lot_repository),
    commodity_repo: ICommodityRepository = Depends(get_commodity_repository),
    registry: GradingStrategyRegistry = Depends(get_grading_registry),
) -> LotGradingService:
    return LotGradingService(lot_repo, commodity_repo, registry)


def get_lot_pool_service(
    lot_repo: ILotRepository = Depends(get_lot_repository),
    fpo_repo: IFpoRepository = Depends(get_fpo_repository),
) -> LotPoolService:
    return LotPoolService(lot_repo, fpo_repo)
