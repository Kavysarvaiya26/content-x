from app.schemas import PresentationOutline
from app.services.generators.base import BaseGenerator


class PresentationGenerator(BaseGenerator):
    output_type = "presentation"
    schema = PresentationOutline

    def to_markdown(self, payload: PresentationOutline) -> str:
        parts = [f"# {payload.title}", payload.subtitle]
        for i, slide in enumerate(payload.slides, start=1):
            bullets = "\n".join("  " * b.level + f"- {b.text}" for b in slide.bullets)
            parts.append(f"## Slide {i}: {slide.title}\nLayout: {slide.layout}\n{bullets}\nNotes: {slide.speaker_notes}")
        return "\n\n".join(parts)
