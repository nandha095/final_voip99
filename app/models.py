from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


CallState = Literal["queued", "ringing", "answered", "completed", "failed", "hangup"]


class CallRequest(BaseModel):
    destination: str = Field(min_length=3, max_length=32)
    caller_id: Optional[str] = Field(default=None, max_length=64)
    metadata: dict = Field(default_factory=dict)


class CallRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    destination: str
    caller_id: Optional[str] = None
    state: CallState = "queued"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provider_reference: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    error: Optional[str] = None


class CallStatusResponse(BaseModel):
    call: CallRecord


class PublicSipConfig(BaseModel):
    websocket_url: str
    uri: str
    authorization_username: str
    password: str
    display_name: str
