from typing import List, Dict, Optional


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

    lines = []
    lines.append("---")
    lines.append("layout: hn")
    lines.append(f'title: "{fm_title}"')
    lines.append("---")
    lines.append("")

    # Header (NO outer hn-wrap here; layout provides it)
    lines.append(f"<h1 class='hn-h1'>{page_title}</h1>")

    source_link = "<a href='https://news.ycombinator.com/' target='_blank' rel='noopener noreferrer'>news.ycombinator.com</a>"
    subtitle = page_subtitle.strip()
    if subtitle:
        subtitle = f"{subtitle} · Source: {source_link}"
    else:
        subtitle = f"Source: {source_link}"
    lines.append(f"<p class='hn-subtitle'>{subtitle}</p>")

    # badges
    lines.append("<div class='hn-badges'>")
    lines.append(f"<span class='hn-badge'>Top {len(items)}</span>")
    lines.append("<span class='hn-badge'>Best Stories</span>")
    lines.append("</div>")

    lines.append("<hr class='hn-rule'/>")
    lines.append("<div class='hn-list'>")

    for i, it in enumerate(items, start=1):
        title_en: str = it["title_en"]
        url: str = it["url"]
        title_zh: str = it.get("title_zh", "")
        summary_en: str = it.get("summary_en", "")
        summary_zh: str = it.get("summary_zh", "")
        image_url: Optional[str] = it.get("image_url")


        lines.append("<div class='hn-card'>")
        lines.append("<div class='hn-body'>")

        lines.append(
            f"<p class='hn-title'>({i}) "
            f"<a href='{url}' target='_blank' rel='noopener noreferrer'>{title_en}</a>"
            f"</p>"
        )

        if title_zh:
            lines.append(f"<p class='hn-meta'>{title_zh}</p>")

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
