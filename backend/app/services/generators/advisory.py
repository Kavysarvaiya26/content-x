from app.schemas import Advisory
from app.services.generators.base import BaseGenerator


class AdvisoryGenerator(BaseGenerator):
    output_type = "advisory"
    schema = Advisory
    # Guidelines for the LLM – keep sections distinct and omit empty ones.
    output_guidelines = [
        "Separate situation, findings, and recommendations; do not repeat sentences.",
        "If a section has no content, omit its heading.",
        "Write concisely for security decision‑makers; avoid filler.",
    ]

    def to_markdown(self, payload: Advisory) -> str:
        recs = "\n".join(f"1. {x}" for x in payload.recommendations)
        watch = "\n".join(f"- {x}" for x in payload.watch_items)
        caveats = "\n".join(f"- {x}" for x in payload.caveats)
        parts = [f"# {payload.header}\n\n"]
        if payload.situation:
            parts.append(f"## Situation\n{payload.situation}\n\n")
        if payload.assessment:
            parts.append(f"## Operational Assessment\n{payload.assessment}\n\n")
        if recs:
            parts.append(f"## Recommended Actions\n{recs}\n\n")
        if watch:
            parts.append(f"## Watch Items & Monitoring\n{watch}\n\n")
        if caveats:
            parts.append(f"## Caveats & Operational Constraints\n{caveats}\n")
        return "".join(parts)
