"""OpenGraph 메타데이터 fetch + 카드 렌더링."""

import html as html_mod
import re
from urllib.parse import urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_og_metadata(url: str) -> dict | None:
    """URL에서 OpenGraph 메타데이터를 가져온다."""
    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        title = og_title["content"] if og_title and og_title.get("content") else soup.title.string if soup.title else ""
        desc = og_desc["content"] if og_desc and og_desc.get("content") else ""
        image = og_image["content"] if og_image and og_image.get("content") else ""
        domain = urlparse(url).netloc
        return {"title": title or domain, "description": desc, "image": image, "domain": domain, "url": url}
    except Exception:
        domain = urlparse(url).netloc
        return {"title": domain, "description": "", "image": "", "domain": domain, "url": url}


def extract_urls(text: str) -> list[str]:
    """텍스트에서 URL을 추출한다."""
    return list(dict.fromkeys(re.findall(r'https?://[^\s\)\]<>"]+', text)))


def render_og_cards(text: str, og_cache: list[dict] | None = None):
    """텍스트 내 URL을 OpenGraph 카드로 렌더링한다."""
    if og_cache is not None:
        cards = og_cache
    else:
        urls = extract_urls(text)
        if not urls:
            return []
        cards = [fetch_og_metadata(u) for u in urls[:5]]
        cards = [c for c in cards if c]

    for card in cards:
        esc = html_mod.escape
        img_html = f'<img class="og-card-img" src="{esc(card["image"])}" alt="" />' if card.get("image") else ""
        st.markdown(f"""
        <a class="og-card" href="{esc(card['url'])}" target="_blank" rel="noopener">
            {img_html}
            <div class="og-card-body">
                <div class="og-card-title">{esc(card.get('title', ''))}</div>
                <div class="og-card-desc">{esc(card.get('description', ''))}</div>
                <div class="og-card-url">{esc(card.get('domain', ''))}</div>
            </div>
        </a>
        """, unsafe_allow_html=True)
    return cards
