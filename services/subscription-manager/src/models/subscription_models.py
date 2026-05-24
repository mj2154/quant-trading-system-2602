"""Pydantic models for subscription management."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SubscriptionTaskData(BaseModel):
    """Data from a subscription_task_new notification."""

    id: int
    type: str  # subscribe, unsubscribe, heartbeat
    subscription_key: str | None = None
    data_type: str | None = None
    subscriber: str


class SubscriberHeartbeat(BaseModel):
    """Subscriber heartbeat record."""

    subscriber_id: str
    last_heartbeat: datetime


class RealtimeDataRecord(BaseModel):
    """A row from the realtime_data table."""

    id: int
    subscription_key: str
    data_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    event_time: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    subscribers: list[str] = Field(default_factory=list)
