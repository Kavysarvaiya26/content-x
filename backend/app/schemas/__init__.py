from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field

Tone = Literal["formal", "neutral", "urgent", "advisory", "public"]
DetailLevel = Literal["brief", "standard", "deep"]
OutputType = Literal[
    "executive_summary",
    "advisory",
    "linkedin_post",
    "presentation",
    "x_thread",
    "infographic",
    "video_package",
]
GENERATOR_NODE = {
    "executive_summary": "generate_executive_summary",
    "advisory": "generate_advisory",
    "linkedin_post": "generate_linkedin",
    "presentation": "generate_presentation",
    "x_thread": "generate_x_thread",
    "infographic": "generate_infographic",
    "video_package": "generate_video_package",
}


class TransformConfig(BaseModel):
    audience: str = "senior decision makers"
    tone: Tone = "advisory"
    language: str = "en"
    detail_level: DetailLevel = "standard"
    objective: str = "inform and recommend"
    content_style: str = "intelligence brief"


class SourceSpan(BaseModel):
    chunk_id: str
    page: Optional[int] = None
    section: Optional[str] = None
    quote: str = ""


class CanonicalFact(BaseModel):
    key: str
    label: str
    value: Any
    value_type: str = "string"
    unit: Optional[str] = None
    confidence: float = 0.7
    importance: Literal["low", "normal", "high", "critical"] = "normal"
    severity: Optional[str] = None
    spans: list[SourceSpan] = Field(default_factory=list)


class Entity(BaseModel):
    name: str
    type: Literal["person", "org", "location", "technology", "other"] = "other"
    role: Optional[str] = None
    spans: list[SourceSpan] = Field(default_factory=list)


class Claim(BaseModel):
    statement: str
    polarity: Literal["positive", "negative", "neutral"] = "neutral"
    spans: list[SourceSpan] = Field(default_factory=list)
    supported: bool = True


class CanonicalKnowledge(BaseModel):
    title: str = "Untitled source"
    source_type: str = "pdf"
    executive_brief: str = ""
    key_points: list[str] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    statistics: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source_references: list[SourceSpan] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class LengthConstraints(BaseModel):
    min_chars: int = 0
    max_chars: int = 8000
    min_items: int = 0
    max_items: int = 20


class TransformationPlan(BaseModel):
    output_type: str
    communication_objective: str
    target_audience: str
    tone: str
    detail_level: str
    content_style: str
    must_use_fact_keys: list[str] = Field(default_factory=list)
    relevant_entities: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    length_constraints: LengthConstraints = Field(default_factory=LengthConstraints)
    prohibited_assumptions: list[str] = Field(default_factory=list)
    grounding_requirements: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    fact_key: Optional[str] = None
    span: Optional[SourceSpan] = None


class ExecutiveSummary(BaseModel):
    headline: str
    context: str
    key_findings: list[str]
    implications: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    fact_keys_used: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class Advisory(BaseModel):
    header: str = "UNCLASSIFIED — DEMO"
    situation: str
    assessment: str
    recommendations: list[str]
    watch_items: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    fact_keys_used: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class LinkedInPost(BaseModel):
    hook: str
    body: str
    hashtags: list[str] = Field(default_factory=list)
    cta: str = ""
    fact_keys_used: list[str] = Field(default_factory=list)


class Bullet(BaseModel):
    text: str
    level: int = 0


class Slide(BaseModel):
    layout: Literal["title", "section", "title_bullets", "two_column", "closing"] = "title_bullets"
    title: str
    bullets: list[Bullet] = Field(default_factory=list)
    right_column_bullets: list[Bullet] = Field(default_factory=list)
    speaker_notes: str = ""
    fact_keys: list[str] = Field(default_factory=list)


class PresentationOutline(BaseModel):
    title: str
    subtitle: str = ""
    footer: str = "TransformAI"
    slides: list[Slide]
    fact_keys_used: list[str] = Field(default_factory=list)


class XTweet(BaseModel):
    index: int
    text: str


class XThread(BaseModel):
    tweets: list[XTweet]
    fact_keys_used: list[str] = Field(default_factory=list)


class InfographicSection(BaseModel):
    heading: str
    body: str
    callout: Optional[str] = None


class InfographicSpec(BaseModel):
    title: str
    sections: list[InfographicSection]
    callouts: list[str] = Field(default_factory=list)
    chart_suggestions: list[str] = Field(default_factory=list)
    fact_keys_used: list[str] = Field(default_factory=list)


class VideoScene(BaseModel):
    index: int
    description: str
    on_screen_text: str = ""
    narration: str = ""
    duration_seconds: int = 8


class VideoPackage(BaseModel):
    title: str
    objective: str
    target_audience: str
    duration: str = "60s"
    script: str
    storyboard: list[str] = Field(default_factory=list)
    scenes: list[VideoScene] = Field(default_factory=list)
    narration: str = ""
    subtitles: list[str] = Field(default_factory=list)
    on_screen_text: list[str] = Field(default_factory=list)
    visual_recommendations: list[str] = Field(default_factory=list)
    fact_keys_used: list[str] = Field(default_factory=list)


OutputPayload = Union[
    ExecutiveSummary,
    Advisory,
    LinkedInPost,
    PresentationOutline,
    XThread,
    InfographicSpec,
    VideoPackage,
]


class GeneratedArtifact(BaseModel):
    output_type: str
    status: str = "succeeded"
    payload: dict[str, Any] = Field(default_factory=dict)
    markdown: str = ""
    fact_keys_used: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class ValidationIssue(BaseModel):
    code: str
    message: str


class ValidationReport(BaseModel):
    output_type: str
    check_type: Literal["consistency", "grounding", "quality"]
    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    attempt: int = 0
    severity: str = "info"


class JobCreate(BaseModel):
    source_id: str
    selected_outputs: list[OutputType]
    config: TransformConfig = Field(default_factory=TransformConfig)


class TextSourceCreate(BaseModel):
    text: str
    filename: str = "pasted.txt"


class UrlSourceCreate(BaseModel):
    url: str


class OutputEdit(BaseModel):
    content_markdown: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None
