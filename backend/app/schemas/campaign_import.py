"""Structured historical campaign import schema. Missing facts stay unset — never guessed."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SourcedValue(BaseModel):
    value: Optional[Any] = None
    source_filename: Optional[str] = None
    source_type: Optional[str] = None
    confidence: Optional[float] = None


class ExtractedCreator(BaseModel):
    name: Optional[str] = None
    handle: Optional[str] = None
    platform: Optional[str] = None
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    category: Optional[str] = None
    followers: Optional[int] = None
    engagement_rate: Optional[float] = None
    audience_fit_score: Optional[float] = None
    match_score: Optional[float] = None
    predicted_roas: Optional[float] = None
    discovery_decision: Optional[str] = None
    outreach_result: Optional[str] = None
    shortlisted: Optional[bool] = None
    approved: Optional[bool] = None
    discovered: Optional[bool] = None


class ExtractedOutreach(BaseModel):
    creator_name: Optional[str] = None
    outreach_sent: Optional[bool] = None
    outreach_date: Optional[str] = None
    message: Optional[str] = None
    creator_reply: Optional[str] = None
    reply_date: Optional[str] = None
    status: Optional[str] = None
    negotiation_status: Optional[str] = None
    final_agreed_price: Optional[float] = None
    currency: Optional[str] = None
    deliverables: Optional[List[str]] = None


class ExtractedContract(BaseModel):
    creator_name: Optional[str] = None
    contract_status: Optional[str] = None
    compensation: Optional[float] = None
    currency: Optional[str] = None
    deliverables: Optional[List[str]] = None
    payment_terms: Optional[str] = None
    usage_rights: Optional[str] = None
    exclusivity: Optional[str] = None
    signed_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ExtractedContent(BaseModel):
    creator_name: Optional[str] = None
    platform: Optional[str] = None
    content_url: Optional[str] = None
    video_id: Optional[str] = None
    published_at: Optional[str] = None
    content_type: Optional[str] = None


class ExtractedPerformance(BaseModel):
    creator_name: Optional[str] = None
    views: Optional[int] = None
    reach: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    clicks: Optional[int] = None
    conversions: Optional[int] = None
    engagement: Optional[float] = None
    spend: Optional[float] = None
    revenue: Optional[float] = None
    roas: Optional[float] = None
    roi: Optional[float] = None
    performance_status: Optional[str] = None
    measurement_date: Optional[str] = None
    metric_kind: str = "HISTORICAL_REPORTED"


class ExtractedOptimization(BaseModel):
    recommendations: Optional[List[str]] = None
    approved_actions: Optional[List[str]] = None
    rejected_actions: Optional[List[str]] = None
    status: Optional[str] = None


class ExtractedApproval(BaseModel):
    kind: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class StageEvidence(BaseModel):
    campaign: bool = False
    strategy: bool = False
    discovery: bool = False
    shortlist: bool = False
    outreach: bool = False
    negotiation: bool = False
    contract: bool = False
    content: bool = False
    performance: bool = False
    optimization: bool = False
    approval: bool = False


class DuplicateMatch(BaseModel):
    campaign_id: str
    campaign_name: str
    confidence: str = "HIGH"
    reason: str = ""


class FieldConflict(BaseModel):
    entity: str
    field: str
    values: List[Dict[str, Any]] = Field(default_factory=list)


class HistoricalCampaignCandidate(BaseModel):
    key: str
    external_id: Optional[str] = None
    campaign_name: Optional[str] = None
    brand: Optional[str] = None
    product: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    platform: Optional[str] = None
    audience: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[float] = None
    actual_spend: Optional[float] = None
    reported_status: Optional[str] = None
    reported_stage: Optional[str] = None
    selected_count: Optional[int] = None
    creators: List[ExtractedCreator] = Field(default_factory=list)
    outreach_records: List[ExtractedOutreach] = Field(default_factory=list)
    negotiations: List[ExtractedOutreach] = Field(default_factory=list)
    contracts: List[ExtractedContract] = Field(default_factory=list)
    content_records: List[ExtractedContent] = Field(default_factory=list)
    performance_records: List[ExtractedPerformance] = Field(default_factory=list)
    optimization_records: List[ExtractedOptimization] = Field(default_factory=list)
    approvals: List[ExtractedApproval] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    conflicts: List[FieldConflict] = Field(default_factory=list)
    evidence: StageEvidence = Field(default_factory=StageEvidence)
    classification: str = "NEEDS_REVIEW"  # COMPLETED | IN_PROGRESS | NEEDS_REVIEW
    current_stage: Optional[str] = None
    next_step_key: Optional[str] = None
    continue_route: Optional[str] = None
    continue_tab: Optional[str] = None
    workflow_state: Optional[str] = None
    duplicate: Optional[DuplicateMatch] = None
    confidence: float = 0.0
    user_classification: Optional[str] = None
    import_action: str = "IMPORT"  # IMPORT | MERGE | SKIP


class HistoricalCampaignImportPreview(BaseModel):
    model_config = ConfigDict(extra="ignore")

    import_id: str
    status: str
    detected_campaigns: int = 0
    completed_campaigns: int = 0
    in_progress_campaigns: int = 0
    needs_review: int = 0
    creator_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    campaigns: List[HistoricalCampaignCandidate] = Field(default_factory=list)
    files: List[Dict[str, Any]] = Field(default_factory=list)


class ConfirmImportRequest(BaseModel):
    campaigns: Optional[List[Dict[str, Any]]] = None


class ResolveConflictRequest(BaseModel):
    campaign_key: str
    entity: str
    field: str
    chosen_value: Any
    source_filename: Optional[str] = None


class ClassifyCampaignRequest(BaseModel):
    campaign_key: str
    classification: str  # COMPLETED | IN_PROGRESS | NEEDS_REVIEW
    import_action: Optional[str] = None  # IMPORT | MERGE | SKIP
    merge_campaign_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    campaign_id: Optional[str] = None
    import_id: Optional[str] = None


class ChatActionCard(BaseModel):
    label: str
    href: Optional[str] = None
    action: Optional[str] = None
    campaign_id: Optional[str] = None
    import_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    actions: List[ChatActionCard] = Field(default_factory=list)
    preview: Optional[HistoricalCampaignImportPreview] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)
