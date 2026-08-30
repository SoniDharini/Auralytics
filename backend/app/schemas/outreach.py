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
    negotiationState: Optional[str] = Field("INITIAL_OUTREACH", alias="negotiation_state")
    responseStatus: Optional[str] = Field("PENDING_RESPONSE", alias="response_status")
    responseText: Optional[str] = Field(None, alias="response_text")
    finalAmount: Optional[float] = Field(None, alias="final_amount")
    currency: Optional[str] = Field("INR", alias="currency")
    deliverables: Optional[List[str]] = Field(default_factory=list, alias="deliverables")
    timelineStart: Optional[str] = Field(None, alias="timeline_start")
    timelineEnd: Optional[str] = Field(None, alias="timeline_end")
    additionalTerms: Optional[str] = Field(None, alias="additional_terms")
    rejectionReason: Optional[str] = Field(None, alias="rejection_reason")
    rejectionNotes: Optional[str] = Field(None, alias="rejection_notes")
    contractId: Optional[str] = Field(None, alias="contract_id")
    extractedTerms: Optional[dict] = Field(default_factory=dict, alias="extracted_terms")
    conversationHistory: Optional[List[dict]] = Field(default_factory=list, alias="conversation_history")
    createdAt: Optional[Any] = Field(None, alias="created_at")
    updatedAt: Optional[Any] = Field(None, alias="updated_at")


class OutreachGenerateRequest(BaseModel):
    influencer_id: Optional[str] = None


class OutreachStatusUpdate(BaseModel):
    status: str
    reply: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    short_dm: Optional[str] = None
    negotiation_state: Optional[str] = None
    extracted_terms: Optional[dict] = None


class OutreachNegotiateRequest(BaseModel):
    influencer_reply: str = Field(..., description="The pasted response from the creator")
    user_instruction: Optional[str] = Field(None, description="Optional steering instruction (e.g. 'Counteroffer ₹55,000')")


class OutreachNegotiateResponse(BaseModel):
    conversation_state: str
    influencer_reply_summary: str
    extracted_terms: dict
    recommended_action: str
    subject: Optional[str] = None
    message: str
    short_dm: Optional[str] = None
    confidence: float = 0.90
    budget_constraint_warning: Optional[str] = None
    outreach_message: Optional[OutreachResponse] = None


class OutreachStatusDecisionRequest(BaseModel):
    status: str = Field(..., description="ACCEPTED | DECLINED | REJECTED | NEGOTIATING | CONTACTED")
    agreed_terms: Optional[dict] = None
    note: Optional[str] = None


class OutreachAcceptanceRequest(BaseModel):
    response_notes: Optional[str] = Field(None, description="Creator response text or negotiation notes")
    final_amount: float = Field(..., gt=0, description="Final agreed collaboration amount in specified currency")
    currency: str = Field(default="INR", description="Currency code (INR, USD, etc.)")
    deliverables: List[str] = Field(..., min_length=1, description="List of agreed deliverables")
    timeline_start: str = Field(..., min_length=1, description="Campaign / deliverable start date")
    timeline_end: str = Field(..., min_length=1, description="Campaign / deliverable end date")
    additional_terms: Optional[str] = Field(None, description="Additional special terms or approval conditions")


class OutreachRejectionRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=1, description="Reason for rejection")
    rejection_notes: Optional[str] = Field(None, description="Additional notes regarding the rejection")
