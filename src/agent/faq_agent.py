"""
LINE WORKS FAQ 에이전트.

하이브리드 RAG(벡터 검색 + 지식그래프) 기반 PydanticAI 에이전트로,
크롤링된 FAQ/게시판/홈페이지 데이터를 기반으로 사용자 질문에 답변한다.
"""

import os

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.anthropic import AnthropicModel

from agent.graph_database import GraphRAGDatabase

load_dotenv()

# Streamlit Cloud secrets → 환경변수 주입
try:
    import streamlit as st
    for key in ("ANTHROPIC_API_KEY",):
        if key in st.secrets and key not in os.environ:
            os.environ[key] = st.secrets[key]
except Exception:
    pass



def search_faq(ctx: RunContext[GraphRAGDatabase], query: str) -> str:
    """사용자 질문을 기반으로 FAQ 데이터베이스를 의미 검색합니다.
    유사도가 낮은 결과만 나오면 list_titles로 목록 조회를 시도하세요."""
    results = ctx.deps.search(query)
    if not results:
        return "관련 항목을 찾을 수 없습니다. list_titles로 목록 조회를 시도해보세요."

    # 유사도가 모두 낮으면 경고
    max_score = max(r.get("score", 0) for r in results)
    low_quality = max_score < 0.03

    source_labels = {"faq": "FAQ", "board": "게시판", "eluocnc": "회사 홈페이지"}
    output_parts = []

    if low_quality:
        output_parts.append(
            "⚠️ 검색 결과의 유사도가 낮습니다. "
            "질문이 넓은 범위를 다루는 경우 list_titles(source='board') 또는 "
            "list_titles(keyword='키워드')로 목록을 조회하는 것이 더 나을 수 있습니다.\n"
        )

    for i, r in enumerate(results, 1):
        source = source_labels.get(r.get("source", "faq"), r.get("source", ""))
        part = (
            f"[{i}] [{source}] {r['title']}\n"
            f"내용: {r['content']}\n"
        )
        related_entities = r.get("related_entities", [])
        if related_entities:
            if isinstance(related_entities[0], dict):
                entity_strs = [
                    f"{e['entity']} → {e.get('relation', 'RELATED_TO')}"
                    for e in related_entities
                ]
            else:
                entity_strs = related_entities
            part += f"관련 개념: {', '.join(entity_strs)}\n"
        part += (
            f"URL: {r['url']}\n"
            f"유사도: {r['score']:.3f}"
        )
        output_parts.append(part)
    return "\n\n".join(output_parts)


def list_titles(ctx: RunContext[GraphRAGDatabase], source: str = "", keyword: str = "") -> str:
    """등록된 항목들의 제목 목록을 반환합니다.

    Args:
        source: 필터할 출처. "faq", "board", "eluocnc", 또는 ""(전체).
        keyword: 제목에 포함된 키워드로 필터 (선택사항).
    """
    items = ctx.deps.items
    if source:
        items = [item for item in items if item.get("source") == source]
    if keyword:
        keyword_lower = keyword.lower()
        items = [item for item in items if keyword_lower in item.get("title", "").lower()
                 or keyword_lower in item.get("content", "")[:200].lower()]

    if not items:
        source_label = {"faq": "FAQ", "board": "게시판", "eluocnc": "회사 홈페이지"}.get(source, source)
        return f"{source_label} 데이터가 없습니다." if source else "등록된 데이터가 없습니다."

    source_labels = {"faq": "FAQ", "board": "게시판", "eluocnc": "회사 홈페이지"}
    lines = []
    for i, item in enumerate(items, 1):
        src = source_labels.get(item.get("source", ""), "")
        title = item.get("title", "(제목 없음)")
        # 내용 미리보기 (첫 80자)
        preview = item.get("content", "")[:80].replace("\n", " ").strip()
        line = f"{i}. [{src}] {title}"
        if preview:
            line += f" — {preview}..."
        lines.append(line)
    return "\n".join(lines)


def get_item_detail(ctx: RunContext[GraphRAGDatabase], title: str) -> str:
    """제목으로 특정 항목의 전체 내용을 반환합니다.

    Args:
        title: 조회할 항목의 제목 (부분 일치 검색).
    """
    title_lower = title.lower()
    for item in ctx.deps.items:
        if title_lower in item.get("title", "").lower():
            source_labels = {"faq": "FAQ", "board": "게시판", "eluocnc": "회사 홈페이지"}
            source = source_labels.get(item.get("source", ""), item.get("source", ""))
            parts = [
                f"[{source}] {item.get('title', '')}",
                f"URL: {item.get('url', '없음')}",
                f"\n{item.get('content', '내용 없음')}",
            ]
            attachments = item.get("attachments", [])
            if attachments:
                att_names = [a.get("filename", a.get("name", "")) for a in attachments]
                parts.append(f"\n첨부파일: {', '.join(att_names)}")
            return "\n".join(parts)
    return f"'{title}'과(와) 일치하는 항목을 찾을 수 없습니다."


def get_data_stats(ctx: RunContext[GraphRAGDatabase]) -> str:
    """데이터 소스별 항목 수 등 통계 정보를 반환합니다."""
    items = ctx.deps.items
    total = len(items)
    faq_count = sum(1 for item in items if item.get("source") == "faq")
    board_count = sum(1 for item in items if item.get("source") == "board")
    eluocnc_count = sum(1 for item in items if item.get("source") == "eluocnc")
    return (
        f"전체 항목 수: {total}\n"
        f"- FAQ: {faq_count}건\n"
        f"- 게시판: {board_count}건\n"
        f"- 회사 홈페이지: {eluocnc_count}건"
    )


def explore_topic(ctx: RunContext[GraphRAGDatabase], topic: str) -> str:
    """특정 토픽의 연결된 엔티티와 문서를 그래프에서 탐색합니다."""
    graph = ctx.deps.graph
    if graph is None or graph.number_of_nodes() == 0:
        return "지식그래프가 로드되지 않았습니다."

    topic_lower = topic.lower()

    # topic과 매칭되는 ENTITY 노드 찾기 (부분 문자열 매칭)
    matched_entities = []
    for node, data in graph.nodes(data=True):
        if data.get("node_type") != "ENTITY":
            continue
        if topic_lower in node.lower() or node.lower() in topic_lower:
            matched_entities.append((node, data))

    if not matched_entities:
        return f"'{topic}'과(와) 관련된 엔티티를 찾을 수 없습니다."

    output_parts = []
    for entity_name, entity_data in matched_entities:
        entity_type = entity_data.get("entity_type", "")
        description = entity_data.get("description", "")
        header = f"[{entity_type}] {entity_name}"
        if description:
            header += f" — {description}"
        output_parts.append(header)

        # 이웃 노드 (엔티티 + 문서) 목록
        neighbors = []
        for neighbor in graph.neighbors(entity_name):
            n_data = graph.nodes[neighbor]
            edge_data = graph.edges[entity_name, neighbor]
            relation = edge_data.get("relation", "RELATED_TO")
            n_type = n_data.get("node_type", "")

            if n_type == "ENTITY":
                n_entity_type = n_data.get("entity_type", "")
                neighbors.append(f"  → [{relation}] [{n_entity_type}] {neighbor}")
            elif n_type == "DOCUMENT":
                title = n_data.get("title", neighbor)
                source = n_data.get("source", "")
                source_labels = {"faq": "FAQ", "board": "게시판", "eluocnc": "회사 홈페이지"}
                source_label = source_labels.get(source, source)
                neighbors.append(f"  → [{relation}] [{source_label}] {title}")

        if neighbors:
            output_parts.append("  연결된 항목:")
            output_parts.extend(neighbors)
        output_parts.append("")  # 빈 줄 구분

    return "\n".join(output_parts)


model = AnthropicModel("claude-sonnet-4-20250514")

faq_agent = Agent(
    model=model,
    deps_type=GraphRAGDatabase,
    system_prompt=(
        "당신은 엘루오씨앤씨(디지털 마케팅 에이전시)의 사내 도우미입니다.\n"
        "LINE WORKS FAQ, 사내 규정/업무가이드(게시판), 회사 홈페이지 데이터를 기반으로 답변합니다.\n\n"
        "## 질문 의도 파악 및 도구 사용 전략\n"
        "사용자의 질문 의도를 먼저 파악한 후, 적합한 도구를 선택하세요:\n\n"
        "1. **넓은 탐색 질문 / 카테고리 질문** (예: '업무 가이드 알려줘', '프로젝트 알려줘', '회사 소개해줘', '규정 알려줘', '사내 가이드')\n"
        "   → 먼저 list_titles로 관련 항목 목록을 조회하세요\n"
        "     - 업무/규정/가이드 관련: list_titles(source='board')\n"
        "     - 회사/프로젝트 관련: list_titles(source='eluocnc')\n"
        "     - 불확실하면: list_titles(keyword='검색어')\n"
        "   → 여러 항목이 있으면 목록을 보여주고 '어떤 항목이 궁금하신가요?'라고 되물으세요\n"
        "   → 항목이 1-2개면 get_item_detail로 바로 상세 조회하여 답변\n\n"
        "2. **특정 주제 질문** (예: '비밀번호 변경 방법', '연차 신청은?', '경조금 규정')\n"
        "   → search_faq로 의미 기반 검색\n"
        "   → 결과가 명확하면 바로 답변\n"
        "   → 유사 항목이 여러 개면 목록 제시 후 선택 요청\n\n"
        "3. **목록/통계 질문** (예: '게시판 글 목록', '데이터 몇 건이야?')\n"
        "   → list_titles 또는 get_data_stats 사용\n\n"
        "4. **특정 항목 상세 질문** (예: '이마트 프로젝트 자세히', '경동나비엔 프로젝트 알려줘')\n"
        "   → get_item_detail로 바로 상세 조회\n\n"
        "5. **탐색적 질문** (예: 'LINE WORKS 메일 관련 기능', '엘루오 프로젝트 종류')\n"
        "   → explore_topic으로 그래프에서 연결된 개념 탐색\n"
        "   → 탐색 결과를 바탕으로 관련 항목을 search_faq나 get_item_detail로 추가 조회\n\n"
        "## 중요 원칙\n"
        "- 질문이 모호하거나 넓은 범위를 다루면, 바로 답변하지 말고 목록을 보여주며 되물으세요.\n"
        "- search_faq 결과의 유사도가 낮거나(0.03 미만) 관련 없어 보이면, list_titles로 전환하세요.\n"
        "- 절대 관련 없는 검색 결과를 억지로 답변에 포함시키지 마세요.\n\n"
        "## 데이터 출처 구분\n"
        "- source='faq': LINE WORKS 도움말 FAQ\n"
        "- source='board': 사내 게시판 (규정, 업무가이드)\n"
        "- source='eluocnc': 회사 홈페이지 (회사 소개, 프로젝트, 블로그)\n\n"
        "## 답변 규칙\n"
        "- 답변은 항상 한국어로, 자연스럽고 친절한 톤으로 작성하세요.\n"
        "- 도구로 조회한 결과(목록, 검색 결과)를 반드시 답변에 포함하세요. 도구를 호출만 하고 결과를 보여주지 않는 것은 절대 안 됩니다.\n"
        "- list_titles로 여러 항목이 조회되면, 번호가 매겨진 목록을 답변에 포함하고 '어떤 항목에 대해 더 알고 싶으신가요?'라고 물어보세요.\n"
        "- 답변 끝에 출처(FAQ/게시판/회사 홈페이지)와 관련 URL을 함께 제공하세요.\n"
        "- 검색 결과가 없거나 관련이 없는 경우, 솔직하게 모른다고 답변하세요.\n"
        "- 도구를 한 번만 호출해서 부족하면, 추가 도구를 호출하여 충분한 정보를 확보한 뒤 답변하세요.\n\n"
        "## 후속 질문 처리\n"
        "- '링크 줘', '상세 알려줘', '더 자세히' 같은 후속 질문은 이전 대화에서 언급된 항목에 대한 추가 정보 요청입니다.\n"
        "- URL이나 상세 정보를 요청받으면, 반드시 get_item_detail 도구를 호출하여 실제 데이터를 조회한 뒤 URL과 내용을 제공하세요.\n"
        "- 이전 대화 내용만으로 답변하지 말고, 항상 도구를 호출하여 정확한 정보를 가져오세요.\n"
        "- '~해드릴게요'라고만 말하고 실제 정보를 주지 않는 것은 절대 안 됩니다. 반드시 도구를 호출하고 결과를 포함하세요."
    ),
    tools=[
        Tool(search_faq, takes_ctx=True),
        Tool(list_titles, takes_ctx=True),
        Tool(get_item_detail, takes_ctx=True),
        Tool(get_data_stats, takes_ctx=True),
        Tool(explore_topic, takes_ctx=True),
    ],
)


def get_graph_db() -> GraphRAGDatabase:
    """GraphRAG 데이터베이스를 로드하여 반환한다."""
    return GraphRAGDatabase().load()



def ask(question: str, message_history=None) -> str:
    """질문에 대한 답변을 반환한다."""
    db = get_graph_db()
    result = faq_agent.run_sync(
        user_prompt=question,
        deps=db,
        message_history=message_history,
    )
    return result.output


if __name__ == "__main__":
    answer = ask("비밀번호를 잊어버렸어요")
    print(answer)
