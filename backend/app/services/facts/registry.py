from app.schemas import CanonicalFact


class FactRegistry:
    def __init__(self, facts: list[CanonicalFact] | None = None):
        self.facts: list[CanonicalFact] = list(facts or [])

    def add(self, fact: CanonicalFact) -> None:
        existing = self.get(fact.key)
        if existing:
            self.facts = [f for f in self.facts if f.key != fact.key]
        self.facts.append(fact)

    def get(self, key: str) -> CanonicalFact | None:
        for fact in self.facts:
            if fact.key == key:
                return fact
        return None

    def require(self, keys: list[str]) -> list[CanonicalFact]:
        found = []
        for key in keys:
            fact = self.get(key)
            if fact:
                found.append(fact)
        return found

    def as_map(self) -> dict[str, CanonicalFact]:
        return {f.key: f for f in self.facts}

    def as_dicts(self) -> list[dict]:
        return [f.model_dump() for f in self.facts]

    def conflicts_with(self, text: str) -> list[tuple[CanonicalFact, str]]:
        issues: list[tuple[CanonicalFact, str]] = []
        lowered = text.lower()
        for fact in self.facts:
            value = fact.value
            if fact.value_type in {"number", "int", "float"} or isinstance(value, (int, float)):
                canonical = _normalize_number(value)
                for token in _extract_numbers(text):
                    if abs(token - canonical) > 0 and _near_label(lowered, fact):
                        if abs(token - canonical) / max(abs(canonical), 1) > 0.05:
                            issues.append((fact, str(token)))
            else:
                sval = str(value)
                if sval and sval.lower() not in lowered and fact.key.replace("_", " ") in lowered:
                    issues.append((fact, sval))
        return issues


def _normalize_number(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    digits = "".join(ch for ch in str(value) if ch.isdigit() or ch in ".-")
    try:
        return float(digits)
    except ValueError:
        return 0.0


def _extract_numbers(text: str) -> list[float]:
    import re

    values = []
    for match in re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?", text):
        try:
            values.append(float(match.replace(",", "")))
        except ValueError:
            continue
    return values


def _near_label(text: str, fact: CanonicalFact) -> bool:
    label = (fact.label or fact.key).lower()
    tokens = [t for t in label.replace("_", " ").split() if len(t) > 3]
    return any(t in text for t in tokens)
