# Hacker News Daily - 更新日志

本文档记录了对 Hacker News Daily 抓取和展示系统的主要更新。

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
