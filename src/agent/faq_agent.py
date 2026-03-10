"""
LINE WORKS FAQ 에이전트.

TF-IDF 기반 검색 툴을 갖춘 PydanticAI 에이전트로,
크롤링된 FAQ 데이터를 기반으로 사용자 질문에 답변한다.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import nest_asyncio
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.google import GoogleModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()
nest_asyncio.apply()

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FAQ_DATA_PATH = DATA_DIR / "faq_lineworks.json"
BOARD_DATA_PATH = DATA_DIR / "board_lineworks.json"


@dataclass
class FAQDatabase:
    """TF-IDF 인덱스를 포함한 FAQ 데이터베이스."""

    items: list[dict] = field(default_factory=list)
    vectorizer: TfidfVectorizer = field(default_factory=TfidfVectorizer)
    tfidf_matrix: object = None  # sparse matrix

    def load(self, paths: list[Path] | None = None) -> "FAQDatabase":
        """하나 이상의 JSON 파일을 로드하고 TF-IDF 인덱스를 구축한다."""
        if paths is None:
            paths = [FAQ_DATA_PATH, BOARD_DATA_PATH]

        self.items = []
        for path in paths:
            if not path.exists():
                print(f"[warn] 데이터 파일 없음 (건너뜀): {path}")
                continue
            with open(path, encoding="utf-8") as f:
                items = json.load(f)
                # source 필드가 없으면 파일명 기반으로 추가
                default_source = "board" if "board" in path.name else "faq"
                for item in items:
                    item.setdefault("source", default_source)
                self.items.extend(items)

        if not self.items:
            raise ValueError("데이터가 비어있습니다. FAQ 또는 게시판 데이터를 먼저 수집해주세요.")

        # 제목 + 본문을 합쳐서 TF-IDF 벡터화
        documents = [
            f"{item.get('title', '')} {item.get('content', '')}" for item in self.items
        ]
        self.tfidf_matrix = self.vectorizer.fit_transform(documents)
        return self

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """쿼리와 가장 유사한 상위 k개 FAQ를 반환한다."""
        if self.tfidf_matrix is None:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        top_indices = similarities.argsort()[::-1][:top_k]
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:
                item = self.items[idx]
                # 첨부파일에서 이미지 경로 수집
                images = []
                for att in item.get("attachments", []):
                    images.extend(att.get("images", []))
                results.append(
                    {
                        "title": item.get("title", ""),
                        "content": item.get("content", "")[:500],
                        "url": item.get("url", ""),
                        "source": item.get("source", "faq"),
                        "score": float(similarities[idx]),
                        "images": images,
                    }
                )
        return results


def search_faq(ctx: RunContext[FAQDatabase], query: str) -> str:
    """사용자 질문을 기반으로 FAQ 데이터베이스를 검색합니다."""
    results = ctx.deps.search(query)
    if not results:
        return "관련 FAQ를 찾을 수 없습니다."

    source_labels = {"faq": "FAQ", "board": "게시판"}
    output_parts = []
    for i, r in enumerate(results, 1):
        source = source_labels.get(r.get("source", "faq"), r.get("source", ""))
        output_parts.append(
            f"[{i}] [{source}] {r['title']}\n"
            f"내용: {r['content']}\n"
            f"URL: {r['url']}\n"
            f"유사도: {r['score']:.3f}"
        )
    return "\n\n".join(output_parts)


model = GoogleModel("gemini-2.5-flash")

faq_agent = Agent(
    model=model,
    deps_type=FAQDatabase,
    system_prompt=(
        "당신은 엘루오 회사의 LINE WORKS FAQ 및 사내 규정/업무가이드 전문 도우미입니다. "
        "사용자의 질문에 대해 search_faq 도구를 사용하여 FAQ와 사내 게시판 자료를 검색한 후, "
        "검색 결과를 바탕으로 정확하고 친절하게 답변해주세요. "
        "답변 시 출처(FAQ 또는 게시판)와 관련 URL도 함께 제공해주세요. "
        "검색 결과가 없거나 관련이 없는 경우, 솔직하게 모른다고 답변하세요. "
        "항상 한국어로 답변하세요."
    ),
    tools=[Tool(search_faq, takes_ctx=True)],
)


def get_faq_db() -> FAQDatabase:
    """FAQ 데이터베이스를 로드하여 반환한다."""
    return FAQDatabase().load()


def ask(question: str, message_history=None) -> str:
    """질문에 대한 답변을 반환한다."""
    db = get_faq_db()
    result = faq_agent.run_sync(
        user_prompt=question,
        deps=db,
        message_history=message_history,
    )
    return result.output


if __name__ == "__main__":
    answer = ask("비밀번호를 잊어버렸어요")
    print(answer)
