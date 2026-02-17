import json
from typing import Dict, List, Any
from openai import OpenAI

def _safe_json_loads(text: str) -> Any:
    s = text.strip()
    try:
        return json.loads(s)
    except Exception:
        pass

    # Try to locate the first JSON token
    idxs = [i for i in [s.find("["), s.find("{")] if i != -1]
    if not idxs:
        raise RuntimeError(f"LLM output is not JSON: {s[:300]}")
    s2 = s[min(idxs):]
    return json.loads(s2)

def llm_enrich_batch(
    items: List[Dict[str, str]],
    model: str = "gpt-5-mini",
) -> Dict[int, Dict[str, str]]:
    """
    items: [{"id": int, "title_en": str, "url": str}]
    return: id -> {"title_zh", "summary_en", "summary_zh"}
    """
    client = OpenAI()

    input_payload = [
        {"id": int(it["id"]), "title_en": it["title_en"], "url": it["url"]}
        for it in items
    ]

    prompt = f"""
You generate bilingual news snippets for Hacker News items.

For each item, produce:
- title_zh: Chinese translation of title_en (natural, concise)
- summary_en: 3-5 sentences brief intro in English (factual, neutral). Use only the title and URL context. Do NOT invent specific claims.
- summary_zh: Chinese translation of summary_en (natural)

Return STRICT JSON as an array. Each element must be:
{{
  "id": <same id>,
  "title_zh": "...",
  "summary_en": "...",
  "summary_zh": "..."
}}

Input items JSON:
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

    out: Dict[int, Dict[str, str]] = {}
    for obj in data:
        if not isinstance(obj, dict) or "id" not in obj:
            continue
        _id = int(obj["id"])
        for k in ["title_zh", "summary_en", "summary_zh"]:
            if k not in obj or not isinstance(obj[k], str):
                raise RuntimeError(f"Missing/invalid key {k} for id={_id}")
        out[_id] = {
            "title_zh": obj["title_zh"].strip(),
            "summary_en": obj["summary_en"].strip(),
            "summary_zh": obj["summary_zh"].strip(),
        }

    missing = [int(it["id"]) for it in items if int(it["id"]) not in out]
    if missing:
        raise RuntimeError(f"LLM batch missing ids: {missing[:10]} (total {len(missing)})")

    return out
