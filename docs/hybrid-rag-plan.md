# Hybrid RAG 구현 플랜

## 1. 개요

### 1.1 현재 상태

| 항목 | 현재 |
|------|------|
| **검색** | TF-IDF 키워드 기반 (scikit-learn `TfidfVectorizer` + `cosine_similarity`) |
| **LLM** | Google Gemini 2.5 Flash (`GoogleModel`) |
| **데이터** | 3개 JSON 파일 (~800개 문서) |
| **UI** | Streamlit 채팅 인터페이스 + 레퍼런스 패널 |

**데이터 소스:**

- `data/faq_lineworks.json` — LINE WORKS FAQ (~700개)
- `data/board_lineworks.json` — 사내 게시판 (~15-20개, 첨부파일 포함)
- `data/eluocnc.json` — 회사 홈페이지 (~50개)

### 1.2 목표

TF-IDF를 **Hybrid RAG (GraphRAG + VectorRAG)**로 교체하여 검색 품질을 향상시키고, LLM을 Gemini에서 **Claude**로 전환합니다.

### 1.3 사용 리소스

| 리소스 | 용도 |
|--------|------|
| Claude API 키 | LLM (대화, 엔티티 추출) |
| Pinecone API 키 | 벡터 DB (임베딩 저장/검색) |
| sentence-transformers (로컬) | 임베딩 생성 (무료, 한국어 지원) |
| NetworkX (로컬) | 지식그래프 저장/탐색 (무료) |

---

## 2. 아키텍처

### 2.1 현재 데이터 파이프라인

```
JSON 파일 → FAQDatabase.load() → TF-IDF 벡터화 → cosine_similarity 검색
```

### 2.2 새로운 데이터 파이프라인

```
┌─────────────────────────────────────────────────────────┐
│                    빌드 단계 (1회)                        │
│                                                         │
│  JSON 파일                                               │
│    ├─→ sentence-transformers 임베딩 → Pinecone 업로드     │
│    └─→ Claude 엔티티/관계 추출 → NetworkX 그래프 → JSON    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    런타임 (매 쿼리)                       │
│                                                         │
│  사용자 질문                                              │
│    ├─→ 벡터 검색: 임베딩 → Pinecone 유사도 검색            │
│    ├─→ 그래프 검색: 엔티티 매칭 → 그래프 탐색              │
│    └─→ 하이브리드 합산 → 상위 결과 → Claude 답변 생성      │
└─────────────────────────────────────────────────────────┘
```

### 2.3 어드민 페이지 확장 시나리오 (향후)

```
관리자가 새 자료 업로드 → "제출" 클릭
  ├─→ sentence-transformers로 즉시 임베딩 (로컬, 비용 0원)
  ├─→ Pinecone에 upsert (기존 인덱스에 추가)
  └─→ Claude로 엔티티 추출 → 그래프에 노드/엣지 추가
```

---

## 3. 핵심 개념 설명

### 3.1 임베딩 (Embedding)이란?

텍스트를 **숫자 벡터(숫자 배열)**로 변환하는 기술입니다.

```
"비밀번호 변경" → [0.12, -0.45, 0.78, ...] (384차원)
"패스워드 수정" → [0.11, -0.44, 0.77, ...] (유사한 벡터)
"오늘 날씨"    → [0.89, 0.23, -0.56, ...] (다른 벡터)
```

의미가 비슷한 문장은 비슷한 벡터가 되므로, **동의어/유사 표현도 검색 가능**합니다.

| 방식 | "비밀번호" 검색 시 |
|------|-------------------|
| TF-IDF | "비밀번호"라는 단어가 있는 문서만 찾음 |
| 임베딩 | "패스워드", "로그인 정보", "계정 보안" 등도 찾음 |

### 3.2 VectorRAG (Pinecone)

문서를 임베딩 벡터로 변환하여 Pinecone에 저장하고, 질문도 벡터로 변환하여 가장 유사한 문서를 찾는 방식입니다.

- **장점**: 의미 기반 검색, 구현 단순
- **한계**: 문서 간 관계를 모름 (각 문서를 독립적으로 취급)

### 3.3 GraphRAG (NetworkX)

문서에서 **엔티티(개체)**와 **관계**를 추출하여 지식그래프를 구축합니다.

```
예시:
문서: "LINE WORKS 드라이브에서 파일을 공유하려면 관리자 권한이 필요합니다"

엔티티:
  - LINE WORKS (제품)
  - 드라이브 (기능)
  - 파일 공유 (기능)
  - 관리자 권한 (권한)

관계:
  - LINE WORKS ──HAS_FEATURE──→ 드라이브
  - 드라이브 ──HAS_FEATURE──→ 파일 공유
  - 파일 공유 ──REQUIRES──→ 관리자 권한
```

- **장점**: 문서 간 연결 관계 파악, "관련 기능" 탐색 가능
- **한계**: 구축에 LLM 호출 필요 (비용/시간)

### 3.4 Hybrid = VectorRAG + GraphRAG

두 검색 결과를 합산하여 최종 결과를 반환합니다.

| 질문 유형 | 예시 | 강한 검색 방식 |
|-----------|------|---------------|
| 구체적 질문 | "비밀번호 변경 방법" | 벡터 검색 |
| 탐색적 질문 | "LINE WORKS 메일 관련 기능 알려줘" | 그래프 탐색 |
| 하이브리드 | 두 결과를 합침 | 어떤 유형에도 좋은 결과 |

---

## 4. 구현 단계

### 4.1 환경 설정 및 의존성 추가

**수정 파일**: `requirements.txt`

추가할 패키지:

```
networkx>=3.2                    # 지식그래프
sentence-transformers>=2.2.0     # 임베딩 (로컬)
pinecone-client>=3.0.0           # 벡터 DB
pydantic-ai[anthropic]           # Claude 연동
```

**수정 파일**: `.env.example`, `.env`

```env
# 추가
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=pcsk_...

# 제거 (선택)
# GEMINI_API_KEY=...
```

---

### 4.2 LLM 교체 (Gemini → Claude)

**수정 파일**: `src/agent/faq_agent.py`

| 변경 전 | 변경 후 |
|---------|---------|
| `from pydantic_ai.models.google import GoogleModel` | `from pydantic_ai.models.anthropic import AnthropicModel` |
| `GoogleModel("gemini-2.5-flash")` | `AnthropicModel("claude-sonnet-4-20250514")` |
| `GEMINI_API_KEY` 환경변수 | `ANTHROPIC_API_KEY` 환경변수 |

> 시스템 프롬프트(한국어)는 그대로 유지

---

### 4.3 임베딩 모듈 구현

**새 파일**: `src/graph/__init__.py`, `src/graph/embedding_index.py`

| 함수 | 기능 |
|------|------|
| `embed_documents(items)` | 문서 리스트를 임베딩 벡터 리스트로 변환 |
| `embed_query(query)` | 단일 쿼리를 임베딩 벡터로 변환 |
| `init_pinecone(api_key, index_name)` | Pinecone 인덱스 초기화 |
| `upsert_vectors(index, vectors, metadata)` | 벡터 + 메타데이터 Pinecone에 업로드 |
| `search_pinecone(index, query_vector, top_k)` | Pinecone에서 유사 벡터 검색 |

**임베딩 모델**: `paraphrase-multilingual-MiniLM-L12-v2`
- 한국어 + 영어 + 50개 언어 지원
- 384차원 벡터
- ~140MB 모델 크기 (최초 1회 다운로드)

**Pinecone 메타데이터 구조:**

```json
{
  "title": "비밀번호 변경 방법",
  "url": "https://help.worksmobile.com/...",
  "source": "faq",
  "content_preview": "비밀번호를 변경하려면... (처음 500자)"
}
```

---

### 4.4 지식그래프 구축 모듈

**새 파일**: `src/graph/graph_builder.py`

#### 4.4.1 Pydantic 스키마 정의

```python
class Entity(BaseModel):
    name: str           # "LINE WORKS", "드라이브", "비밀번호"
    entity_type: str    # PRODUCT, FEATURE, PROCEDURE, POLICY, COMPANY, PROJECT
    description: str    # 한국어 설명

class Relationship(BaseModel):
    source: str         # 엔티티 이름
    target: str         # 엔티티 이름
    relation: str       # HAS_FEATURE, SOLVES, BELONGS_TO, REQUIRES
    description: str    # 관계 설명

class DocumentGraphExtraction(BaseModel):
    entities: list[Entity]
    relationships: list[Relationship]
```

#### 4.4.2 엔티티/관계 추출

- Claude API로 각 문서에서 엔티티와 관계를 추출
- PydanticAI의 `output_type=DocumentGraphExtraction`으로 구조화된 출력
- 한국어 프롬프트 + few-shot 예시 포함
- 한국어 조사 제거 지시: "엔티티 이름에서 조사(을, 를, 이, 가, 의 등)를 제거하세요"

#### 4.4.3 엔티티 중복 해결

- 동일 엔티티 병합: "라인웍스" = "LINE WORKS" = "NAVER WORKS"
- 방법: 엔티티 이름을 임베딩으로 변환 → 유사도 0.85 이상이면 병합
- 대표 이름 선택 (가장 빈번한 이름 사용)

#### 4.4.4 NetworkX 그래프 구축

**노드 유형:**

| 유형 | 속성 |
|------|------|
| ENTITY | type, description, document_ids |
| DOCUMENT | title, url, source |

**엣지 유형:**

| 연결 | 유형 |
|------|------|
| 엔티티 ↔ 엔티티 | 관계 (relation, description) |
| 문서 → 엔티티 | MENTIONS |

**직렬화**: `networkx.node_link_data()` → `data/knowledge_graph.json`

---

### 4.5 빌드 스크립트

**새 파일**: `src/graph/build_index.py`

```bash
python src/graph/build_index.py
```

**처리 순서:**

1. JSON 데이터 파일 3개 로드
2. 문서 임베딩 생성 (sentence-transformers)
3. Pinecone 인덱스 생성 및 벡터 업로드
4. Claude로 엔티티/관계 추출 (문서별 API 호출)
5. 엔티티 중복 해결
6. NetworkX 그래프 구축 및 JSON 저장

**예상 소요 시간:**

| 단계 | 시간 |
|------|------|
| 임베딩 생성 | ~30초 (800개 문서, 로컬) |
| Claude 엔티티 추출 | ~5-10분 (문서당 API 호출 1회) |
| Pinecone 업로드 | ~1분 |
| **총** | **~10분 (최초 1회)** |

---

### 4.6 Hybrid 검색 데이터베이스 클래스

**새 파일**: `src/agent/graph_database.py`

기존 `FAQDatabase`를 대체하는 `GraphRAGDatabase`:

```python
@dataclass
class GraphRAGDatabase:
    items: list[dict]                    # 원본 문서 데이터
    graph: nx.Graph                      # 지식그래프
    pinecone_index: Any                  # Pinecone 인덱스
    embed_model: SentenceTransformer     # 임베딩 모델
```

**주요 메서드:**

| 메서드 | 기능 |
|--------|------|
| `load()` | JSON 데이터 + knowledge_graph.json + Pinecone 연결 + 모델 로드 |
| `vector_search(query, top_k)` | 쿼리 임베딩 → Pinecone cosine similarity 검색 |
| `graph_search(query, top_k)` | 쿼리 임베딩 → 엔티티 매칭 → 1-2홉 그래프 탐색 |
| `hybrid_search(query, top_k)` | vector + graph 결과를 Reciprocal Rank Fusion으로 합산 |

---

### 4.7 에이전트 도구 업데이트

**수정 파일**: `src/agent/faq_agent.py`

**변경 사항:**

- `deps_type`을 `GraphRAGDatabase`로 변경
- `search_faq` 도구: `db.hybrid_search(query)` 호출

**검색 결과 반환 형식:**

```
[1] [FAQ] 비밀번호 변경 방법
내용: ...
관련 개념: LINE WORKS → HAS_FEATURE → 비밀번호 관리
URL: ...
유사도: 0.856
```

**새 도구 추가:**

| 도구 | 용도 |
|------|------|
| `explore_topic(topic)` | 그래프에서 특정 토픽의 연결된 엔티티와 문서를 탐색 |

> 기존 도구 유지: `list_titles`, `get_item_detail`, `get_data_stats`

**시스템 프롬프트 업데이트:**

- `search_faq`: 구체적 질문 → 하이브리드 검색
- `explore_topic`: 탐색적 질문 → 그래프 탐색
- 에이전트가 질문 유형에 따라 도구를 선택하도록 안내

---

### 4.8 Streamlit UI 업데이트

**수정 파일**: `src/app.py`

| 변경 항목 | 내용 |
|-----------|------|
| Import | `FAQDatabase` → `GraphRAGDatabase` |
| 캐시 함수 | `get_faq_db()` → `get_graph_db()` |
| 사이드바 | 엔티티 수, 관계 수 표시 (예: "Knowledge Graph: 150 엔티티, 300 관계") |
| 레퍼런스 패널 | 기존 출처 뱃지 + 유사도 + URL에 "관련 개념" 섹션 추가 |

> 나머지 UI (채팅, 스타일링, 에러 처리)는 그대로 유지

---

## 5. 파일 구조 변경

```
src/
  agent/
    faq_agent.py          # [수정] Claude 모델, GraphRAGDatabase deps, 도구 업데이트
    graph_database.py     # [새로 생성] GraphRAGDatabase 클래스
  graph/
    __init__.py           # [새로 생성]
    graph_builder.py      # [새로 생성] 엔티티/관계 추출, 그래프 구축
    embedding_index.py    # [새로 생성] 임베딩 + Pinecone 연동
    build_index.py        # [새로 생성] CLI 빌드 스크립트
  app.py                  # [수정] GraphRAGDatabase 연동, UI 확장
data/
  faq_lineworks.json      # [기존] 변경 없음
  board_lineworks.json    # [기존] 변경 없음
  eluocnc.json            # [기존] 변경 없음
  knowledge_graph.json    # [새로 생성] NetworkX 직렬화
requirements.txt          # [수정] 패키지 추가
.env.example              # [수정] 키 추가
```

---

## 6. 실행 명령어

```bash
# 의존성 설치
pip install -r requirements.txt

# sentence-transformers 모델 최초 다운로드 (자동, ~140MB)
# 첫 실행 시 자동으로 다운로드됨

# 인덱스 빌드 (최초 1회, 데이터 변경 시 재실행)
python src/graph/build_index.py

# 챗봇 실행
streamlit run src/app.py
```

---

## 7. 검증 방법

| 테스트 | 입력 | 기대 결과 |
|--------|------|-----------|
| 벡터 검색 | "비밀번호를 잊어버렸어요" | FAQ에서 비밀번호 관련 문서 찾기 (의미 기반) |
| 그래프 탐색 | "LINE WORKS 메일 관련 기능" | 그래프에서 메일 엔티티 → 연결된 기능 목록 |
| 하이브리드 | "경조금 규정" | 게시판 문서에서 정확한 답변 |
| 동의어 검색 | "패스워드 변경" | "비밀번호 변경" 문서도 검색됨 (TF-IDF 대비 개선) |
| UI 확인 | 아무 질문 | 레퍼런스 패널에 출처 + 관련 개념 표시 |

---

## 8. 주의사항 및 한계

- **Claude API 비용**: 엔티티 추출 시 문서당 1회 API 호출. 800개 문서 기준 최초 빌드 시 약 $1-2 예상
- **sentence-transformers 메모리**: 모델이 ~140MB RAM 차지. 서버에서 상시 로드 필요
- **Pinecone 무료 티어**: Starter 플랜에서 1개 인덱스, 100K 벡터까지 무료. 현재 ~800개 문서로 충분
- **한국어 엔티티 추출**: 조사(을/를/이/가) 처리, 한영 혼용 엔티티 병합 주의
- **네트워크 의존성**: Pinecone 검색은 인터넷 연결 필요. TF-IDF 대비 오프라인 동작 불가
