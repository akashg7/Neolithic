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
    AssayRecordOut, LotPublishRequest,
)
from app.services.lot_grading_service import LotGradingService
from app.schemas.matches import MatchesRes
from app.services import lot_service
from fastapi import UploadFile, File, HTTPException, Response
import io
import logging
from pathlib import Path
from PIL import Image
from app.utils import s3 as s3_utils

logger = logging.getLogger("krishi.lots.router")
_LOCAL_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "data" / "uploads"

router = APIRouter()


def _lot_pk(lot_id: str) -> int:
    """Lot ids are integers; anything else is simply a lot that doesn't exist."""
    if not str(lot_id).isdigit():
        raise HTTPException(status_code=404, detail="Lot not found")
    return int(lot_id)


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
    return await lot_service.get_lot(db, user, _lot_pk(lot_id))


@router.get("/{lot_id}/assay", response_model=AssayRecordOut)
async def get_lot_assay(
    lot_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The lot's stored self-assay answers + derived grade. Owner, or a buyer with an offer on it."""
    return await lot_service.get_lot_assay(db, user, _lot_pk(lot_id))


@router.post("/{lot_id}/publish", response_model=LotOut)
async def publish_lot(
    lot_id: str,
    payload: LotPublishRequest,
    user: User = Depends(require_role("FARMER", "FPO_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Set the asking price and list the lot to buyers. Owner only."""
    return await lot_service.publish_lot(db, user, _lot_pk(lot_id), payload.expected_price_paise)


@router.post("/{lot_id}/assay", response_model=SelfAssayResponse)
async def submit_self_assay(
    lot_id: str,
    payload: SelfAssayRequest,
    user: User = Depends(require_role("FARMER", "FPO_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Submit self-assay quality answers for a lot. Returns computed grade."""
    return await lot_service.submit_self_assay(db, user, _lot_pk(lot_id), payload)


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
    return await lot_service.get_price_suggestion(db, user, _lot_pk(lot_id))


@router.get("/{lot_id}/matches", response_model=MatchesRes)
async def get_lot_matches(
    lot_id: str,
    user: User = Depends(require_role("FARMER", "FPO_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Find matching buyer demands for a lot."""
    return await lot_service.get_lot_matches(db, user, _lot_pk(lot_id))

@router.post("/{lot_id}/photo")
async def upload_lot_photo(
    lot_id: str,
    file: UploadFile = File(...),
    user: User = Depends(require_role("FARMER", "FPO_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Upload lot photo, strip EXIF metadata, store in MinIO/S3 (with local fallback), and link on Lot."""
    pk = _lot_pk(lot_id)
    lot = await db.get(Lot, pk)
    if lot is None or lot.farmer_id != user.id:
        raise HTTPException(status_code=404, detail="Lot not found")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty image upload")

    try:
        image = Image.open(io.BytesIO(content))
        output_io = io.BytesIO()
        image.convert("RGB").save(output_io, format="JPEG", quality=88)
        jpeg_bytes = output_io.getvalue()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")

    storage_key = f"lots/{pk}/photo.jpg"
    local_file = _LOCAL_UPLOAD_ROOT / storage_key
    local_file.parent.mkdir(parents=True, exist_ok=True)
    local_file.write_bytes(jpeg_bytes)

    try:
        await s3_utils.upload_file(jpeg_bytes, storage_key, content_type="image/jpeg")
    except Exception as exc:
        logger.warning("MinIO upload failed for %s (%s); serving via local cache", storage_key, exc)

    photo_path = f"/api/v1/lots/{pk}/photo"
    lot.image_url = photo_path
    await db.commit()

    return {"photo_path": photo_path}


@router.get("/{lot_id}/photo")
async def get_lot_photo(lot_id: str):
    """Serve an uploaded lot photo from MinIO/S3 or local fallback."""
    pk = _lot_pk(lot_id)
    storage_key = f"lots/{pk}/photo.jpg"
    data = await s3_utils.download_file(storage_key)
    if data is None:
        local_file = _LOCAL_UPLOAD_ROOT / storage_key
        if local_file.is_file():
            data = local_file.read_bytes()
    if data is None:
        raise HTTPException(status_code=404, detail="Lot photo not found")
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=300"},
    )
