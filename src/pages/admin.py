"""
문서 관리 어드민 페이지.

문서 업로드/삭제 → Pinecone 벡터 인덱스 단건 관리.
"""

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

# src 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graph.embedding_index import (
    get_embed_model,
    get_or_create_index,
    init_pinecone,
    list_all_doc_ids,
)
from graph.ingest import delete_document, ingest_document

st.set_page_config(page_title="문서 관리", page_icon="📄", layout="wide")
st.title("📄 문서 관리")
st.caption("문서를 업로드하거나 삭제하여 Pinecone 벡터 인덱스를 관리합니다.")

# ── Streamlit Cloud secrets → 환경변수 주입 ──
for key in ("PINECONE_API_KEY", "ANTHROPIC_API_KEY"):
    if key in st.secrets and key not in os.environ:
        os.environ[key] = st.secrets[key]


# ── 리소스 로드 ──

@st.cache_resource
def load_resources():
    """임베딩 모델 + Pinecone 인덱스를 로드한다."""
    api_key = os.environ.get("PINECONE_API_KEY", "")
    if not api_key:
        return None, None
    embed_model = get_embed_model()
    pc = init_pinecone(api_key)
    index = get_or_create_index(pc)
    return embed_model, index


embed_model, pinecone_index = load_resources()

if pinecone_index is None:
    st.error("PINECONE_API_KEY가 설정되지 않았습니다.")
    st.stop()

# ── 탭 구성 ──
tab_upload, tab_list = st.tabs(["📤 문서 업로드", "📋 등록된 문서"])

# ── 문서 업로드 탭 ──
with tab_upload:
    st.subheader("새 문서 등록")

    source = st.selectbox("출처 분류", ["board", "eluocnc", "faq"], format_func={
        "board": "사내 게시판",
        "eluocnc": "회사 홈페이지",
        "faq": "FAQ",
    }.get)

    input_method = st.radio("입력 방식", ["파일 업로드", "직접 입력"], horizontal=True)

    title = ""
    content = ""
    url = ""

    if input_method == "파일 업로드":
        uploaded = st.file_uploader(
            "파일 선택 (PDF, DOCX, XLSX, TXT)",
            type=["pdf", "docx", "xlsx", "txt"],
        )
        title = st.text_input("제목 (빈칸이면 파일명 사용)")
        url = st.text_input("관련 URL (선택사항)")

        if uploaded:
            if not title:
                title = uploaded.name

            # 파일에서 텍스트 추출
            suffix = Path(uploaded.name).suffix.lower()
            if suffix == ".txt":
                content = uploaded.read().decode("utf-8", errors="ignore")
            else:
                # 임시 파일로 저장 후 file_extractor로 추출
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = Path(tmp.name)
                try:
                    from scraper.file_extractor import extract_text
                    content = extract_text(tmp_path)
                except Exception as e:
                    st.error(f"파일 텍스트 추출 실패: {e}")
                    content = ""
                finally:
                    tmp_path.unlink(missing_ok=True)

            if content:
                with st.expander("추출된 텍스트 미리보기"):
                    st.text(content[:2000] + ("..." if len(content) > 2000 else ""))
    else:
        title = st.text_input("제목")
        url = st.text_input("관련 URL (선택사항)")
        content = st.text_area("본문 내용", height=300)

    # URL이 없으면 제목 기반으로 생성
    if not url and title:
        url = f"admin://{title}"

    # 제출 버튼
    if st.button("📥 등록", type="primary", disabled=not (title and content)):
        with st.spinner("임베딩 및 업로드 중..."):
            result = ingest_document(
                title=title,
                content=content,
                source=source,
                url=url,
                embed_model=embed_model,
                pinecone_index=pinecone_index,
            )
        if result["deleted"] > 0:
            st.info(f"기존 문서 {result['deleted']}개 청크 삭제 후 재등록")
        st.success(f"등록 완료! {result['chunks']}개 청크로 분할하여 업로드했습니다.")
        # 문서 목록 캐시 초기화
        st.cache_data.clear()

    if not (title and content):
        st.info("제목과 내용을 입력하면 등록 버튼이 활성화됩니다.")

# ── 등록된 문서 목록 탭 ──
with tab_list:
    st.subheader("Pinecone에 등록된 문서 목록")

    if st.button("🔄 새로고침"):
        st.cache_data.clear()

    @st.cache_data(ttl=60)
    def get_doc_list():
        return list_all_doc_ids(pinecone_index)

    with st.spinner("문서 목록 조회 중..."):
        docs = get_doc_list()

    if not docs:
        st.info("등록된 문서가 없습니다.")
    else:
        st.metric("총 문서 수", len(docs))

        source_labels = {"board": "게시판", "eluocnc": "홈페이지", "faq": "FAQ"}
        for i, doc in enumerate(docs):
            src_label = source_labels.get(doc["source"], doc["source"])
            col1, col2, col3 = st.columns([5, 1, 1])
            with col1:
                st.markdown(f"**[{src_label}]** {doc['title']}")
                if doc["url"] and not doc["url"].startswith("admin://"):
                    st.caption(doc["url"])
            with col2:
                st.caption(f"{doc['chunk_count']}청크")
            with col3:
                if st.button("🗑️", key=f"del_{doc['doc_prefix']}"):
                    if doc["url"]:
                        deleted = delete_document(doc["url"], pinecone_index)
                        st.toast(f"'{doc['title']}' 삭제 완료 ({deleted}개 청크)")
                        st.cache_data.clear()
                        st.rerun()
