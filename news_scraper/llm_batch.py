import json
from typing import Dict, List, Any
from openai import OpenAI

def _safe_json_loads(text: str) -> Any:
    """Parse JSON from LLM output, handling common issues like
    markdown fences, extra trailing data, and concatenated objects."""
    s = text.strip()

    # Strip markdown code fences if present
    if s.startswith("```"):
        lines = s.split("\n")
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        s = "\n".join(lines).strip()

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # Locate the first JSON token
    idxs = [i for i in [s.find("["), s.find("{")] if i != -1]
    if not idxs:
        raise RuntimeError(f"LLM output is not JSON: {s[:300]}")
    s2 = s[min(idxs):]

    # Use JSONDecoder to parse only the first valid JSON value
    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(s2)
        return obj
    except json.JSONDecodeError:
        pass

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

    prompt = f"""You are a tech news editor writing brief, insightful summaries for a Hacker News daily digest.

For each item below, produce:
- title_zh: Natural, concise Chinese translation of title_en.
- summary_en: A 2-3 sentence English summary that is informative and engaging. You may use your general knowledge to provide useful context, background, or explain why the story matters. Focus on the key takeaway for a tech-savvy reader.
- summary_zh: A 2-3 sentence Chinese summary covering the same information as summary_en. Write it naturally in Chinese (not a word-for-word translation).

STRICT RULES:
- Do NOT include meta-commentary like "this summary is based on..." or "the linked article discusses...".
- Do NOT restate the title as the summary. Add value beyond what the title already says.
- Do NOT mention the URL, the source website name, or where the link points to.
- Do NOT use filler phrases like "the article explores", "the post highlights", "the piece discusses".
- Start directly with the substance. Be concise and informative.
- If you truly cannot infer anything beyond the title, write one sentence that rephrases the core idea with minimal added context, and stop.

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

    if resp.output is None:
        raise RuntimeError(f"LLM returned None output. Status: {getattr(resp, 'status', 'unknown')}")

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
