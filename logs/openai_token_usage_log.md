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
| **Subtotal** | **3 calls** | — | **6,658** | **0** | **19,855** | **26,513** | **$0.008274** | Scrape #1 |

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 06:28:27 | gpt-5-nano | llm_batch | 1,183 | 0 | 9,161 | 10,344 | $0.003724 | enrich 18 items, attempt 1 |
| 06:29:18 | gpt-5-nano | tag_generator | 2,607 | 0 | 4,476 | 7,083 | $0.001921 | tag 25 items, attempt 1 |
| 06:29:50 | gpt-5-nano | tag_generator | 2,351 | 0 | 3,660 | 6,011 | $0.001582 | tag 24 items, attempt 1 |
| **Subtotal** | **3 calls** | — | **6,141** | **0** | **17,297** | **23,438** | **$0.007227** | Scrape #2 |

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 10:32:59 | gpt-5-nano | llm_batch | 1,115 | 0 | 10,707 | 11,822 | $0.004339 | enrich 17 items, attempt 1 |
| 10:34:17 | gpt-5-nano | llm_batch | 1,115 | 0 | 9,467 | 10,582 | $0.003843 | enrich 17 items, attempt 2 |
| 10:35:01 | gpt-5-nano | tag_generator | 2,568 | 0 | 3,472 | 6,040 | $0.001517 | tag 25 items, attempt 1 |
| 10:35:30 | gpt-5-nano | tag_generator | 2,645 | 0 | 3,888 | 6,533 | $0.001687 | tag 25 items, attempt 1 |
| 10:35:53 | gpt-5-nano | tag_generator | 1,779 | 0 | 3,030 | 4,809 | $0.001301 | tag 16 items, attempt 1 |
| **Subtotal** | **5 calls** | — | **9,222** | **0** | **30,564** | **39,786** | **$0.012687** | Scrape #3 |

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 14:15:23 | gpt-5-nano | llm_batch | 1,397 | 0 | 15,101 | 16,498 | $0.006110 | enrich 24 items, attempt 1 |
| 14:15:54 | gpt-5-nano | tag_generator | 2,611 | 0 | 3,713 | 6,324 | $0.001616 | tag 25 items, attempt 1 |
| 14:16:18 | gpt-5-nano | tag_generator | 2,556 | 0 | 4,330 | 6,886 | $0.001860 | tag 25 items, attempt 1 |
| 14:16:40 | gpt-5-nano | tag_generator | 2,530 | 0 | 4,023 | 6,553 | $0.001736 | tag 25 items, attempt 1 |
| 14:16:54 | gpt-5-nano | tag_generator | 1,573 | 0 | 2,635 | 4,208 | $0.001133 | tag 15 items, attempt 1 |
| **Subtotal** | **5 calls** | — | **10,667** | **0** | **29,802** | **40,469** | **$0.012455** | Scrape #4 |

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 20:19:03 | gpt-5-nano | llm_batch | 1,550 | 0 | 11,874 | 13,424 | $0.004827 | enrich 25 items, attempt 1 |
| 20:19:42 | gpt-5-nano | tag_generator | 2,400 | 0 | 3,378 | 5,778 | $0.001471 | tag 25 items, attempt 1 |
| 20:20:11 | gpt-5-nano | tag_generator | 2,498 | 0 | 3,768 | 6,266 | $0.001632 | tag 25 items, attempt 1 |
| 20:20:40 | gpt-5-nano | tag_generator | 2,703 | 0 | 3,243 | 5,946 | $0.001432 | tag 25 items, attempt 1 |
| 20:21:14 | gpt-5-nano | tag_generator | 2,424 | 0 | 4,194 | 6,618 | $0.001799 | tag 25 items, attempt 1 |
| **Subtotal** | **5 calls** | — | **11,575** | **0** | **26,457** | **38,032** | **$0.011161** | Scrape #5 |

| | | | | | | | | |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| **DAILY TOTAL** | **21 calls** | — | **44,263** | **0** | **123,975** | **168,238** | **$0.051804** | 2026-02-22 |

## 2026-02-23

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 05:16:15 | gpt-5-nano | llm_batch | 1,860 | 0 | 14,199 | 16,059 | $0.005773 | enrich 35 items, attempt 1 |
| 05:17:04 | gpt-5-nano | tag_generator | 2,046 | 0 | 4,180 | 6,226 | $0.001774 | tag 25 items, attempt 1 |
| 05:17:39 | gpt-5-nano | tag_generator | 2,103 | 0 | 4,123 | 6,226 | $0.001754 | tag 25 items, attempt 1 |
| **Subtotal** | **3 calls** | — | **6,009** | **0** | **22,502** | **28,511** | **$0.009301** | Scrape batch |

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 06:49:00 | gpt-5-nano | llm_batch | 1,367 | 0 | 11,018 | 12,385 | $0.004476 | enrich 21 items, attempt 1 |
| 06:49:39 | gpt-5-nano | tag_generator | 2,424 | 0 | 3,256 | 5,680 | $0.001424 | tag 25 items, attempt 1 |
| 06:50:13 | gpt-5-nano | tag_generator | 2,372 | 0 | 4,187 | 6,559 | $0.001793 | tag 24 items, attempt 1 |
| **Subtotal** | **3 calls** | — | **6,163** | **0** | **18,461** | **24,624** | **$0.007693** | Scrape batch |

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 11:00:01 | gpt-5-nano | llm_batch | 1,568 | 0 | 10,998 | 12,566 | $0.004478 | enrich 25 items, attempt 1 |
| 11:00:55 | gpt-5-nano | tag_generator | 2,539 | 0 | 3,912 | 6,451 | $0.001692 | tag 25 items, attempt 1 |
| 11:01:32 | gpt-5-nano | tag_generator | 2,373 | 0 | 4,083 | 6,456 | $0.001752 | tag 25 items, attempt 1 |
| 11:02:05 | gpt-5-nano | tag_generator | 2,376 | 0 | 3,789 | 6,165 | $0.001634 | tag 24 items, attempt 1 |
| **Subtotal** | **4 calls** | — | **8,856** | **0** | **22,782** | **31,638** | **$0.009556** | Scrape batch |

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 14:32:27 | gpt-5-nano | llm_batch | 1,375 | 0 | 7,912 | 9,287 | $0.003234 | enrich 20 items, attempt 1 |
| 14:33:02 | gpt-5-nano | tag_generator | 2,625 | 0 | 3,939 | 6,564 | $0.001707 | tag 25 items, attempt 1 |
| 14:33:26 | gpt-5-nano | tag_generator | 2,444 | 0 | 3,416 | 5,860 | $0.001489 | tag 25 items, attempt 1 |
| 14:33:53 | gpt-5-nano | tag_generator | 2,397 | 0 | 3,927 | 6,324 | $0.001691 | tag 25 items, attempt 1 |
| 14:34:25 | gpt-5-nano | tag_generator | 1,773 | 0 | 3,019 | 4,792 | $0.001296 | tag 18 items, attempt 1 |
| **Subtotal** | **5 calls** | — | **10,614** | **0** | **22,213** | **32,827** | **$0.009417** | Scrape batch |

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 20:14:20 | gpt-5-nano | llm_batch | 1,668 | 0 | 11,950 | 13,618 | $0.004863 | enrich 25 items, attempt 1 |
| 20:15:09 | gpt-5-nano | tag_generator | 2,719 | 0 | 4,373 | 7,092 | $0.001885 | tag 25 items, attempt 1 |
| 20:15:43 | gpt-5-nano | tag_generator | 2,569 | 0 | 3,469 | 6,038 | $0.001516 | tag 25 items, attempt 1 |
| 20:16:14 | gpt-5-nano | tag_generator | 2,441 | 0 | 3,626 | 6,067 | $0.001572 | tag 25 items, attempt 1 |
| 20:16:47 | gpt-5-nano | tag_generator | 2,439 | 0 | 3,651 | 6,090 | $0.001582 | tag 25 items, attempt 1 |
| **Subtotal** | **5 calls** | — | **11,836** | **0** | **27,069** | **38,905** | **$0.011418** | Scrape batch |

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 23:10:27 | gpt-5-nano | llm_batch | 770 | 0 | 8,254 | 9,024 | $0.003340 | enrich 9 items, attempt 1 |
| 23:11:13 | gpt-5-nano | tag_generator | 2,719 | 0 | 4,708 | 7,427 | $0.002019 | tag 25 items, attempt 1 |
| 23:11:51 | gpt-5-nano | tag_generator | 2,585 | 0 | 4,135 | 6,720 | $0.001783 | tag 25 items, attempt 1 |
| 23:12:21 | gpt-5-nano | tag_generator | 2,441 | 0 | 3,522 | 5,963 | $0.001531 | tag 25 items, attempt 1 |
| 23:12:58 | gpt-5-nano | tag_generator | 2,477 | 0 | 4,872 | 7,349 | $0.002073 | tag 25 items, attempt 1 |
| **Subtotal** | **5 calls** | — | **10,992** | **0** | **25,491** | **36,483** | **$0.010746** | Scrape batch |

## 2026-02-24

| Time | Model | Caller | Input | Cached | Output | Total | Cost (USD) | Note |
|------|-------|--------|------:|-------:|-------:|------:|-----------:|------|
| 05:17:18 | gpt-5-nano | llm_batch | 1,765 | 0 | 11,413 | 13,178 | $0.004653 | enrich 27 items, attempt 1 |
| 05:18:04 | gpt-5-nano | tag_generator | 2,849 | 0 | 4,332 | 7,181 | $0.001875 | tag 25 items, attempt 1 |
| 05:18:45 | gpt-5-nano | tag_generator | 2,011 | 0 | 4,620 | 6,631 | $0.001949 | tag 25 items, attempt 1 |
| **Subtotal** | **3 calls** | — | **6,625** | **0** | **20,365** | **26,990** | **$0.008477** | Scrape batch |

