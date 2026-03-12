"""
지식그래프 구축 모듈.

Claude API로 문서에서 엔티티/관계를 추출하고,
중복 엔티티를 병합한 뒤 NetworkX 그래프를 구축한다.
"""

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

import networkx as nx
import numpy as np
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
GRAPH_PATH = DATA_DIR / "knowledge_graph.json"
EXTRACTION_CACHE_DIR = DATA_DIR / "extraction_cache"
ENTITY_EMBEDDINGS_PATH = DATA_DIR / "entity_embeddings.npz"


# ── Pydantic 스키마 ──


class Entity(BaseModel):
    name: str  # "LINE WORKS", "드라이브", "비밀번호"
    entity_type: str  # PRODUCT, FEATURE, PROCEDURE, POLICY, COMPANY, PROJECT
    description: str  # 한국어 설명


class Relationship(BaseModel):
    source: str  # 엔티티 이름
    target: str  # 엔티티 이름
    relation: str  # HAS_FEATURE, SOLVES, BELONGS_TO, REQUIRES 등
    description: str  # 관계 설명


class DocumentGraphExtraction(BaseModel):
    entities: list[Entity]
    relationships: list[Relationship]


# ── 엔티티/관계 추출 ──

EXTRACTION_PROMPT = """\
아래 문서에서 엔티티(개체)와 관계를 추출하세요.

## 규칙
- 엔티티 이름에서 한국어 조사(을, 를, 이, 가, 의, 에서, 으로 등)를 제거하세요.
- entity_type은 다음 중 하나: PRODUCT, FEATURE, PROCEDURE, POLICY, COMPANY, PROJECT, PERSON, DEPARTMENT
- relation은 다음 중 하나: HAS_FEATURE, SOLVES, BELONGS_TO, REQUIRES, RELATED_TO, PROVIDES, MANAGES
- 핵심적인 엔티티와 관계만 추출하세요 (문서당 3-8개 엔티티).
- description은 한국어로 간결하게 작성하세요.

## 문서
제목: {title}
출처: {source}

{content}
"""


async def extract_from_document(
    agent, item: dict, max_retries: int = 3,
) -> DocumentGraphExtraction | None:
    """단일 문서에서 엔티티와 관계를 추출한다. 429 에러 시 재시도."""
    title = item.get("title", "")
    content = item.get("content", "")
    source_labels = {"faq": "FAQ", "board": "사내 게시판", "eluocnc": "회사 홈페이지"}
    source = source_labels.get(item.get("source", ""), item.get("source", ""))

    # 본문이 너무 길면 앞부분만 사용
    if len(content) > 3000:
        content = content[:3000] + "\n...(이하 생략)"

    prompt = EXTRACTION_PROMPT.format(title=title, source=source, content=content)

    for attempt in range(max_retries):
        try:
            result = await agent.run(prompt)
            return result.output
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = 15 * (attempt + 1)
                print(f"  [rate limit] '{title[:30]}' — {wait}초 대기 후 재시도 ({attempt+1}/{max_retries})")
                await asyncio.sleep(wait)
            else:
                print(f"  [error] '{title[:40]}': {e}")
                return None
    print(f"  [fail] '{title[:40]}': 최대 재시도 초과")
    return None


def _cache_key(item: dict) -> str:
    """문서 URL + 본문 앞부분으로 캐시 키를 생성한다. 내용 변경 시 자동 재추출."""
    url = item.get("url", item.get("title", ""))
    content_prefix = item.get("content", "")[:500]
    raw = f"{url}|{content_prefix}"
    return hashlib.md5(raw.encode()).hexdigest()


def _load_cached_extraction(item: dict) -> DocumentGraphExtraction | None:
    """캐시된 추출 결과를 로드한다."""
    cache_file = EXTRACTION_CACHE_DIR / f"{_cache_key(item)}.json"
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)
        return DocumentGraphExtraction.model_validate(data)
    except Exception:
        return None


def _save_extraction_cache(item: dict, extraction: DocumentGraphExtraction):
    """추출 결과를 캐시에 저장한다."""
    EXTRACTION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = EXTRACTION_CACHE_DIR / f"{_cache_key(item)}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(extraction.model_dump_json(indent=2))


async def extract_all(items: list[dict]) -> list[tuple[dict, DocumentGraphExtraction]]:
    """모든 문서에서 엔티티/관계를 추출한다. 캐시 히트 시 재사용, 미스 시 동시 추출."""
    from pydantic_ai import Agent
    from pydantic_ai.models.anthropic import AnthropicModel

    # 1차 패스: 캐시 확인
    cached_results: list[tuple[dict, DocumentGraphExtraction]] = []
    items_to_extract: list[dict] = []

    for item in items:
        cached = _load_cached_extraction(item)
        if cached and (cached.entities or cached.relationships):
            cached_results.append((item, cached))
        else:
            items_to_extract.append(item)

    print(f"  캐시 {len(cached_results)}건, 신규 추출 {len(items_to_extract)}건")

    if not items_to_extract:
        return cached_results

    # 2차 패스: 동시 추출 (Semaphore로 동시성 제어)
    model = AnthropicModel("claude-haiku-4-5-20251001")
    agent = Agent(
        model=model,
        output_type=DocumentGraphExtraction,
        system_prompt="문서에서 엔티티와 관계를 추출하는 전문가입니다. JSON 형식으로 정확히 응답하세요.",
    )

    semaphore = asyncio.Semaphore(4)
    new_extractions: list[tuple[dict, DocumentGraphExtraction]] = []
    lock = asyncio.Lock()

    async def extract_one(idx: int, item: dict):
        async with semaphore:
            print(f"  [{idx+1}/{len(items_to_extract)}] {item.get('title', '')[:50]}...", end=" ", flush=True)
            result = await extract_from_document(agent, item)
            if result and (result.entities or result.relationships):
                _save_extraction_cache(item, result)
                async with lock:
                    new_extractions.append((item, result))
                print(f"✓ 엔티티 {len(result.entities)}개, 관계 {len(result.relationships)}개")
            else:
                print("✗")

    await asyncio.gather(*(extract_one(i, item) for i, item in enumerate(items_to_extract)))

    return cached_results + new_extractions


# ── 엔티티 중복 해결 ──


def deduplicate_entities(
    extractions: list[tuple[dict, DocumentGraphExtraction]],
    embed_model=None,
    threshold: float = 0.85,
) -> dict[str, str]:
    """유사한 엔티티 이름을 병합하고, 이름 → 대표 이름 매핑을 반환한다."""
    from collections import Counter

    # 모든 엔티티 이름 수집 (빈도 포함)
    name_counter: Counter = Counter()
    for _, extraction in extractions:
        for entity in extraction.entities:
            name_counter[entity.name.strip()] += 1

    names = list(name_counter.keys())
    if not names or embed_model is None:
        return {n: n for n in names}

    # 임베딩으로 유사도 계산
    from graph.embedding_index import embed_documents

    vectors = embed_documents(embed_model, names)

    import numpy as np

    vecs = np.array(vectors)
    # cosine similarity matrix
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = vecs / norms
    sim_matrix = normalized @ normalized.T

    # Union-Find로 유사 엔티티 그룹핑
    parent = list(range(len(names)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if sim_matrix[i][j] >= threshold:
                union(i, j)

    # 그룹별 대표 이름 선택 (가장 빈번한 이름)
    groups: dict[int, list[str]] = {}
    for i, name in enumerate(names):
        root = find(i)
        groups.setdefault(root, []).append(name)

    name_map: dict[str, str] = {}
    for group_names in groups.values():
        # 빈도 높은 이름을 대표로
        representative = max(group_names, key=lambda n: name_counter[n])
        for name in group_names:
            name_map[name] = representative

    merged_count = sum(1 for v in name_map.values() if v != v)  # 실제 병합 수
    unique_groups = len(set(name_map.values()))
    print(f"  엔티티 {len(names)}개 → {unique_groups}개 그룹으로 병합")

    return name_map


# ── NetworkX 그래프 구축 ──


def build_graph(
    items: list[dict],
    extractions: list[tuple[dict, DocumentGraphExtraction]],
    name_map: dict[str, str],
) -> nx.Graph:
    """엔티티/관계/문서로 NetworkX 그래프를 구축한다."""
    G = nx.Graph()

    # 엔티티 노드 추가
    entity_info: dict[str, dict] = {}  # 대표이름 → {type, description, doc_ids}
    for item, extraction in extractions:
        doc_id = item.get("url", item.get("title", ""))
        for entity in extraction.entities:
            canonical = name_map.get(entity.name.strip(), entity.name.strip())
            if canonical not in entity_info:
                entity_info[canonical] = {
                    "type": entity.entity_type,
                    "description": entity.description,
                    "document_ids": [],
                }
            entity_info[canonical]["document_ids"].append(doc_id)

    for name, info in entity_info.items():
        G.add_node(
            name,
            node_type="ENTITY",
            entity_type=info["type"],
            description=info["description"],
            document_ids=list(set(info["document_ids"])),
        )

    # 문서 노드 추가
    for item in items:
        doc_id = item.get("url", item.get("title", ""))
        G.add_node(
            doc_id,
            node_type="DOCUMENT",
            title=item.get("title", ""),
            url=item.get("url", ""),
            source=item.get("source", ""),
        )

    # 엔티티-엔티티 엣지
    for _, extraction in extractions:
        for rel in extraction.relationships:
            src = name_map.get(rel.source.strip(), rel.source.strip())
            tgt = name_map.get(rel.target.strip(), rel.target.strip())
            if src in G.nodes and tgt in G.nodes:
                G.add_edge(src, tgt, relation=rel.relation, description=rel.description)

    # 문서-엔티티 MENTIONS 엣지
    for item, extraction in extractions:
        doc_id = item.get("url", item.get("title", ""))
        for entity in extraction.entities:
            canonical = name_map.get(entity.name.strip(), entity.name.strip())
            if doc_id in G.nodes and canonical in G.nodes:
                G.add_edge(doc_id, canonical, relation="MENTIONS")

    return G


def save_graph(G: nx.Graph, path: Path = GRAPH_PATH):
    """그래프를 JSON으로 직렬화하여 저장한다."""
    data = nx.node_link_data(G)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  그래프 저장: {path}")


def load_graph(path: Path = GRAPH_PATH) -> nx.Graph:
    """저장된 JSON에서 그래프를 로드한다."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data)


# ── 메인 빌드 ──


def save_entity_embeddings(G: nx.Graph, embed_model, path: Path = ENTITY_EMBEDDINGS_PATH):
    """그래프의 ENTITY 노드 임베딩을 사전 계산하여 저장한다."""
    entity_nodes = [
        (n, d) for n, d in G.nodes(data=True)
        if d.get("node_type") == "ENTITY"
    ]
    if not entity_nodes or embed_model is None:
        return

    names = [n for n, _ in entity_nodes]
    entity_texts = [f"{n} {d.get('description', '')}" for n, d in entity_nodes]
    vectors = embed_model.encode(entity_texts, batch_size=64)
    vectors = np.array(vectors, dtype=np.float32)

    np.savez(path, names=np.array(names, dtype=object), vectors=vectors)
    print(f"  엔티티 임베딩 저장: {path} ({len(names)}개)")


async def build_knowledge_graph(items: list[dict], embed_model=None) -> nx.Graph:
    """전체 파이프라인: 추출 → 중복 해결 → 그래프 구축 → 저장."""

    print("\n[1/3] Claude로 엔티티/관계 추출...")
    extractions = await extract_all(items)
    total_entities = sum(len(e.entities) for _, e in extractions)
    total_rels = sum(len(e.relationships) for _, e in extractions)
    print(f"  {len(extractions)}건 문서에서 엔티티 {total_entities}개, 관계 {total_rels}개 추출")

    print("\n[2/3] 엔티티 중복 해결...")
    name_map = deduplicate_entities(extractions, embed_model)

    print("\n[3/3] NetworkX 그래프 구축...")
    G = build_graph(items, extractions, name_map)
    save_graph(G)

    entity_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "ENTITY"]
    doc_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "DOCUMENT"]
    print(f"  노드: 엔티티 {len(entity_nodes)}개 + 문서 {len(doc_nodes)}개")
    print(f"  엣지: {G.number_of_edges()}개")

    # 엔티티 임베딩 사전 계산
    if embed_model is not None:
        print("\n[4/4] 엔티티 임베딩 사전 계산...")
        save_entity_embeddings(G, embed_model)

    return G
