import json
import re
from typing import Type

from pydantic import BaseModel

from app.schemas import (
    Advisory,
    CanonicalFact,
    CanonicalKnowledge,
    Claim,
    Entity,
    ExecutiveSummary,
    InfographicSection,
    InfographicSpec,
    LinkedInPost,
    PresentationOutline,
    Slide,
    SourceSpan,
    TransformationPlan,
    VideoPackage,
    VideoScene,
    XThread,
    XTweet,
)
from app.services.facts.registry import FactRegistry


def _context(messages: list[dict]) -> dict:
    for msg in reversed(messages):
        try:
            return json.loads(msg["content"])
        except Exception:
            continue
    return {"text": messages[-1]["content"] if messages else ""}


def _chunks_text(payload: dict) -> str:
    if "source_text" in payload and payload["source_text"]:
        return str(payload["source_text"])
    if "text" in payload and payload["text"]:
        return str(payload["text"])
    if "chunks" in payload and isinstance(payload["chunks"], list):
        return "\n".join(c.get("text", "") for c in payload["chunks"] if isinstance(c, dict))
    if "knowledge" in payload and isinstance(payload["knowledge"], dict):
        k = payload["knowledge"]
        return str(k.get("executive_brief", "")) + "\n" + "\n".join(k.get("key_points", []))
    return str(payload)[:10000]


def build_heuristic(schema: Type[BaseModel], messages: list[dict]) -> BaseModel:
    payload = _context(messages)
    if schema is CanonicalKnowledge:
        return _knowledge_from_chunks(payload)
    
    knowledge_raw = payload.get("knowledge") or payload
    if isinstance(knowledge_raw, dict):
        knowledge = CanonicalKnowledge.model_validate(knowledge_raw)
    elif isinstance(knowledge_raw, CanonicalKnowledge):
        knowledge = knowledge_raw
    else:
        knowledge = CanonicalKnowledge()

    facts = []
    for f in payload.get("fact_registry") or []:
        try:
            if isinstance(f, dict):
                facts.append(CanonicalFact.model_validate(f))
            elif isinstance(f, CanonicalFact):
                facts.append(f)
        except Exception:
            continue
    registry = FactRegistry(facts)

    if schema is ExecutiveSummary:
        return _exec(knowledge, registry)
    if schema is Advisory:
        return _advisory(knowledge, registry)
    if schema is LinkedInPost:
        return _linkedin(knowledge, registry)
    if schema is PresentationOutline:
        return _presentation(knowledge, registry)
    if schema is XThread:
        return _xthread(knowledge, registry)
    if schema is InfographicSpec:
        return _infographic(knowledge, registry)
    if schema is VideoPackage:
        return _video(knowledge, registry, payload.get("config") or {})
    if schema is TransformationPlan:
        return _plan(payload, knowledge, registry)
    return schema.model_validate({})


def _knowledge_from_chunks(payload: dict) -> CanonicalKnowledge:
    chunks = payload.get("chunks") or []
    text = _chunks_text(payload)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip() and len(s.strip()) > 5]

    first_span = (
        SourceSpan(
            chunk_id=chunks[0]["chunk_id"],
            page=chunks[0].get("page"),
            quote=sentences[0][:180],
        )
        if chunks and sentences
        else None
    )

    # 1. Extract Document Title
    title = payload.get("title")
    if not title or title == "Untitled source":
        # Try explicit Title: pattern
        title_match = re.search(r"(?:Incident\s+)?Title:\s*([^\n]+)", text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            # Fallback: use first non-empty line that looks like a title and is not a generic heading
            for line in lines:
                stripped = line.strip()
                if stripped and len(stripped.split()) <= 12 and not stripped.isupper():
                    if stripped.upper() not in {"CYBERSECURITY INCIDENT ASSESSMENT", "INCIDENT REPORT", "ASSESSMENT REPORT"}:
                        title = stripped
                        break
            else:
                title = "Security Incident Assessment"

    # 2. Extract Executive Brief / Summary
    summary_match = re.search(r"Summary:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\n|\n[A-Z][A-Za-z\s]+:)", text, re.IGNORECASE)
    if summary_match:
        executive_brief = summary_match.group(1).strip().replace("\n", " ")
    else:
        executive_brief = " ".join(sentences[:3])[:1200]

    # 3. Extract Bullet Points / Key Findings (preserve leading numbers!)
    bullet_pts = [
        re.sub(r"^[-*•\s]+|^\d+\.\s*", "", line).strip()
        for line in lines
        if (line.startswith("-") or line.startswith("*") or line.startswith("•") or re.match(r"^\d+\.", line))
        and len(line.strip()) > 5
    ]

    key_pts = [s for s in bullet_pts if not re.search(r"\b(recommend|action|investigation|monitor)\b", s, re.I)]
    if not key_pts:
        key_pts = bullet_pts or [s for s in sentences if len(s) > 20 and not s.endswith(":")]

    # 4. Extract Recommendations / Actions
    recs = [
        s for s in bullet_pts
        if re.search(r"\b(recommend|action|investigation|monitor|enable|review|notify)\b", s, re.I)
    ]
    if not recs:
        recs = [s for s in sentences if re.search(r"\b(recommend|should|must|advise|action|enable|review)\b", s, re.I)]

    # 5. Extract Entities & Statistics & Dates
    orgs = _unique(re.findall(r"\b([A-Z][A-Za-z0-9_-]+(?:\s+[A-Z][A-Za-z0-9_-]+){0,3})\b", text)[:12])
    numbers = re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?%?\b", text)[:8]
    dates = re.findall(r"\b(?:\d{1,2}\s)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s?\d{0,4}\b|\b\d{4}-\d{2}-\d{2}\b", text, re.IGNORECASE)[:6]

    return CanonicalKnowledge(
        title=title[:180],
        source_type=payload.get("source_type", "pdf"),
        executive_brief=executive_brief[:1200],
        key_points=key_pts[:6] or sentences[:5],
        entities=[Entity(name=n, type="org") for n in orgs[:6]],
        organizations=orgs[:6],
        dates=dates,
        statistics=numbers,
        recommendations=recs[:5],
        claims=[Claim(statement=s, spans=[first_span] if first_span else []) for s in key_pts[:4]],
        keywords=orgs[:8],
        source_references=[first_span] if first_span else [],
        unknowns=["Items not explicitly stated in the source telemetry must not be assumed."],
    )


def _fact_keys(registry: FactRegistry) -> list[str]:
    keys = [f.key for f in registry.facts[:8]]
    if not keys:
        return ["fact_1", "fact_2"]
    return keys


def _exec(k: CanonicalKnowledge, r: FactRegistry) -> ExecutiveSummary:
    findings = k.key_points[:6] if k.key_points else [f"{f.label}: {f.value}" for f in r.facts[:6]]
    implications = (
        k.recommendations[:3]
        if k.recommendations
        else ["Enhanced authentication monitoring required.", "Privileged access reviews should be conducted."]
    )
    open_questions = [
        "What was the initial vector for account credential exposure?",
        "Are additional external networks involved in authentication sweeps?",
    ]
    return ExecutiveSummary(
        headline=k.title or "Executive Incident Summary",
        context=k.executive_brief,
        key_findings=findings,
        implications=implications,
        open_questions=open_questions,
        fact_keys_used=_fact_keys(r),
    )


def _advisory(k: CanonicalKnowledge, r: FactRegistry) -> Advisory:
    situation = k.executive_brief or "Suspicious authentication activity detected."
    assessment = (
        " ".join(k.key_points[:4])
        if k.key_points
        else "Investigation indicates unauthorized authentication attempts against employee portal credentials."
    )
    recommendations = (
        k.recommendations
        if k.recommendations
        else [
            "Complete log review of authentication servers.",
            "Enforce immediate password reset for affected accounts.",
            "Verify multi-factor authentication compliance.",
        ]
    )
    watch_items = [
        "Monitoring for additional external network authentication attempts.",
        "Auditing database queries from compromised user accounts.",
    ]
    caveats = [
        "Investigation is active and ongoing.",
        "Findings are based on current telemetry logs as of date of assessment.",
    ]
    return Advisory(
        header=f"SECURITY ADVISORY - {k.title.upper()}",
        situation=situation,
        assessment=assessment,
        recommendations=recommendations,
        watch_items=watch_items,
        caveats=caveats,
        fact_keys_used=_fact_keys(r),
       )

def _linkedin(k: CanonicalKnowledge, r: FactRegistry) -> LinkedInPost:
    # Hook: concise title without brackets
    hook = k.title if k.title else "Security Incident Brief"

    # Build a natural narrative paragraph
    parts: list[str] = []
    if k.executive_brief:
        parts.append(k.executive_brief)
    if k.key_points:
        parts.append(" ".join(k.key_points[:3]))
    if k.recommendations:
        parts.append(k.recommendations[0].rstrip('.'))
    body = " ".join(parts).strip()

    return LinkedInPost(
        hook=hook,
        body=body[:1300],
        hashtags=["#Cybersecurity", "#IncidentResponse", "#TransformAI", "#InfoSec"],
        cta="Review authentication logs and enforce multi-factor authentication for privileged accounts.",
        fact_keys_used=_fact_keys(r),
    )
def _presentation(k: CanonicalKnowledge, r: FactRegistry) -> PresentationOutline:
    slides = [
        Slide(
            layout="title",
            title=k.title or "Incident Assessment Briefing",
            speaker_notes="Executive briefing on security assessment findings.",
            fact_keys=_fact_keys(r)[:2],
        ),
        Slide(
            layout="title_bullets",
            title="Executive Context & Situation",
            bullets=[{"text": k.executive_brief[:250], "level": 0}],
            speaker_notes="Summarize initial portal anomaly telemetry.",
            fact_keys=_fact_keys(r)[:3],
        ),
        Slide(
            layout="title_bullets",
            title="Key Findings",
            bullets=[{"text": p, "level": 0} for p in (k.key_points[:5] or [k.executive_brief])],
            speaker_notes="Review affected accounts and timeline of activity.",
            fact_keys=_fact_keys(r),
        ),
        Slide(
            layout="title_bullets",
            title="Recommended Action Plan",
            bullets=[{"text": p, "level": 0} for p in (k.recommendations[:5] or k.key_points[:3])],
            speaker_notes="Highlight immediate password resets and MFA enforcement.",
            fact_keys=_fact_keys(r)[:4],
        ),
        Slide(
            layout="closing",
            title="Next Steps & Watch Items",
            bullets=[
                {"text": "Complete full log audit across external network telemetry.", "level": 0},
                {"text": "Provide follow-up briefing to decision makers.", "level": 0},
            ],
            speaker_notes="Close briefing with ongoing monitoring status.",
        ),
    ]
    return PresentationOutline(
        title=k.title or "Incident Assessment Briefing",
        subtitle="TransformAI Intelligence Briefing",
        slides=slides,
        fact_keys_used=_fact_keys(r),
    )


def _xthread(k: CanonicalKnowledge, r: FactRegistry) -> XThread:
    tweets = []
    # Tweet 1 – hook with title and concise context
    hook = k.title if k.title else "Security Incident"
    intro = k.executive_brief if k.executive_brief else "An incident was reported."
    tweets.append(
        XTweet(index=1, text=f"{hook}: {intro[:260]}")
    )
    # Tweet 2 – core event description using first key point
    if k.key_points:
        tweets.append(
            XTweet(index=2, text=k.key_points[0][:260])
        )
    # Tweet 3 – additional observations (next key points)
    if len(k.key_points) > 1:
        additional = " ".join(k.key_points[1:3])
        tweets.append(
            XTweet(index=3, text=additional[:260])
        )
    # Tweet 4 – impact metrics woven naturally
    metrics_parts = []
    if k.statistics:
        metrics_parts.append(", ".join(k.statistics[:2]))
    if k.dates:
        metrics_parts.append(", ".join(k.dates[:2]))
    if metrics_parts:
        tweets.append(
            XTweet(index=4, text=f"{', '.join(metrics_parts)[:260]}")
        )
    # Tweet 5 – recommendation narrative
    if k.recommendations:
        tweets.append(
            XTweet(index=5, text=k.recommendations[0][:260])
        )
    # Tweet 6 – concluding call to action
    tweets.append(
        XTweet(index=6, text="Stay vigilant and continue monitoring for any further activity.")
    )
    return XThread(tweets=tweets, fact_keys_used=_fact_keys(r))


def _infographic(k: CanonicalKnowledge, r: FactRegistry) -> InfographicSpec:
    sections = [
        InfographicSection(heading=f"Finding {i}", body=p)
        for i, p in enumerate(k.key_points[:4], start=1)
    ]
    callouts = [f"{f.label}: {f.value}" for f in r.facts[:4]]
    if not callouts and k.statistics:
        callouts = [f"Affected Metric: {s}" for s in k.statistics]
    return InfographicSpec(
        title=k.title or "Incident Data Visual",
        sections=sections,
        callouts=callouts,
        chart_suggestions=["Telemetry Timeline Chart", "Affected Account Distribution"],
        fact_keys_used=_fact_keys(r),
    )


def _video(k: CanonicalKnowledge, r: FactRegistry, config: dict) -> VideoPackage:
    scenes = [
        VideoScene(
            index=1,
            description="Title Card",
            on_screen_text=k.title or "Incident Briefing",
            narration=f"Security intelligence briefing: {k.title}.",
            duration_seconds=6,
        ),
        VideoScene(
            index=2,
            description="Situation Context",
            on_screen_text="Situation Summary",
            narration=k.executive_brief[:400],
            duration_seconds=15,
        ),
        VideoScene(
            index=3,
            description="Key Findings",
            on_screen_text="Incident Findings",
            narration=" ".join(k.key_points[:3]),
            duration_seconds=20,
        ),
        VideoScene(
            index=4,
            description="Remediation Actions",
            on_screen_text="Recommended Actions",
            narration=" ".join(k.recommendations[:3]),
            duration_seconds=15,
        ),
    ]
    script = "\n\n".join(f"Scene {s.index}: {s.narration}" for s in scenes)
    return VideoPackage(
        title=k.title or "Security Intelligence Video Package",
        objective=config.get("objective", "inform and recommend"),
        target_audience=config.get("audience", "decision makers"),
        duration="56s",
        script=script,
        storyboard=[s.description for s in scenes],
        scenes=scenes,
        narration=script,
        subtitles=[s.narration[:120] for s in scenes],
        on_screen_text=[s.on_screen_text for s in scenes],
        visual_recommendations=["Display clear text overlays for key statistics", "Use restrained dark theme styling"],
        fact_keys_used=_fact_keys(r),
    )


def _plan(
    payload: dict,
    k: CanonicalKnowledge,
    r: FactRegistry,
) -> TransformationPlan:
    config = payload.get("config") or {}
    output_type = payload.get("output_type") or "executive_summary"

    return TransformationPlan(
        output_type=output_type,
        communication_objective=config.get(
            "objective",
            "inform and recommend",
        ),
        target_audience=config.get(
            "audience",
            "senior decision makers",
        ),
        tone=config.get(
            "tone",
            "advisory",
        ),
        detail_level=config.get(
            "detail",
            "standard",
        ),
        content_style=config.get(
            "content_style",
            "intelligence brief",
        ),
        must_use_fact_keys=_fact_keys(r),
        relevant_entities=[e.name for e in k.entities[:8]],
        required_sections=[],
        prohibited_assumptions=[
            "Do not invent facts, numbers, dates, names, events, or conclusions.",
            "Do not treat unknown information as confirmed.",
        ],
        grounding_requirements=[
            "Use only information supported by the canonical knowledge.",
            "Preserve factual consistency with the source.",
        ],
    )


def _unique(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        key = item.lower()
        if key in seen or len(item) < 3:
            continue
        seen.add(key)
        out.append(item)
    return out
