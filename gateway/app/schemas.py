from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RunbookBase(BaseModel):
    name: str = Field(..., min_length=1)
    yaml: str = Field(..., min_length=1)


class RunbookCreate(RunbookBase):
    pass


class RunbookRead(RunbookBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class PolicyBase(BaseModel):
    name: str = Field(..., min_length=1)
    yaml: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)


class PolicyCreate(PolicyBase):
    pass


class PolicyRead(PolicyBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


RunbookList = List[RunbookRead]
PolicyList = List[PolicyRead]


class StepRead(BaseModel):
    id: str
    name: str
    tool: str
    status: str
    input: Optional[dict] = None
    output: Optional[dict] = None
    error: Optional[dict] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RunRead(BaseModel):
    id: str
    runbook_id: str
    status: str
    metrics: dict
    created_at: datetime
    steps: List[StepRead] = []

    class Config:
        from_attributes = True

