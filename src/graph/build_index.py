"""
Pinecone 벡터 인덱스 + 지식그래프 빌드 스크립트.

board_lineworks.json + eluocnc.json 데이터를
임베딩 → 청킹 → Pinecone 업로드 + 엔티티 추출 → 지식그래프 구축.

Usage:
    python src/graph/build_index.py              # 전체 빌드
    python src/graph/build_index.py --pinecone   # Pinecone만
    python src/graph/build_index.py --graph      # 지식그래프만
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# src를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graph.embedding_index import (
    chunk_text,
    embed_documents,
    get_embed_model,
    get_or_create_index,
    init_pinecone,
    make_doc_id,
    upsert_vectors,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MIN_CONTENT_LEN = 50


def load_json_data() -> list[dict]:
    """board + eluocnc JSON 데이터를 로드한다."""
    files = {
        "board": DATA_DIR / "board_lineworks.json",
        "eluocnc": DATA_DIR / "eluocnc.json",
    }

    items = []
    for default_source, path in files.items():
        if not path.exists():
            print(f"[warn] 파일 없음 (건너뜀): {path}")
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            item.setdefault("source", default_source)
        items.extend(data)
        print(f"  {path.name}: {len(data)}건 로드")

    return items


def deduplicate(items: list[dict]) -> list[dict]:
    """중복 URL 제거 + 짧은 콘텐츠 필터링."""
    seen_urls: set[str] = set()
    result = []
    for item in items:
        content = item.get("content", "").strip()
        if len(content) < MIN_CONTENT_LEN:
            continue
        url = item.get("url", "")
        base_url = url.split("?")[0] if url else ""
        if base_url and base_url in seen_urls:
            continue
        if base_url:
            seen_urls.add(base_url)
        result.append(item)
    return result


def prepare_records(items: list[dict]) -> tuple[list[str], list[str], list[dict]]:
    """문서를 청킹하고 업로드용 (ids, texts, metadata) 튜플을 준비한다."""
    ids = []
    texts = []
    metadata_list = []

    for item in items:
        title = item.get("title", "")
        content = item.get("content", "")
        url = item.get("url", "")
        source = item.get("source", "")

        # 제목 + 본문을 합쳐서 청킹
        full_text = f"{title}\n{content}" if title else content
        chunks = chunk_text(full_text, max_chars=1000, overlap=200)

        for chunk_idx, chunk in enumerate(chunks):
            doc_id = make_doc_id(url or title, chunk_idx)
            ids.append(doc_id)
            texts.append(chunk)
            metadata_list.append({
                "title": title[:200],
                "url": url,
                "source": source,
                "content_preview": chunk[:500],
                "chunk_index": chunk_idx,
                "total_chunks": len(chunks),
            })

    return ids, texts, metadata_list


def build_pinecone(items: list[dict], embed_model):
    """Pinecone 벡터 인덱스를 빌드한다."""
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("PINECONE_API_KEY 환경변수를 설정해주세요.")
        sys.exit(1)

    # 청킹 & 레코드 준비
    print("\n[Pinecone] 문서 청킹...")
    ids, texts, metadata_list = prepare_records(items)
    print(f"  총 {len(texts)}개 청크 생성")

    # 임베딩 생성
    print("\n[Pinecone] 임베딩 생성...")
    vectors = embed_documents(embed_model, texts)
    print(f"  {len(vectors)}개 벡터 생성 완료 (차원: {len(vectors[0])})")

    # Pinecone 업로드
    print("\n[Pinecone] 업로드...")
    pc = init_pinecone(api_key)
    index = get_or_create_index(pc)
    count = upsert_vectors(index, ids, vectors, metadata_list)
    print(f"  {count}개 벡터 업로드 완료")

    stats = index.describe_index_stats()
    print(f"  Pinecone 총 벡터 수: {stats.total_vector_count}")


def build_graph(items: list[dict], embed_model):
    """지식그래프를 빌드한다."""
    from graph.graph_builder import build_knowledge_graph

    asyncio.run(build_knowledge_graph(items, embed_model))


def main():
    args = set(sys.argv[1:])
    do_pinecone = "--pinecone" in args or not args
    do_graph = "--graph" in args or not args

    print("=" * 50)
    print("Hybrid RAG 인덱스 빌드")
    if do_pinecone:
        print("  - Pinecone 벡터 인덱스")
    if do_graph:
        print("  - 지식그래프 (NetworkX)")
    print("=" * 50)

    # 데이터 로드
    print("\n[데이터] 로드...")
    items = load_json_data()
    items = deduplicate(items)
    print(f"  총 {len(items)}건 (중복/빈 항목 제거 후)")

    # 임베딩 모델 로드 (공유)
    print("\n[모델] 임베딩 모델 로드...")
    embed_model = get_embed_model()

    if do_pinecone:
        build_pinecone(items, embed_model)

    if do_graph:
        build_graph(items, embed_model)

    print("\n" + "=" * 50)
    print("빌드 완료!")
    print("=" * 50)


if __name__ == "__main__":
    main()
