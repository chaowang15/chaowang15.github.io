# Implementation Notes

## Feature 1: Enrich Index Page
- Modify `index_updater.py` `_collect_entries()` to also extract top story title from JSON
- Modify `Entry` dataclass to include `top_title: Optional[str]`
- Modify `update_hackernews_index()` to render count + top title in each row
- Each JSON has: `meta.count_written` and `items[0].title_en`
- CSS classes: `.hn-row`, `.hn-date`, `.hn-link`, `.hn-index-line`, `.hn-index-meta`
- `.hn-index-meta` already has ellipsis overflow handling!
- Mobile: keep compact, use ellipsis for long titles

## Feature 2: Tag System
- Use GPT to classify each story from existing JSONs
- Add `tags` field to each item in JSON
- Tags: predefined common categories (AI, Programming, Security, Science, Business, etc.)
- Render as badges below meta2 line (before image)
- Store in JSON for future filtering
- CSS: pill-shaped badges, similar to existing `.hn-badge` but smaller/colored
- Need to add `data-tags` attribute on cards for future JS filtering

## Files to modify:
1. `news_scraper/index_updater.py` - enrich index
2. `assets/hn/hn.css` - index row styling + tag badges
3. `news_scraper/md_writer.py` - render tags
4. `news_scraper/main.py` - integrate tag generation in pipeline
5. All 3 JSON files - add tags
6. All 3 MD files - rebuild with tags
7. `hackernews/index.md` - rebuild enriched
