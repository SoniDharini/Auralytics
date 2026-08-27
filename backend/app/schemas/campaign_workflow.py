"""Read-only campaign journey guidance — derived from existing records."""

from typing import List, Optional

from pydantic import BaseModel, Field


class WorkflowAction(BaseModel):
    key: str
    label: str
    description: str
    route: str
    tab: Optional[str] = None
    enabled: bool = True
    running: bool = False


class WorkflowStep(BaseModel):
    key: str
    label: str
    status: str
    route: Optional[str] = None
    tab: Optional[str] = None
    hint: Optional[str] = None


class CampaignWorkflowResponse(BaseModel):
    campaign_id: str
    current_step: str
    next_step: str
    progress_percentage: int = Field(..., ge=0, le=100)
    blocking_reason: Optional[str] = None
    next_action: WorkflowAction
    steps: List[WorkflowStep]
    discovered_count: int = 0
    shortlisted_count: int = 0
    outreach_count: int = 0
    pending_approval: bool = False
