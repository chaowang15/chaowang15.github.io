from typing import List, Dict, Optional

def render_markdown(items: List[Dict], page_title: str, page_subtitle: str = "") -> str:
    """
    Render a stylish markdown page (GitHub Pages / Jekyll) with:
    - YAML front matter title
    - Elegant inline CSS
    - Image thumbnail (max width) with rounded corners
    - Each story shown as a "card"
    """
    lines = []
    lines.append("---")
    lines.append("layout: default")
    lines.append(f'title: "{page_title}"')
    lines.append("---")
    lines.append("")
    lines.append(f"# {page_title}")
    if page_subtitle:
        lines.append("")
        lines.append(f"<p class='hn-subtitle'>{page_subtitle}</p>")
    lines.append("")
    lines.append("<style>")
    lines.append("""
/* HackerNews pages - lightweight, elegant */
.hn-subtitle { margin-top: -8px; opacity: 0.8; }
.hn-list { display: flex; flex-direction: column; gap: 16px; margin-top: 18px; }
.hn-card {
  padding: 16px 18px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 16px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.06);
  background: rgba(255,255,255,0.90);
}
@media (prefers-color-scheme: dark) {
  .hn-card {
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(20,20,20,0.55);
    box-shadow: 0 6px 18px rgba(0,0,0,0.35);
  }
}
.hn-title { font-size: 1.05rem; font-weight: 700; margin: 0 0 6px 0; }
.hn-meta { font-size: 0.95rem; opacity: 0.85; margin: 0 0 12px 0; }
.hn-img {
  display: block;
  max-width: min(720px, 100%);
  width: 100%;
  height: auto;
  border-radius: 14px;
  margin: 10px 0 12px 0;
}
.hn-bullets { margin: 0; padding-left: 18px; }
.hn-bullets li { margin: 6px 0; }
""".strip())
    lines.append("</style>")
    lines.append("")
    lines.append("<div class='hn-list'>")

    for i, it in enumerate(items, start=1):
        title_en: str = it["title_en"]
        url: str = it["url"]
        title_zh: str = it["title_zh"]
        scrape_time: str = it["scrape_time"]
        summary_en: str = it["summary_en"]
        summary_zh: str = it["summary_zh"]
        image_url: Optional[str] = it.get("image_url")

        # Card start
        lines.append("<div class='hn-card'>")

        # Title line with index + bold link
        lines.append(
            f"<p class='hn-title'>({i}) <a href='{url}' target='_blank' rel='noopener noreferrer'>{title_en}</a></p>"
        )

        # Meta line
        lines.append(f"<p class='hn-meta'>{title_zh} &nbsp;|&nbsp; {scrape_time}</p>")

        # Image (thumbnail)
        if image_url:
            lines.append(
                f"<img class='hn-img' src='{image_url}' alt='preview image' loading='lazy'/>"
            )

        # Bullets
        lines.append("<ul class='hn-bullets'>")
        lines.append(f"<li>{summary_en}</li>")
        lines.append(f"<li>{summary_zh}</li>")
        lines.append("</ul>")

        # Card end
        lines.append("</div>")

    lines.append("</div>")
    lines.append("")

    return "\n".join(lines)
