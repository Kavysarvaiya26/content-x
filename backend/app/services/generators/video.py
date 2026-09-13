from app.schemas import VideoPackage
from app.services.generators.base import BaseGenerator


class VideoPackageGenerator(BaseGenerator):
    output_type = "video_package"
    schema = VideoPackage

    def to_markdown(self, payload: VideoPackage) -> str:
        scenes = "\n".join(f"{s.index}. {s.description}: {s.narration}" for s in payload.scenes)
        return (
            f"# {payload.title}\nAudience: {payload.target_audience}\nDuration: {payload.duration}\n\n"
            f"## Script\n{payload.script}\n\n## Scenes\n{scenes}\n"
        )
