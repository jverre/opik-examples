"""Launch-planning crew for Fernwick Mobility, traced with Opik.

Three agents run in sequence: a market analyst digests a fictional launch
file (data/product_brief.md), a messaging strategist turns the findings
into positioning against each competitor, and a launch planner writes a
90-day launch plan. One call to track_crewai logs the whole run to the
"crewai-product-launch" Opik project: one trace per kickoff, with nested
spans per task and agent, and token usage and cost on every LLM call.

No web-search tools are involved, so the run is offline and cheap.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent

# Load a local .env (if present) before crewai/opik read the keys.
load_dotenv(ROOT / ".env")

PROJECT = "crewai-product-launch"
# Make the project explicit for the whole process, including the Opik client
# used by the cost report, so no trace lands in a default project.
os.environ["OPIK_PROJECT_NAME"] = PROJECT

import opik
from crewai import Agent, Crew, Process, Task
from opik.integrations.crewai import track_crewai

MODEL = "gpt-4o-mini"

LAUNCH_FILE = (ROOT / "data" / "product_brief.md").read_text()

# --- Agents -----------------------------------------------------------------

market_analyst = Agent(
    role="Market Analyst",
    goal="Pull the facts that decide a launch out of raw research notes.",
    backstory=(
        "A methodical analyst who never speculates: every claim is grounded "
        "in the notes you were given, with the number attached."
    ),
    llm=MODEL,
)

messaging_strategist = Agent(
    role="Messaging Strategist",
    goal="Decide what Fernwick Glide should say, and to whom, against each rival.",
    backstory=(
        "A former product marketer who has launched hardware into crowded "
        "categories and writes positioning that fits on one slide."
    ),
    llm=MODEL,
)

launch_planner = Agent(
    role="Launch Planner",
    goal="Turn analysis and positioning into a 90-day plan the team can execute.",
    backstory=(
        "A pragmatic program manager who sizes every plan to the budget and "
        "the team that has to deliver it. You never exceed the budget."
    ),
    llm=MODEL,
)

# --- Tasks (sequential) -----------------------------------------------------

analysis_task = Task(
    name="Analyze the market",
    description=(
        "Read the launch file below and summarize what matters for launching "
        "Fernwick Glide. Use ONLY this file; do not invent facts or numbers."
        "\n\nLAUNCH FILE:\n\n{launch_file}"
    ),
    expected_output=(
        "6-8 bullet points covering the buyer, purchase drivers, objections, "
        "each competitor's weakness, and which channels reach research-stage "
        "buyers. Every bullet cites a number from the file."
    ),
    agent=market_analyst,
)

messaging_task = Task(
    name="Write the positioning",
    description=(
        "Using the market analysis, write positioning for Fernwick Glide: one "
        "core message, then one short paragraph per competitor (StrideX S2, "
        "Voltaire Mini, Cobalt Roam) with the line to use against them. "
        "Address the top buyer objection directly."
    ),
    expected_output=(
        "A core message of at most 20 words, three competitor paragraphs, and "
        "one sentence answering the top objection."
    ),
    agent=messaging_strategist,
    context=[analysis_task],
)

plan_task = Task(
    name="Plan the 90-day launch",
    description=(
        "Using the analysis and positioning, write the 90-day launch plan for "
        "Fernwick Glide. Split the $180,000 budget across channels, name the "
        "owner for each activity from the team (2 marketers, 1 community "
        "manager, 1 part-time designer), and say what to measure each month."
        "\n\nThe launch file is repeated here for the budget and channel costs:"
        "\n\n{launch_file}"
    ),
    expected_output=(
        "A plan under 350 words with a budget table whose rows add up to "
        "$180,000 or less, then Month 1, Month 2, Month 3 with owners and "
        "one metric each."
    ),
    agent=launch_planner,
    context=[analysis_task, messaging_task],
)

# --- Crew + Opik ------------------------------------------------------------

crew = Crew(
    agents=[market_analyst, messaging_strategist, launch_planner],
    tasks=[analysis_task, messaging_task, plan_task],
    process=Process.sequential,
    verbose=False,
)

track_crewai(project_name=PROJECT, crew=crew)

if __name__ == "__main__":
    result = crew.kickoff(inputs={"launch_file": LAUNCH_FILE})
    print("\n=== 90-DAY LAUNCH PLAN ===\n")
    print(result)

    # Wait for the trace to reach Opik, then print tokens and dollars per agent.
    opik.flush_tracker()
    from cost_report import print_cost_report

    print_cost_report(PROJECT)
