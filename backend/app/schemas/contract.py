from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CompensationTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    total: float = Field(..., ge=0, description="Total agreed compensation amount")
    currency: str = Field(default="INR", description="Currency symbol/code")


class PaymentScheduleTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    structure: str = Field(default="50_50", description="50_50 | 100_completion | custom")
    advance_percentage: float = Field(default=50.0, ge=0, le=100)
    advance_amount: float = Field(default=0.0, ge=0)
    balance_percentage: float = Field(default=50.0, ge=0, le=100)
    balance_amount: float = Field(default=0.0, ge=0)
    method: str = Field(default="Bank Transfer", description="Bank Transfer | UPI | Payment Gateway | Other")
    balance_due_days: int = Field(default=7, ge=0, description="Days after delivery/completion when balance is due")
    terms_text: Optional[str] = Field(default="", description="Detailed summary text of payment schedule")


class TimelineTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    start_date: str = Field(default="", description="Campaign start date")
    end_date: str = Field(default="", description="Campaign end date")
    draft_submission_deadline: Optional[str] = Field(default="", description="Deadline for submitting draft for approval")
    publishing_deadline: Optional[str] = Field(default="", description="Deadline for publishing approved content")


class RevisionTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    allowed_rounds: int = Field(default=2, ge=0, description="Number of included revision rounds")
    scope: str = Field(
        default="Factual accuracy, brand guidelines, approved product claims, and agreed brief requirements.",
        description="Permissible scope of revisions",
    )


class ApprovalTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pre_publication_required: bool = Field(default=True, description="Whether brand approval is required before publishing")
    review_window_days: int = Field(default=3, ge=1, description="Days for brand to review and provide feedback")


class ProductClaimsTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    policy: str = Field(default="BRAND_APPROVED_ONLY", description="BRAND_APPROVED_ONLY | INDEPENDENT_PERMITTED")
    claim_guidelines: str = Field(
        default="Creator shall not make unapproved efficacy, performance, medical, or comparative product claims.",
        description="Rules regarding product claims",
    )


class UsageRightsTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    organic_reposting: bool = Field(default=True, description="Brand can repost content organically on social channels")
    paid_ads: bool = Field(default=False, description="Brand can use content in paid ad campaigns")
    website_use: bool = Field(default=True, description="Brand can display content on website & marketing pages")
    duration: str = Field(default="3 Months", description="Duration of usage license (e.g. 30 Days, 3 Months, 12 Months)")
    territory: str = Field(default="India", description="Geographic scope (e.g. India, Worldwide)")


class OwnershipTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    copyright_owner: str = Field(default="INFLUENCER", description="INFLUENCER | BRAND")
    license_grant: str = Field(
        default="Influencer retains copyright and grants Brand a non-exclusive license as specified in Usage Rights.",
        description="Intellectual property license summary",
    )


class ExclusivityTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    required: bool = Field(default=False, description="Whether category exclusivity is required")
    category: Optional[str] = Field(default="", description="Direct competitor product category (e.g. Skincare serums)")
    duration_days: int = Field(default=30, ge=0, description="Exclusivity duration in days post-publishing")
    scope: Optional[str] = Field(default="", description="Scope and restrictions of exclusivity")


class CancellationTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    brand_cancellation: str = Field(
        default="Brand may cancel prior to draft creation with payment for work performed to date. Advance is refundable if no work commenced.",
        description="Brand cancellation terms",
    )
    influencer_cancellation: str = Field(
        default="Creator cancellation requires full refund of any advance received and return of gifted products.",
        description="Influencer cancellation terms",
    )
    force_majeure: str = Field(
        default="Neither party liable for failure due to unforeseen events beyond reasonable control.",
        description="Force majeure clause",
    )


class TerminationTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")
    grounds: List[str] = Field(
        default_factory=lambda: [
            "Material breach of agreement terms",
            "Failure to deliver content by agreed deadline",
            "Publication without required brand pre-approval",
            "Violation of brand safety or product claim guidelines",
        ]
    )


class ContractTermsPayload(BaseModel):
    """Complete pre-contract commercial terms confirmed by user before contract generation."""
    model_config = ConfigDict(extra="ignore")

    influencer_id: Optional[str] = None
    campaign_id: Optional[str] = None
    creator_name: Optional[str] = None
    creator_username: Optional[str] = None
    campaign_name: Optional[str] = None
    brand_name: Optional[str] = None

    compensation: CompensationTerms
    payment: PaymentScheduleTerms
    deliverables: List[str] = Field(default_factory=list)
    timeline: TimelineTerms = Field(default_factory=TimelineTerms)
    revisions: RevisionTerms = Field(default_factory=RevisionTerms)
    approval: ApprovalTerms = Field(default_factory=ApprovalTerms)
    product_claims: ProductClaimsTerms = Field(default_factory=ProductClaimsTerms)
    usage_rights: UsageRightsTerms = Field(default_factory=UsageRightsTerms)
    ownership: OwnershipTerms = Field(default_factory=OwnershipTerms)
    exclusivity: ExclusivityTerms = Field(default_factory=ExclusivityTerms)
    cancellation: CancellationTerms = Field(default_factory=CancellationTerms)
    termination: TerminationTerms = Field(default_factory=TerminationTerms)
    additional_terms: Optional[str] = Field(default="")

    @model_validator(mode="after")
    def validate_deterministic_math(self) -> "ContractTermsPayload":
        """Ensure payment advance + balance amounts and percentages correctly reconcile."""
        total = self.compensation.total
        p = self.payment
        if p.structure == "50_50":
            p.advance_percentage = 50.0
            p.balance_percentage = 50.0
            p.advance_amount = round(total * 0.5, 2)
            p.balance_amount = round(total - p.advance_amount, 2)
        elif p.structure == "100_completion":
            p.advance_percentage = 0.0
            p.balance_percentage = 100.0
            p.advance_amount = 0.0
            p.balance_amount = total
        else:
            # Custom structure: reconcile amounts from percentages if provided
            if p.advance_amount == 0.0 and p.advance_percentage > 0:
                p.advance_amount = round(total * (p.advance_percentage / 100.0), 2)
                p.balance_amount = round(total - p.advance_amount, 2)
                p.balance_percentage = 100.0 - p.advance_percentage
            elif p.advance_amount > 0:
                p.balance_amount = round(total - p.advance_amount, 2)
                p.advance_percentage = round((p.advance_amount / total) * 100.0, 1) if total > 0 else 0
                p.balance_percentage = round(100.0 - p.advance_percentage, 1)

        # Generate clear readable terms_text
        if p.advance_amount > 0:
            p.terms_text = (
                f"{self.compensation.currency} {p.advance_amount:,.2f} ({p.advance_percentage:.0f}%) advance payable upon agreement execution; "
                f"remaining {self.compensation.currency} {p.balance_amount:,.2f} ({p.balance_percentage:.0f}%) payable via {p.method} within {p.balance_due_days} days of completion."
            )
        else:
            p.terms_text = f"100% of fee ({self.compensation.currency} {total:,.2f}) payable via {p.method} within {p.balance_due_days} days of delivery and approval."

        return self


class ContractReadinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    ready: bool
    status: str = Field(..., description="READY | LOCKED | WAITING | NOT_APPLICABLE | CONTRACT_INFORMATION_REQUIRED")
    missing_fields: List[str] = Field(default_factory=list, alias="missing_fields")
    blocking_reason: Optional[str] = Field(None, alias="blocking_reason")
    final_terms: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="final_terms")
    suggested_terms: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="suggested_terms")
    creator_name: Optional[str] = Field(None, alias="creator_name")
    creator_username: Optional[str] = Field(None, alias="creator_username")
    outreach_status: Optional[str] = Field(None, alias="outreach_status")
    shortlist_status: Optional[str] = Field(None, alias="shortlist_status")
    contract_id: Optional[str] = Field(None, alias="contract_id")


class ContractAnalyzeRequest(BaseModel):
    influencer_id: str = Field(..., description="Influencer ID to analyze/draft contract for")
    contract_text: Optional[str] = Field(None, description="Optional uploaded contract document text to verify against negotiated terms")
    custom_terms: Optional[Dict[str, Any]] = Field(default=None, description="Optional overrides or clarifications")
    confirmed_terms: Optional[ContractTermsPayload] = Field(default=None, description="Full user-confirmed commercial terms payload")


class ContractApprovalRequest(BaseModel):
    notes: Optional[str] = Field(None, description="Optional reviewer sign-off notes")


class ContractChangeRequest(BaseModel):
    requested_changes: str = Field(..., description="Detailed explanation of clauses requiring revision")
    reason: str = Field(..., description="Business or legal rationale")


class ContractRejectRequest(BaseModel):
    reason: str = Field(..., description="Reason for rejection")
    notes: Optional[str] = Field(None, description="Additional notes")


class ContractBodyUpdateRequest(BaseModel):
    contract_body: str = Field(..., description="Updated full agreement text")
    reanalyze: bool = Field(default=False, description="Whether to trigger Contract Agent re-analysis immediately")


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    campaignId: Optional[str] = Field(None, alias="campaign_id")
    influencerId: Optional[str] = Field(None, alias="influencer_id")
    outreachId: Optional[str] = Field(None, alias="outreach_id")
    agentRunId: Optional[str] = Field(None, alias="agent_run_id")
    creator: str
    username: str
    campaign: str
    value: float
    currency: Optional[str] = "INR"
    status: str
    version: int = 1
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

    # Rich analysis & verification metadata
    analysisJson: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="analysis_json")
    missingClauses: List[str] = Field(default_factory=list, alias="missing_clauses")
    conflicts: List[Dict[str, Any]] = Field(default_factory=list, alias="conflicts")
    riskFlags: List[Dict[str, Any]] = Field(default_factory=list, alias="risk_flags")
    commercialTermsMatch: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="commercial_terms_match")
    overallStatus: str = Field(default="READY_FOR_REVIEW", alias="overall_status")

    # Approval and Change Request tracking
    approvedBy: Optional[str] = Field(None, alias="approved_by")
    approvedAt: Optional[datetime] = Field(None, alias="approved_at")
    changeRequests: List[Dict[str, Any]] = Field(default_factory=list, alias="change_requests")
    createdAt: Optional[datetime] = Field(None, alias="created_at")
    updatedAt: Optional[datetime] = Field(None, alias="updated_at")
