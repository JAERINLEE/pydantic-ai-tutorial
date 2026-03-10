"""
LINE WORKS FAQ 크롤러.

https://help.worksmobile.com/ko/faqs-sitemap.xml 에서 FAQ URL을 수집하고,
각 페이지의 제목/본문을 추출하여 data/faq_lineworks.json에 저장한다.
"""

import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

SITEMAP_URL = "https://help.worksmobile.com/ko/faqs-sitemap.xml"
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "faq_lineworks.json"
REQUEST_DELAY = 1.5  # seconds between requests
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_faq_urls(sitemap_url: str = SITEMAP_URL) -> list[str]:
    """Sitemap XML에서 FAQ URL 목록을 추출한다."""
    resp = requests.get(sitemap_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    # sitemap XML namespace
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text for loc in root.findall(".//sm:loc", ns) if loc.text]
    print(f"[sitemap] {len(urls)}개 FAQ URL 수집 완료")
    return urls


def extract_category_from_url(url: str) -> str:
    """URL 경로에서 카테고리를 추출한다."""
    parts = urlparse(url).path.strip("/").split("/")
    # /ko/category/subcategory/slug 형태에서 category 추출
    if len(parts) >= 3:
        return parts[1]
    return "general"


def scrape_faq_page(url: str) -> dict | None:
    """FAQ 페이지에서 제목과 본문을 추출한다."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[error] {url} 요청 실패: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # 제목 추출
    title_tag = soup.select_one("h1, h2.article-title, .content-header h1, .article__title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # 본문 추출
    content_tag = soup.select_one(
        "article, .article-body, .content-body, .faq-content, "
        ".article__body, main .content, .helpdesk-content"
    )
    if content_tag:
        # 불필요한 요소 제거
        for tag in content_tag.select("script, style, nav, header, footer"):
            tag.decompose()
        content = content_tag.get_text(separator="\n", strip=True)
    else:
        # fallback: body 전체에서 텍스트 추출
        body = soup.find("body")
        if body:
            for tag in body.select("script, style, nav, header, footer"):
                tag.decompose()
            content = body.get_text(separator="\n", strip=True)
        else:
            content = ""

    if not title and not content:
        print(f"[skip] {url} - 콘텐츠 없음")
        return None

    return {
        "url": url,
        "title": title,
        "content": content,
        "category": extract_category_from_url(url),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def scrape_all_faqs() -> list[dict]:
    """모든 FAQ를 크롤링한다."""
    urls = fetch_faq_urls()
    results = []

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        item = scrape_faq_page(url)
        if item:
            results.append(item)
        time.sleep(REQUEST_DELAY)

    return results


def save_results(results: list[dict], output_path: Path = OUTPUT_PATH) -> None:
    """결과를 JSON 파일로 저장한다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[done] {len(results)}개 FAQ를 {output_path}에 저장 완료")


def main():
    results = scrape_all_faqs()
    save_results(results)


if __name__ == "__main__":
    main()
