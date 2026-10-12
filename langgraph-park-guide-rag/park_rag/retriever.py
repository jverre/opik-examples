"""Retriever: an in-memory vector store, wrapped so Opik records each lookup."""

import opik
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

from park_rag.config import EMBEDDING_MODEL
from park_rag.corpus import load_chunks

_store: InMemoryVectorStore | None = None


def _get_store() -> InMemoryVectorStore:
    global _store
    if _store is None:
        _store = InMemoryVectorStore.from_texts(
            load_chunks(), OpenAIEmbeddings(model=EMBEDDING_MODEL)
        )
    return _store


# A named tool span, so the retrieval step is always visible in the trace
# (LangChain retriever runs are not reliably kept by OpikTracer).
@opik.track(name="search_guide", type="tool")
def search_guide(question: str, k: int) -> list[str]:
    """Return the k guide sections most similar to the question."""
    docs = _get_store().similarity_search(question, k=k)
    return [doc.page_content for doc in docs]
