import os
import glob
import re
from typing import List, Dict, Any
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_SENTENCE_TRANSFORMERS = True
except Exception as e:
    print(f"SentenceTransformer/FAISS warning: {e}. Fallback to keyword TF-IDF matcher.")
    HAS_SENTENCE_TRANSFORMERS = False

RETRIEVAL_STOP_WORDS = {
    "about", "after", "again", "also", "any", "are", "been", "before", "being",
    "between", "both", "care", "could", "does", "during", "each", "from", "have",
    "health", "help", "here", "hospital", "into", "just", "medical", "more", "most",
    "much", "need", "other", "our", "patient", "please", "should", "some", "tell",
    "than", "that", "their", "them", "then", "there", "these", "they", "this", "those",
    "through", "what", "when", "where", "which", "while", "with", "would", "your",
}

class KnowledgeBaseVectorStore:
    def __init__(self, kb_dir: str = "../knowledge_base"):
        self.kb_dir = kb_dir
        self.documents = []
        self.model = None
        self.index = None
        self.doc_embeddings = None
        self.is_initialized = False

    def load_and_index(self):
        # Resolve path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        target_kb_dir = os.path.join(base_dir, "knowledge_base")
        if not os.path.exists(target_kb_dir):
            target_kb_dir = self.kb_dir

        md_files = glob.glob(os.path.join(target_kb_dir, "*.md"))
        chunks = []

        for file_path in md_files:
            file_name = os.path.basename(file_path)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Chunk by section headers (## or #)
                sections = content.split("\n## ")
                for i, sec in enumerate(sections):
                    prefix = "## " if i > 0 else ""
                    chunk_text = (prefix + sec).strip()
                    if len(chunk_text) > 30:
                        chunks.append({
                            "source": file_name,
                            "content": chunk_text
                        })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

        self.documents = chunks
        print(f"Loaded {len(self.documents)} knowledge base chunks from {target_kb_dir}.")

        if HAS_SENTENCE_TRANSFORMERS and len(self.documents) > 0:
            try:
                print("Initializing sentence-transformers/all-MiniLM-L6-v2 embedding model...")
                self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                texts = [doc["content"] for doc in self.documents]
                embeddings = self.model.encode(
                    texts,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )
                self.doc_embeddings = embeddings.astype('float32')

                dimension = embeddings.shape[1]
                self.index = faiss.IndexFlatIP(dimension)
                self.index.add(self.doc_embeddings)
                self.is_initialized = True
                print("FAISS Vector Index initialized successfully.")
                return
            except Exception as e:
                print(f"FAISS/Embedding initialization error: {e}. Falling back to text matching.")

        self.is_initialized = True

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.is_initialized:
            self.load_and_index()

        if not self.documents:
            return []

        if HAS_SENTENCE_TRANSFORMERS and self.model and self.index:
            try:
                query_vec = self.model.encode(
                    [query],
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                ).astype('float32')
                similarities, indices = self.index.search(query_vec, min(top_k, len(self.documents)))

                results = []
                for similarity, idx in zip(similarities[0], indices[0]):
                    if 0 <= idx < len(self.documents) and similarity >= 0.30:
                        results.append(self.documents[idx])
                return results
            except Exception as e:
                print(f"FAISS search failed ({e}), using fallback matcher.")

        # Text matching fallback
        q_tokens = set(re.findall(r"\b\w+\b", query.lower()))
        scored_docs = []
        for doc in self.documents:
            doc_tokens = set(re.findall(r"\b\w+\b", doc["content"].lower()))
            score = sum(
                1 for token in q_tokens
                if len(token) > 3 and token not in RETRIEVAL_STOP_WORDS and token in doc_tokens
            )
            scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:top_k] if score > 0]

# Global singleton instance
vector_store = KnowledgeBaseVectorStore()
