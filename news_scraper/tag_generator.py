"""
Tag generator: uses GPT to assign category tags to each HN story item.

Predefined tag categories (kept small and common for consistency):
  AI, Programming, Security, Science, Business, Finance,
  Hardware, Open Source, Design, Web, DevOps, Data,
  Gaming, Entertainment, Politics, Health, Education, Career,
  Privacy, Legal, Culture, Space, Energy, Startups, Show HN

Usage:
  python news_scraper/tag_generator.py            # tag all JSON files
  python news_scraper/tag_generator.py <path.json> # tag one file
"""

import glob
import json
import os
import sys
from typing import Any, Dict, List

from openai import OpenAI

ALLOWED_TAGS = [
    "AI", "Programming", "Security", "Science", "Business", "Finance",
    "Hardware", "Open Source", "Design", "Web", "DevOps", "Data",
    "Gaming", "Entertainment", "Politics", "Health", "Education", "Career",
    "Privacy", "Legal", "Culture", "Space", "Energy", "Startups", "Show HN",
]

TAG_SET = set(t.lower() for t in ALLOWED_TAGS)
TAG_CANONICAL = {t.lower(): t for t in ALLOWED_TAGS}


def _safe_json_loads(text: str) -> Any:
    s = text.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    idxs = [i for i in [s.find("["), s.find("{")] if i != -1]
    if not idxs:
        raise RuntimeError(f"LLM output is not JSON: {s[:300]}")
    s2 = s[min(idxs):]
    return json.loads(s2)


def generate_tags_for_items(
    items: List[Dict],
    model: str = "gpt-4.1-nano",
) -> Dict[int, List[str]]:
    """
    Given a list of items (each with title_en, url, summary_en, and an index),
    returns a dict mapping item index -> list of tag strings.
    """
    client = OpenAI()

    input_payload = []
    for idx, it in enumerate(items):
        input_payload.append({
            "idx": idx,
            "title_en": it.get("title_en", ""),
            "url": it.get("url", ""),
            "summary_en": it.get("summary_en", ""),
        })

    allowed_str = ", ".join(ALLOWED_TAGS)

    prompt = f"""You are a news classifier. For each Hacker News story below, assign 1-3 tags from this EXACT list:
{allowed_str}

Rules:
- Use ONLY tags from the list above (case-sensitive, exact match).
- Assign 1-3 tags per story. Prefer fewer, more relevant tags.
- If a story is about a new AI model or AI tool, use "AI".
- If a story is about coding, languages, or developer tools, use "Programming".
- "Show HN" tag is ONLY for stories whose title starts with "Show HN:".

Return STRICT JSON array. Each element:
{{"idx": <same idx>, "tags": ["Tag1", "Tag2"]}}

Input:
{json.dumps(input_payload, ensure_ascii=False)}
"""

    resp = client.responses.create(
        model=model,
        input=prompt,
    )

    text = resp.output_text.strip()
    data = _safe_json_loads(text)

    if not isinstance(data, list):
        raise RuntimeError(f"Expected JSON array, got: {type(data)}")

    result: Dict[int, List[str]] = {}
    for obj in data:
        if not isinstance(obj, dict) or "idx" not in obj:
            continue
        idx = int(obj["idx"])
        raw_tags = obj.get("tags", [])
        if not isinstance(raw_tags, list):
            continue
        # Normalize and filter to allowed tags
        clean_tags = []
        for t in raw_tags:
            t_lower = str(t).strip().lower()
            if t_lower in TAG_SET:
                clean_tags.append(TAG_CANONICAL[t_lower])
        if not clean_tags:
            clean_tags = ["Programming"]  # safe fallback
        result[idx] = clean_tags[:3]

    return result


def tag_json_file(json_path: str, model: str = "gpt-4.1-nano") -> bool:
    """
    Read a backup JSON, generate tags for all items, write tags back.
    Returns True if tags were added/updated.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    if not items:
        print(f"  [SKIP] No items in {json_path}")
        return False

    # Check if already tagged
    already_tagged = all("tags" in it for it in items)
    if already_tagged:
        print(f"  [SKIP] Already tagged: {json_path}")
        return False

    print(f"  [TAG] Generating tags for {len(items)} items in {json_path} ...")
    tag_map = generate_tags_for_items(items, model=model)

    for idx, it in enumerate(items):
        tags = tag_map.get(idx, ["Programming"])
        it["tags"] = tags

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [DONE] Tagged {len(items)} items in {json_path}")
    return True


def tag_all_json_files(base_dir: str = "hackernews", model: str = "gpt-4.1-nano"):
    """Tag all JSON backup files under base_dir."""
    pattern = os.path.join(base_dir, "*", "*", "*", "best_stories_*.json")
    json_paths = sorted(glob.glob(pattern))

    if not json_paths:
        print(f"[TAG] No JSON files found under {pattern}")
        return

    print(f"[TAG] Found {len(json_paths)} JSON files. Processing...")
    for jp in json_paths:
        try:
            tag_json_file(jp, model=model)
        except Exception as e:
            print(f"  [ERROR] Failed for {jp}: {e}")

    print("[TAG] All done.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        tag_json_file(path)
    else:
        tag_all_json_files()
