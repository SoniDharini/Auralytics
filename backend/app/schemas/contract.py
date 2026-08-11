from typing import List
from pydantic import BaseModel, ConfigDict, Field


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    creator: str
    username: str
    campaign: str
    value: float
    status: str
    startDate: str = Field(..., alias="start_date")
    endDate: str = Field(..., alias="end_date")
    paymentDue: str = Field(..., alias="payment_due")
    risk: str
    deliverables: List[str]
    usageRights: str = Field(..., alias="usage_rights")
    exclusivity: str
    aiRisks: List[str] = Field(..., alias="ai_risks")
