from app.schemas import InfographicSpec
from app.services.generators.base import BaseGenerator


class InfographicGenerator(BaseGenerator):
    output_type = "infographic"
    schema = InfographicSpec

    def to_markdown(self, payload: InfographicSpec) -> str:
        sections = "\n\n".join(f"## {s.heading}\n{s.body}" for s in payload.sections)
        callouts = "\n".join(f"- {c}" for c in payload.callouts)
        return f"# {payload.title}\n\n{sections}\n\n## Callouts\n{callouts}\n"
