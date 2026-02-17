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

    # Google Fonts + global CSS/JS (same as daily pages)
    lines.append("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;650;750;800&family=Source+Serif+4:opsz,wght@8..60,450;8..60,600&display=swap" rel="stylesheet">

<link rel="stylesheet" href="/assets/hn/hn.css">
<script src="/assets/hn/hn.js" defer></script>
""".strip())
    lines.append("")

    lines.append("<div class='hn-wrap'>")
    lines.append("<h1 class='hn-h1'>Hacker News (Daily)</h1>")
    source_link = "<a href='https://news.ycombinator.com/' target='_blank' rel='noopener noreferrer'>news.ycombinator.com</a>"
    lines.append(f"<p class='hn-subtitle'>Daily scraped <b>Hacker News — Best Stories</b>. · Source: {source_link}</p>")

    # badges (home)
    lines.append("<div class='hn-badges'>")
    lines.append("<span class='hn-badge'>Best Stories</span>")
    lines.append("<span class='hn-badge'>Daily</span>")
    lines.append("<span class='hn-badge'>PST/PDT</span>")
    lines.append("</div>")

    lines.append("<hr class='hn-rule'/>")

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
    lines.append("")

    md = "\n".join(lines)
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md
