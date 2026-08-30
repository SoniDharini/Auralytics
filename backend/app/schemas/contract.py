from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    campaignId: Optional[str] = Field(None, alias="campaign_id")
    influencerId: Optional[str] = Field(None, alias="influencer_id")
    outreachId: Optional[str] = Field(None, alias="outreach_id")
    creator: str
    username: str
    campaign: str
    value: float
    currency: Optional[str] = "INR"
    status: str
    startDate: str = Field(..., alias="start_date")
    endDate: str = Field(..., alias="end_date")
    paymentDue: str = Field(..., alias="payment_due")
    risk: str
    deliverables: List[str]
    usageRights: str = Field(..., alias="usage_rights")
    exclusivity: str
    additionalTerms: Optional[str] = Field(None, alias="additional_terms")
    contractBody: Optional[str] = Field(None, alias="contract_body")
    aiRisks: List[str] = Field(default_factory=list, alias="ai_risks")
