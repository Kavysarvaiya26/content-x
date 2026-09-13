from app.schemas import LinkedInPost
from app.services.generators.base import BaseGenerator


class LinkedInGenerator(BaseGenerator):
    output_type = "linkedin_post"
    schema = LinkedInPost

    def to_markdown(self, payload: LinkedInPost) -> str:
        tags = " ".join(payload.hashtags)
        return f"{payload.hook}\n\n{payload.body}\n\n{payload.cta}\n\n{tags}\n"
