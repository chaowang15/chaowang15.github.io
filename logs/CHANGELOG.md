# Hacker News Daily - 更新日志

本文档记录了对 Hacker News Daily 抓取和展示系统的主要更新。

---

## 2026年2月19日 (新增 Top Stories 支持和跨日去重)

本次更新是一个重要的功能扩展，新增了 Top Stories 的爬取，并实现了跨日去重机制以节省 LLM tokens。

- **新增 Top Stories 爬取**:
  - `main.py` 现在支持 4 种模式：`best`（仅 Best Stories）、`top`（仅 Top Stories）、`all`（同时爬取两者）、`rebuild`（从 JSON 重建所有页面）。
  - `news_config.yml` 新增 `top` 配置段（count: 50, prefix: top_stories）。
  - Top Stories 基于 HN 首页实时排名，更新频率远高于 Best Stories，每天内容变化更大。

- **跨日去重机制**:
  - 新增 `_load_previous_day_items()` 和 `_is_same_story()` 函数，在爬取新数据后自动加载前一天的 JSON 文件。
  - 通过 HN ID 匹配 + 标题相似度验证（精确匹配、包含关系、80%词汇重叠率）来确认同一篇新闻。
  - 对于重复新闻，直接复用前一天的 LLM 摘要（title_zh, summary_en, summary_zh）、预览图和标签，仅更新 score 和 comment count 等时效性数据。
  - 只有新出现的新闻才会调用 LLM 生成摘要，显著节省 tokens 开支。

- **索引页面重新设计**:
  - `index_updater.py` 完全重写，支持按日期分组显示 Best Stories 和 Top Stories。
  - 每个日期行内显示蓝色 "Best Stories" 和金色 "Top Stories" 两个彩色药丸标签，各自可点击跳转。
  - 索引页标题从 "Hacker News (Daily)" 更新为 "Hacker News Daily"。
  - CSS 新增 `.hn-day-row`、`.hn-day-date`、`.hn-day-stories`、`.hn-type-best`、`.hn-type-top` 等样式，支持 dark mode 和移动端响应式。

- **GitHub Actions Workflow**:
  - `hn_news.yml` 需要手动更新为 `python news_scraper/main.py all`（由于 GitHub App 权限限制，workflow 文件无法通过 API 推送）。

**修改文件**: `news_scraper/main.py`, `news_scraper/index_updater.py`, `news_config.yml`, `assets/hn/hn.css`, `hackernews/index.md`

---

## 2026年2月19日 (日志文件夹迁移和 Jekyll 构建修复)

将备份日志文件夹从 `hackernews/log/` 迁移到 repo 根目录的 `logs/`，并在 `_config.yml` 中将 `logs/`、`news_scraper/`、`news_config.yml`、`requirements.txt` 加入 Jekyll 的 `exclude` 列表。此前 `integration_proposal.md` 中包含了 Liquid 模板语法（`{% for %}`），导致 Jekyll 构建时解析失败（Pages build failure）。迁移并排除后，这些纯备份文件不再参与 Jekyll 构建，从根本上避免了此类问题。

---

## 2026年2月19日 (可靠性、日志和模型优化)

本次更新旨在全面提升系统的稳定性和可维护性。

- **模型配置优化**:
  - 在 `news_config.yml` 中恢复使用 `gpt-5-nano` 作为摘要和标签生成的主力模型，以降低成本。
  - 为摘要和标签分别配置了不同的 fallback 模型 (`gpt-5-mini` 和 `gpt-4.1-nano`)，在主力模型失败时自动切换。
  - 新增 `max_retries: 2` 配置，为所有 LLM 调用增加了2次重试机制（带指数退避）。

- **全面的日志系统**:
  - 重写了 `main.py` 的日志输出，现在会以清晰的步骤格式（`[STEP 1/5]...`）展示 pipeline 进度。
  - 每个步骤都记录了耗时、成功/失败状态和重试信息，方便在 GitHub Actions 中快速定位问题。
  - 标签生成模块现在会输出标签分布统计，便于监控分类质量。

- **健壮的 JSON 解析和内容清洗**:
  - 在 `llm_batch.py` 和 `tag_generator.py` 中重写了 `_safe_json_loads` 函数，现在可以处理 markdown 代码围栏、Extra data 错误、前导文本等5种常见的 LLM 输出异常。
  - 新增 `_clean_summary` 函数，使用正则表达式自动移除 GPT 生成的元评论（如 "The article discusses..."），提升摘要质量。
  - 将标签生成任务分批处理（每批25条），从根本上解决了因输出过长导致的 JSON 截断和解析失败问题。

---

## 2026年2月19日 (Scheduled Run 标签功能修复)

- **问题诊断**: 通过分析 GitHub Actions 日志，定位到每日定时执行的任务没有生成标签，原因是 LLM 输出过长（50条新闻一次性处理）导致 JSON 截断，`json.loads()` 抛出 `Extra data` 异常，该异常被静默捕获，导致标签步骤跳过。
- **修复措施**: 
  - 在 `tag_generator.py` 中引入分批处理机制，将50条新闻分批次调用 LLM。
  - 增强了 `_safe_json_loads` 函数的健壮性，使其能处理不完整的 JSON 输出。
  - 更新了 `news_config.yml` 中的模型配置，使用更可靠的 `gpt-4.1-mini` 作为临时解决方案。

---

## 2026年2月19日 (摘要质量和 UI 优化)

- **摘要质量提升**:
  - 重写了 `llm_batch.py` 中的 prompt，要求模型提供更有深度的背景信息，并严格禁止了元评论和重复标题等冗余信息。
  - 创建了 `resummarize.py` 脚本，使用新的 prompt 重新生成了全部 150 篇存量新闻的摘要。

- **UI 清理**:
  - 从每个新闻页面的副标题下方移除了 "Top 50" 和 "Best Stories" 两个固定的 badge。
  - 简化了新闻页面的副标题，现在只显示抓取时间，移除了 "Top 50 stories" 和来源链接。

---

## 2026年2月19日 (索引页丰富化和标签系统)

- **索引页丰富化**:
  - 修改了 `index_updater.py`，现在索引页 (`/hackernews/`) 每一行会显示当天的 **新闻数量** 和 **头条新闻标题**。
  - 优化了 CSS，使详情行在移动端能优雅地截断，避免布局错乱。

- **标签系统实现**:
  - 创建了 `tag_generator.py` 模块，使用 GPT 为每篇新闻分配 1-3 个预定义标签（共25个类别）。
  - 实现了 **关键字补充** 功能：在 GPT 分类的基础上，通过正则表达式扫描摘要和标题，自动补充 `AI`, `Security`, `Open Source` 等被遗漏的标签。
  - 在 `md_writer.py` 中增加了标签渲染逻辑，以彩色药丸形状的 badge 展示在每篇新闻卡片上。
  - 在 `assets/hn/hn.css` 中为 15+ 种标签设计了独立的颜色方案，并支持暗黑模式。
  - 将标签生成和补充逻辑完整地集成到了 `main.py` 的日常 pipeline 中。

---

## 2026年2月19日 (个人主页整合)

- 在个人主页 (`/index.md`) 的末尾新增了 **"Side Projects"** 板块。
- 在该板块下添加了指向 Hacker News Daily 项目的链接，并撰写了一段简明的英文介绍，涵盖了项目的核心技术和特点（API, GPT, Bilingual, GitHub Actions）。
- 修正了个人主页 "Services" 板块中 Conference Reviewers 列表的格式，移除了年份数字。

---

## 2026年2月19日 (项目启动和初步分析)

- 克隆 `chaowang15.github.io` 仓库。
- 分析了 `news_scraper`, `hackernews`, `assets/hn` 等核心目录的代码结构和功能。
- 梳理了 `hn_news.yml` GitHub Actions workflow 的执行流程。
- 提供了初步的分析报告和改进建议。
