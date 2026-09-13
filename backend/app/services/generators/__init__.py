from app.services.generators.advisory import AdvisoryGenerator
from app.services.generators.executive import ExecutiveSummaryGenerator
from app.services.generators.infographic import InfographicGenerator
from app.services.generators.linkedin import LinkedInGenerator
from app.services.generators.presentation import PresentationGenerator
from app.services.generators.video import VideoPackageGenerator
from app.services.generators.x_thread import XThreadGenerator

GENERATORS = {
    "executive_summary": ExecutiveSummaryGenerator(),
    "advisory": AdvisoryGenerator(),
    "linkedin_post": LinkedInGenerator(),
    "presentation": PresentationGenerator(),
    "x_thread": XThreadGenerator(),
    "infographic": InfographicGenerator(),
    "video_package": VideoPackageGenerator(),
}
