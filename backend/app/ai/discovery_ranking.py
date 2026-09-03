"""Persona-aware ranking of already-eligible Discovery candidates.

Hard filters must already have passed. Weights live here so they are not
copied across agents. Product similarity is a supporting signal unless the
user set an exclusive niche.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.ai.audience_profile import PERSONA_ADULT, PERSONA_GEN_Z, PERSONA_MATURE, is_awareness_objective


# Centralized 0–1 weights. Do not duplicate these in other modules.
RANKING_WEIGHTS: Dict[str, Dict[str, float]] = {
    "awareness": {
        "persona": 0.30,
        "trend": 0.25,
        "recent_views": 0.20,
        "collaboration": 0.10,
        "cultural": 0.10,
        "product": 0.05,
        "engagement": 0.00,
    },
    "conversion": {
        "persona": 0.25,
        "product": 0.25,
        "collaboration": 0.15,
        "engagement": 0.15,
        "trend": 0.10,
        "cultural": 0.10,
        "recent_views": 0.00,
    },
    "education": {
        "persona": 0.25,
        "product": 0.25,
        "collaboration": 0.15,
        "cultural": 0.15,
        "trend": 0.10,
        "engagement": 0.10,
        "recent_views": 0.00,
    },
}

_LEVEL_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0, "": 0}


def _level(value: Any) -> int:
    return _LEVEL_RANK.get(str(value or "UNKNOWN").upper(), 0)


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _profile_for_objective(objective: str) -> str:
    blob = str(objective or "").lower()
    if any(token in blob for token in ("conversion", "sales", "roas", "purchase")):
        return "conversion"
    if any(token in blob for token in ("education", "educat", "tutorial", "explain")):
        return "education"
    return "awareness"


def ranking_weights(*, objective: str, explicit_niche: bool = False) -> Dict[str, float]:
    weights = dict(RANKING_WEIGHTS.get(_profile_for_objective(objective)) or RANKING_WEIGHTS["awareness"])
    if explicit_niche:
        weights["product"] = max(weights.get("product", 0), 0.25)
        rest = 1.0 - weights["product"]
        others = [k for k in weights if k != "product"]
        total = sum(weights[k] for k in others) or 1.0
        for key in others:
            weights[key] = weights[key] / total * rest
    return weights


def ranking_score(
    rec: Dict[str, Any],
    cand: Dict[str, Any],
    *,
    target_persona: str,
    objective: str,
    explicit_niche: bool = False,
) -> float:
    weights = ranking_weights(objective=objective, explicit_niche=explicit_niche)
    persona = rec.get("persona_relevance") or {}
    classification = rec.get("classification") or {}
    persona_level = _level(persona.get("level"))
    if str(persona.get("target") or "").upper() != target_persona and target_persona not in ("", "UNKNOWN"):
        persona_level = min(persona_level, 1)
    gen_z = _level(classification.get("gen_z_relevance"))
    adult = _level(classification.get("adult_relevance"))
    mature = _level(classification.get("mature_audience_relevance"))
    if target_persona == PERSONA_GEN_Z:
        persona_focus = max(persona_level, gen_z)
    elif target_persona == PERSONA_MATURE:
        persona_focus = max(persona_level, mature, adult)
    elif target_persona == PERSONA_ADULT:
        persona_focus = max(persona_level, adult)
    else:
        persona_focus = persona_level

    recent_views = _as_int(cand.get("recent_avg_views") or cand.get("avg_views") or rec.get("avg_views"))
    views_norm = min(1.0, recent_views / 500_000) if recent_views > 0 else 0.0
    trend_score = _as_float(cand.get("auralytics_trend_score") or rec.get("auralytics_trend_score")) / 100.0
    if trend_score <= 0:
        trend_score = _level(classification.get("trend_relevance") or cand.get("recent_momentum")) / 3.0
    collab = _level(rec.get("collaboration_suitability")) / 3.0
    cultural = _level(classification.get("cultural_relevance")) / 3.0
    product = _level(classification.get("product_relevance") or classification.get("niche_match")) / 3.0
    if is_awareness_objective(objective) and not explicit_niche:
        product = min(product, 0.4)
    engagement = min(1.0, _as_float(cand.get("engagement_rate") or rec.get("engagement_rate")) / 8.0)
    ratio = _as_float(cand.get("views_to_subscriber_ratio"))
    if ratio > 0:
        trend_score = max(trend_score, min(1.0, ratio))

    components = {
        "persona": persona_focus / 3.0,
        "trend": trend_score,
        "recent_views": views_norm,
        "collaboration": collab,
        "cultural": cultural,
        "product": product,
        "engagement": engagement,
    }
    return round(sum(components.get(key, 0.0) * weight for key, weight in weights.items()), 4)


def persona_sort_key(
    rec: Dict[str, Any],
    cand: Dict[str, Any],
    *,
    target_persona: str,
    objective: str,
    explicit_niche: bool = False,
) -> Tuple:
    return (
        1 if rec.get("eligibility") == "ELIGIBLE" else 0,
        ranking_score(
            rec,
            cand,
            target_persona=target_persona,
            objective=objective,
            explicit_niche=explicit_niche,
        ),
        rec.get("final_score") or 0,
        rec.get("ai_fit_score") or 0,
    )


def sort_recommendations(
    recs: List[Dict[str, Any]],
    candidates_by_id: Dict[str, Dict[str, Any]],
    *,
    target_persona: str,
    objective: str,
    explicit_niche: bool = False,
) -> List[Dict[str, Any]]:
    ranked = sorted(
        recs,
        key=lambda r: persona_sort_key(
            r,
            candidates_by_id.get(str(r.get("influencer_id"))) or {},
            target_persona=target_persona,
            objective=objective,
            explicit_niche=explicit_niche,
        ),
        reverse=True,
    )
    for rec in ranked:
        cand = candidates_by_id.get(str(rec.get("influencer_id"))) or {}
        rec["ranking_score"] = ranking_score(
            rec,
            cand,
            target_persona=target_persona,
            objective=objective,
            explicit_niche=explicit_niche,
        )
    return ranked
