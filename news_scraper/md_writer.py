from typing import List, Dict, Optional


def render_markdown(
    items: List[Dict],
    page_title: str,
    page_subtitle: str = "",
    html_title: Optional[str] = None,
) -> str:
    """
    New version:
    - No inline <style> or <script>
    - Use shared assets:
        /assets/hn/hn.css
        /assets/hn/hn.js
    - Use Google Fonts (Inter + Source Serif 4)
    - All old pages will update if you change hn.css / hn.js
    """
    fm_title = html_title or page_title

    lines = []
    lines.append("---")
    lines.append("layout: default")
    lines.append(f'title: "{fm_title}"')
    lines.append("---")
    lines.append("")

    # Google Fonts + global CSS/JS
    lines.append("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;650;750;800&family=Source+Serif+4:opsz,wght@8..60,450;8..60,600&display=swap" rel="stylesheet">

<link rel="stylesheet" href="/assets/hn/hn.css">
<script src="/assets/hn/hn.js" defer></script>
""".strip())
    lines.append("")

    # Header
    lines.append("<div class='hn-wrap'>")
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
    lines.append("<span class='hn-badge'>PST/PDT</span>")
    lines.append("</div>")

    lines.append("<hr class='hn-rule'/>")

    lines.append("<div class='hn-list'>")

    for i, it in enumerate(items, start=1):
        title_en: str = it["title_en"]
        url: str = it["url"]
        title_zh: str = it["title_zh"]
        scrape_time: str = it["scrape_time"]
        summary_en: str = it["summary_en"]
        summary_zh: str = it["summary_zh"]
        image_url: Optional[str] = it.get("image_url")

        lines.append("<div class='hn-card'>")

        if image_url:
            # click => handled by hn.js
            lines.append(
                f"<img class='hn-img' src='{image_url}' data-full='{image_url}' alt='preview image' loading='lazy'/>"
            )

        lines.append("<div class='hn-body'>")
        lines.append(
            f"<p class='hn-title'>({i}) <a href='{url}' target='_blank' rel='noopener noreferrer'>{title_en}</a></p>"
        )
        lines.append(f"<p class='hn-meta'>{title_zh} &nbsp;|&nbsp; {scrape_time}</p>")
        lines.append(f"<p class='hn-text-en'>{summary_en}</p>")
        lines.append(f"<p class='hn-text-zh'>{summary_zh}</p>")
        lines.append("</div>")  # hn-body

        lines.append("</div>")  # hn-card

    lines.append("</div>")  # hn-list
    lines.append("</div>")  # hn-wrap
    lines.append("")

    return "\n".join(lines)
