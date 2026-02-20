# Hacker News API: Best vs Top vs New Stories Research

## API Endpoints

| Endpoint | URL | Max Items | Description |
|---|---|---|---|
| Top Stories | `/v0/topstories.json` | 500 | Current front page stories + jobs, ranked by HN's ranking algorithm |
| Best Stories | `/v0/beststories.json` | 200 | High-quality stories over a longer time window, ranked by score |
| New Stories | `/v0/newstories.json` | 500 | Most recently submitted stories |

## Key Findings

### Best Stories (`/v0/beststories`)
- Returns up to **200** story IDs
- Ranked primarily by **score** (upvotes)
- Contains stories from a **longer time window** (days to weeks)
- Top stories have ages ranging from 6h to 46h+ in our sample
- Very high scores (500-1000+) dominate the top positions
- **Slow turnover**: 50% overlap between consecutive days (02/17 vs 02/18)
- Essentially a "hall of fame" of recent high-quality stories

### Top Stories (`/v0/topstories`)
- Returns up to **500** story IDs
- Ranked by HN's **ranking algorithm**: `score / (age + 2)^gravity`
- Represents the **current front page** (what you see at news.ycombinator.com)
- Stories are much more **time-sensitive** - heavily penalizes older stories
- Top stories ages: 2.7h to 12h (much fresher than best stories)
- **Fast turnover**: changes significantly every few hours
- Also contains job postings

### New Stories (`/v0/newstories`)
- Returns up to **500** story IDs
- Simply the **most recently submitted** stories, no quality filter
- Very high noise - most stories have very low scores

## Actual Data Comparison (Feb 19, 2026)

- Top 50 vs Best 50 overlap: only **15/50 (30%)**
- Top 200 vs Best 200 overlap: **111/200 (55%)**
- Full top 500 vs best 200 overlap: **166/200 (83%)**

## Day-to-Day Overlap in Existing Data

- 02/17 best vs 02/18 best: **25/50 (50%)** overlap - confirms the user's observation

## Conclusion

**Best stories** is a slow-moving "best of" list that accumulates high-scoring stories over days/weeks.
**Top stories** is the live front page that changes rapidly based on recency + score.

For a "daily news digest" use case, **top stories** is the better choice because:
1. It changes much more frequently (hourly vs days)
2. It emphasizes recency through the time-decay algorithm
3. Day-to-day overlap should be much lower than best stories

However, even top stories can have some overlap. A deduplication mechanism would further improve freshness.
