"""
Tag generator: uses GPT to assign category tags to each HN story item,
then supplements with keyword-based detection from title and summary text.

Predefined tag categories (kept small and common for consistency):
  AI, Programming, Security, Science, Business, Finance,
  Hardware, Open Source, Design, Web, DevOps, Data,
  Gaming, Entertainment, Politics, Health, Education, Career,
  Privacy, Legal, Culture, Space, Energy, Startups, Show HN

Usage:
  python news_scraper/tag_generator.py                  # tag all JSON files (skip already tagged)
  python news_scraper/tag_generator.py --force           # force re-tag all JSON files
  python news_scraper/tag_generator.py <path.json>       # tag one file
  python news_scraper/tag_generator.py --force <path.json>  # force re-tag one file
"""

import glob
import json
import os
import re
import sys
from typing import Any, Dict, List, Set

from openai import OpenAI

ALLOWED_TAGS = [
    "AI", "Programming", "Security", "Science", "Business", "Finance",
    "Hardware", "Open Source", "Design", "Web", "DevOps", "Data",
    "Gaming", "Entertainment", "Politics", "Health", "Education", "Career",
    "Privacy", "Legal", "Culture", "Space", "Energy", "Startups", "Show HN",
]

TAG_SET = set(t.lower() for t in ALLOWED_TAGS)
TAG_CANONICAL = {t.lower(): t for t in ALLOWED_TAGS}

# ---------------------------------------------------------------------------
# Keyword-based tag supplement rules
# ---------------------------------------------------------------------------
# Each entry maps a canonical tag to a list of regex patterns.
# Patterns are matched case-insensitively against title_en + summary_en.
# If ANY pattern matches and the tag is not already present, the tag is added.
# ---------------------------------------------------------------------------
KEYWORD_RULES: Dict[str, List[str]] = {
    "AI": [
        r"\bAI\b",
        r"\bartificial intelligence\b",
        r"\bLLM\b",
        r"\blarge language model\b",
        r"\bGPT\b",
        r"\bChatGPT\b",
        r"\bOpenAI\b",
        r"\bClaude\b",
        r"\bAnthropic\b",
        r"\bGemini\b",
        r"\bdeep\s?learning\b",
        r"\bmachine learning\b",
        r"\bneural net\b",
        r"\btransformer model\b",
        r"\bdiffusion model\b",
        r"\bStable Diffusion\b",
        r"\bMidjourney\b",
        r"\bcopilot\b",
    ],
    "Programming": [
        r"\bRust\b",
        r"\bPython\b",
        r"\bJavaScript\b",
        r"\bTypeScript\b",
        r"\bGo(?:lang)?\b",
        r"\bC\+\+\b",
        r"\bcompiler\b",
        r"\binterpreter\b",
        r"\bprogramming language\b",
        r"\bgit\b",
        r"\bGitHub\b",
        r"\bcode review\b",
        r"\brefactor\b",
        r"\bIDE\b",
        r"\bdebug\b",
    ],
    "Security": [
        r"\bsecurity\b",
        r"\bvulnerabilit\w*\b",
        r"\bexploit\b",
        r"\bcyber\s?attack\b",
        r"\bransomware\b",
        r"\bmalware\b",
        r"\bphishing\b",
        r"\bencryption\b",
        r"\bzero[- ]day\b",
        r"\bCVE\b",
    ],
    "Privacy": [
        r"\bprivacy\b",
        r"\bsurveillance\b",
        r"\btracking\b",
        r"\bGDPR\b",
        r"\bdata breach\b",
    ],
    "Open Source": [
        r"\bopen[- ]source\b",
        r"\bFOSS\b",
        r"\bGPL\b",
        r"\bMIT license\b",
        r"\bApache license\b",
    ],
    "Science": [
        r"\bscientific\b",
        r"\bphysics\b",
        r"\bbiology\b",
        r"\bchemistry\b",
        r"\bneuroscience\b",
        r"\bquantum\b",
        r"\bresearch paper\b",
        r"\bpeer[- ]review\b",
    ],
    "Space": [
        r"\bNASA\b",
        r"\bSpaceX\b",
        r"\bspace\s?station\b",
        r"\basteroid\b",
        r"\brocket\b",
        r"\borbit\b",
        r"\btelescope\b",
        r"\bmars\b",
        r"\bmoon landing\b",
    ],
    "Health": [
        r"\bhealth\b",
        r"\bmedical\b",
        r"\bvaccine\b",
        r"\bcancer\b",
        r"\bCOVID\b",
        r"\bpandemic\b",
        r"\bFDA\b",
        r"\bclinical trial\b",
    ],
    "Finance": [
        r"\bfinance\b",
        r"\bstock market\b",
        r"\bcryptocurrency\b",
        r"\bbitcoin\b",
        r"\bethereum\b",
        r"\bblockchain\b",
        r"\bIPO\b",
        r"\bventure capital\b",
    ],
    "Hardware": [
        r"\bhardware\b",
        r"\bchip\b",
        r"\bsemiconductor\b",
        r"\bCPU\b",
        r"\bGPU\b",
        r"\bFPGA\b",
        r"\bRISC-V\b",
        r"\bArduino\b",
        r"\bRaspberry Pi\b",
    ],
    "DevOps": [
        r"\bDevOps\b",
        r"\bKubernetes\b",
        r"\bDocker\b",
        r"\bCI/CD\b",
        r"\binfrastructure\b",
        r"\bterraform\b",
    ],
    "Web": [
        r"\bweb\s?app\b",
        r"\bfrontend\b",
        r"\bbackend\b",
        r"\bReact\b",
        r"\bVue\b",
        r"\bCSS\b",
        r"\bHTML\b",
        r"\bbrowser\b",
    ],
    "Data": [
        r"\bdata\s?base\b",
        r"\bSQL\b",
        r"\bPostgreSQL\b",
        r"\bdata\s?set\b",
        r"\bdata engineer\b",
        r"\bdata science\b",
        r"\banalytics\b",
    ],
    "Gaming": [
        r"\bgaming\b",
        r"\bvideo game\b",
        r"\bgame engine\b",
        r"\bUnity\b",
        r"\bUnreal Engine\b",
        r"\bNintendo\b",
        r"\bPlayStation\b",
        r"\bXbox\b",
    ],
    "Education": [
        r"\beducation\b",
        r"\buniversity\b",
        r"\bstudent\b",
        r"\bcourse\b",
        r"\btutorial\b",
        r"\blearning platform\b",
    ],
    "Energy": [
        r"\benergy\b",
        r"\bsolar\b",
        r"\bnuclear\b",
        r"\bbattery\b",
        r"\brenewable\b",
        r"\belectric vehicle\b",
        r"\bEV\b",
    ],
    "Startups": [
        r"\bstartup\b",
        r"\bY Combinator\b",
        r"\bYC\b",
        r"\bseed round\b",
        r"\bSeries [A-D]\b",
    ],
    "Show HN": [
        r"^Show HN:",
    ],
    "Politics": [
        r"\bpolitics\b",
        r"\bCongress\b",
        r"\bSenate\b",
        r"\bWhite House\b",
        r"\blegislat\w*\b",
        r"\belection\b",
        r"\bgovernment\b",
        r"\bFCC\b",
        r"\bregulat\w*\b",
    ],
    "Legal": [
        r"\blawsuit\b",
        r"\bcourt\b",
        r"\blegal\b",
        r"\bpatent\b",
        r"\bantitrust\b",
        r"\bcopyright\b",
        r"\bDMCA\b",
    ],
    "Business": [
        r"\bacquisition\b",
        r"\bmerger\b",
        r"\bCEO\b",
        r"\brevenue\b",
        r"\bprofit\b",
        r"\blayoff\b",
    ],
}

# Pre-compile all patterns for performance
_COMPILED_RULES: Dict[str, List[re.Pattern]] = {
    tag: [re.compile(p, re.IGNORECASE) for p in patterns]
    for tag, patterns in KEYWORD_RULES.items()
}


def supplement_tags_by_keywords(item: Dict) -> List[str]:
    """
    Scan title_en and summary_en for keyword patterns.
    Returns a list of additional tags that should be added
    (tags already present in item["tags"] are excluded).
    """
    existing: Set[str] = set(item.get("tags", []))
    text = (item.get("title_en", "") + " " + item.get("summary_en", "")).strip()
    if not text:
        return []

    extra: List[str] = []
    for tag, patterns in _COMPILED_RULES.items():
        if tag in existing:
            continue
        for pat in patterns:
            if pat.search(text):
                extra.append(tag)
                break

    return extra


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


def tag_json_file(json_path: str, model: str = "gpt-4.1-nano", force: bool = False) -> bool:
    """
    Read a backup JSON, generate tags for all items via GPT,
    then supplement with keyword-based detection, and write back.
    Returns True if tags were added/updated.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    if not items:
        print(f"  [SKIP] No items in {json_path}")
        return False

    already_tagged = all("tags" in it for it in items)

    if already_tagged and not force:
        # Even if already tagged, run keyword supplement pass
        supplemented = 0
        for it in items:
            extra = supplement_tags_by_keywords(it)
            if extra:
                merged = list(dict.fromkeys(it["tags"] + extra))  # preserve order, deduplicate
                it["tags"] = merged
                supplemented += 1

        if supplemented > 0:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  [SUPPLEMENT] Added keyword-based tags to {supplemented} items in {json_path}")
            return True

        print(f"  [SKIP] Already tagged (no new keywords): {json_path}")
        return False

    # GPT tagging (either first time or forced re-tag)
    print(f"  [TAG] Generating tags for {len(items)} items in {json_path} ...")
    tag_map = generate_tags_for_items(items, model=model)

    for idx, it in enumerate(items):
        gpt_tags = tag_map.get(idx, ["Programming"])
        it["tags"] = gpt_tags

    # Keyword supplement pass: add any tags that GPT missed
    supplemented = 0
    for it in items:
        extra = supplement_tags_by_keywords(it)
        if extra:
            merged = list(dict.fromkeys(it["tags"] + extra))  # preserve order, deduplicate
            it["tags"] = merged
            supplemented += 1

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [DONE] Tagged {len(items)} items ({supplemented} supplemented by keywords) in {json_path}")
    return True


def tag_all_json_files(base_dir: str = "hackernews", model: str = "gpt-4.1-nano", force: bool = False):
    """Tag all JSON backup files under base_dir."""
    pattern = os.path.join(base_dir, "*", "*", "*", "best_stories_*.json")
    json_paths = sorted(glob.glob(pattern))

    if not json_paths:
        print(f"[TAG] No JSON files found under {pattern}")
        return

    print(f"[TAG] Found {len(json_paths)} JSON files. Processing (force={force})...")
    for jp in json_paths:
        try:
            tag_json_file(jp, model=model, force=force)
        except Exception as e:
            print(f"  [ERROR] Failed for {jp}: {e}")

    print("[TAG] All done.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--force"]

    if args:
        path = args[0]
        tag_json_file(path, force=force)
    else:
        tag_all_json_files(force=force)
