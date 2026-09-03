"""Deterministic campaign workflow states for the Supervisor."""

from __future__ import annotations


class WorkflowState:
    CAMPAIGN_CREATED = "CAMPAIGN_CREATED"
    STRATEGY_PENDING = "STRATEGY_PENDING"
    STRATEGY_COMPLETED = "STRATEGY_COMPLETED"
    DISCOVERY_PENDING = "DISCOVERY_PENDING"
    DISCOVERY_COMPLETED = "DISCOVERY_COMPLETED"
    SHORTLIST_APPROVAL_PENDING = "SHORTLIST_APPROVAL_PENDING"
    SHORTLIST_APPROVED = "SHORTLIST_APPROVED"
    OUTREACH_PENDING = "OUTREACH_PENDING"
    OUTREACH_COMPLETED = "OUTREACH_COMPLETED"
    CONTRACT_PENDING = "CONTRACT_PENDING"
    CONTRACT_COMPLETED = "CONTRACT_COMPLETED"
    CAMPAIGN_LIVE = "CAMPAIGN_LIVE"
    PERFORMANCE_MONITORING = "PERFORMANCE_MONITORING"
    OPTIMIZATION_PENDING = "OPTIMIZATION_PENDING"
    OPTIMIZATION_APPROVAL_PENDING = "OPTIMIZATION_APPROVAL_PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    ALL = (
        CAMPAIGN_CREATED,
        STRATEGY_PENDING,
        STRATEGY_COMPLETED,
        DISCOVERY_PENDING,
        DISCOVERY_COMPLETED,
        SHORTLIST_APPROVAL_PENDING,
        SHORTLIST_APPROVED,
        OUTREACH_PENDING,
        OUTREACH_COMPLETED,
        CONTRACT_PENDING,
        CONTRACT_COMPLETED,
        CAMPAIGN_LIVE,
        PERFORMANCE_MONITORING,
        OPTIMIZATION_PENDING,
        OPTIMIZATION_APPROVAL_PENDING,
        COMPLETED,
        FAILED,
    )


# Allowed next states from each state (deterministic; not LLM-decided).
ALLOWED_TRANSITIONS = {
    WorkflowState.CAMPAIGN_CREATED: {WorkflowState.STRATEGY_PENDING},
    WorkflowState.STRATEGY_PENDING: {
        WorkflowState.STRATEGY_COMPLETED,
        WorkflowState.FAILED,
    },
    WorkflowState.STRATEGY_COMPLETED: {WorkflowState.DISCOVERY_PENDING},
    WorkflowState.DISCOVERY_PENDING: {
        WorkflowState.DISCOVERY_COMPLETED,
        WorkflowState.FAILED,
    },
    WorkflowState.DISCOVERY_COMPLETED: {
        WorkflowState.SHORTLIST_APPROVAL_PENDING,
        WorkflowState.DISCOVERY_PENDING,
    },
    WorkflowState.SHORTLIST_APPROVAL_PENDING: {
        WorkflowState.SHORTLIST_APPROVED,
        WorkflowState.DISCOVERY_PENDING,
    },
    WorkflowState.SHORTLIST_APPROVED: {WorkflowState.OUTREACH_PENDING},
    WorkflowState.OUTREACH_PENDING: {
        WorkflowState.OUTREACH_COMPLETED,
        WorkflowState.FAILED,
    },
    WorkflowState.OUTREACH_COMPLETED: {WorkflowState.CONTRACT_PENDING},
    WorkflowState.CONTRACT_PENDING: {
        WorkflowState.CONTRACT_COMPLETED,
        WorkflowState.FAILED,
    },
    WorkflowState.CONTRACT_COMPLETED: {WorkflowState.CAMPAIGN_LIVE},
    WorkflowState.CAMPAIGN_LIVE: {WorkflowState.PERFORMANCE_MONITORING},
    WorkflowState.PERFORMANCE_MONITORING: {
        WorkflowState.OPTIMIZATION_PENDING,
        WorkflowState.COMPLETED,
    },
    WorkflowState.OPTIMIZATION_PENDING: {
        WorkflowState.OPTIMIZATION_APPROVAL_PENDING,
        WorkflowState.FAILED,
    },
    WorkflowState.OPTIMIZATION_APPROVAL_PENDING: {
        WorkflowState.PERFORMANCE_MONITORING,
        WorkflowState.OPTIMIZATION_PENDING,
    },
    WorkflowState.COMPLETED: set(),
    WorkflowState.FAILED: {WorkflowState.STRATEGY_PENDING, WorkflowState.DISCOVERY_PENDING},
}


class AgentRunStatus:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    CANCELLED = "CANCELLED"

    ALL = (QUEUED, RUNNING, COMPLETED, FAILED, WAITING_APPROVAL, CANCELLED)


class ApprovalStatus:
    PENDING = "pending"
    APPROVED = "approve"
    REJECTED = "reject"
    MODIFIED = "edit"
    # Canonical uppercase aliases used by new agent code
    PENDING_U = "PENDING"
    APPROVED_U = "APPROVED"
    REJECTED_U = "REJECTED"
    MODIFIED_U = "MODIFIED"


class AgentNames:
    SUPERVISOR = "supervisor"
    STRATEGY = "strategy"
    DISCOVERY = "discovery"
    OUTREACH = "outreach"
    CONTRACT = "contract"
    PERFORMANCE = "performance"
    OPTIMIZATION = "optimization"
