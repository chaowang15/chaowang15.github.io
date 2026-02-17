from typing import List, Dict, Optional

def render_markdown(items: List[Dict]) -> str:
    lines = []
    for i, it in enumerate(items, start=1):
        title_en: str = it["title_en"]
        url: str = it["url"]
        title_zh: str = it["title_zh"]
        scrape_time: str = it["scrape_time"]
        summary_en: str = it["summary_en"]
        summary_zh: str = it["summary_zh"]
        image_url: Optional[str] = it.get("image_url")

        lines.append(f"({i}) [**{title_en}**]({url})")
        lines.append(f"> {title_zh} | {scrape_time}")
        if image_url:
            lines.append(f"![]({image_url})")
        lines.append(f"- {summary_en}")
        lines.append(f"- {summary_zh}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
