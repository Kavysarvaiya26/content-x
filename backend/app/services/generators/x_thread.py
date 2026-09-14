from app.schemas import XThread
from app.services.generators.base import BaseGenerator


class XThreadGenerator(BaseGenerator):
    output_type = "x_thread"
    schema = XThread
    # Guidelines for XThread generation
    output_guidelines = [
        "Create a 5-6 tweet thread that tells a logical story: what happened, evidence, impact, response, and takeaway.",
        "Each tweet must add new information; avoid repeating the same sentence.",
        "Keep each tweet ≤280 characters.",
    ]

    def to_markdown(self, payload: XThread) -> str:
        return "\n\n".join(f"{t.index}/{len(payload.tweets)} {t.text}" for t in payload.tweets)
