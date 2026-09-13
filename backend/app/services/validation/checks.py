import hashlib
import json
import re

from app.db.models import GeneratedOutput, SessionLocal, SourceChunk, ValidationResult
from app.schemas import GeneratedArtifact, TransformationPlan, ValidationIssue, ValidationReport
from app.services.facts.registry import FactRegistry


def persist_validation(job_id: str, output_type: str, report: ValidationReport) -> None:
    db = SessionLocal()
    try:
        output = (
            db.query(GeneratedOutput)
            .filter(GeneratedOutput.job_id == job_id, GeneratedOutput.output_type == output_type)
            .order_by(GeneratedOutput.version.desc())
            .first()
        )
        row = ValidationResult(
            job_id=job_id,
            output_id=output.id if output else None,
            check_type=report.check_type,
            passed=report.passed,
            severity=report.severity,
            attempt=report.attempt,
            details_json={"issues": [i.model_dump() for i in report.issues]},
        )
        db.add(row)
        db.commit()
    finally:
        db.close()


def check_consistency(artifact: GeneratedArtifact, registry: FactRegistry, attempt: int) -> ValidationReport:
    text = artifact.markdown + json.dumps(artifact.payload)
    issues: list[ValidationIssue] = []
    for fact, observed in registry.conflicts_with(text):
        issues.append(
            ValidationIssue(
                code="fact_mismatch",
                message=f"{fact.key} expected {fact.value} but output used {observed}",
            )
        )
    for key in artifact.fact_keys_used:
        if registry.get(key) is None:
            issues.append(ValidationIssue(code="unknown_fact_key", message=f"Referenced missing fact {key}"))
    return ValidationReport(
        output_type=artifact.output_type,
        check_type="consistency",
        passed=len(issues) == 0,
        issues=issues,
        attempt=attempt,
        severity="error" if issues else "info",
    )


def check_grounding(artifact: GeneratedArtifact, registry: FactRegistry, source_id: str, attempt: int, grounding_keys: list[str]) -> ValidationReport:
    db = SessionLocal()
    issues: list[ValidationIssue] = []
    try:
        for key in grounding_keys:
            fact = registry.get(key)
            if not fact or fact.importance not in {"high", "critical"}:
                continue
            value = str(fact.value)
            if not value:
                continue
            spans = fact.spans
            found = False
            for span in spans:
                chunk = (
                    db.query(SourceChunk)
                    .filter(SourceChunk.source_id == source_id, SourceChunk.chunk_id == span.chunk_id)
                    .first()
                )
                haystack = (chunk.text if chunk else "") + " " + (span.quote or "")
                if value in haystack or _number_in(value, haystack):
                    found = True
                    break
            if not found and spans:
                issues.append(
                    ValidationIssue(code="ungrounded_fact", message=f"{key}={value} not found in cited chunks")
                )
    finally:
        db.close()
    return ValidationReport(
        output_type=artifact.output_type,
        check_type="grounding",
        passed=len(issues) == 0,
        issues=issues,
        attempt=attempt,
        severity="error" if issues else "info",
    )


def check_quality(artifact: GeneratedArtifact, plan: TransformationPlan, attempt: int) -> ValidationReport:
    issues: list[ValidationIssue] = []
    if artifact.status == "failed" or not artifact.payload:
        issues.append(ValidationIssue(code="empty", message="Output payload is empty"))
        return ValidationReport(
            output_type=artifact.output_type,
            check_type="quality",
            passed=False,
            issues=issues,
            attempt=attempt,
            severity="error",
        )
    payload = artifact.payload
    for section in plan.required_sections:
        if section not in payload or payload[section] in (None, "", [], {}):
            issues.append(ValidationIssue(code="missing_section", message=f"Missing section {section}"))
    constraints = plan.length_constraints
    text = artifact.markdown
    if constraints.max_chars and len(text) > constraints.max_chars + 500:
        issues.append(ValidationIssue(code="too_long", message="Output exceeds length budget"))
    if artifact.output_type == "linkedin_post":
        body = str(payload.get("body") or "")
        if len(body) > 1300:
            issues.append(ValidationIssue(code="linkedin_length", message="LinkedIn body exceeds 1300 characters"))
        if len(body) < 40:
            issues.append(ValidationIssue(code="linkedin_short", message="LinkedIn body is too short"))
    if artifact.output_type == "x_thread":
        for tweet in payload.get("tweets") or []:
            if len(tweet.get("text") or "") > 280:
                issues.append(ValidationIssue(code="tweet_length", message="Tweet exceeds 280 characters"))
        if len(payload.get("tweets") or []) < 2:
            issues.append(ValidationIssue(code="thread_short", message="Thread needs at least 2 tweets"))
    if artifact.output_type == "presentation":
        slides = payload.get("slides") or []
        if len(slides) < 3:
            issues.append(ValidationIssue(code="slides_min", message="Presentation needs at least 3 slides"))
        if any(not s.get("speaker_notes") for s in slides):
            issues.append(ValidationIssue(code="notes_missing", message="Every slide needs speaker notes"))
    return ValidationReport(
        output_type=artifact.output_type,
        check_type="quality",
        passed=len(issues) == 0,
        issues=issues,
        attempt=attempt,
        severity="error" if issues else "info",
    )


def knowledge_hash(knowledge: dict) -> str:
    blob = json.dumps(knowledge, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _number_in(value: str, haystack: str) -> bool:
    digits = re.sub(r"[^\d.]", "", value)
    return bool(digits) and digits in haystack
