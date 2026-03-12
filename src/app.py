"""
Ask Eluo — Streamlit 채팅 UI.

PydanticAI 에이전트 기반 사내 지식 검색 챗봇.
"""

import sys
from pathlib import Path

# sniffio 패치 + 백그라운드 루프 — 반드시 첫 번째 import
from ui.async_runtime import run_async  # noqa: E402

import streamlit as st

# src 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent.faq_agent import GraphRAGDatabase, faq_agent, get_graph_db
from ui.og_cards import render_og_cards

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_STATIC = Path(__file__).resolve().parent / "ui" / "static"
_AVATAR_BOT = str(_STATIC / "avatar_bot.svg")
_AVATAR_USER = str(_STATIC / "avatar_user.svg")

st.set_page_config(page_title="Ask Eluo", page_icon="💬", layout="wide")

# ── CSS / JS 로드 ──
st.markdown(f"<style>\n{_STATIC.joinpath('style.css').read_text()}\n</style>", unsafe_allow_html=True)

st.markdown(f"<script>\n{_STATIC.joinpath('scroll_lock.js').read_text()}\n</script>", unsafe_allow_html=True)


@st.cache_resource
def load_faq_db() -> GraphRAGDatabase:
    """FAQ 데이터베이스를 로드하고 캐시한다."""
    return get_graph_db()


# DB 로드
try:
    faq_db = load_faq_db()
    pinecone_ok = faq_db.pinecone_index is not None
    badge_class = "connected" if pinecone_ok else "disconnected"
    badge_text = "Pinecone" if pinecone_ok else "Pinecone 연결 안됨"
    st.markdown(f"""
    <div class="pinecone-badge {badge_class}">
        <span class="pinecone-dot"></span>
        {badge_text}
    </div>
    """, unsafe_allow_html=True)
except FileNotFoundError:
    st.error(
        "데이터가 없습니다. 먼저 크롤러를 실행해주세요:\n\n"
        "`python src/scraper/board_scraper.py`\n\n"
        "`python src/scraper/eluocnc_scraper.py`"
    )
    st.stop()
except ValueError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"데이터 로드 실패: {e}")
    st.stop()

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pydantic_history" not in st.session_state:
    st.session_state.pydantic_history = []

# 웰컴 — 대화 시작 전에만 표시
welcome_slot = st.empty()
if not st.session_state.messages:
    welcome_slot.markdown("""
    <div class="welcome-card">
        <div class="welcome-greeting">Ask Eluo</div>
    </div>
    """, unsafe_allow_html=True)

# 대화 히스토리 표시
for idx, msg in enumerate(st.session_state.messages):
    avatar = _AVATAR_BOT if msg["role"] == "assistant" else _AVATAR_USER
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("og_cards"):
            render_og_cards(msg["content"], og_cache=msg["og_cards"])

if prompt := st.chat_input("질문을 입력하세요..."):
    welcome_slot.empty()
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=_AVATAR_USER):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=_AVATAR_BOT):
        placeholder = st.empty()

        async def _stream(user_prompt, deps, history):
            """PydanticAI run_stream_events로 도구 호출 후에도 텍스트를 스트리밍한다."""
            import time

            from pydantic_ai import (
                AgentRunResultEvent,
                PartDeltaEvent,
                TextPartDelta,
            )

            full_text = ""
            last_render = 0.0
            render_interval = 0.05  # 50ms 간격으로 화면 갱신
            placeholder.markdown("검색 중... ⏳")
            async for event in faq_agent.run_stream_events(
                user_prompt=user_prompt,
                deps=deps,
                message_history=history or None,
            ):
                if isinstance(event, AgentRunResultEvent):
                    final_output = event.result.output
                    if isinstance(final_output, str):
                        full_text = final_output
                    placeholder.markdown(full_text)
                    return full_text, event.result.all_messages()
                elif isinstance(event, PartDeltaEvent):
                    if isinstance(event.delta, TextPartDelta):
                        full_text += event.delta.content_delta
                        now = time.monotonic()
                        if now - last_render >= render_interval:
                            placeholder.markdown(full_text + "▌")
                            last_render = now
            placeholder.markdown(full_text or "답변을 생성하지 못했습니다.")
            return full_text, []

        try:
            answer, all_messages = run_async(
                _stream(prompt, faq_db, st.session_state.pydantic_history)
            )
            st.session_state.pydantic_history = all_messages
        except Exception:
            try:
                answer, all_messages = run_async(
                    _stream(prompt, faq_db, None)
                )
                st.session_state.pydantic_history = all_messages
            except Exception as e:
                answer = f"죄송합니다. 오류가 발생했습니다: {e}"
                placeholder.markdown(answer)

        # URL이 있으면 OpenGraph 카드로 렌더링
        og_cards = render_og_cards(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "og_cards": og_cards,
    })
