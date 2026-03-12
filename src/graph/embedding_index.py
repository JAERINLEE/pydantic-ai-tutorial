"""
임베딩 생성 + Pinecone 벡터 인덱스 연동 모듈.

sentence-transformers로 로컬 임베딩을 생성하고,
Pinecone에 업로드/검색하는 함수를 제공한다.
"""

import hashlib
import re
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBED_DIM = 384
INDEX_NAME = "eluo-faq"


def get_embed_model() -> SentenceTransformer:
    """임베딩 모델을 로드한다 (최초 호출 시 ~140MB 다운로드)."""
    return SentenceTransformer(EMBED_MODEL_NAME)


def embed_documents(model: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    """문서 리스트를 임베딩 벡터 리스트로 변환한다."""
    vectors = model.encode(texts, show_progress_bar=True, batch_size=32)
    return vectors.tolist()


def embed_query(model: SentenceTransformer, query: str) -> list[float]:
    """단일 쿼리를 임베딩 벡터로 변환한다."""
    return model.encode(query).tolist()


def init_pinecone(api_key: str) -> Pinecone:
    """Pinecone 클라이언트를 초기화한다."""
    return Pinecone(api_key=api_key)


def get_or_create_index(pc: Pinecone, index_name: str = INDEX_NAME):
    """Pinecone 인덱스를 가져오거나 새로 생성한다."""
    existing = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print(f"인덱스 '{index_name}' 생성 완료")
    else:
        print(f"인덱스 '{index_name}' 이미 존재")
    return pc.Index(index_name)


def make_doc_id(url: str, chunk_idx: int = 0) -> str:
    """URL 기반 문서 ID + 청크 인덱스. prefix 기반 list/delete 가능한 형식."""
    doc_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"{doc_hash}#chunk{chunk_idx}"


def doc_id_prefix(url: str) -> str:
    """URL로부터 문서 ID prefix를 생성한다 (list/delete용)."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def delete_doc_vectors(index, url: str, namespace: str = "") -> int:
    """특정 문서의 모든 청크 벡터를 Pinecone에서 삭제한다."""
    prefix = doc_id_prefix(url)
    ids_to_delete = []
    for id_list in index.list(prefix=prefix, namespace=namespace):
        ids_to_delete.extend(id_list)
    if ids_to_delete:
        index.delete(ids=ids_to_delete, namespace=namespace)
    return len(ids_to_delete)


def list_all_doc_ids(index, namespace: str = "") -> list[dict]:
    """Pinecone에서 모든 벡터를 조회하여 고유 문서 목록을 반환한다."""
    all_ids = []
    for id_list in index.list(namespace=namespace):
        all_ids.extend(id_list)

    if not all_ids:
        return []

    # chunk0만 fetch해서 메타데이터 추출 → 문서 목록 구성
    chunk0_ids = [vid for vid in all_ids if vid.endswith("#chunk0")]
    docs = []
    # fetch는 한 번에 최대 100개
    for i in range(0, len(chunk0_ids), 100):
        batch = chunk0_ids[i:i + 100]
        fetched = index.fetch(ids=batch, namespace=namespace)
        for vid, vec_data in fetched.vectors.items():
            meta = vec_data.metadata or {}
            prefix = vid.split("#")[0]
            chunk_count = sum(1 for aid in all_ids if aid.startswith(prefix + "#"))
            docs.append({
                "doc_prefix": prefix,
                "title": meta.get("title", ""),
                "url": meta.get("url", ""),
                "source": meta.get("source", ""),
                "chunk_count": chunk_count,
            })

    return sorted(docs, key=lambda d: d["title"])


def split_sentences(text: str) -> list[str]:
    """한국어 문장 경계를 인식하여 문장 단위로 분리한다."""
    # 한국어 종결어미(다/요/죠) + 마침표, 느낌표, 물음표, 빈 줄, 불릿 리스트 앞 줄바꿈
    pattern = r'(?<=[다요죠]\.)\s+|(?<=[.!?])\s+|(?<=\n)\n+|(?=\n[-•·▶►●○])'
    raw = re.split(pattern, text.strip())

    sentences: list[str] = []
    for piece in raw:
        piece = piece.strip()
        if not piece:
            continue
        # 20자 미만의 짧은 조각은 이전 문장에 병합
        if len(piece) < 20 and sentences:
            sentences[-1] = sentences[-1] + " " + piece
        else:
            sentences.append(piece)
    return sentences


def chunk_text(text: str, max_chars: int = 1000, overlap: int = 200) -> list[str]:
    """문장 단위로 청킹한다. 한국어 문장 경계를 인식하여 문장이 잘리지 않도록 한다."""
    if len(text) <= max_chars:
        return [text]

    sentences = split_sentences(text)
    if not sentences:
        return [text]

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_len = 0

    for sent in sentences:
        # 단일 문장이 max_chars 초과 시 문자 분할로 폴백
        if len(sent) > max_chars:
            # 현재까지 모은 것이 있으면 먼저 저장
            if current_sentences:
                chunks.append(" ".join(current_sentences))
                current_sentences = []
                current_len = 0
            # 긴 문장을 문자 기준으로 분할
            start = 0
            while start < len(sent):
                chunks.append(sent[start:start + max_chars])
                start += max_chars - overlap
            continue

        # 문장 추가 시 max_chars 초과하면 새 청크 시작
        added_len = len(sent) + (1 if current_sentences else 0)
        if current_len + added_len > max_chars and current_sentences:
            chunks.append(" ".join(current_sentences))
            # overlap: 이전 청크의 마지막 문장들을 예산 내에서 이월
            overlap_sentences: list[str] = []
            overlap_len = 0
            for prev_sent in reversed(current_sentences):
                if overlap_len + len(prev_sent) + 1 > overlap:
                    break
                overlap_sentences.insert(0, prev_sent)
                overlap_len += len(prev_sent) + 1
            current_sentences = overlap_sentences
            current_len = sum(len(s) for s in current_sentences) + max(0, len(current_sentences) - 1)

        current_sentences.append(sent)
        current_len += len(sent) + (1 if len(current_sentences) > 1 else 0)

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks


def upsert_vectors(
    index,
    ids: list[str],
    vectors: list[list[float]],
    metadata_list: list[dict],
    namespace: str = "",
    batch_size: int = 100,
) -> int:
    """벡터 + 메타데이터를 Pinecone에 업로드한다."""
    total = 0
    for i in range(0, len(ids), batch_size):
        batch = list(zip(
            ids[i:i + batch_size],
            vectors[i:i + batch_size],
            metadata_list[i:i + batch_size],
        ))
        index.upsert(vectors=batch, namespace=namespace)
        total += len(batch)
        print(f"  업로드: {total}/{len(ids)}")
    return total


def search_pinecone(
    index,
    query_vector: list[float],
    top_k: int = 5,
    namespace: str = "",
) -> list[dict]:
    """Pinecone에서 유사 벡터를 검색한다."""
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
    )
    return [
        {
            "id": match.id,
            "score": match.score,
            **match.metadata,
        }
        for match in results.matches
    ]
