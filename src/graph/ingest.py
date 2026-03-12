"""
단건 문서 인제스트 파이프라인.

어드민 UI에서 문서를 첨부/제출하면 이 모듈이 호출되어
해당 문서만 청킹 → 임베딩 → Pinecone upsert를 수행한다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graph.embedding_index import (
    chunk_text,
    delete_doc_vectors,
    embed_documents,
    make_doc_id,
    upsert_vectors,
)


def ingest_document(
    title: str,
    content: str,
    source: str,
    url: str,
    embed_model,
    pinecone_index,
    namespace: str = "",
) -> dict:
    """단일 문서를 청킹 → 임베딩 → Pinecone에 업로드한다.

    기존에 같은 URL의 문서가 있으면 삭제 후 재업로드.

    Returns:
        {"chunks": 청크 수, "deleted": 삭제된 기존 청크 수}
    """
    # 1) 기존 벡터 삭제 (같은 URL로 이미 등록된 경우)
    deleted = delete_doc_vectors(pinecone_index, url, namespace=namespace)

    # 2) 청킹
    full_text = f"{title}\n{content}" if title else content
    chunks = chunk_text(full_text, max_chars=1000, overlap=200)

    # 3) ID, 메타데이터 준비
    ids = [make_doc_id(url, i) for i in range(len(chunks))]
    metadata_list = [
        {
            "title": title[:200],
            "url": url,
            "source": source,
            "content_preview": chunk[:500],
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        for i, chunk in enumerate(chunks)
    ]

    # 4) 임베딩
    vectors = embed_documents(embed_model, chunks)

    # 5) Pinecone upsert
    upsert_vectors(pinecone_index, ids, vectors, metadata_list, namespace=namespace)

    return {"chunks": len(chunks), "deleted": deleted}


def delete_document(url: str, pinecone_index, namespace: str = "") -> int:
    """문서를 Pinecone에서 삭제한다. 삭제된 벡터 수를 반환."""
    return delete_doc_vectors(pinecone_index, url, namespace=namespace)
