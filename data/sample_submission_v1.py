"""
AI Microservice & RAG Pipeline Implementation - Deliverable
Intern: Aarav Patel (INT-2026-001)
Department: AI/ML
Version: 1.0
"""

import os
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="RAG Document Intelligence Microservice")

class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: Dict[str, Any]

class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

class QueryResponse(BaseModel):
    query: str
    matched_chunks: List[DocumentChunk]
    similarity_score: float

# In-memory vector store mock
vector_index: Dict[str, DocumentChunk] = {}

def extract_and_chunk_document(text: str, chunk_size: int = 250) -> List[DocumentChunk]:
    """Splits input document text into structured semantic chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk_text = " ".join(words[i:i + chunk_size])
        chunks.append(DocumentChunk(
            chunk_id=f"chk-{len(chunks) + 1}",
            content=chunk_text,
            metadata={"word_count": len(chunk_text.split()), "offset": i}
        ))
    return chunks

@app.post("/api/documents/index")
def index_document(document_text: str):
    """REST API Architecture: Index new document chunks into memory."""
    if not document_text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty.")
    chunks = extract_and_chunk_document(document_text)
    for c in chunks:
        vector_index[c.chunk_id] = c
    return {"status": "indexed", "total_chunks": len(chunks)}

@app.post("/api/rag/query", response_model=QueryResponse)
def query_rag(req: QueryRequest):
    """RAG Document Retrieval: Finds relevant chunks matching query tokens."""
    q_tokens = set(req.query.lower().split())
    scored = []
    for chunk in vector_index.values():
        c_tokens = set(chunk.content.lower().split())
        overlap = len(q_tokens.intersection(c_tokens))
        if overlap > 0:
            scored.append((chunk, float(overlap) / max(len(q_tokens), 1)))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_results = [item[0] for item in scored[:req.top_k]]
    top_score = scored[0][1] if scored else 0.0

    return QueryResponse(
        query=req.query,
        matched_chunks=top_results,
        similarity_score=top_score
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
