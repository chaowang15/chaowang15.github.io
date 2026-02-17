import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

BEST_RE = re.compile(r"^best_stories_(\d{8})\.md$")  # MMDDYYYY

@dataclass
class Entry:
    abs_path: str
    rel_url: str
    date_dir: str
    mmddyyyy: str
    dt: datetime

def _try_parse_dt(date_dir: str, mmddyyyy: str) -> Optional[datetime]:
    try:
        y, m, d = date_dir.split("/")
        return datetime(int(y), int(m), int(d))
    except Exception:
        pass
    try:
        return datetime.strptime(mmddyyyy, "%m%d%Y")
    except Exception:
        return None

def _collect_best_entries(base_dir: str) -> List[Entry]:
    entries: List[Entry] = []
    if not os.path.isdir(base_dir):
        return entries

    for root, _, files in os.walk(base_dir):
        for fn in files:
            m = BEST_RE.match(fn)
            if not m:
                continue
            mmddyyyy = m.group(1)
            abs_path = os.path.join(root, fn)
            rel_dir = os.path.relpath(root, base_dir).replace("\\", "/")
            if rel_dir.startswith("."):
                continue
            dt = _try_parse_dt(rel_dir, mmddyyyy)
            if dt is None:
                continue
            rel_url = f"/{base_dir}/{rel_dir}/{fn[:-3]}".replace("//", "/")
            entries.append(Entry(abs_path=abs_path, rel_url=rel_url, date_dir=rel_dir, mmddyyyy=mmddyyyy, dt=dt))

    entries.sort(key=lambda e: (e.dt, e.abs_path), reverse=True)
    return entries

def update_hackernews_index(
    base_dir: str = "hackernews",
    index_path: str = "hackernews/index.md",
    max_items: int = 30,
) -> str:
    entries = _collect_best_entries(base_dir)[:max_items]

    lines = []
    lines.append("---")
    lines.append("layout: default")
    lines.append('title: "Hacker News (Daily)"')
    lines.append("---")
    lines.append("")

    # Google Fonts (same as daily pages)
    lines.append("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;650;750;800&family=Source+Serif+4:opsz,wght@8..60,450;8..60,600&display=swap" rel="stylesheet">
""".strip())
    lines.append("")

    lines.append("<style>")
    lines.append("""
:root{
  --hn-maxw: 920px;
  --hn-radius: 16px;
  --hn-border: rgba(0,0,0,0.10);
  --hn-shadow: 0 10px 26px rgba(0,0,0,0.08);
  --hn-muted: rgba(0,0,0,0.62);
  --hn-fg: rgba(0,0,0,0.92);
  --hn-card-bg: rgba(255,255,255,0.92);

  --hn-sans: "Inter", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
  --hn-serif: "Source Serif 4", ui-serif, Georgia, Cambria, "Times New Roman", Times, serif;
}
@media (prefers-color-scheme: dark) {
  :root{
    --hn-border: rgba(255,255,255,0.14);
    --hn-shadow: 0 10px 26px rgba(0,0,0,0.42);
    --hn-muted: rgba(255,255,255,0.74);
    --hn-fg: rgba(255,255,255,0.92);
    --hn-card-bg: rgba(20,20,20,0.60);
  }
}

.hn-wrap{
  max-width: var(--hn-maxw);
  margin: 0 auto;
  padding: 18px 16px 34px 16px;
  color: var(--hn-fg);
  font-family: var(--hn-serif);
  font-size: 18px;                 /* ✅ bigger overall */
}

.hn-h1{
  font-family: var(--hn-sans);
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
.hn-rule{
  height: 1px;
  border: 0;
  background: var(--hn-border);
  margin: 14px 0 6px 0;
}

.hn-subtitle a{
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.hn-grid{ display: flex; flex-direction: column; gap: 14px; margin-top: 16px; }

.hn-row{
  padding: 14px 16px;
  border: 1px solid var(--hn-border);
  border-radius: var(--hn-radius);
  box-shadow: var(--hn-shadow);
  background: var(--hn-card-bg);
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 14px;
}
.hn-row{
  transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
}
.hn-row:hover{
  transform: translateY(-2px);
  box-shadow: 0 14px 34px rgba(0,0,0,0.12);
}
@media (prefers-color-scheme: dark){
  .hn-row:hover{
    box-shadow: 0 14px 34px rgba(0,0,0,0.55);
  }
}


.hn-date{
  font-family: var(--hn-sans);
  font-weight: 750;
}
.hn-link a{
  font-family: var(--hn-sans);
  font-weight: 750;
  text-decoration: none;
}
.hn-link a:hover{
  text-decoration: underline;
  text-underline-offset: 3px;
}

.hn-hint{ margin-top: 16px; color: var(--hn-muted); font-size: 0.98rem; }
""".strip())
    lines.append("</style>")
    lines.append("")

    lines.append("<div class='hn-wrap'>")
    lines.append("<h1 class='hn-h1'>Hacker News (Daily)</h1>")
    source_link = "<a href='https://news.ycombinator.com/' target='_blank' rel='noopener noreferrer'>news.ycombinator.com</a>"
    lines.append(f"<p class='hn-subtitle'>Daily scraped <b>Hacker News — Best Stories</b>. · Source: {source_link}</p>")
    lines.append("<hr class='hn-rule'/>")
    lines.append("")

    lines.append("<h2 style='font-family: var(--hn-sans); margin-top: 6px;'>Latest Files</h2>")
    if not entries:
        lines.append("<p class='hn-hint'>No files found yet. Run the workflow once to generate the first file.</p>")
    else:
        lines.append("<div class='hn-grid'>")
        for e in entries:
            label = e.dt.strftime("%Y-%m-%d")
            lines.append(
                f"<div class='hn-row'>"
                f"<div class='hn-date'>{label}</div>"
                f"<div class='hn-link'><a href='{e.rel_url}'>Best Stories</a></div>"
                f"</div>"
            )
        lines.append("</div>")

    lines.append("")
    lines.append(f"<p class='hn-hint'>Browse by date: <code>/{base_dir}/YYYY/MM/DD/</code></p>")
    lines.append("</div>")

    md = "\n".join(lines)
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md
