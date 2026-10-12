"""A wildlife survey team in LangGraph, traced with Opik.

A planner turns one question about a fictional nature reserve into survey
sub-questions, field researchers work through them one pass at a time against
an offline corpus of field notes in data/, and a writer composes the survey
report. The compiled graph is wrapped once with track_langgraph, so the whole
run lands in Opik as a single deep trace, loop included.
"""

import math
import os
import pathlib
import re

PROJECT_NAME = "langgraph-wildlife-survey-team"
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

import dotenv

dotenv.load_dotenv()

import opik
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from opik.integrations.langchain import OpikTracer, track_langgraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from costs import print_cost_per_agent

DATA_DIR = pathlib.Path(__file__).parent / "data"
QUESTION = (
    "Which species at Marrow Fen Reserve should get protection priority next "
    "season, and what should the survey team do about it?"
)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# --- The offline corpus: field notes, searched by keyword overlap --------------

def load_corpus() -> list[dict]:
    """One searchable entry per '##' section of each field-notes file."""
    entries = []
    for path in sorted(DATA_DIR.glob("*.md")):
        title, *sections = path.read_text().split("\n## ")
        for section in sections:
            entries.append({
                "source": path.name,
                "text": f"{title.strip()}\n\n## {section.strip()}",
            })
    return entries


CORPUS = load_corpus()
STOPWORDS = frozenset(
    "the a an and or of to in for is are was were be been being what how why "
    "when which who should would could can may might must with on by as at it "
    "its if into from that this these those do does did not no so such any "
    "some next season reserve marrow fen team survey".split()
)


def rarity(term: str) -> float:
    """Weight a term by how few corpus sections contain it (a tiny IDF)."""
    containing = sum(1 for e in CORPUS if term in e["text"].lower())
    return math.log(len(CORPUS) / containing) if containing else 0.0


def search_notes(query: str, k: int = 3) -> list[dict]:
    """Rank corpus sections by the rarity-weighted query terms they contain."""
    terms = set(re.findall(r"[a-z0-9]+", query.lower())) - STOPWORDS

    def score(entry: dict) -> float:
        text = entry["text"].lower()
        return sum(rarity(t) for t in terms if t in text)

    return sorted(CORPUS, key=score, reverse=True)[:k]


# --- The team state -------------------------------------------------------------

class Finding(TypedDict):
    sub_question: str
    answer: str
    sources: list[str]


class SurveyState(TypedDict):
    question: str
    sub_questions: list[str]
    findings: list[Finding]
    report: str


# --- Agent 1: the planner splits the question -----------------------------------

class SurveyPlan(BaseModel):
    """The planner's output: 4 focused sub-questions."""

    sub_questions: list[str] = Field(
        description="Exactly 4 sub-questions that together answer the main question"
    )


def planner(state: SurveyState) -> dict:
    """Break the survey question into sub-questions for the field researchers."""
    plan = llm.with_structured_output(SurveyPlan).invoke([
        ("system",
         "You lead a wildlife survey team at a nature reserve. The team has "
         "field notes on four areas: the north fen transects (birds), the "
         "kestrel ridge raptor watch, the Cold Spring Creek amphibian and "
         "mammal survey, and the trail camera log, plus the reserve's survey "
         "protocols. Split the user's question into exactly 4 concrete "
         "sub-questions, each answerable from those notes. Ask about "
         "population trends and threats, not just counts, and cover birds, "
         "raptors, creek wildlife, and how reliable the data and budget are."),
        ("user", state["question"]),
    ])
    return {"sub_questions": plan.sub_questions, "findings": []}


# --- Agent 2: a field researcher answers one sub-question per pass --------------

def field_researcher(state: SurveyState) -> dict:
    """Answer the next open sub-question from the best-matching field notes."""
    sub_question = state["sub_questions"][len(state["findings"])]
    hits = search_notes(sub_question)
    excerpts = "\n\n---\n\n".join(f"[{h['source']}]\n{h['text']}" for h in hits)
    answer = llm.invoke([
        ("system",
         "You are a field researcher. Answer the sub-question using only the "
         "note excerpts below. Quote concrete counts, name the source file for "
         "each claim, and mention any coverage caveat. If the excerpts do not "
         "answer it, say so.\n\n" + excerpts),
        ("user", sub_question),
    ])
    finding: Finding = {
        "sub_question": sub_question,
        "answer": answer.content,
        "sources": sorted({h["source"] for h in hits}),
    }
    return {"findings": state["findings"] + [finding]}


def route_research(state: SurveyState) -> str:
    """Loop the field researcher until every sub-question has a finding."""
    if len(state["findings"]) < len(state["sub_questions"]):
        return "field_researcher"
    return "writer"


# --- Agent 3: the writer composes the report ------------------------------------

def writer(state: SurveyState) -> dict:
    """Turn the findings into a survey report with a ranked recommendation."""
    notes = "\n\n".join(
        f"### {f['sub_question']}\n{f['answer']}\n(Sources: {', '.join(f['sources'])})"
        for f in state["findings"]
    )
    report = llm.invoke([
        ("system",
         "You are the survey team's writer. Compose a survey report in "
         "markdown: a two-sentence summary, one short section per finding, a "
         "ranked list of priority species, and the next-season actions. Use "
         "only the research notes below, keep every count and source "
         "citation accurate, and flag low-confidence data. Under 450 "
         "words.\n\n" + notes),
        ("user", state["question"]),
    ])
    return {"report": report.content}


# --- Wire the graph: planner -> (field researcher loop) -> writer ---------------

graph = StateGraph(SurveyState)
graph.add_node("planner", planner)
graph.add_node("field_researcher", field_researcher)
graph.add_node("writer", writer)
graph.add_edge(START, "planner")
graph.add_edge("planner", "field_researcher")
graph.add_conditional_edges(
    "field_researcher",
    route_research,
    {"field_researcher": "field_researcher", "writer": "writer"},
)
graph.add_edge("writer", END)

# Wrap the compiled graph once. Every invocation becomes one Opik trace with
# the agent graph attached and one span per node pass, LLM calls nested inside.
opik_tracer = OpikTracer(project_name=PROJECT_NAME, tags=["wildlife-survey"])
app = track_langgraph(graph.compile(), opik_tracer)


def main() -> None:
    print(f"Survey question: {QUESTION}\n")
    result = app.invoke({"question": QUESTION})

    print("The planner split the question into:")
    for i, sq in enumerate(result["sub_questions"], 1):
        print(f"  {i}. {sq}")
    print(f"\nThe field researchers produced {len(result['findings'])} findings. "
          "The writer's report:\n")
    print(result["report"])

    opik_tracer.flush()
    opik.flush_tracker()
    print_cost_per_agent(PROJECT_NAME)


if __name__ == "__main__":
    main()
