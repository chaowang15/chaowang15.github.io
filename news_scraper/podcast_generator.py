"""
Podcast Generator — Generate daily Chinese podcast from HN Daily Best stories.

Pipeline (runs twice per day — Part 1 and Part 2):
  1. Load today's best_stories JSON
  2. Split stories into Part 1 (stories 1-20) and Part 2 (stories 21-40)
  3. Randomly select a voice pair for today
  4. For each part: generate Chinese dialogue transcript via LLM (gpt-4.1-mini)
  5. Convert raw transcript to reading-friendly Markdown
  6. Synthesize audio via Azure Speech TTS (SSML multi-speaker)
  7. Upload MP3 + transcript to GitHub Releases (monthly release, daily append)

Usage:
  python news_scraper/podcast_generator.py              # auto-detect today's best JSON
  python news_scraper/podcast_generator.py --date 2026-03-22  # specific date
  python news_scraper/podcast_generator.py --skip-upload  # generate only, no release upload
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
AZURE_SPEECH_KEY = os.environ.get("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.environ.get("AZURE_SPEECH_REGION", "westus")

# LLM settings
LLM_MODEL = "gpt-4.1-mini"
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 4000

# File naming
PODCAST_PREFIX = "hn-podcast"

# Base dir (relative to repo root)
BASE_DIR = "hackernews"

# Temporary working directory for intermediate files
WORK_DIR = "/tmp/podcast_work"

# Two-part split: each part covers 20 stories, total 40
STORIES_PER_PART = 20

# ---------------------------------------------------------------------------
# Voice Pairs — 6 female-male pairs for random daily rotation
# Each pair: (female_voice_id, female_name, female_style,
#             male_voice_id, male_name, male_style)
# ---------------------------------------------------------------------------
VOICE_PAIRS = [
    {
        "female_voice": "zh-CN-XiaoxiaoNeural",
        "female_name": "晓晓",
        "female_style": "chat",
        "male_voice": "zh-CN-YunxiNeural",
        "male_name": "云希",
        "male_style": "chat",
    },
    {
        "female_voice": "zh-CN-XiaomengNeural",
        "female_name": "晓梦",
        "female_style": "chat",
        "male_voice": "zh-CN-YunyangNeural",
        "male_name": "云扬",
        "male_style": "newscast-casual",
    },
    {
        "female_voice": "zh-CN-XiaoshuangNeural",
        "female_name": "晓双",
        "female_style": "chat",
        "male_voice": "zh-CN-YunzeNeural",
        "male_name": "云泽",
        "male_style": "cheerful",
    },
    {
        "female_voice": "zh-CN-XiaoyouMultilingualNeural",
        "female_name": "晓悠",
        "female_style": "chat",
        "male_voice": "zh-CN-YunjianNeural",
        "male_name": "云健",
        "male_style": "narration-relaxed",
    },
    {
        "female_voice": "zh-CN-XiaoyiNeural",
        "female_name": "晓伊",
        "female_style": "cheerful",
        "male_voice": "zh-CN-YunyeNeural",
        "male_name": "云野",
        "male_style": "cheerful",
    },
    {
        "female_voice": "zh-CN-XiaoxiaoNeural",
        "female_name": "晓晓",
        "female_style": "chat-casual",
        "male_voice": "zh-CN-YunfengNeural",
        "male_name": "云枫",
        "male_style": "cheerful",
    },
]


def select_voice_pair(date_tag: str) -> dict:
    """Select a voice pair deterministically based on the date.

    Uses a hash of the date string so the same date always gets the same pair,
    but different dates get different pairs in a seemingly random pattern.
    """
    h = int(hashlib.md5(date_tag.encode()).hexdigest(), 16)
    idx = h % len(VOICE_PAIRS)
    pair = VOICE_PAIRS[idx]
    print(f"[PODCAST] Voice pair selected: {pair['female_name']} + {pair['male_name']} (pair {idx + 1})")
    return pair


# ---------------------------------------------------------------------------
# Step 1: Load news data from JSON
# ---------------------------------------------------------------------------
def find_best_json(base_dir: str, target_date: datetime) -> str:
    """Find the best_stories JSON file for a given date."""
    date_dir = target_date.strftime("%Y/%m/%d")
    date_suffix = target_date.strftime("%m%d%Y")
    json_path = os.path.join(base_dir, date_dir, f"best_stories_{date_suffix}.json")
    if os.path.exists(json_path):
        return json_path
    raise FileNotFoundError(
        f"No best_stories JSON found for {target_date.strftime('%Y-%m-%d')} at {json_path}"
    )


def load_news_items(json_path: str) -> tuple:
    """Load news items from JSON and return (items, date_str)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])
    meta = data.get("metadata", {})
    date_str = meta.get("date", "")
    if not date_str:
        basename = os.path.basename(json_path)
        m = re.search(r"(\d{8})", basename)
        if m:
            d = datetime.strptime(m.group(1), "%m%d%Y")
            date_str = d.strftime("%B %d, %Y")
    return items, date_str


# ---------------------------------------------------------------------------
# Step 2: Prepare text input for LLM
# ---------------------------------------------------------------------------
def prepare_news_text(items: list, date_str: str, part_num: int = 1) -> str:
    """Format news items into a text block for LLM input.

    Args:
        items: List of news items (already sliced for this part).
        date_str: Human-readable date string.
        part_num: 1 or 2 (Part 1 = top stories, Part 2 = more stories).
    """
    part_label = "上半场" if part_num == 1 else "下半场"
    offset = 0 if part_num == 1 else STORIES_PER_PART

    lines = [
        f"Hacker News Daily Best Stories — {date_str} ({part_label})",
        f"The following is Part {part_num} of today's top stories from "
        f"Hacker News on {date_str} (stories {offset + 1}-{offset + len(items)}).",
        "",
    ]
    for i, item in enumerate(items, 1):
        title = item.get("title_en", item.get("title", "Untitled"))
        summary = item.get("summary_en", "No summary available.")
        score = item.get("hn", {}).get("score", 0)
        comments = item.get("hn", {}).get("descendants", 0)
        lines.append(f"Story {offset + i}: {title}")
        lines.append(f"Votes: {score}, Comments: {comments}")
        lines.append(f"Summary: {summary}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 3: Generate Chinese dialogue transcript via LLM
# ---------------------------------------------------------------------------
def build_system_prompt(voice_pair: dict, part_num: int = 1) -> str:
    """Build the LLM system prompt with the selected voice pair names."""
    female_name = voice_pair["female_name"]
    male_name = voice_pair["male_name"]

    if part_num == 1:
        part_intro = (
            "这是今天的上半场节目，涵盖排名最靠前的新闻。\n"
            "开场：简短介绍今天的精选概况，说明这是上半场。\n"
            "结尾：简短预告下半场还有更多精彩内容，不要说再见。"
        )
    else:
        part_intro = (
            "这是今天的下半场节目，涵盖更多精彩新闻。\n"
            "开场：简短说明这是下半场，直接进入新闻。\n"
            "结尾：简短总结今天的全部内容并告别。"
        )

    return f"""你是一个专业的播客脚本编剧。你需要将一组 Hacker News 每日精选新闻转化为一段双人对话形式的播客脚本。

播客名称：HN Daily Best（HN 每日精选）
主持人：{female_name}（女，活泼开朗）和{male_name}（男，沉稳有见解）

{part_intro}

语言风格要求：
1. 主体语言用中文，语气自然、口语化，像两个科技爱好者在聊天
2. 新闻标题直接用中文说，不需要保留英文原标题
3. 技术关键词保留英文，例如：GDPR、API、GrapheneOS、RSS、Git、FPGA、AI、TTS、LLM 等
4. 中英文之间要加空格，例如："这个 GDPR 的问题确实很重要"
5. 不要把所有英文词都翻译成中文，尤其是专有名词和技术术语

内容要求：
1. 尽量涵盖所有给出的新闻故事，覆盖面优先
2. 每个故事的讨论要非常简洁精炼：排名靠前的 1-3 句话，排名靠后的 1 句话快速带过
3. 两人要有互动、有观点碰撞、偶尔有幽默
4. 总字数严格控制在 2500 字以内（约 6-7 分钟音频），这是硬性上限，宁可每个故事少说几句也不要超字数

输出格式：
严格使用 <Person1> 和 <Person2> 标签包裹每段对话。
Person1 = {female_name}（女主持）
Person2 = {male_name}（男主持）

示例：
<Person1>大家好，欢迎收听 HN Daily Best！我是{female_name}。</Person1>
<Person2>我是{male_name}。今天的 Hacker News 精选真的很精彩，我们赶紧开始吧！</Person2>
"""


def generate_transcript(news_text: str, voice_pair: dict, part_num: int = 1) -> str:
    """Generate Chinese-English mixed podcast transcript using OpenAI LLM."""
    from openai import OpenAI

    client = OpenAI()  # Uses OPENAI_API_KEY env var

    system_prompt = build_system_prompt(voice_pair, part_num)

    part_label = "上半场" if part_num == 1 else "下半场"
    user_prompt = (
        f"请根据以下 Hacker News 每日精选新闻数据（{part_label}），"
        "生成一段中英混合的双人播客对话脚本：\n\n"
        f"{news_text}"
    )

    print(f"[PODCAST] Generating Chinese transcript via LLM (Part {part_num})...")
    t0 = time.time()

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )

    transcript = response.choices[0].message.content
    usage = response.usage
    elapsed = time.time() - t0

    print(f"[PODCAST] Transcript generated: {len(transcript)} chars in {elapsed:.1f}s")
    print(
        f"[PODCAST] Tokens: input={usage.prompt_tokens}, "
        f"output={usage.completion_tokens}, total={usage.total_tokens}"
    )
    cost = usage.prompt_tokens * 0.4 / 1e6 + usage.completion_tokens * 1.6 / 1e6
    print(f"[PODCAST] Estimated LLM cost: ${cost:.4f}")

    return transcript


# ---------------------------------------------------------------------------
# Step 4: Convert raw transcript to reading-friendly Markdown
# ---------------------------------------------------------------------------
def transcript_to_markdown(raw_transcript: str, date_str: str, voice_pair: dict,
                           part_num: int = 1) -> str:
    """Convert <Person1>/<Person2> tagged transcript to readable Markdown."""
    female_name = voice_pair["female_name"]
    male_name = voice_pair["male_name"]

    part_label = "上半场" if part_num == 1 else "下半场"
    lines = [
        f"# HN 每日精选播客（{part_label}） — {date_str}",
        "",
        f"> HN Daily Best — Part {part_num}",
        "",
        f"**主持人：** {female_name}（女主持）和{male_name}（男主持）",
        "",
        "---",
        "",
    ]

    # Parse dialogue segments
    pattern = r"<(Person[12])>(.*?)</\1>"
    segments = re.findall(pattern, raw_transcript, re.DOTALL)

    current_story = None
    for speaker, content in segments:
        content = content.strip()
        if not content:
            continue

        # Detect story transitions
        story_match = re.search(
            r"(?:第\s*(\d+)\s*条|Story\s*(\d+)|第(\d+)个)", content
        )
        if story_match:
            num = story_match.group(1) or story_match.group(2) or story_match.group(3)
            if num != current_story:
                current_story = num
                lines.append("")
                lines.append("---")
                lines.append("")

        name = female_name if speaker == "Person1" else male_name
        lines.append(f"**{name}：** {content}")
        lines.append("")

    # Add footer
    lines.extend([
        "---",
        "",
        "*本播客由 AI 自动生成，内容基于 Hacker News 每日精选新闻。*",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 5: Synthesize audio via Azure Speech TTS (SSML multi-speaker)
# ---------------------------------------------------------------------------
def _build_ssml_chunk(segments: list, voice_pair: dict) -> str:
    """Build a single SSML document from a list of (speaker, content) segments."""
    female_voice = voice_pair["female_voice"]
    female_style = voice_pair["female_style"]
    male_voice = voice_pair["male_voice"]
    male_style = voice_pair["male_style"]

    ssml_parts = [
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">'
    ]
    for speaker, content in segments:
        content = content.strip()
        if not content:
            continue
        content = content.replace("&", "&amp;")
        content = content.replace("<", "&lt;")
        content = content.replace(">", "&gt;")
        if speaker == "Person1":
            voice_id, style = female_voice, female_style
        else:
            voice_id, style = male_voice, male_style
        ssml_parts.append(
            f'  <voice name="{voice_id}">\n'
            f'    <mstts:express-as xmlns:mstts="http://www.w3.org/2001/mstts" style="{style}">\n'
            f'      {content}\n'
            f'    </mstts:express-as>\n'
            f'  </voice>'
        )
    ssml_parts.append('</speak>')
    return '\n'.join(ssml_parts)


def _synthesize_one_chunk(ssml: str, output_path: str, speech_key: str, speech_region: str) -> bool:
    """Synthesize a single SSML chunk to an MP3 file. Returns True on success."""
    import azure.cognitiveservices.speech as speechsdk

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )

    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"[PODCAST] ERROR: Azure TTS canceled: {cancellation.reason}")
        if cancellation.error_details:
            print(f"[PODCAST]   Details: {cancellation.error_details}")
        return False
    else:
        print(f"[PODCAST] ERROR: Azure TTS unexpected result: {result.reason}")
        return False


def synthesize_audio(raw_transcript: str, output_mp3: str, voice_pair: dict) -> bool:
    """Synthesize audio from transcript using Azure Speech TTS.

    Azure Free F0 tier has a ~10 minute / ~14MB per-request limit.
    If the transcript has many segments, we split into chunks of
    MAX_SEGMENTS_PER_CHUNK segments, synthesize each chunk separately,
    then concatenate with ffmpeg.
    """
    MAX_SEGMENTS_PER_CHUNK = 25  # ~6-7 min per chunk, safely under 10 min limit

    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        print("[PODCAST] ERROR: azure-cognitiveservices-speech not installed.")
        print("[PODCAST]   Run: pip install azure-cognitiveservices-speech")
        return False

    speech_key = AZURE_SPEECH_KEY
    speech_region = AZURE_SPEECH_REGION
    if not speech_key:
        print("[PODCAST] ERROR: AZURE_SPEECH_KEY not set")
        return False

    # Parse all dialogue segments
    pattern = r"<(Person[12])>(.*?)</\1>"
    all_segments = re.findall(pattern, raw_transcript, re.DOTALL)
    all_segments = [(s, c.strip()) for s, c in all_segments if c.strip()]

    if not all_segments:
        print("[PODCAST] WARNING: No dialogue segments found in transcript")
        return False

    total_segments = len(all_segments)
    print(f"[PODCAST] Total dialogue segments: {total_segments}")

    # Decide whether to chunk
    if total_segments <= MAX_SEGMENTS_PER_CHUNK:
        # Single request — no chunking needed
        ssml = _build_ssml_chunk(all_segments, voice_pair)
        print(f"[PODCAST] SSML built: {len(ssml)} chars, {total_segments} voice segments (single chunk)")
        print("[PODCAST] Starting Azure TTS synthesis...")
        t0 = time.time()
        success = _synthesize_one_chunk(ssml, output_mp3, speech_key, speech_region)
        elapsed = time.time() - t0
    else:
        # Split into chunks
        chunks = []
        for i in range(0, total_segments, MAX_SEGMENTS_PER_CHUNK):
            chunks.append(all_segments[i:i + MAX_SEGMENTS_PER_CHUNK])
        num_chunks = len(chunks)
        print(f"[PODCAST] Splitting into {num_chunks} chunks ({MAX_SEGMENTS_PER_CHUNK} segments each)")

        chunk_files = []
        t0 = time.time()
        for idx, chunk_segments in enumerate(chunks):
            chunk_ssml = _build_ssml_chunk(chunk_segments, voice_pair)
            chunk_path = os.path.join(WORK_DIR, f"chunk_{idx:02d}.mp3")
            print(f"[PODCAST]   Chunk {idx + 1}/{num_chunks}: {len(chunk_segments)} segments, {len(chunk_ssml)} chars")

            if not _synthesize_one_chunk(chunk_ssml, chunk_path, speech_key, speech_region):
                print(f"[PODCAST] ERROR: Chunk {idx + 1} failed")
                return False

            chunk_files.append(chunk_path)
            print(f"[PODCAST]   Chunk {idx + 1}/{num_chunks} done: {os.path.getsize(chunk_path) / (1024*1024):.1f} MB")

        elapsed = time.time() - t0

        # Concatenate chunks with ffmpeg
        print(f"[PODCAST] Concatenating {num_chunks} chunks with ffmpeg...")
        concat_list = os.path.join(WORK_DIR, "concat_list.txt")
        with open(concat_list, "w") as f:
            for cf in chunk_files:
                f.write(f"file '{cf}'\n")

        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list, "-c", "copy", output_mp3,
        ]
        concat_result = subprocess.run(concat_cmd, capture_output=True, text=True)
        if concat_result.returncode != 0:
            print(f"[PODCAST] ERROR: ffmpeg concat failed: {concat_result.stderr}")
            return False

        # Clean up chunk files
        for cf in chunk_files:
            os.remove(cf)
        os.remove(concat_list)

        success = True

    if success:
        mp3_size = os.path.getsize(output_mp3) / (1024 * 1024)
        probe = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                output_mp3,
            ],
            capture_output=True, text=True,
        )
        duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
        print(f"[PODCAST] Azure TTS completed in {elapsed:.1f}s")
        print(f"[PODCAST]   Duration: {duration:.0f}s ({duration / 60:.1f} min)")
        print(f"[PODCAST]   Size: {mp3_size:.1f} MB")
        return True

    return False


# ---------------------------------------------------------------------------
# Step 6: Upload to GitHub Releases (monthly release, daily append)
# ---------------------------------------------------------------------------
def upload_to_release(files: list, target_date: datetime, repo: str = "") -> bool:
    """Upload files to a monthly GitHub Release.

    Creates the release if it doesn't exist, otherwise appends files.
    Uses subprocess list args (not shell=True) to avoid shell escaping issues.
    """
    tag = f"podcast-{target_date.strftime('%Y-%m')}"
    title = f"HN Podcast - {target_date.strftime('%B %Y')}"
    body = (
        f"Daily HN podcast audio and transcripts for {target_date.strftime('%B %Y')}.\n\n"
        "Each day includes two parts:\n"
        "- Part 1: Top stories (hn-podcast-YYYY-MM-DD-part1.mp3)\n"
        "- Part 2: More stories (hn-podcast-YYYY-MM-DD-part2.mp3)\n"
        "- Markdown transcripts for each part\n\n"
        "Audio: Chinese, Azure Speech TTS"
    )

    repo_args = ["--repo", repo] if repo else []

    # Check if release already exists
    check_cmd = ["gh", "release", "view", tag] + repo_args
    result = subprocess.run(check_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Create new release
        print(f"[PODCAST] Creating new release: {tag}")
        create_cmd = (
            ["gh", "release", "create", tag]
            + list(files)
            + ["--title", title, "--notes", body]
            + repo_args
        )
        result = subprocess.run(create_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[PODCAST] ERROR creating release: {result.stderr}")
            return False
        print(f"[PODCAST] Release created: {tag}")
    else:
        # Upload to existing release
        print(f"[PODCAST] Uploading to existing release: {tag}")
        upload_cmd = (
            ["gh", "release", "upload", tag]
            + list(files)
            + ["--clobber"]
            + repo_args
        )
        result = subprocess.run(upload_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[PODCAST] ERROR uploading: {result.stderr}")
            return False
        print(f"[PODCAST] Files uploaded to release: {tag}")

    # Print download URLs
    for f in files:
        fname = os.path.basename(f)
        if repo:
            url_repo = repo
        else:
            detect = subprocess.run(
                ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                capture_output=True, text=True,
            )
            url_repo = detect.stdout.strip() if detect.returncode == 0 else "OWNER/REPO"
        url = f"https://github.com/{url_repo}/releases/download/{tag}/{fname}"
        print(f"[PODCAST]   {fname}: {url}")

    return True


# ---------------------------------------------------------------------------
# Generate one part of the podcast
# ---------------------------------------------------------------------------
def _generate_one_part(
    items: list,
    date_str: str,
    date_tag: str,
    voice_pair: dict,
    part_num: int,
    target_date: datetime,
    skip_upload: bool,
    repo: str,
) -> dict:
    """Generate one part (Part 1 or Part 2) of the daily podcast.

    Returns a dict with paths and metadata, or empty dict on failure.
    """
    part_label = f"Part {part_num}"
    part_suffix = f"part{part_num}"

    print(f"\n{'─' * 50}")
    print(f"[PODCAST] === Generating {part_label} ({len(items)} stories) ===")
    print(f"{'─' * 50}")

    # --- Prepare news text ---
    news_text = prepare_news_text(items, date_str, part_num)
    print(f"[PODCAST] News text ({part_label}): {len(news_text)} characters")

    # --- Generate transcript ---
    raw_transcript = generate_transcript(news_text, voice_pair, part_num)

    # --- Validate and fix transcript tags ---
    from transcript_validator import validate_transcript
    raw_transcript = validate_transcript(raw_transcript, label="PODCAST")

    # Save raw transcript (after validation)
    raw_path = os.path.join(WORK_DIR, f"transcript_raw_{date_tag}_{part_suffix}.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_transcript)

    # --- Convert to Markdown ---
    md_transcript = transcript_to_markdown(raw_transcript, date_str, voice_pair, part_num)

    transcript_filename = f"{PODCAST_PREFIX}-{date_tag}-{part_suffix}-transcript.md"
    transcript_path = os.path.join(WORK_DIR, transcript_filename)
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(md_transcript)
    print(f"[PODCAST] Transcript saved: {transcript_path}")

    # --- Synthesize audio ---
    print(f"\n[PODCAST] Synthesizing audio ({part_label}) via Azure Speech TTS...")
    mp3_filename = f"{PODCAST_PREFIX}-{date_tag}-{part_suffix}.mp3"
    mp3_path = os.path.join(WORK_DIR, mp3_filename)
    success = synthesize_audio(raw_transcript, mp3_path, voice_pair)
    if not success:
        print(f"[PODCAST] Audio synthesis failed for {part_label}")
        return {}

    # --- Upload ---
    release_tag = f"podcast-{target_date.strftime('%Y-%m')}"
    upload_files = [mp3_path, transcript_path]

    if skip_upload:
        print(f"[PODCAST] Skipping upload for {part_label} (--skip-upload)")
    else:
        print(f"[PODCAST] Uploading {part_label} to GitHub Releases...")
        upload_success = upload_to_release(upload_files, target_date, repo=repo)
        if not upload_success:
            print(f"[PODCAST] WARNING: Upload failed for {part_label}, files saved locally")

    # Determine download URL
    detect = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True, text=True,
    )
    url_repo = detect.stdout.strip() if detect.returncode == 0 else repo
    if not url_repo:
        url_repo = "chaowang15/chaowang15.github.io"

    mp3_url = (
        f"https://github.com/{url_repo}/releases/download/"
        f"{release_tag}/{mp3_filename}"
    )
    transcript_url = (
        f"https://github.com/{url_repo}/releases/download/"
        f"{release_tag}/{transcript_filename}"
    )

    mp3_size = os.path.getsize(mp3_path) / (1024 * 1024)

    return {
        "part": part_num,
        "mp3_path": mp3_path,
        "mp3_filename": mp3_filename,
        "mp3_url": mp3_url,
        "transcript_path": transcript_path,
        "transcript_filename": transcript_filename,
        "transcript_url": transcript_url,
        "release_tag": release_tag,
        "size_mb": mp3_size,
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def generate_daily_podcast(
    base_dir: str = BASE_DIR,
    target_date: datetime = None,
    skip_upload: bool = False,
    repo: str = "",
) -> dict:
    """Run the full podcast generation pipeline (two parts).

    Returns a dict with paths and metadata for both parts, or empty dict on failure.
    """
    t_start = time.time()

    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)

    date_tag = target_date.strftime("%Y-%m-%d")
    print(f"\n{'=' * 60}")
    print(f"[PODCAST] Generating podcast for {date_tag} (2 parts)")
    print(f"{'=' * 60}")

    # Ensure work directory
    os.makedirs(WORK_DIR, exist_ok=True)

    # --- Step 0: Select voice pair ---
    print(f"\n[PODCAST] Step 0: Selecting voice pair...")
    voice_pair = select_voice_pair(date_tag)

    # --- Step 1: Load news data ---
    print(f"\n[PODCAST] Step 1: Loading news data...")
    try:
        json_path = find_best_json(base_dir, target_date)
    except FileNotFoundError as e:
        print(f"[PODCAST] {e}")
        return {}

    items, date_str = load_news_items(json_path)
    if not items:
        print("[PODCAST] No news items found, skipping podcast generation")
        return {}
    print(f"[PODCAST] Loaded {len(items)} stories from {json_path}")

    # --- Step 2: Split into two parts ---
    total_stories = min(len(items), STORIES_PER_PART * 2)  # Use at most 40 stories
    part1_items = items[:STORIES_PER_PART]
    part2_items = items[STORIES_PER_PART:total_stories]

    print(f"[PODCAST] Splitting: Part 1 = {len(part1_items)} stories, Part 2 = {len(part2_items)} stories")

    if len(part2_items) == 0:
        print("[PODCAST] Not enough stories for Part 2, generating Part 1 only")

    # --- Generate each part ---
    results = {}
    release_tag = f"podcast-{target_date.strftime('%Y-%m')}"

    for part_num, part_items in [(1, part1_items), (2, part2_items)]:
        if not part_items:
            continue

        part_result = _generate_one_part(
            items=part_items,
            date_str=date_str,
            date_tag=date_tag,
            voice_pair=voice_pair,
            part_num=part_num,
            target_date=target_date,
            skip_upload=skip_upload,
            repo=repo,
        )

        if not part_result:
            print(f"[PODCAST] Part {part_num} failed, continuing with other parts...")
            continue

        results[f"part{part_num}"] = part_result

    if not results:
        print("[PODCAST] All parts failed")
        return {}

    # --- Create .podcast marker file ---
    marker_dir = os.path.join(
        base_dir, target_date.strftime("%Y"), target_date.strftime("%m"),
        target_date.strftime("%d")
    )
    os.makedirs(marker_dir, exist_ok=True)
    marker_path = os.path.join(marker_dir, ".podcast")

    marker_lines = [
        f"parts={len(results)}",
        f"release={release_tag}",
        f"female={voice_pair['female_name']}",
        f"male={voice_pair['male_name']}",
    ]
    for key, part_data in sorted(results.items()):
        pn = part_data["part"]
        marker_lines.append(f"mp3_part{pn}={part_data['mp3_filename']}")
        marker_lines.append(f"transcript_part{pn}={part_data['transcript_filename']}")

    with open(marker_path, "w") as f:
        f.write("\n".join(marker_lines) + "\n")
    print(f"[PODCAST] Marker created: {marker_path}")

    # --- Summary ---
    elapsed = time.time() - t_start
    total_size = sum(r["size_mb"] for r in results.values())

    print(f"\n{'=' * 60}")
    print(f"[PODCAST] DONE! Total time: {elapsed:.1f}s")
    print(f"[PODCAST]   Voice: {voice_pair['female_name']} + {voice_pair['male_name']}")
    print(f"[PODCAST]   Parts generated: {len(results)}")
    for key, part_data in sorted(results.items()):
        print(f"[PODCAST]   {key}: {part_data['mp3_filename']} ({part_data['size_mb']:.1f} MB)")
    print(f"[PODCAST]   Total size: {total_size:.1f} MB")
    print(f"{'=' * 60}")

    return {
        "date": date_tag,
        "release_tag": release_tag,
        "voice_pair": voice_pair,
        "parts": results,
        # Convenience: first part's URL for backward compatibility
        "mp3_url": results.get("part1", {}).get("mp3_url", ""),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate HN Daily Podcast")
    parser.add_argument(
        "--date",
        type=str,
        default="",
        help="Target date in YYYY-MM-DD format (default: yesterday)",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip uploading to GitHub Releases",
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default=BASE_DIR,
        help="Base directory for hackernews data",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="",
        help="GitHub repo in owner/repo format (auto-detected if empty)",
    )
    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        target_date = datetime.now() - timedelta(days=1)

    result = generate_daily_podcast(
        base_dir=args.base_dir,
        target_date=target_date,
        skip_upload=args.skip_upload,
        repo=args.repo,
    )

    if not result:
        print("[PODCAST] Pipeline failed")
        sys.exit(1)

    print(f"\n[PODCAST] Success! MP3 URLs:")
    for key, part_data in sorted(result.get("parts", {}).items()):
        print(f"[PODCAST]   {key}: {part_data['mp3_url']}")


if __name__ == "__main__":
    main()
