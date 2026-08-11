from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject|edit)$")
    reason: Optional[str] = None


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    agent: str
    type: str
    action: str
    reason: str
    campaign: str
    financialImpact: str = Field(..., alias="financial_impact")
    confidence: float
    timestamp: str
    status: str
