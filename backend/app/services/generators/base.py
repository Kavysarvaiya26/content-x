import json
from typing import Type

from pydantic import BaseModel

from app.schemas import CanonicalKnowledge, GeneratedArtifact, TransformationPlan
from app.services.facts.registry import FactRegistry
from app.services.llm.provider import get_provider


class BaseGenerator:
    output_type: str
    schema: Type[BaseModel]

    def system_prompt(self) -> str:
        # Base instruction common to all generators
        base = (
            "You transform canonical structured knowledge into one communication deliverable. "
            "Use only FactRegistry values for numbers, dates, and names. "
            "Never invent facts. If something is listed under unknowns or prohibited assumptions, omit it. "
            "Return JSON only."
        )
        # Append any subclass‑specific guidelines if they exist
        if getattr(self, "output_guidelines", []):
            guidelines = " ".join(self.output_guidelines)
            return f"{base} {guidelines}"
        return base


    def build_messages(
        self,
        knowledge: CanonicalKnowledge,
        registry: FactRegistry,
        plan: TransformationPlan,
        repair_issues: list[str] | None = None,
    ) -> list[dict]:
        payload = {
            "knowledge": knowledge.model_dump(),
            "fact_registry": registry.as_dicts(),
            "plan": plan.model_dump(),
        }
        if repair_issues:
            payload["repair_issues"] = repair_issues
        return [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": json.dumps(payload)},
        ]

    def to_markdown(self, payload: BaseModel) -> str:
        return f"```json\n{payload.model_dump_json(indent=2)}\n```"

    async def generate(
        self,
        knowledge: CanonicalKnowledge,
        registry: FactRegistry,
        plan: TransformationPlan,
        repair_issues: list[str] | None = None,
    ) -> GeneratedArtifact:
        try:
            llm = get_provider()
            messages = self.build_messages(knowledge, registry, plan, repair_issues)
            result = await llm.structured(messages, self.schema)
            data = result.model_dump()
            keys = data.get("fact_keys_used") or plan.must_use_fact_keys
            return GeneratedArtifact(
                output_type=self.output_type,
                status="repaired" if repair_issues else "succeeded",
                payload=data,
                markdown=self.to_markdown(result),
                fact_keys_used=keys,
            )
        except Exception as exc:
            return GeneratedArtifact(
                output_type=self.output_type,
                status="failed",
                payload={},
                markdown="",
                error=str(exc)[:400],
            )
