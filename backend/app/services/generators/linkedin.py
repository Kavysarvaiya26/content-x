from app.schemas import LinkedInPost
from app.services.generators.base import BaseGenerator


class LinkedInGenerator(BaseGenerator):
    output_type = "linkedin_post"
    schema = LinkedInPost
    # Guidelines for natural LinkedIn post
    output_guidelines = [
        "Write a concise, conversational LinkedIn post aimed at security professionals.",
        "Start with a hook, include a brief story, explain why it matters, and end with a takeaway.",
        "Do not use formal report headings like 'KEY INCIDENT FINDINGS'.",
        "Keep the body between 150 and 1300 characters, but prioritize natural flow over exact length.",
    ]

    def to_markdown(self, payload: LinkedInPost) -> str:
        tags = " ".join(payload.hashtags)
        return f"{payload.hook}\n\n{payload.body}\n\n{payload.cta}\n\n{tags}\n"
