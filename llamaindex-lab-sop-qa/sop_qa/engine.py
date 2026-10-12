"""Index the SOP PDFs and answer questions with a LlamaIndex query engine."""

from dataclasses import dataclass

from llama_index.core import (
    PromptTemplate,
    Settings,
    SimpleDirectoryReader,
    VectorStoreIndex,
    set_global_handler,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from . import PROJECT_NAME
from .pdfs import ensure_pdfs

ANSWER_MODEL = "gpt-4o-mini"

# The synthesis prompt. It shows up verbatim in the "templating" span in Opik.
QA_TEMPLATE = PromptTemplate(
    "You answer questions for staff of the Fennmoor Cell Biology Lab using only the "
    "SOP excerpts below. Quote exact figures (times, masses, speeds, extensions). "
    "If the excerpts do not cover the question, say that the SOPs do not cover it.\n"
    "---------------------\n{context_str}\n---------------------\n"
    "Question: {query_str}\nAnswer: "
)


@dataclass
class Answer:
    question: str
    answer: str
    excerpts: list[dict]  # what the retrieve step returned, in rank order


def enable_tracing() -> None:
    """Opik's LlamaIndex integration: one call, every retrieve/synthesize/llm step is traced."""
    set_global_handler("opik", project_name=PROJECT_NAME, skip_index_construction_trace=True)


def build_engine(top_k: int = 3):
    """Read the PDFs, chunk them by section-sized pieces, embed, and return a query engine."""
    Settings.llm = OpenAI(model=ANSWER_MODEL, temperature=0.0)
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    # Small chunks so that one chunk is roughly one numbered SOP section.
    Settings.node_parser = SentenceSplitter(chunk_size=160, chunk_overlap=20)
    documents = SimpleDirectoryReader(str(ensure_pdfs())).load_data()
    index = VectorStoreIndex.from_documents(documents)
    return index.as_query_engine(similarity_top_k=top_k, text_qa_template=QA_TEMPLATE)


def ask(engine, question: str) -> Answer:
    response = engine.query(question)
    excerpts = [
        {
            "source": node.node.metadata.get("file_name", "?"),
            "score": round(node.score or 0.0, 3),
            "text": node.node.get_content().strip(),
        }
        for node in response.source_nodes
    ]
    return Answer(question=question, answer=str(response).strip(), excerpts=excerpts)
