from app.schemas import ExecutiveSummary
from app.services.generators.base import BaseGenerator


class ExecutiveSummaryGenerator(BaseGenerator):
    output_type = "executive_summary"
    schema = ExecutiveSummary

    def to_markdown(self, payload: ExecutiveSummary) -> str:
        findings = "\n".join(f"- {x}" for x in payload.key_findings)
        implications = "\n".join(f"- {x}" for x in payload.implications)
        questions = "\n".join(f"- {x}" for x in payload.open_questions)
        return (
            f"# {payload.headline}\n\n{payload.context}\n\n"
            f"## Key findings\n{findings}\n\n## Implications\n{implications}\n\n"
            f"## Open questions\n{questions}\n"
        )
