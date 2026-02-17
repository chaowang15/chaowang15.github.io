import requests
from typing import Any, Dict, List, Optional

HN_BASE = "https://hacker-news.firebaseio.com/v0"

def _get_json(url: str, timeout: int = 20) -> Any:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()

def get_story_ids(kind: str) -> List[int]:
    """
    kind: 'best' | 'new' | 'top'
    """
    mapping = {
        "best": f"{HN_BASE}/beststories.json",
        "new":  f"{HN_BASE}/newstories.json",
        "top":  f"{HN_BASE}/topstories.json",
    }
    if kind not in mapping:
        raise ValueError(f"Unknown kind={kind}, must be one of {list(mapping.keys())}")
    return _get_json(mapping[kind])

def get_item(item_id: int) -> Optional[Dict[str, Any]]:
    url = f"{HN_BASE}/item/{item_id}.json"
    return _get_json(url)

def get_item_url(item: Dict[str, Any]) -> str:
    # Ask HN / Show HN 可能没有 url
    if item.get("url"):
        return item["url"]
    return f"https://news.ycombinator.com/item?id={item.get('id')}"
