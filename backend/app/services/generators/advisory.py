from app.schemas import Advisory
from app.services.generators.base import BaseGenerator


class AdvisoryGenerator(BaseGenerator):
    output_type = "advisory"
    schema = Advisory

    def to_markdown(self, payload: Advisory) -> str:
        recs = "\n".join(f"- {x}" for x in payload.recommendations)
        watch = "\n".join(f"- {x}" for x in payload.watch_items)
        caveats = "\n".join(f"- {x}" for x in payload.caveats)
        return (
            f"# {payload.header}\n\n## Situation\n{payload.situation}\n\n"
            f"## Assessment\n{payload.assessment}\n\n## Recommendations\n{recs}\n\n"
            f"## Watch items\n{watch}\n\n## Caveats\n{caveats}\n"
        )
