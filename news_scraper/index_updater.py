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
    lines.append("# Hacker News (Daily)")
    lines.append("")
    lines.append("<p class='hn-subtitle'>Daily scraped <b>Hacker News — Best Stories</b>.</p>")
    lines.append("")
    lines.append("<style>")
    lines.append("""
.hn-subtitle { margin-top: -8px; opacity: 0.85; }
.hn-grid { display: flex; flex-direction: column; gap: 12px; margin-top: 18px; }
.hn-row{
  padding: 14px 16px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 14px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.06);
  background: rgba(255,255,255,0.90);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
}
@media (prefers-color-scheme: dark) {
  .hn-row{
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(20,20,20,0.55);
    box-shadow: 0 6px 18px rgba(0,0,0,0.35);
  }
}
.hn-date { font-weight: 700; }
.hn-link a { font-weight: 700; text-decoration: none; }
.hn-link a:hover { text-decoration: underline; }
.hn-hint { margin-top: 16px; opacity: 0.8; font-size: 0.95rem; }
""".strip())
    lines.append("</style>")
    lines.append("")
    lines.append("## Latest Files")
    lines.append("")
    if not entries:
        lines.append("_No files found yet. Run the workflow once to generate the first file._")
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
    lines.append("## Browse by date")
    lines.append("")
    lines.append(f"- Folder pattern: `/{base_dir}/YYYY/MM/DD/`")
    lines.append("")
    lines.append("<p class='hn-hint'>Tip: GitHub Pages may take a minute to reflect a fresh workflow run.</p>")
    lines.append("")

    md = "\n".join(lines)
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md
