from typing import List, Dict, Optional
import re
from datetime import datetime, timedelta

# Tag color mapping: each tag gets a distinct hue for visual differentiation.
# Colors are defined as CSS class suffixes; actual colors are in hn.css.
TAG_COLOR_MAP = {
    "AI":            "blue",
    "Programming":   "indigo",
    "Security":      "red",
    "Science":       "teal",
    "Business":      "amber",
    "Finance":       "amber",
    "Hardware":      "slate",
    "Open Source":   "green",
    "Design":        "pink",
    "Web":           "cyan",
    "DevOps":        "indigo",
    "Data":          "violet",
    "Gaming":        "purple",
    "Entertainment": "purple",
    "Politics":      "orange",
    "Health":        "emerald",
    "Education":     "sky",
    "Career":        "sky",
    "Privacy":       "red",
    "Legal":         "orange",
    "Culture":       "rose",
    "Space":         "teal",
    "Energy":        "emerald",
    "Startups":      "amber",
    "Show HN":       "green",
}


def _tag_html(tag: str) -> str:
    """Render a single tag as an inline badge with color class and data attribute."""
    color = TAG_COLOR_MAP.get(tag, "slate")
    safe_tag = tag.replace('"', '&quot;')
    return f"<span class='hn-tag hn-tag--{color}' data-tag='{safe_tag}'>{tag}</span>"


def _detect_mode(page_title: str) -> str:
    """Detect story mode from page title string."""
    if "Trending" in page_title:
        return "top"
    return "best"


def render_markdown(
    items: List[Dict],
    page_title: str,
    page_subtitle: str = "",
    html_title: Optional[str] = None,
) -> str:
    """
    New version:
    - layout: hn (handled by _layouts/hn.html)
    - No inline <style> or <script> (layout includes /assets/hn/hn.css + hn.js)
    Note: main.py will additionally clean legacy head tags / wrap if present.
    """
    fm_title = html_title or page_title
    mode = _detect_mode(page_title)

    lines = []
    lines.append("---")
    lines.append("layout: hn")
    lines.append(f'title: "{fm_title}"')
    lines.append("---")
    lines.append("")

    # Header with mode badge
    if mode == "top":
        badge = "<span class='hn-mode-badge hn-mode-top'>Trending</span>"
    else:
        badge = "<span class='hn-mode-badge hn-mode-best'>Daily Best</span>"

    # Extract the date portion for a cleaner H1
    # page_title: "Hacker News — Daily Best (2026-02-18)" or "Hacker News — Trending (2026-02-19)"
    m_date = re.search(r"\((\d{4}-\d{2}-\d{2})\)", page_title)
    date_str = m_date.group(1) if m_date else ""

    if date_str:
        h1_text = f"Hacker News Daily — {date_str}"
    else:
        h1_text = "Hacker News Daily"

    lines.append(f"<h1 class='hn-h1'>{h1_text} {badge}</h1>")

    # Prev / Index / Next navigation
    prev_href = None
    next_href = None
    file_prefix = "top_stories" if mode == "top" else "best_stories"

    if m_date:
        try:
            dt = datetime.strptime(m_date.group(1), "%Y-%m-%d")

            prev_dt = dt - timedelta(days=1)
            next_dt = dt + timedelta(days=1)

            prev_href = (
                f"/hackernews/{prev_dt.strftime('%Y/%m/%d')}/"
                f"{file_prefix}_{prev_dt.strftime('%m%d%Y')}"
            )
            next_href = (
                f"/hackernews/{next_dt.strftime('%Y/%m/%d')}/"
                f"{file_prefix}_{next_dt.strftime('%m%d%Y')}"
            )
        except Exception:
            prev_href = None
            next_href = None

    # Build Prev/Index/Next nav with pill button styling
    nav_html = "<div class='hn-nav'>"

    if prev_href:
        nav_html += f"<a class='hn-nav-btn hn-prev' href='{prev_href}'>‹ Prev day</a>"
    else:
        nav_html += "<span></span>"

    nav_html += "<a class='hn-nav-btn hn-nav-index' href='/hackernews/'>← Index</a>"

    if next_href:
        nav_html += f"<a class='hn-nav-btn hn-next' href='{next_href}'>Next day ›</a>"
    else:
        nav_html += "<span></span>"

    nav_html += "</div>"
    lines.append(nav_html)

    subtitle = page_subtitle.strip()
    if subtitle:
        lines.append(f"<p class='hn-subtitle'>{subtitle}</p>")

    lines.append("<hr class='hn-rule'/>")
    lines.append("<div class='hn-list'>")

    for i, it in enumerate(items, start=1):
        title_en: str = it["title_en"]
        url: str = it["url"]
        title_zh: str = it.get("title_zh", "")
        summary_en: str = it.get("summary_en", "")
        summary_zh: str = it.get("summary_zh", "")
        image_url: Optional[str] = it.get("image_url")
        tags: List[str] = it.get("tags", [])

        # Build data-tags attribute for future JS filtering
        tags_data = ",".join(tags) if tags else ""

        # Anchor ID from HN story ID for deep linking
        hn_id = (it.get("hn") or {}).get("id", "")
        id_attr = f" id='story-{hn_id}'" if hn_id else ""

        lines.append(f"<div class='hn-card'{id_attr} data-tags='{tags_data}'>")
        lines.append("<div class='hn-body'>")

        lines.append(
            f"<p class='hn-title'>({i}) "
            f"<a href='{url}' target='_blank' rel='noopener noreferrer'>{title_en}</a>"
            f"</p>"
        )

        # Chinese subtitle line
        if title_zh:
            lines.append(f"<p class='hn-meta'>{title_zh}</p>")

        # New info row under Chinese subtitle (backward compatible)
        created_display = it.get("created_display", "")
        hn = it.get("hn") or {}
        hn_score = hn.get("score")
        hn_by = hn.get("by")
        comments_url = hn.get("comments_url")
        hn_desc = hn.get("descendants")

        parts = []

        # Created time
        if created_display:
            parts.append(f"<span class='hn-meta2-created'>{created_display}</span>")

        # "120 points by cheeaun"
        if hn_score is not None and hn_by:
            parts.append(f"<span class='hn-meta2-points'>{hn_score} points by {hn_by}</span>")

        # Comments link (optionally show count if available)
        if comments_url:
            if hn_desc is not None:
                parts.append(
                    f"<a class='hn-meta2-comments' href='{comments_url}' target='_blank' rel='noopener noreferrer'>Comments ({hn_desc})</a>"
                )
            else:
                parts.append(
                    f"<a class='hn-meta2-comments' href='{comments_url}' target='_blank' rel='noopener noreferrer'>Comments</a>"
                )

        # Only show the new row if anything exists (old json won't show it)
        if parts:
            lines.append("<p class='hn-meta2'>" + "<span class='hn-sep'> · </span>".join(parts) + "</p>")

        # Tags row (rendered as colored pill badges)
        if tags:
            tags_html = " ".join(_tag_html(t) for t in tags)
            lines.append(f"<div class='hn-tags'>{tags_html}</div>")

        # Image under meta (subtitle)
        if image_url:
            lines.append(
                f"<img class='hn-img' src='{image_url}' data-full='{image_url}' "
                f"alt='preview image' loading='lazy'/>"
            )

        if summary_en:
            lines.append(f"<p class='hn-text-en'>{summary_en}</p>")
        if summary_zh:
            lines.append(f"<p class='hn-text-zh'>{summary_zh}</p>")

        lines.append("</div>")  # hn-body
        lines.append("</div>")  # hn-card

    lines.append("</div>")  # hn-list
    lines.append("")
    return "\n".join(lines)
