"""
LINE WORKS 게시판 크롤러 (Playwright 방식).

board.worksmobile.com에서 사내업무가이드/규정/서식 데이터를 수집한다.
브라우저 로그인 자동화 후 게시글 본문 + 첨부파일을 추출한다.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import os

from playwright.sync_api import sync_playwright

from file_extractor import extract_from_directory, extract_pdf_images, extract_text

# 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = PROJECT_ROOT / "data" / "board_lineworks.json"
DOWNLOAD_DIR = PROJECT_ROOT / "data" / "board_attachments"
IMAGES_DIR = PROJECT_ROOT / "data" / "board_images"
STORAGE_STATE_PATH = PROJECT_ROOT / "data" / ".auth_state.json"

# 인증 정보
LINEWORKS_ID = os.getenv("LINEWORKS_ID", "") or os.getenv("ID", "")
LINEWORKS_PW = os.getenv("LINEWORKS_PW", "") or os.getenv("PW", "")

# 게시판 URL (환경 변수로 커스터마이징 가능)
BOARD_URL = os.getenv(
    "LINEWORKS_BOARD_URL",
    "https://board.worksmobile.com/main/board/4070000000141270911?t=53290",
)

# 크롤링 설정
PAGE_DELAY = 2.0  # 페이지 간 대기 시간 (초)


def login(page, context):
    """LINE WORKS에 로그인하고 세션을 저장한다."""
    if not LINEWORKS_ID or not LINEWORKS_PW:
        raise ValueError(
            "LINEWORKS_ID와 LINEWORKS_PW 환경 변수를 .env 파일에 설정해주세요."
        )

    print("[login] LINE WORKS 로그인 시작...")
    page.goto("https://auth.worksmobile.com/login/login")
    page.wait_for_load_state("networkidle")

    # ID 입력
    page.fill('input[type="text"], input[name="userId"], #userId', LINEWORKS_ID)
    # PW 입력
    page.fill('input[type="password"], input[name="password"], #password', LINEWORKS_PW)
    # 로그인 버튼 클릭
    page.click('button[type="submit"], .btn-login, #loginBtn')

    # 로그인 완료 대기 (URL이 auth 페이지에서 벗어날 때까지)
    try:
        page.wait_for_url(lambda url: "auth.worksmobile.com" not in url, timeout=30000)
        print("[login] 로그인 성공")
    except Exception:
        # 2FA/OTP가 필요한 경우 수동 개입을 위해 대기
        print("[login] 자동 로그인 실패. 2FA/OTP가 필요할 수 있습니다.")
        print("[login] 브라우저에서 수동으로 로그인을 완료해주세요... (60초 대기)")
        try:
            page.wait_for_url(
                lambda url: "auth.worksmobile.com" not in url, timeout=60000
            )
            print("[login] 수동 로그인 완료 감지")
        except Exception:
            raise RuntimeError("로그인 시간 초과. 브라우저에서 로그인을 완료하지 못했습니다.")

    # 세션 상태 저장
    STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(STORAGE_STATE_PATH))
    print(f"[login] 세션 저장 완료: {STORAGE_STATE_PATH}")


def collect_post_links(page) -> list[str]:
    """게시판 페이지에서 게시글 링크를 추출한다 (페이지네이션 포함)."""
    print("[collect] 게시글 목록 수집 시작...")
    all_links = []
    page_num = 1

    while True:
        print(f"  [page {page_num}] 게시글 링크 수집 중...")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)  # SPA 렌더링 대기

        # LINE WORKS 게시판 셀렉터: .block_list a[href*='/article/']
        links = page.eval_on_selector_all(
            ".block_list a[href*='/article/'], "
            ".board_list a[href*='/article/'], "
            "a[href*='/main/article/']",
            "elements => elements.map(el => el.href).filter(href => href)",
        )
        # 중복 제거
        new_links = [link for link in links if link not in all_links]
        all_links.extend(new_links)
        print(f"  [page {page_num}] {len(new_links)}개 새 링크 발견 (총 {len(all_links)}개)")

        if not new_links:
            break

        # 다음 페이지 버튼 찾기
        next_btn = page.query_selector(
            "a.next, button.next, .pagination .next:not(.disabled), "
            "[aria-label='Next'], .btn-next, [class*=paging] .next"
        )
        if next_btn and next_btn.is_visible():
            next_btn.click()
            page_num += 1
            time.sleep(PAGE_DELAY)
        else:
            break

    print(f"[collect] 총 {len(all_links)}개 게시글 링크 수집 완료")
    return all_links


def scrape_post(page, url: str) -> dict | None:
    """게시글 페이지에서 제목, 본문, 첨부파일을 추출한다."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)  # SPA 렌더링 대기
    except Exception as e:
        print(f"  [error] 페이지 로드 실패: {e}")
        return None

    # 제목 추출 (LINE WORKS: .subject)
    title = ""
    for selector in [".board_view .subject", ".subject", "h3.txt"]:
        el = page.query_selector(selector)
        if el:
            title = el.inner_text().strip()
            # "toggle important post" 등 불필요한 텍스트 제거
            title = title.split("\n")[0].strip()
            if title:
                break

    # 본문 추출 (LINE WORKS: .board_view .cont)
    content = ""
    for selector in [".board_view .cont", ".board_view .content", ".cont"]:
        el = page.query_selector(selector)
        if el:
            content = el.inner_text().strip()
            if content:
                break

    if not title and not content:
        print(f"  [skip] 콘텐츠 없음: {url}")
        return None

    return {
        "url": url,
        "title": title,
        "content": content,
        "category": "사내업무가이드",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source": "board",
        "attachments": [],
    }


def download_attachments(page, post_data: dict) -> list[dict]:
    """게시글의 첨부파일을 다운로드하고 텍스트를 추출한다."""
    # LINE WORKS: 첨부파일은 button.btn_down_pc 으로 다운로드
    download_buttons = page.query_selector_all(
        ".lw_file_attach_view button.btn_down_pc"
    )
    if not download_buttons:
        return []

    print(f"  [attach] {len(download_buttons)}개 첨부파일 발견")
    attachments = []
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    for btn in download_buttons:
        try:
            with page.expect_download(timeout=30000) as download_info:
                btn.click()
            download = download_info.value
            file_path = DOWNLOAD_DIR / download.suggested_filename
            download.save_as(str(file_path))
            print(f"    - 다운로드: {file_path.name}")

            # 텍스트 추출
            extracted_text = ""
            try:
                extracted_text = extract_text(file_path)
            except Exception as e:
                print(f"    [warn] 텍스트 추출 실패: {e}")

            # PDF인 경우 페이지별 이미지 추출
            image_paths = []
            if file_path.suffix.lower() == ".pdf":
                try:
                    image_paths = extract_pdf_images(file_path, IMAGES_DIR)
                except Exception as e:
                    print(f"    [warn] 이미지 추출 실패: {e}")

            attachments.append({
                "filename": file_path.name,
                "extracted_text": extracted_text,
                "images": image_paths,
            })
        except Exception as e:
            print(f"    [error] 다운로드 실패: {e}")

    return attachments


def scrape_board():
    """Playwright로 게시판을 크롤링한다."""
    print(f"[start] LINE WORKS 게시판 크롤링 시작")
    print(f"[url] {BOARD_URL}")

    with sync_playwright() as p:
        # 저장된 세션이 있으면 재사용
        if STORAGE_STATE_PATH.exists():
            print("[auth] 저장된 세션 사용")
            context = p.chromium.launch(headless=False).new_context(
                storage_state=str(STORAGE_STATE_PATH)
            )
        else:
            context = p.chromium.launch(headless=False).new_context()

        page = context.new_page()

        # 게시판 접속 시도
        page.goto(BOARD_URL, wait_until="domcontentloaded")

        # 로그인 페이지로 리다이렉트되었는지 확인
        if "auth.worksmobile.com" in page.url:
            login(page, context)
            page.goto(BOARD_URL, wait_until="domcontentloaded")

        # 게시글 목록 수집
        post_links = collect_post_links(page)
        if not post_links:
            print("[warn] 게시글을 찾을 수 없습니다. CSS 셀렉터를 확인해주세요.")
            print(f"[debug] 현재 URL: {page.url}")
            print(f"[debug] 페이지 제목: {page.title()}")
            context.browser.close()
            return []

        # 각 게시글 상세 수집
        results = []
        for i, link in enumerate(post_links, 1):
            print(f"[{i}/{len(post_links)}] {link}")
            post_data = scrape_post(page, link)
            if post_data:
                # 첨부파일 다운로드 및 텍스트 추출
                attachments = download_attachments(page, post_data)
                post_data["attachments"] = attachments

                # 첨부파일 텍스트를 본문에 병합
                for att in attachments:
                    if att["extracted_text"]:
                        post_data["content"] += f"\n\n[첨부: {att['filename']}]\n{att['extracted_text']}"

                results.append(post_data)
            time.sleep(PAGE_DELAY)

        context.browser.close()

    return results


def scrape_from_local(local_dir: Path) -> list[dict]:
    """수동 다운로드한 파일에서 텍스트를 추출한다 (폴백 모드)."""
    print(f"[local] 로컬 파일에서 텍스트 추출: {local_dir}")
    extracted = extract_from_directory(local_dir)

    results = []
    for item in extracted:
        results.append({
            "url": "",
            "title": Path(item["filename"]).stem,
            "content": item["extracted_text"],
            "category": "사내업무가이드",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "source": "board",
            "attachments": [item],
        })
    return results


def save_results(results: list[dict], output_path: Path = OUTPUT_PATH) -> None:
    """결과를 JSON 파일로 저장한다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[done] {len(results)}개 게시글을 {output_path}에 저장 완료")


def main():
    parser = argparse.ArgumentParser(description="LINE WORKS 게시판 크롤러")
    parser.add_argument(
        "--from-local",
        type=Path,
        help="수동 다운로드한 파일이 있는 디렉토리 (폴백 모드)",
    )
    args = parser.parse_args()

    if args.from_local:
        results = scrape_from_local(args.from_local)
    else:
        results = scrape_board()

    if results:
        save_results(results)
    else:
        print("[warn] 수집된 데이터가 없습니다.")


if __name__ == "__main__":
    main()
