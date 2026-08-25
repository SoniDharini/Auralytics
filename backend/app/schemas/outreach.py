from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OutreachResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    campaignId: Optional[str] = Field(None, alias="campaign_id")
    influencerId: str = Field(..., alias="influencer_id")
    agentRunId: Optional[str] = Field(None, alias="agent_run_id")
    influencerName: str = Field(..., alias="influencer_name")
    influencerUsername: str = Field(..., alias="influencer_username")
    campaignName: str = Field(..., alias="campaign_name")
    channel: str
    subject: Optional[str] = None
    body: str
    shortDm: Optional[str] = Field(None, alias="short_dm")
    callToAction: Optional[str] = Field(None, alias="call_to_action")
    personalizationPoints: Optional[List[str]] = Field(None, alias="personalization_points")
    confidence: Optional[float] = None
    status: str
    sentAt: Optional[str] = Field(None, alias="sent_at")
    reply: Optional[str] = None
    createdAt: Optional[Any] = Field(None, alias="created_at")


class OutreachGenerateRequest(BaseModel):
    influencer_id: Optional[str] = None


class OutreachStatusUpdate(BaseModel):
    status: str
    reply: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    short_dm: Optional[str] = None
