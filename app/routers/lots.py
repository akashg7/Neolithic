from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.schemas.lot import (
    LotCreate, LotOut, SelfAssayRequest, SelfAssayResponse,
    PriceSuggestionResponse,
)
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
    # Ensure lot exists and belongs to user
    lot = await lot_service.get_lot(db, user, int(lot_id))
    if not lot:
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
        
        # Update lot photo_path in DB
        lot.photo_path = photo_path
        await db.commit()
        
        return {"photo_path": photo_path}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image file")
