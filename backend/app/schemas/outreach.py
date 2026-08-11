from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class OutreachResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    influencerId: str = Field(..., alias="influencer_id")
    influencerName: str = Field(..., alias="influencer_name")
    influencerUsername: str = Field(..., alias="influencer_username")
    campaignName: str = Field(..., alias="campaign_name")
    channel: str
    subject: Optional[str] = None
    body: str
    status: str
    sentAt: Optional[str] = Field(None, alias="sent_at")
    reply: Optional[str] = None


class OutreachStatusUpdate(BaseModel):
    status: str
    reply: Optional[str] = None
