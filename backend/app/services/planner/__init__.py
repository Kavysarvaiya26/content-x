from app.schemas import LengthConstraints, TransformationPlan, TransformConfig
from app.services.facts.registry import FactRegistry

DEFAULTS = {
    "executive_summary": {
        "sections": ["headline", "context", "key_findings", "implications", "open_questions"],
        "length": LengthConstraints(min_chars=200, max_chars=4000, min_items=3, max_items=8),
    },
    "advisory": {
        "sections": ["header", "situation", "assessment", "recommendations", "watch_items", "caveats"],
        "length": LengthConstraints(min_chars=200, max_chars=5000, min_items=2, max_items=8),
    },
    "linkedin_post": {
        "sections": ["hook", "body", "hashtags", "cta"],
        "length": LengthConstraints(min_chars=80, max_chars=1300, min_items=1, max_items=1),
    },
    "presentation": {
        "sections": ["title", "slides", "speaker_notes"],
        "length": LengthConstraints(min_chars=0, max_chars=8000, min_items=3, max_items=12),
    },
    "x_thread": {
        "sections": ["tweets"],
        "length": LengthConstraints(min_chars=1, max_chars=280, min_items=2, max_items=8),
    },
    "infographic": {
        "sections": ["title", "sections", "callouts"],
        "length": LengthConstraints(min_chars=40, max_chars=3000, min_items=2, max_items=8),
    },
    "video_package": {
        "sections": ["title", "objective", "script", "scenes", "narration"],
        "length": LengthConstraints(min_chars=80, max_chars=8000, min_items=3, max_items=10),
    },
}


def build_plans(selected: list[str], config: TransformConfig, registry: FactRegistry, unknowns: list[str]) -> dict[str, TransformationPlan]:
    important = [f.key for f in registry.facts if f.importance in {"high", "critical"}] or [f.key for f in registry.facts[:6]]
    entities = [str(f.value) for f in registry.facts if f.value_type == "entity"][:8]
    plans = {}
    for output_type in selected:
        spec = DEFAULTS[output_type]
        plans[output_type] = TransformationPlan(
            output_type=output_type,
            communication_objective=config.objective,
            target_audience=config.audience,
            tone=config.tone,
            detail_level=config.detail_level,
            content_style=config.content_style,
            must_use_fact_keys=important,
            relevant_entities=entities,
            required_sections=spec["sections"],
            length_constraints=spec["length"],
            prohibited_assumptions=list(unknowns) + ["Do not invent numbers, dates, or named entities."],
            grounding_requirements=important[:4],
        )
    return plans
