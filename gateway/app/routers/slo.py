"""SLO (Service Level Objective) API endpoints."""

from fastapi import APIRouter, Query
from typing import Optional

from ..slo import get_slo_config, get_slo_evaluator

router = APIRouter(prefix="/slo", tags=["slo"])


@router.get("/targets")
async def get_targets():
    """Get SLO targets configuration."""
    config = get_slo_config()
    return {"targets": config.get_targets()}


@router.get("/status")
async def get_status(check: Optional[str] = Query(None, description="Check type (e.g., 'canary')")):
    """Get current SLO status."""
    evaluator = get_slo_evaluator()
    is_canary_check = check == "canary"
    status = await evaluator.check_status(check_canary=is_canary_check)
    
    # For canary checks, return simple ok/eligible format
    if is_canary_check:
        return {"ok": status["ok"], "eligible": status["ok"]}
    
    return status

