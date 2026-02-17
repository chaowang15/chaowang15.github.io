from typing import List, Dict, Optional

def render_markdown(items: List[Dict], page_title: str, page_subtitle: str = "") -> str:
    """
    Modern, clean, "media" style:
    - Centered content with max-width (less empty right space)
    - Better typography (bigger body text)
    - Title slightly smaller than before, but still strong
    - Image becomes a consistent cover (fixed height, crop with object-fit: cover)
    - Remove bullet list; show EN + ZH as two paragraphs (less clutter)
    - Subtitle includes source link (Hacker News)
    """
    lines = []
    lines.append("---")
    lines.append("layout: default")
    lines.append(f'title: "{page_title}"')
    lines.append("---")
    lines.append("")

    lines.append("<style>")
    lines.append("""
:root{
  --hn-maxw: 920px;
  --hn-radius: 16px;
  --hn-border: rgba(0,0,0,0.10);
  --hn-shadow: 0 10px 26px rgba(0,0,0,0.08);
  --hn-muted: rgba(0,0,0,0.62);
}
@media (prefers-color-scheme: dark) {
  :root{
    --hn-border: rgba(255,255,255,0.14);
    --hn-shadow: 0 10px 26px rgba(0,0,0,0.42);
    --hn-muted: rgba(255,255,255,0.70);
  }
}

/* Center the whole page content */
.hn-wrap{
  max-width: var(--hn-maxw);
  margin: 0 auto;
  padding: 18px 16px 34px 16px;
}

/* Header typography */
.hn-h1{
  font-size: 1.75rem;
  line-height: 1.18;
  margin: 0 0 8px 0;
  letter-spacing: -0.015em;
}
.hn-subtitle{
  margin: 0 0 18px 0;
  color: var(--hn-muted);
  font-size: 1.02rem;
}
.hn-subtitle a{
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 3px;
}

/* List spacing */
.hn-list{ display: flex; flex-direction: column; gap: 14px; margin-top: 16px; }

/* Card */
.hn-card{
  border: 1px solid var(--hn-border);
  border-radius: var(--hn-radius);
  box-shadow: var(--hn-shadow);
  background: rgba(255,255,255,0.92);
  overflow: hidden;
}
@media (prefers-color-scheme: dark){
  .hn-card{ background: rgba(20,20,20,0.55); }
}

/* Card body */
.hn-body{ padding: 14px 16px 16px 16px; }

/* Title row */
.hn-title{
  font-size: 1.06rem;          /* slightly smaller than before */
  line-height: 1.25;
  font-weight: 750;
  margin: 0 0 6px 0;
}
.hn-title a{
  text-decoration: none;
}
.hn-title a:hover{
  text-decoration: underline;
  text-underline-offset: 3px;
}

/* Meta row */
.hn-meta{
  margin: 0 0 10px 0;
  color: var(--hn-muted);
  font-size: 0.98rem;          /* larger */
}

/* Image: consistent cover */
.hn-img{
  width: 100%;
  height: 260px;               /* fixed height */
  object-fit: cover;           /* crop to look modern */
  display: block;
  background: rgba(0,0,0,0.04);
}
@media (max-width: 520px){
  .hn-img{ height: 210px; }
}

/* Text blocks */
.hn-text-en{
  margin: 10px 0 8px 0;
  font-size: 1.05rem;          /* bigger body text */
  line-height: 1.55;
}
.hn-text-zh{
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.55;
  color: var(--hn-muted);
}

/* Make paragraphs not too wide for readability */
.hn-text-en, .hn-text-zh { max-width: 76ch; }
""".strip())
    lines.append("</style>")
    lines.append("")

    # Header
    lines.append("<div class='hn-wrap'>")
    lines.append(f"<h1 class='hn-h1'>{page_title}</h1>")
    # subtitle includes source link
    # page_subtitle already includes scrape time; we append source link
    source_link = "<a href='https://news.ycombinator.com/' target='_blank' rel='noopener noreferrer'>news.ycombinator.com</a>"
    subtitle = page_subtitle.strip()
    if subtitle:
        subtitle = f"{subtitle} · Source: {source_link}"
    else:
        subtitle = f"Source: {source_link}"
    lines.append(f"<p class='hn-subtitle'>{subtitle}</p>")

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
            lines.append(f"<img class='hn-img' src='{image_url}' alt='preview image' loading='lazy'/>")

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
