from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    userId: str = Field(..., validation_alias="user_id", serialization_alias="userId")
    campaignId: str = Field(..., validation_alias="campaign_id", serialization_alias="campaignId")
    agentName: str = Field(..., validation_alias="agent_name", serialization_alias="agentName")
    agentVersion: str = Field(..., validation_alias="agent_version", serialization_alias="agentVersion")
    status: str
    trigger: str
    inputSummary: Optional[str] = Field(None, validation_alias="input_summary", serialization_alias="inputSummary")
    outputJson: Optional[Dict[str, Any]] = Field(
        None, validation_alias="output_json", serialization_alias="outputJson"
    )
    confidence: Optional[float] = None
    requiresApproval: bool = Field(
        False, validation_alias="requires_approval", serialization_alias="requiresApproval"
    )
    errorMessage: Optional[str] = Field(
        None, validation_alias="error_message", serialization_alias="errorMessage"
    )
    provider: Optional[str] = None
    model: Optional[str] = None
    providerLatencyMs: Optional[float] = Field(
        None, validation_alias="provider_latency_ms", serialization_alias="providerLatencyMs"
    )
    startedAt: Optional[datetime] = Field(None, validation_alias="started_at", serialization_alias="startedAt")
    completedAt: Optional[datetime] = Field(
        None, validation_alias="completed_at", serialization_alias="completedAt"
    )
    createdAt: datetime = Field(..., validation_alias="created_at", serialization_alias="createdAt")

    @field_validator("userId", mode="before")
    @classmethod
    def coerce_user_id(cls, v: Any) -> str:
        if isinstance(v, UUID):
            return str(v)
        return str(v)


class CampaignStrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    campaignId: str = Field(..., validation_alias="campaign_id", serialization_alias="campaignId")
    agentRunId: Optional[str] = Field(
        None, validation_alias="agent_run_id", serialization_alias="agentRunId"
    )
    strategyJson: Dict[str, Any] = Field(
        ..., validation_alias="strategy_json", serialization_alias="strategyJson"
    )
    version: int
    createdAt: datetime = Field(..., validation_alias="created_at", serialization_alias="createdAt")
    updatedAt: datetime = Field(..., validation_alias="updated_at", serialization_alias="updatedAt")


class SupervisorStartResponse(BaseModel):
    campaignId: str
    workflowState: str
    next: Optional[str] = None
    message: str
    agentRun: Optional[AgentRunResponse] = None


class AIStatusResponseSchema(BaseModel):
    provider: str
    configured: bool
    reachable: bool
    modelConfigured: bool = Field(..., alias="model_configured")
    model: Optional[str] = None
    detail: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
