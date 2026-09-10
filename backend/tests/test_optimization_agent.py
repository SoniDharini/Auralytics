"""Optimization Agent validation, freshness, and no-garbage rules."""

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.ai.agents.optimization import (
    OptimizationAgent,
    campaign_timeline,
    cites_unavailable_metric,
    classify_data_quality,
    infer_overall_assessment,
    parse_campaign_date,
    present,
    previous_plan_is_stale,
    unavailable_metric_keys,
)
from app.ai.schemas import AgentResultEnvelope
from app.models.campaign import Campaign


def test_present_does_not_turn_none_into_zero():
    assert present(None) == "NOT_AVAILABLE"
    assert present(0) == 0
    assert present(0.0) == 0.0


def test_first_optimization_run_does_not_treat_missing_previous_plan_as_dict():
    assert previous_plan_is_stale("NOT_AVAILABLE", "panal-1") is False
    assert previous_plan_is_stale(None, "panal-1") is False
    assert previous_plan_is_stale({"performance_analysis_id": "panal-old"}, "panal-1") is True
    assert previous_plan_is_stale({"performance_analysis_id": "panal-1"}, "panal-1") is False


def test_campaign_timeline_calculates_remaining_days():
    campaign = Campaign(
        id="camp-tl",
        owner_id="11111111-1111-1111-1111-111111111111",
        name="Timeline",
        start_date="2026-09-01",
        end_date="2026-09-30",
        objective="Awareness",
    )
    now = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    timeline = campaign_timeline(campaign, now)
    assert timeline["campaign_age_days"] == 9
    assert timeline["days_remaining"] == 20
    assert timeline["campaign_timeline_ended"] is False
    assert parse_campaign_date("2026-09-01") == date(2026, 9, 1)


def test_campaign_end_date_does_not_silently_complete():
    campaign = Campaign(
        id="camp-ended",
        owner_id="11111111-1111-1111-1111-111111111111",
        name="Ended",
        start_date="2026-08-01",
        end_date="2026-08-31",
        objective="Awareness",
    )
    now = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    timeline = campaign_timeline(campaign, now)
    assert timeline["campaign_timeline_ended"] is True
    assert timeline["days_remaining"] == 0


def test_data_quality_limited_for_early_content():
    assert classify_data_quality(
        snapshot_count=1,
        content_age_hours=5,
        baseline_available=False,
        has_kpis=True,
    ) == "LIMITED"


def test_missing_roi_is_unavailable_and_cannot_be_cited():
    facts = {"roi": "NOT_AVAILABLE", "roas": "NOT_AVAILABLE", "attributed_revenue": "NOT_AVAILABLE"}
    unavailable = unavailable_metric_keys(facts)
    rec = {
        "action": "Scale this creator",
        "reason": "ROI is strong",
        "evidence": ["ROAS is 4.5x"],
    }
    assert cites_unavailable_metric(rec, unavailable) is True


def test_no_action_needed_when_no_valid_recommendations():
    assert infer_overall_assessment([], "SUFFICIENT") == "NO_ACTION_NEEDED"
    assert infer_overall_assessment([], "INSUFFICIENT") == "INSUFFICIENT_DATA"
    assert infer_overall_assessment(
        [{"category": "MONITOR"}],
        "LIMITED",
    ) == "CONTINUE_MONITORING"


@pytest.mark.asyncio
async def test_validate_output_strips_fake_roi_and_garbage_numbers():
    agent = OptimizationAgent()
    ctx = SimpleNamespace()
    payload = {
        "campaign_id": "camp-1",
        "data_quality": "SUFFICIENT",
        "performance_analysis_id": "panal-1",
        "latest_snapshot_id": "csnap-1",
        "campaign_creator_names": ["Maya"],
        "creator_name": "Maya",
        "kpis": {
            "views": 100000,
            "roi": "NOT_AVAILABLE",
            "roas": "NOT_AVAILABLE",
            "attributed_revenue": "NOT_AVAILABLE",
            "remaining_budget": "NOT_AVAILABLE",
            "conversions": "NOT_AVAILABLE",
            "orders": "NOT_AVAILABLE",
        },
        "financial": {
            "roi": "NOT_AVAILABLE",
            "roas": "NOT_AVAILABLE",
            "attributed_revenue": "NOT_AVAILABLE",
            "remaining_budget": "NOT_AVAILABLE",
        },
        "content_age_hours": 5,
        "content_stage": "EARLY_STAGE",
        "momentum": "RISING",
    }
    result = AgentResultEnvelope(
        status="SUCCESS",
        summary="Generated 3 optimization recommendation(s).",
        recommendations=[],
        data={
            "recommendations": [
                {
                    "priority": "HIGH",
                    "category": "BUDGET",
                    "action": "Increase budget by 37% because expected ROI will become 220%.",
                    "reason": "Projected revenue will rise.",
                    "evidence": ["ROAS is 4.5x"],
                    "requires_human_approval": True,
                },
                {
                    "priority": "MEDIUM",
                    "category": "MONITOR",
                    "action": "Continue monitoring for another 48 hours.",
                    "reason": "The video is only 5 hours old.",
                    "evidence": ["Content age: 5 hours", "Momentum: RISING"],
                    "requires_human_approval": True,
                },
                {
                    "priority": "LOW",
                    "category": "CONTENT",
                    "action": "Improve engagement.",
                    "reason": "Make better content.",
                    "evidence": [],
                    "requires_human_approval": True,
                },
            ]
        },
    )
    validated = await agent.validate_output(ctx, result, payload)
    recs = validated.data["recommendations"]
    assert len(recs) <= 3
    assert all("roi" not in (r.get("action", "") + r.get("reason", "")).lower() for r in recs)
    assert all("4.5" not in " ".join(r.get("evidence") or []) for r in recs)
    assert all(r.get("action") != "Improve engagement." for r in recs)
    assert validated.data["overall_assessment"] in {"CONTINUE_MONITORING", "NO_ACTION_NEEDED", "ADJUST_STRATEGY"}
    assert validated.data["performance_analysis_id"] == "panal-1"
