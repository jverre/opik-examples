"""The LangGraph pipeline: retrieve -> generate, traced by OpikTracer."""

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from opik.integrations.langchain import OpikTracer, track_langgraph
from typing_extensions import TypedDict

from park_rag.config import ANSWER_MODEL, PROJECT_NAME
from park_rag.retriever import search_guide

SYSTEM_PROMPT = (
    "You are the visitor-information assistant for Alder Hollow National Park. "
    "Answer using only the guide excerpts below. If they do not cover the "
    "question, say the guide does not say. Be concise.\n\n"
)


class State(TypedDict):
    question: str
    context: list[str]
    answer: str


def build_graph(k: int = 3):
    """Compile the graph with k retrieved sections; returns (app, tracer)."""
    llm = ChatOpenAI(model=ANSWER_MODEL, temperature=0)

    def retrieve(state: State) -> dict:
        return {"context": search_guide(state["question"], k)}

    def generate(state: State) -> dict:
        context = "\n\n---\n\n".join(state["context"])
        reply = llm.invoke(
            [("system", SYSTEM_PROMPT + context), ("user", state["question"])]
        )
        return {"answer": reply.content}

    graph = StateGraph(State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    tracer = OpikTracer(
        project_name=PROJECT_NAME,
        graph=graph.compile().get_graph(xray=True),
        tags=[f"k={k}"],
    )
    return track_langgraph(graph.compile(), tracer), tracer
