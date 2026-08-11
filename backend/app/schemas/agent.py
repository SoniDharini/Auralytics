from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    role: str
    status: str
    currentTask: str = Field(..., alias="current_task")
    lastAction: str = Field(..., alias="last_action")
    tasksCompleted: int = Field(..., alias="tasks_completed")
    avgExecutionTime: str = Field(..., alias="avg_execution_time")
    successRate: float = Field(..., alias="success_rate")
    lastActive: str = Field(..., alias="last_active")
    progress: Optional[int] = None
    startedAt: Optional[str] = Field(None, alias="started_at")


class TimelineEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    time: str
    agent: str
    message: str
    type: str
