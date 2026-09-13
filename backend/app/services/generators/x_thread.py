from app.schemas import XThread
from app.services.generators.base import BaseGenerator


class XThreadGenerator(BaseGenerator):
    output_type = "x_thread"
    schema = XThread

    def to_markdown(self, payload: XThread) -> str:
        return "\n\n".join(f"{t.index}/{len(payload.tweets)} {t.text}" for t in payload.tweets)
