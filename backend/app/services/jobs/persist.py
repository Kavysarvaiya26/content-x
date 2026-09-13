from datetime import datetime, timezone

from app.db.models import GeneratedOutput, SessionLocal, TransformationJob
from app.services.jobs.events import publish
from app.services.validation.checks import knowledge_hash


def set_job(job_id: str, **fields) -> None:
    db = SessionLocal()
    try:
        job = db.get(TransformationJob, job_id)
        if not job:
            return
        for key, value in fields.items():
            setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        publish(
            job_id,
            {
                "event": "node",
                "node": fields.get("current_node", job.current_node),
                "status": fields.get("status", job.status),
                "message": fields.get("error_message") or fields.get("current_node"),
            },
        )
    finally:
        db.close()


def upsert_output(job_id: str, artifact: dict, knowledge: dict | None) -> None:
    db = SessionLocal()
    try:
        existing = (
            db.query(GeneratedOutput)
            .filter(GeneratedOutput.job_id == job_id, GeneratedOutput.output_type == artifact["output_type"])
            .one_or_none()
        )
        hashed = knowledge_hash(knowledge or {})
        if existing:
            existing.content_json = artifact.get("payload") or {}
            existing.content_markdown = artifact.get("markdown") or ""
            existing.status = artifact.get("status") or "succeeded"
            existing.fact_keys_used = artifact.get("fact_keys_used") or []
            existing.knowledge_hash = hashed
            existing.version = (existing.version or 1) + 1
        else:
            db.add(
                GeneratedOutput(
                    job_id=job_id,
                    output_type=artifact["output_type"],
                    status=artifact.get("status") or "succeeded",
                    content_json=artifact.get("payload") or {},
                    content_markdown=artifact.get("markdown") or "",
                    fact_keys_used=artifact.get("fact_keys_used") or [],
                    knowledge_hash=hashed,
                )
            )
        db.commit()
    finally:
        db.close()
