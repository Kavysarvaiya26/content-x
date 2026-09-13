from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.schemas import GENERATOR_NODE, GeneratedArtifact
from app.services.graph.nodes import (
    analyze,
    consistency_check,
    extract,
    fan_in,
    finalize,
    generate_output,
    grounding_check,
    ingest,
    plan_outputs,
    quality_check,
    repair_output,
    structure_knowledge,
)


def upsert_artifacts(existing: list | None, new: list | None) -> list:
    items = list(existing or []) + list(new or [])
    by_type = {}

    for item in items:
        if isinstance(item, dict):
            output_type = item.get("output_type")
            item_dict = item
        elif hasattr(item, "model_dump"):
            item_dict = item.model_dump()
            output_type = item_dict.get("output_type")
        elif hasattr(item, "output_type"):
            output_type = getattr(item, "output_type")
            item_dict = {"output_type": output_type}
        else:
            continue

        if output_type:
            by_type[output_type] = item_dict

    return list(by_type.values())


def add_list(existing: list | None, new: list | None) -> list:
    return list(existing or []) + list(new or [])


def merge_dicts(existing: dict | None, new: dict | None) -> dict:
    res = dict(existing or {})
    if new:
        res.update(new)
    return res


def take_last(existing: Any, new: Any) -> Any:
    return new if new is not None else existing


class TransformState(TypedDict, total=False):
    job_id: str
    source_id: str
    knowledge: dict | None
    fact_registry: list
    config: dict
    selected_outputs: list
    output_plans: dict
    generated: Annotated[list, upsert_artifacts]
    validations: Annotated[list, add_list]
    repair_attempts: Annotated[dict, merge_dicts]
    failed_output_types: list
    status: str
    errors: Annotated[list, add_list]
    warnings: Annotated[list, add_list]
    current_node: Annotated[str, take_last]
    target_output_type: str
    repair_issues: list


def _payload(state: TransformState, output_type: str, repair: bool = False) -> dict[str, Any]:
    data = {
        "job_id": state["job_id"],
        "source_id": state["source_id"],
        "knowledge": state.get("knowledge"),
        "fact_registry": state.get("fact_registry") or [],
        "config": state.get("config") or {},
        "selected_outputs": state.get("selected_outputs") or [],
        "output_plans": state.get("output_plans") or {},
        "target_output_type": output_type,
        "repair_attempts": state.get("repair_attempts") or {},
        "generated": state.get("generated") or [],
        "validations": state.get("validations") or [],
    }
    if repair:
        issues = [
            issue
            for report in state.get("validations") or []
            if report.get("output_type") == output_type and not report.get("passed")
            for issue in report.get("issues") or []
        ]
        data["repair_issues"] = issues
    return data


def route_selected_outputs(state: TransformState):
    selected = state.get("selected_outputs") or []
    if not selected:
        return "fan_in"
    return [Send(GENERATOR_NODE[t], _payload(state, t)) for t in selected if t in GENERATOR_NODE]


def route_repair(state: TransformState):
    failed = state.get("failed_output_types") or []
    attempts = dict(state.get("repair_attempts") or {})
    sends = []
    for output_type in failed:
        if attempts.get(output_type, 0) < 1:
            sends.append(Send("repair_output", _payload(state, output_type, repair=True)))
    if sends:
        return sends
    return "finalize"


def make_generator_node(output_type: str):
    async def _node(state: TransformState):
        return await generate_output({**state, "target_output_type": output_type})

    _node.__name__ = GENERATOR_NODE[output_type]
    return _node


def build_graph():
    graph = StateGraph(TransformState)
    graph.add_node("ingest", ingest)
    graph.add_node("extract", extract)
    graph.add_node("analyze", analyze)
    graph.add_node("structure_knowledge", structure_knowledge)
    graph.add_node("plan_outputs", plan_outputs)
    for output_type, node_name in GENERATOR_NODE.items():
        graph.add_node(node_name, make_generator_node(output_type))
    graph.add_node("fan_in", fan_in)
    graph.add_node("consistency_check", consistency_check)
    graph.add_node("grounding_check", grounding_check)
    graph.add_node("quality_check", quality_check)
    graph.add_node("repair_output", repair_output)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "extract")
    graph.add_edge("extract", "analyze")
    graph.add_edge("analyze", "structure_knowledge")
    graph.add_edge("structure_knowledge", "plan_outputs")
    graph.add_conditional_edges("plan_outputs", route_selected_outputs)
    for node_name in GENERATOR_NODE.values():
        graph.add_edge(node_name, "fan_in")
    graph.add_edge("fan_in", "consistency_check")
    graph.add_edge("consistency_check", "grounding_check")
    graph.add_edge("grounding_check", "quality_check")
    graph.add_conditional_edges("quality_check", route_repair)
    graph.add_edge("repair_output", "fan_in")
    graph.add_edge("finalize", END)
    return graph.compile()


compiled_graph = None


def get_graph():
    global compiled_graph
    if compiled_graph is None:
        compiled_graph = build_graph()
    return compiled_graph
