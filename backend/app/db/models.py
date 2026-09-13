from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    safe_filename: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(32))
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    origin_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    extract_preview: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    chunks: Mapped[list["SourceChunk"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    jobs: Mapped[list["TransformationJob"]] = relationship(back_populates="source")


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("sources.id"), index=True)
    chunk_id: Mapped[str] = mapped_column(String(64), index=True)
    page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_char: Mapped[int] = mapped_column(Integer, default=0)
    end_char: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)

    source: Mapped[Source] = relationship(back_populates="chunks")


class TransformationJob(Base):
    __tablename__ = "transformation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("sources.id"), index=True)
    status: Mapped[str] = mapped_column(String(48), default="queued", index=True)
    current_node: Mapped[str] = mapped_column(String(64), default="queued")
    selected_outputs: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    output_plans: Mapped[dict] = mapped_column(JSON, default=dict)
    repair_attempts: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    source: Mapped[Source] = relationship(back_populates="jobs")
    knowledge: Mapped[Optional["CanonicalKnowledgeRow"]] = relationship(back_populates="job", uselist=False)
    facts: Mapped[list["FactRow"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    outputs: Mapped[list["GeneratedOutput"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    validations: Mapped[list["ValidationResult"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class CanonicalKnowledgeRow(Base):
    __tablename__ = "canonical_knowledge"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("transformation_jobs.id"), unique=True)
    knowledge_json: Mapped[dict] = mapped_column(JSON, default=dict)

    job: Mapped[TransformationJob] = relationship(back_populates="knowledge")


class FactRow(Base):
    __tablename__ = "fact_registry"
    __table_args__ = (UniqueConstraint("job_id", "key", name="uq_fact_job_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("transformation_jobs.id"), index=True)
    key: Mapped[str] = mapped_column(String(128))
    label: Mapped[str] = mapped_column(String(255))
    value_json: Mapped[object] = mapped_column(JSON)
    value_type: Mapped[str] = mapped_column(String(32), default="string")
    unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    importance: Mapped[str] = mapped_column(String(32), default="normal")
    severity: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    spans_json: Mapped[list] = mapped_column(JSON, default=list)

    job: Mapped[TransformationJob] = relationship(back_populates="facts")


class GeneratedOutput(Base):
    __tablename__ = "generated_outputs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("transformation_jobs.id"), index=True)
    output_type: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    content_markdown: Mapped[str] = mapped_column(Text, default="")
    fact_keys_used: Mapped[list] = mapped_column(JSON, default=list)
    knowledge_hash: Mapped[str] = mapped_column(String(64), default="")
    edited_by_human: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job: Mapped[TransformationJob] = relationship(back_populates="outputs")
    validations: Mapped[list["ValidationResult"]] = relationship(back_populates="output")


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("transformation_jobs.id"), index=True)
    output_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("generated_outputs.id"), nullable=True, index=True)
    check_type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16), default="info")
    passed: Mapped[bool] = mapped_column(default=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[TransformationJob] = relationship(back_populates="validations")
    output: Mapped[Optional[GeneratedOutput]] = relationship(back_populates="validations")


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
