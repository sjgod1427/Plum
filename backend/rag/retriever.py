import chromadb
from chromadb import EmbeddingFunction, Embeddings
from openai import OpenAI
from config import settings


class _OpenAIEmbedder(EmbeddingFunction):
    def __init__(self):
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def __call__(self, input: list[str]) -> Embeddings:
        response = self._client.embeddings.create(
            input=input,
            model="text-embedding-3-small",
        )
        return [item.embedding for item in response.data]


def _get_collection():
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(
        name="policy_terms",
        embedding_function=_OpenAIEmbedder(),
        metadata={"hnsw:space": "cosine"},
    )


def retrieve_policy_context(query: str, top_k: int = 5) -> list[str]:
    """Return top_k relevant policy chunks for the given query."""
    collection = _get_collection()
    if collection.count() == 0:
        return []
    results = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))
    docs = results.get("documents", [[]])[0]
    return docs


def build_rag_query(
    diagnosis: str,
    procedures: list[str],
    medicines: list[str],
    doc_types: list[str],
    hospital: str | None = None,
) -> str:
    parts = [diagnosis] if diagnosis else []
    parts.extend(procedures[:3])
    parts.extend(medicines[:3])
    parts.extend(doc_types)
    if hospital:
        parts.append(hospital)
    return " ".join(parts)
