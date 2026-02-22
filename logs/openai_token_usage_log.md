# OpenAI API Token Usage Log

This file tracks all OpenAI API calls made by the Hacker News Daily pipeline.
Each entry records the model, token counts, and estimated cost.

**Pricing source:** [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing/)

---

## 2026-02-21

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 22:58:38 | gpt-5-nano | llm_batch | 998 | 0 | 7,342 | 8,340 | $0.002987 | enrich 13 items, attempt 1 |
| 22:59:11 | gpt-5-nano | tag_generator | 2,580 | 0 | 3,966 | 6,546 | $0.001715 | tag 25 items, attempt 1 |
| 22:59:38 | gpt-5-nano | tag_generator | 2,587 | 0 | 4,475 | 7,062 | $0.001919 | tag 25 items, attempt 1 |
| 23:00:02 | gpt-5-nano | tag_generator | 2,495 | 0 | 4,017 | 6,512 | $0.001732 | tag 25 items, attempt 1 |
| 23:00:34 | gpt-5-nano | tag_generator | 2,634 | 0 | 4,036 | 6,670 | $0.001746 | tag 25 items, attempt 1 |
| **TOTAL** | **5 calls** | — | **11,294** | **0** | **23,836** | **35,130** | **$0.010099** | Daily summary |

## 2026-02-22

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 05:00:03 | gpt-5-nano | llm_batch | 1,724 | 0 | 12,452 | 14,176 | $0.005067 | enrich 30 items, attempt 1 |
| 05:00:52 | gpt-5-nano | tag_generator | 2,469 | 0 | 3,260 | 5,729 | $0.001427 | tag 25 items, attempt 1 |
| 05:01:33 | gpt-5-nano | tag_generator | 2,465 | 0 | 4,143 | 6,608 | $0.001780 | tag 25 items, attempt 1 |
| **TOTAL** | **3 calls** | — | **6,658** | **0** | **19,855** | **26,513** | **$0.008274** | Daily summary |

