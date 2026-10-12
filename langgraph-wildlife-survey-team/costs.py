"""Read one run back from Opik and print what each agent cost.

Every LLM call is a child span of the node that made it (planner,
field_researcher, writer), so cost per agent is the sum of the llm spans
under each node span. Ingestion is asynchronous, so we poll briefly.
"""

import time
from collections import defaultdict

import opik

AGENTS = ("planner", "field_researcher", "writer")


def _agent_of(span, by_id: dict) -> str | None:
    """Walk up the span tree to the agent node a span belongs to."""
    while span is not None:
        if span.name in AGENTS and span.type == "general":
            return span.id
        span = by_id.get(span.parent_span_id)
    return None


def print_cost_per_agent(project_name: str, timeout: float = 60.0) -> None:
    client = opik.Opik(project_name=project_name)
    deadline = time.time() + timeout
    while True:
        traces = client.search_traces(project_name=project_name, max_results=1)
        spans = (
            client.search_spans(project_name=project_name, trace_id=traces[0].id,
                                max_results=200)
            if traces else []
        )
        llm_spans = [s for s in spans if s.type == "llm"]
        done = {"planner", "writer"} <= {s.name for s in spans} and llm_spans and all(
            s.total_estimated_cost is not None for s in llm_spans
        )
        if done or time.time() > deadline:
            break
        time.sleep(3)

    if not traces or not llm_spans:
        print("\nNo cost data found in Opik yet; check the project in the UI.")
        return

    by_id = {s.id: s for s in spans}
    cost, tokens, passes = defaultdict(float), defaultdict(int), defaultdict(int)
    for s in spans:
        if s.name in AGENTS and s.type == "general":
            passes[s.name] += 1
    for s in llm_spans:
        agent = by_id.get(_agent_of(s, by_id))
        key = agent.name if agent else "other"
        cost[key] += s.total_estimated_cost or 0.0
        tokens[key] += (s.usage or {}).get("total_tokens", 0)

    print(f"\nCost per agent, read back from trace {traces[0].id} in '{project_name}':")
    for name in (*AGENTS, "other"):
        if name in cost:
            print(f"  {name:<17} x{passes.get(name, 0)}  {tokens[name]:>6} tokens  "
                  f"${cost[name]:.5f}")
    print(f"  {'total':<17}     {sum(tokens.values()):>6} tokens  "
          f"${sum(cost.values()):.5f}")
