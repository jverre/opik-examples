"""Read the newest trace back from Opik and print tokens and dollars per agent.

Opik computes the cost server side from the model name and the token usage on
each LLM span, so this report is just a roll-up of what the trace already holds:
walk each LLM span up to its agent span and sum.
"""

import time

import opik

AGENT_ROLES = {"Market Analyst", "Messaging Strategist", "Launch Planner"}


def _wait_for_spans(client, project, expected_agents, timeout=60):
    """Poll until the newest trace has an LLM span with a cost for every agent."""
    deadline = time.time() + timeout
    while True:
        traces = client.search_traces(project_name=project, max_results=1)
        if traces:
            spans = client.search_spans(
                project_name=project, trace_id=traces[0].id, max_results=500
            )
            llm = [s for s in spans if s.type == "llm" and s.total_estimated_cost]
            if len(llm) >= expected_agents or time.time() > deadline:
                return traces[0], spans
        elif time.time() > deadline:
            return None, []
        time.sleep(3)


def print_cost_report(project):
    client = opik.Opik(project_name=project)
    trace, spans = _wait_for_spans(client, project, expected_agents=len(AGENT_ROLES))
    if trace is None:
        print("No trace found yet; open the project in Opik.")
        return

    by_id = {s.id: s for s in spans}

    def agent_of(span):
        while span is not None:
            if span.name in AGENT_ROLES:
                return span.name
            span = by_id.get(span.parent_span_id)
        return "(unattributed)"

    rows = {}
    for s in spans:
        if s.type != "llm":
            continue
        usage = s.usage or {}
        row = rows.setdefault(agent_of(s), [0, 0, 0, 0, 0.0])
        row[0] += 1
        row[1] += usage.get("prompt_tokens", 0)
        row[2] += usage.get("completion_tokens", 0)
        row[3] += usage.get("total_tokens", 0)
        row[4] += s.total_estimated_cost or 0.0

    print(f"\n=== TOKENS AND COST PER AGENT (trace {trace.id}) ===\n")
    print(f"{'agent':<22}{'calls':>6}{'prompt':>9}{'completion':>12}{'total':>8}{'cost (USD)':>13}")
    totals = [0, 0, 0, 0, 0.0]
    for agent in ["Market Analyst", "Messaging Strategist", "Launch Planner"]:
        if agent not in rows:
            continue
        r = rows[agent]
        print(f"{agent:<22}{r[0]:>6}{r[1]:>9}{r[2]:>12}{r[3]:>8}{r[4]:>13.6f}")
        totals = [a + b for a, b in zip(totals, r)]
    print(f"{'TOTAL':<22}{totals[0]:>6}{totals[1]:>9}{totals[2]:>12}{totals[3]:>8}{totals[4]:>13.6f}")
    print(f"\n{len(spans)} spans in one trace, project '{project}'. Open it in Opik to see the same numbers per span.")
