from app.schemas import ExecutiveSummary
from app.services.generators.base import BaseGenerator


class ExecutiveSummaryGenerator(BaseGenerator):
    output_type = "executive_summary"
    schema = ExecutiveSummary
    # Guidelines for the LLM – keep sections separate and omit empty ones.
    output_guidelines = [
        "Separate findings from recommendations; do not list recommendations under findings.",
        "If a section has no content, omit the heading entirely.",
        "Write professionally for decision makers; avoid generic filler.",
    ]

    def to_markdown(self, payload: ExecutiveSummary) -> str:
        parts = [f"# {payload.headline}\n\n"]
        if payload.context:
            parts.append(f"### Executive Context\n{payload.context}\n\n")
        if payload.key_findings:
            findings = "\n".join(f"- {x}" for x in payload.key_findings)
            parts.append(f"### Key Findings\n{findings}\n\n")
        if payload.implications:
            impl = "\n".join(f"- {x}" for x in payload.implications)
            parts.append(f"### Strategic Implications\n{impl}\n\n")
        if payload.open_questions:
            ques = "\n".join(f"- {x}" for x in payload.open_questions)
            parts.append(f"### Required Actions & Open Questions\n{ques}\n")
        return "".join(parts)
