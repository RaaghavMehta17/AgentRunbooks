from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..feature_flags import get_all_flags
from ..models import FeatureFlag

router = APIRouter()


class FeatureFlagCreate(BaseModel):
    tool: str
    mode: str  # "real" or "mock"


class FeatureFlagRead(BaseModel):
    tool: str
    mode: str
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/feature-flags", response_model=FeatureFlagRead, status_code=status.HTTP_201_CREATED)
def create_feature_flag(
    payload: FeatureFlagCreate, request: Request, db: Session = Depends(get_db)
) -> FeatureFlagRead:
    """Create or update a feature flag."""
    if payload.mode not in ("real", "mock"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="mode must be 'real' or 'mock'"
        )

    flag = db.get(FeatureFlag, payload.tool)
    if flag:
        flag.mode = payload.mode
        flag.updated_at = datetime.now(timezone.utc)
    else:
        flag = FeatureFlag(tool=payload.tool, mode=payload.mode)
        db.add(flag)

    db.commit()
    db.refresh(flag)

    write_audit(
        actor_type="user",
        actor_id="admin",
        tenant_id=getattr(request.state, "tenant_id", "default"),
        action="feature_flag.update",
        resource_type="feature_flag",
        resource_id=payload.tool,
        payload={"tool": payload.tool, "mode": payload.mode},
    )

    return FeatureFlagRead.model_validate(flag)


@router.get("/feature-flags", response_model=dict[str, str])
def list_feature_flags() -> dict[str, str]:
    """List all feature flags (env + DB)."""
    return get_all_flags()

