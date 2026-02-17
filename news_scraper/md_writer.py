from typing import List, Dict, Optional

def render_markdown(
    items: List[Dict],
    page_title: str,
    page_subtitle: str = "",
    html_title: Optional[str] = None,
) -> str:
    """
    Improvements:
    1) Click image to open original (no local hosting, no extra tokens)
    2) More spacing between news cards
    3) Bigger story title size
    4) Page <title> simplified via front matter title (we pass filename-like title)
    """
    if html_title:
        fm_title = html_title
    else:
        fm_title = page_title

    lines = []
    lines.append("---")
    lines.append("layout: default")
    lines.append(f'title: "{fm_title}"')
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

.hn-wrap{
  max-width: var(--hn-maxw);
  margin: 0 auto;
  padding: 18px 16px 34px 16px;
}

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

/* More space between cards */
.hn-list{
  display: flex;
  flex-direction: column;
  gap: 22px;               /* ✅ more vertical whitespace */
  margin-top: 18px;
}

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

.hn-body{ padding: 14px 16px 18px 16px; }

/* Bigger story title */
.hn-title{
  font-size: 1.18rem;       /* ✅ larger than before */
  line-height: 1.25;
  font-weight: 780;
  margin: 0 0 8px 0;
}
.hn-title a{ text-decoration: none; }
.hn-title a:hover{ text-decoration: underline; text-underline-offset: 3px; }

.hn-meta{
  margin: 0 0 12px 0;
  color: var(--hn-muted);
  font-size: 0.98rem;
}

/* Image cover (cropped) but clickable to open full original */
.hn-img{
  width: 100%;
  height: 260px;
  object-fit: cover;
  display: block;
  background: rgba(0,0,0,0.04);
}
@media (max-width: 520px){
  .hn-img{ height: 210px; }
}

/* Subtle hint under image */
.hn-img-hint{
  margin: 8px 16px 0 16px;
  color: var(--hn-muted);
  font-size: 0.93rem;
}

/* Text blocks */
.hn-text-en{
  margin: 10px 0 10px 0;
  font-size: 1.12rem;
  line-height: 1.6;
  max-width: 76ch;
}
.hn-text-zh{
  margin: 0;
  font-size: 1.12rem;
  line-height: 1.6;
  color: var(--hn-muted);
  max-width: 76ch;
}
""".strip())
    lines.append("</style>")
    lines.append("")

    lines.append("<div class='hn-wrap'>")
    lines.append(f"<h1 class='hn-h1'>{page_title}</h1>")

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
            # ✅ Click to open full image in new tab (no hosting needed)
            lines.append(f"<a href='{image_url}' target='_blank' rel='noopener noreferrer'>")
            lines.append(f"<img class='hn-img' src='{image_url}' alt='preview image' loading='lazy'/>")
            lines.append("</a>")
            lines.append("<div class='hn-img-hint'>Click image to view full size</div>")

        lines.append("<div class='hn-body'>")
        lines.append(
            f"<p class='hn-title'>({i}) <a href='{url}' target='_blank' rel='noopener noreferrer'>{title_en}</a></p>"
        )
        lines.append(f"<p class='hn-meta'>{title_zh} &nbsp;|&nbsp; {scrape_time}</p>")
        lines.append(f"<p class='hn-text-en'>{summary_en}</p>")
        lines.append(f"<p class='hn-text-zh'>{summary_zh}</p>")
        lines.append("</div>")

        lines.append("</div>")

    lines.append("</div>")
    lines.append("</div>")
    lines.append("")

    return "\n".join(lines)
