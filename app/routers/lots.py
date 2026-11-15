from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.dependencies.lots import get_lot_grading_service
from app.models.lot import Lot
from app.schemas.lot import (
    LotCreate, LotOut, SelfAssayRequest, SelfAssayResponse,
    PriceSuggestionResponse, GradeRequest, GradeResultOut,
)
from app.services.lot_grading_service import LotGradingService
from app.schemas.matches import MatchesRes
from app.services import lot_service
from fastapi import UploadFile, File, HTTPException
import io
from PIL import Image

router = APIRouter()


@router.post("", response_model=LotOut, status_code=status.HTTP_201_CREATED)
async def create_lot(
    payload: LotCreate,
    user: User = Depends(require_role("FARMER", "FPO_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new lot. Auto-calls Price Engine for price band."""
    return await lot_service.create_lot(db, user, payload)


@router.get("", response_model=list[LotOut])
async def list_lots(
    status: Optional[str] = None,
    user: User = Depends(require_role("FARMER", "FPO_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """List lots owned by the current farmer, optionally filtered by status."""
    return await lot_service.list_lots(db, user, status)


@router.get("/{lot_id}", response_model=LotOut)
async def get_lot(
    lot_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single lot. Checks ownership or buyer-has-offer access."""
    return await lot_service.get_lot(db, user, int(lot_id))


@router.post("/{lot_id}/assay", response_model=SelfAssayResponse)
async def submit_self_assay(
    lot_id: str,
    payload: SelfAssayRequest,
    user: User = Depends(require_role("FARMER", "FPO_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Submit self-assay quality answers for a lot. Returns computed grade."""
    return await lot_service.submit_self_assay(db, user, int(lot_id), payload)


@router.post("/{lot_id}/grade", response_model=GradeResultOut)
async def grade_lot(
    lot_id: int,
    payload: GradeRequest,
    user: User = Depends(require_role("FARMER", "FPO_ADMIN")),
    service: LotGradingService = Depends(get_lot_grading_service),
):
    """Grade a lot (A/B/C) from measured parameters using the crop's grading
    strategy. Returns the grade, assessed value and improvement advice."""
    return await service.grade_lot(user, lot_id, payload)


@router.get("/{lot_id}/price-suggestion", response_model=PriceSuggestionResponse)
async def get_price_suggestion(
    lot_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get price band + SELL/HOLD/NO_ADVICE recommendation for a lot."""
    return await lot_service.get_price_suggestion(db, user, int(lot_id))


@router.get("/{lot_id}/matches", response_model=MatchesRes)
async def get_lot_matches(
    lot_id: str,
    user: User = Depends(require_role("FARMER", "FPO_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Find matching buyer demands for a lot."""
    return await lot_service.get_lot_matches(db, user, int(lot_id))

@router.post("/{lot_id}/photo")
async def upload_lot_photo(
    lot_id: str,
    file: UploadFile = File(...),
    user: User = Depends(require_role("FARMER", "FPO_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Upload lot photo, strip EXIF GPS, and save."""
    # Ensure lot exists and belongs to user (owner only; buyers can't upload)
    lot = await db.get(Lot, int(lot_id))
    if lot is None or lot.farmer_id != user.id:
        raise HTTPException(status_code=404, detail="Lot not found")

    content = await file.read()
    
    try:
        # Open image using Pillow to strip EXIF
        image = Image.open(io.BytesIO(content))
        
        # Strip EXIF by re-saving without the exif data
        output_io = io.BytesIO()
        image.convert("RGB").save(output_io, format="JPEG")
        
        # Mock upload to MinIO
        photo_path = f"lots/{lot_id}/photo.jpg"
        
        # Save on the DB row (LotOut exposes image_url as photo_path)
        lot.image_url = photo_path
        await db.commit()
        
        return {"photo_path": photo_path}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image file")
