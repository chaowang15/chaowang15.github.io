import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Optional

def _is_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https")
    except Exception:
        return False

def extract_preview_image_url(
    page_url: str,
    timeout_seconds: int = 15,
    user_agent: str = "Mozilla/5.0",
) -> Optional[str]:
    """
    Extract preview image URL from:
      - <meta property="og:image" ...>
      - <meta name="twitter:image" ...>
      - fallback: first <img> tag

    Return absolute URL or None.
    """
    if not _is_http_url(page_url):
        return None

    headers = {"User-Agent": user_agent}
    try:
        r = requests.get(
            page_url,
            headers=headers,
            timeout=timeout_seconds,
            allow_redirects=True,
        )
        r.raise_for_status()
        html = r.text
    except Exception:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # 1) og:image
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        img = og["content"].strip()
        img_abs = urljoin(page_url, img)
        if _is_http_url(img_abs):
            return img_abs

    # 2) twitter:image
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        img = tw["content"].strip()
        img_abs = urljoin(page_url, img)
        if _is_http_url(img_abs):
            return img_abs

    # 3) fallback: first <img>
    img_tag = soup.find("img")
    if img_tag and img_tag.get("src"):
        img = img_tag["src"].strip()
        img_abs = urljoin(page_url, img)
        if _is_http_url(img_abs):
            return img_abs

    return None
