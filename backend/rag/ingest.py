import json
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


def _build_chunks(policy: dict) -> list[tuple[str, str, dict]]:
    """Returns list of (chunk_id, chunk_text, metadata)."""
    chunks = []
    cd = policy.get("coverage_details", {})

    def add(section_id: str, label: str, data):
        text = f"[{label}]\n{json.dumps(data, indent=2)}"
        chunks.append((section_id, text, {"section": section_id, "source": "policy_terms.json"}))

    add("limits", "Coverage Limits", {
        "annual_limit": policy.get("annual_limit") or cd.get("annual_limit"),  # handle top-level or nested
        "per_claim_limit": cd.get("per_claim_limit"),
        "family_floater_limit": cd.get("family_floater_limit"),
    })
    add("coverage_consultation", "Consultation Fee Coverage", cd.get("consultation_fees", {}))
    add("coverage_diagnostic", "Diagnostic Tests Coverage", cd.get("diagnostic_tests", {}))
    add("coverage_pharmacy", "Pharmacy / Medicines Coverage", cd.get("pharmacy", {}))
    add("coverage_dental", "Dental Treatment Coverage", cd.get("dental", {}))
    add("coverage_vision", "Vision / Eye Care Coverage", cd.get("vision", {}))
    add("coverage_alternative", "Alternative Medicine Coverage", cd.get("alternative_medicine", {}))
    add("waiting_periods", "Waiting Periods", policy.get("waiting_periods", {}))
    add("exclusions", "Policy Exclusions", {"exclusions": policy.get("exclusions", [])})
    add("network_hospitals", "Network Hospitals & Cashless", {
        "network_hospitals": policy.get("network_hospitals", []),
        "cashless_facilities": policy.get("cashless_facilities", {}),
    })
    add("claim_requirements", "Claim Submission Requirements", policy.get("claim_requirements", {}))
    return chunks


def ingest_policy(policy_path: str | None = None, force: bool = False):
    """Load policy_terms.json and embed into ChromaDB. Skips if already ingested."""
    collection = _get_collection()

    if not force and collection.count() > 0:
        return  # already ingested

    path = policy_path or settings.POLICY_TERMS_PATH
    with open(path, "r") as f:
        policy = json.load(f)

    chunks = _build_chunks(policy)

    # Upsert so re-runs are idempotent
    collection.upsert(
        ids=[c[0] for c in chunks],
        documents=[c[1] for c in chunks],
        metadatas=[c[2] for c in chunks],
    )
    print(f"[RAG] Ingested {len(chunks)} policy chunks into ChromaDB.")


def ingest_section(section_id: str, label: str, data: dict):
    """Re-embed a single policy section (used after admin policy update)."""
    collection = _get_collection()
    text = f"[{label}]\n{json.dumps(data, indent=2)}"
    collection.upsert(
        ids=[section_id],
        documents=[text],
        metadatas=[{"section": section_id, "source": "policy_config_db"}],
    )
    print(f"[RAG] Re-ingested section: {section_id}")


def rebuild_from_db(sections: list[dict]):
    """Re-embed all sections from DB policy config records."""
    collection = _get_collection()
    collection.delete(where={"source": "policy_config_db"})
    for s in sections:
        data = json.loads(s["config_json"])
        text = f"[{s['section']}]\n{json.dumps(data, indent=2)}"
        collection.upsert(
            ids=[s["section"]],
            documents=[text],
            metadatas=[{"section": s["section"], "source": "policy_config_db"}],
        )
    print(f"[RAG] Rebuilt {len(sections)} sections from DB.")
