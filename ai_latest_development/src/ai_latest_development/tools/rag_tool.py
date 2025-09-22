import os
from pathlib import Path
from typing import List, Tuple

import chromadb
from chromadb.utils import embedding_functions
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

try:
    import google.generativeai as genai
except Exception as e:  # pragma: no cover
    genai = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


class GeminiEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Embedding function adapter for Chroma using Gemini embeddings."""

    def __init__(self, model: str = "text-embedding-004", api_key_env: str = "GEMINI_API_KEY"):
        self.model = model
        self.api_key_env = api_key_env
        self._configured = False

    def _ensure_configured(self) -> None:
        if self._configured:
            return
        api_key = os.getenv(self.api_key_env) or os.getenv("GOOGLE_API_KEY")
        if genai is None:
            raise RuntimeError("google-generativeai is not installed. Please add it to dependencies.")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY not set in environment.")
        genai.configure(api_key=api_key)
        self._configured = True

    def __call__(self, texts: List[str]) -> List[List[float]]:
        self._ensure_configured()
        vectors: List[List[float]] = []
        for t in texts:
            try:
                resp = genai.embed_content(model=self.model, content=t)
                if isinstance(resp, dict) and "embedding" in resp:
                    vectors.append(resp["embedding"])  # type: ignore[arg-type]
                elif hasattr(resp, "embedding"):
                    vectors.append(getattr(resp, "embedding"))
                elif hasattr(resp, "embeddings") and resp.embeddings:  # type: ignore[attr-defined]
                    vectors.append(resp.embeddings[0].values)  # type: ignore[attr-defined]
                else:
                    # Fallback to zero vector of 768 dims
                    vectors.append([0.0] * 768)
            except Exception:
                vectors.append([0.0] * 768)
        return vectors


def _read_pdf_text(pdf_path: Path) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed. Please add it to dependencies.")
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n\n".join(pages)


def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunk = text[start:end]
        chunks.append(chunk)
        start = max(end - overlap, start + 1)
    return chunks


class RAGIndex:
    """Simple persistent RAG index using Chroma and Gemini embeddings."""

    def __init__(self, data_dir: Path, index_dir: Path):
        self.data_dir = data_dir
        self.index_dir = index_dir
        self.client = chromadb.PersistentClient(path=str(self.index_dir))
        self.embedding_fn = GeminiEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="ai_rules",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

    def build(self) -> None:
        pdf_files = sorted(self.data_dir.glob("*.pdf"))
        for pdf in pdf_files:
            doc_id_prefix = pdf.stem
            # Skip if already indexed by checking one id existence
            existing = self.collection.get(ids=[f"{doc_id_prefix}_0"], include=["metadatas", "documents"])  # type: ignore[arg-type]
            if existing and existing.get("ids"):
                continue
            text = _read_pdf_text(pdf)
            chunks = _chunk_text(text)
            ids = [f"{doc_id_prefix}_{i}" for i in range(len(chunks))]
            metadatas = [{"source": pdf.name, "chunk": i} for i in range(len(chunks))]
            if chunks:
                self.collection.add(ids=ids, documents=chunks, metadatas=metadatas)

    def query(self, question: str, k: int = 6) -> List[Tuple[str, dict]]:
        res = self.collection.query(query_texts=[question], n_results=k)
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        return list(zip(docs, metas))


_index_singleton: RAGIndex | None = None


def _find_project_root(start: Path) -> Path:
    """Walk upwards to find the project root that contains 'AiRules' or pyproject.toml.

    Falls back to the top-most parent.
    """
    current = start
    last = None
    while current != last:
        if (current / "AiRules").exists() or (current / "pyproject.toml").exists():
            return current
        last = current
        current = current.parent
    return start


def _get_index() -> RAGIndex:
    global _index_singleton
    if _index_singleton is None:
        # Discover project root robustly (previous implementation pointed one level too shallow)
        file_path = Path(__file__).resolve()
        project_root = _find_project_root(file_path.parent)
        data_dir = project_root / "AiRules"
        index_dir = project_root / "ai_latest_development" / "knowledge" / "rag_index"
        index_dir.mkdir(parents=True, exist_ok=True)
        _index_singleton = RAGIndex(data_dir=data_dir, index_dir=index_dir)
        # Build only if corpus exists
        if data_dir.exists():
            try:
                _index_singleton.build()
            except Exception:
                # Swallow build errors to keep tool non-fatal; queries will state failure
                pass
    return _index_singleton


def rag_search(query: str, k: int = 6) -> str:
    """Search AiRules corpus and return top-k chunks with citations.

    Returns a markdown string with numbered snippets and sources.
    """
    try:
        index = _get_index()
    except Exception as e:
        return f"RAG unavailable: {e}"
    # Validate corpus exists
    if not index.data_dir.exists():
        return "No AiRules corpus found. Ensure the 'AiRules' folder exists at project root."
    try:
        results = index.query(query, k=k)
    except Exception as e:
        return f"RAG query failed: {e}"
    if not results:
        return "No relevant context found in AiRules."
    lines: List[str] = []
    for i, (doc, meta) in enumerate(results, 1):
        src = meta.get("source", "unknown") if isinstance(meta, dict) else "unknown"
        lines.append(f"[{i}] Source: {src}\n{doc.strip()[:1500]}")
    return "\n\n".join(lines)


class RagSearchInput(BaseModel):
    query: str = Field(..., description="Search query for the AiRules knowledge base")
    k: int = Field(6, description="Number of results to retrieve")


class RagSearchTool(BaseTool):
    name: str = "rag_search"
    description: str = (
        "Search AiRules PDFs and return the top-k contextual snippets with citations."
    )
    args_schema: type[BaseModel] = RagSearchInput

    def _run(self, query: str, k: int = 6) -> str:  # type: ignore[override]
        return rag_search(query=query, k=k)

    async def _arun(self, query: str, k: int = 6) -> str:  # type: ignore[override]
        return rag_search(query=query, k=k)


