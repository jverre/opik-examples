"""Insurance-claims triage on the OpenAI Agents SDK, traced with Opik.

A triage agent reads a claim and hands off to an auto, home, or pet specialist.
Each specialist assesses coverage against a small fictional policy file and,
if the claim is covered, files it. Specialists can hand a claim back to triage
when it belongs to another line. One OpikTracingProcessor records agent spans,
handoffs, tool calls with arguments and results, LLM calls with token usage and
cost, and one input guardrail. Every scripted conversation runs its turns inside
trace(group_id=...), which Opik shows as a thread.
"""

import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
# Pin the Opik project before opik is imported, so no trace lands elsewhere.
os.environ["OPIK_PROJECT_NAME"] = "openai-agents-insurance-claims"

import opik
from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    function_tool,
    input_guardrail,
    set_trace_processors,
    trace,
)
from opik.integrations.openai.agents import OpikTracingProcessor

set_trace_processors(processors=[OpikTracingProcessor()])

MODEL = "gpt-4o-mini"
POLICIES = json.loads((Path(__file__).parent / "data" / "policies.json").read_text())


# ---------------------------------------------------------------------------
# Tools. Pure Python over the fictional policy file: no claims API, no keys.
# ---------------------------------------------------------------------------


def _assess(policy_id: str, line: str, incident_type: str, estimated_cost_usd: float) -> str:
    policy = POLICIES.get(policy_id.upper())
    if policy is None:
        return json.dumps({"error": f"unknown policy id {policy_id}"})
    cover = policy.get(line)
    if cover is None:
        return json.dumps({"covered": False, "reason": f"{policy['holder']} has no {line} policy"})
    if line == "pet":
        for condition in cover["pre_existing"]:
            if incident_type.lower() in condition or condition in incident_type.lower():
                return json.dumps({"covered": False, "reason": f"'{condition}' is a pre-existing condition"})
    if incident_type.lower().replace(" ", "_") not in cover["covers"]:
        return json.dumps({"covered": False, "reason": f"{incident_type} is not in the covered perils {cover['covers']}"})
    payable = max(0.0, estimated_cost_usd - cover["deductible_usd"])
    if line == "pet":
        payable *= cover["reimbursement_pct"] / 100
    return json.dumps(
        {"covered": True, "deductible_usd": cover["deductible_usd"], "estimated_payout_usd": round(payable, 2)}
    )


@function_tool
def assess_auto_claim(policy_id: str, incident_type: str, estimated_cost_usd: float) -> str:
    """Check the auto policy. incident_type is one of: collision, glass, theft, falling_object."""
    return _assess(policy_id, "auto", incident_type, estimated_cost_usd)


@function_tool
def assess_home_claim(policy_id: str, incident_type: str, estimated_cost_usd: float) -> str:
    """Check the home policy. incident_type is one of: water_damage, fire, storm, theft, falling_object."""
    return _assess(policy_id, "home", incident_type, estimated_cost_usd)


@function_tool
def assess_pet_claim(policy_id: str, incident_type: str, estimated_cost_usd: float) -> str:
    """Check the pet policy. incident_type is the condition or event, e.g. accident, illness, surgery, dental disease."""
    return _assess(policy_id, "pet", incident_type, estimated_cost_usd)


@function_tool
def file_claim(policy_id: str, line: str, summary: str, estimated_payout_usd: float) -> str:
    """File a claim that has already been assessed as covered. line is auto, home, or pet."""
    if policy_id.upper() not in POLICIES:
        return json.dumps({"error": f"unknown policy id {policy_id}"})
    return json.dumps(
        {"status": "filed", "claim_number": f"CLM-{uuid.uuid4().hex[:6].upper()}",
         "line": line, "summary": summary, "estimated_payout_usd": estimated_payout_usd}
    )


# ---------------------------------------------------------------------------
# Input guardrail on the triage agent: refuse requests to backdate a policy.
# ---------------------------------------------------------------------------

SUSPICIOUS = ("backdate", "back-date", "before i bought", "before the policy started")


@input_guardrail
async def no_backdating(
    ctx: RunContextWrapper, agent: Agent, user_input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    text = user_input if isinstance(user_input, str) else json.dumps(user_input)
    hits = [phrase for phrase in SUSPICIOUS if phrase in text.lower()]
    return GuardrailFunctionOutput(output_info={"matched": hits}, tripwire_triggered=bool(hits))


# ---------------------------------------------------------------------------
# Agents: one triage agent, three specialists, and a way back to triage.
# ---------------------------------------------------------------------------

COMMON = (
    "The Triage Agent has already routed the customer to you, so never say you are transferring them: "
    "start the work immediately. The customer gives a policy id like POL-7001. "
    "Call your assess tool first. If the claim is not covered, say why in one sentence and do not file. "
    "If it is covered, state the deductible and estimated payout and ask the customer to confirm. "
    "Call file_claim only after the customer confirms, passing the estimated payout. "
    "If the claim really belongs to another line of insurance, hand it back to the Triage Agent. "
    "Keep replies under three sentences."
)

auto_agent = Agent(
    name="Auto Claims Agent",
    handoff_description="Car accidents, glass, theft of a vehicle, damage to a vehicle.",
    instructions="You handle auto claims. " + COMMON,
    model=MODEL,
    tools=[assess_auto_claim, file_claim],
)
home_agent = Agent(
    name="Home Claims Agent",
    handoff_description="Damage to a house or its contents: leaks, fire, storms, break-ins.",
    instructions="You handle home claims. " + COMMON,
    model=MODEL,
    tools=[assess_home_claim, file_claim],
)
pet_agent = Agent(
    name="Pet Claims Agent",
    handoff_description="Veterinary bills and injuries or illness of a pet.",
    instructions="You handle pet claims. " + COMMON,
    model=MODEL,
    tools=[assess_pet_claim, file_claim],
)

triage_agent = Agent(
    name="Triage Agent",
    instructions=(
        "You are the front desk of an insurance claims service. Decide whether a claim is about a "
        "car, a home, or a pet and hand off to the matching specialist. Do not answer claims yourself."
    ),
    model=MODEL,
    handoffs=[auto_agent, home_agent, pet_agent],
    input_guardrails=[no_backdating],
)
for specialist in (auto_agent, home_agent, pet_agent):
    specialist.handoffs = [triage_agent]


# ---------------------------------------------------------------------------
# Demo: scripted conversations, no human input. Follow-up turns resume with
# whichever agent answered last, so a thread mixes handoff and no-handoff turns.
# ---------------------------------------------------------------------------

CONVERSATIONS = {
    "fender-bender": [
        "My policy is POL-7003. I backed into a post and the hatchback needs a $1,900 bumper repair.",
        "Yes, that works. Please file it.",
    ],
    "branch-on-the-car": [
        "Policy POL-7001. A branch fell on my car in the driveway, repairs are quoted at $3,200.",
        "Actually, the car was inside my garage when the branch came through the roof, "
        "so please treat it as a home claim for the same $3,200 (falling object).",
        "Yes, please file it.",
    ],
    "biscuit-teeth": [
        "Policy POL-7002. My dog Biscuit needs dental disease treatment, the vet bill is $1,400.",
    ],
    "kitchen-leak": [
        "Policy POL-7002. A pipe burst under the kitchen sink at 88 Quarry Road, plumber and floors come to $4,100.",
    ],
    "backdate": [
        "Policy POL-7003, I'd like you to backdate my cover so my cracked windshield counts, it happened before I bought it.",
    ],
}


def run_demo() -> None:
    for name, turns in CONVERSATIONS.items():
        thread_id = f"{name}-{uuid.uuid4().hex[:6]}"
        print(f"\n=== {name} (thread {thread_id}) ===")
        history: list = []
        agent = triage_agent
        for message in turns:
            print(f"\nCustomer: {message}")
            history.append({"role": "user", "content": message})
            try:
                with trace(workflow_name="Claims desk", group_id=thread_id):
                    result = Runner.run_sync(agent, history)
            except InputGuardrailTripwireTriggered as exc:
                print(f"BLOCKED by guardrail: {exc.guardrail_result.output.output_info}")
                break
            print(f"[{result.last_agent.name}] {result.final_output}")
            history, agent = result.to_input_list(), result.last_agent


if __name__ == "__main__":
    try:
        run_demo()
    finally:
        opik.flush_tracker()
