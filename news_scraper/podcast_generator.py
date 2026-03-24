"""
Podcast Generator — Generate daily Chinese podcast from HN Daily Best stories.

Pipeline:
  1. Load today's best_stories JSON
  2. Prepare news text input
  3. Generate Chinese-English mixed dialogue transcript via LLM (gpt-4.1-mini)
  4. Convert raw transcript to reading-friendly Markdown
  5. Synthesize audio via Gemini 2.5 Flash TTS (multi-speaker)
  6. Encode to MP3 64kbps
  7. Upload MP3 + transcript to GitHub Releases (monthly release, daily append)

Usage:
  python news_scraper/podcast_generator.py              # auto-detect today's best JSON
  python news_scraper/podcast_generator.py --date 2026-03-22  # specific date
  python news_scraper/podcast_generator.py --skip-upload  # generate only, no release upload
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import wave
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# TTS voices
SPEAKER1_VOICE = "Kore"   # Female voice for 小晓
SPEAKER2_VOICE = "Puck"   # Male voice for 云希

# Audio settings
MP3_BITRATE = "64k"
TTS_SAMPLE_RATE = 24000
TTS_SAMPLE_WIDTH = 2

# LLM settings
LLM_MODEL = "gpt-4.1-mini"
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 8000

# File naming
PODCAST_PREFIX = "hn-podcast"

# Base dir (relative to repo root)
BASE_DIR = "hackernews"

# Temporary working directory for intermediate files
WORK_DIR = "/tmp/podcast_work"


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
    # Extract date from metadata or filename
    meta = data.get("metadata", {})
    date_str = meta.get("date", "")
    if not date_str:
        # Parse from filename: best_stories_MMDDYYYY.json
        basename = os.path.basename(json_path)
        m = re.search(r"(\d{8})", basename)
        if m:
            d = datetime.strptime(m.group(1), "%m%d%Y")
            date_str = d.strftime("%B %d, %Y")
    return items, date_str


# ---------------------------------------------------------------------------
# Step 2: Prepare text input for LLM
# ---------------------------------------------------------------------------
def prepare_news_text(items: list, date_str: str) -> str:
    """Format news items into a text block for LLM input."""
    lines = [
        f"Hacker News Daily Best Stories — {date_str}",
        f"The following is a curated list of the top {len(items)} stories from "
        f"Hacker News on {date_str}, ranked by community engagement. "
        "Each story includes a title and a brief summary.",
        "",
    ]
    for i, item in enumerate(items, 1):
        title = item.get("title_en", item.get("title", "Untitled"))
        summary = item.get("summary_en", "No summary available.")
        score = item.get("hn", {}).get("score", 0)
        comments = item.get("hn", {}).get("descendants", 0)
        lines.append(f"Story {i}: {title}")
        lines.append(f"Votes: {score}, Comments: {comments}")
        lines.append(f"Summary: {summary}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 3: Generate Chinese dialogue transcript via LLM
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """你是一个专业的播客脚本编剧。你需要将一组 Hacker News 每日精选新闻转化为一段双人对话形式的播客脚本。

播客名称：HN Daily Best（HN 每日精选）
主持人：小晓（女，活泼开朗）和云希（男，沉稳有见解）

语言风格要求：
1. 主体语言用中文，语气自然、口语化，像两个科技爱好者在聊天
2. 所有新闻的英文标题必须保留原文，用中文简单解释一下标题含义
3. 技术关键词保留英文，例如：GDPR、API、GrapheneOS、RSS、Git、FPGA、AI、TTS、LLM 等
4. 中英文之间要加空格，例如："这个 GDPR 的问题确实很重要"
5. 不要把所有英文词都翻译成中文，尤其是专有名词和技术术语

内容要求：
1. 开场简短介绍今天的精选概况
2. 重点讨论排名靠前的 10-15 个故事，其余可以快速带过
3. 两人要有互动、有观点碰撞、偶尔有幽默
4. 结尾简短总结和告别
5. 总字数控制在 3000-4000 字左右（约 10-12 分钟音频）

输出格式：
严格使用 <Person1> 和 <Person2> 标签包裹每段对话。
Person1 = 小晓（女主持）
Person2 = 云希（男主持）

示例：
<Person1>大家好，欢迎收听 HN Daily Best！我是小晓。</Person1>
<Person2>我是云希。今天的 Hacker News 精选真的很精彩，我们赶紧开始吧！</Person2>
"""


def generate_transcript(news_text: str) -> str:
    """Generate Chinese-English mixed podcast transcript using OpenAI LLM."""
    from openai import OpenAI

    client = OpenAI()  # Uses OPENAI_API_KEY env var

    user_prompt = (
        "请根据以下 Hacker News 每日精选新闻数据，"
        "生成一段中英混合的双人播客对话脚本：\n\n"
        f"{news_text}"
    )

    print("[PODCAST] Generating Chinese transcript via LLM...")
    t0 = time.time()

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
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
def transcript_to_markdown(raw_transcript: str, date_str: str) -> str:
    """Convert <Person1>/<Person2> tagged transcript to readable Markdown."""
    lines = [
        f"# HN 每日精选播客 — {date_str}",
        "",
        "> HN Daily Best — 每天精选 Hacker News 最佳新闻",
        "",
        "**主持人：** 小晓（女主持）和云希（男主持）",
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

        # Detect story transitions (look for story number patterns)
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

        name = "小晓" if speaker == "Person1" else "云希"
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
# Step 5: Synthesize audio via Gemini 2.5 Flash TTS
# ---------------------------------------------------------------------------
def convert_tags_to_speaker_names(text: str) -> str:
    """Convert <Person1>...</Person1> to 小晓: ... format for Gemini multi-speaker."""
    text = re.sub(r"<Person1>(.*?)</Person1>", r"小晓: \1", text, flags=re.DOTALL)
    text = re.sub(r"<Person2>(.*?)</Person2>", r"云希: \1", text, flags=re.DOTALL)
    text = re.sub(r"</Person[12]>", "", text)
    return text


def split_into_chunks(transcript: str, max_lines: int = 8) -> list:
    """Split transcript into chunks of dialogue lines for TTS processing."""
    lines = [l.strip() for l in transcript.split("\n") if l.strip()]
    chunks = []
    for i in range(0, len(lines), max_lines):
        chunk = "\n".join(lines[i : i + max_lines])
        chunks.append(chunk)
    return chunks


def wave_file(filename: str, pcm: bytes, channels=1, rate=24000, sample_width=2):
    """Write raw PCM data to a WAV file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def add_silence(duration_ms: int = 400, rate: int = 24000, sample_width: int = 2) -> bytes:
    """Generate silence as raw PCM bytes."""
    num_samples = int(rate * duration_ms / 1000)
    return b"\x00" * (num_samples * sample_width)


def synthesize_audio(raw_transcript: str, output_wav: str) -> bool:
    """Synthesize audio from transcript using Gemini 2.5 Flash TTS."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("[PODCAST] ERROR: google-genai package not installed. Run: pip install google-genai")
        return False

    api_key = GEMINI_API_KEY
    if not api_key:
        print("[PODCAST] ERROR: GEMINI_API_KEY not set")
        return False

    # Convert tags to speaker names
    transcript = convert_tags_to_speaker_names(raw_transcript)

    # Split into chunks
    chunks = split_into_chunks(transcript, max_lines=8)
    print(f"[PODCAST] Split transcript into {len(chunks)} TTS chunks")

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    all_audio = bytearray()
    silence = add_silence(400)

    failed_chunks = []
    for i, chunk in enumerate(chunks):
        prompt = f"TTS the following conversation between 小晓 and 云希:\n{chunk}"

        retry_count = 0
        max_retries = 8  # More retries to handle rate limits
        chunk_success = False
        while retry_count < max_retries:
            try:
                print(f"[PODCAST]   TTS chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
                response = client.models.generate_content(
                    model="gemini-2.5-flash-preview-tts",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                                speaker_voice_configs=[
                                    types.SpeakerVoiceConfig(
                                        speaker="小晓",
                                        voice_config=types.VoiceConfig(
                                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                                voice_name=SPEAKER1_VOICE,
                                            )
                                        ),
                                    ),
                                    types.SpeakerVoiceConfig(
                                        speaker="云希",
                                        voice_config=types.VoiceConfig(
                                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                                voice_name=SPEAKER2_VOICE,
                                            )
                                        ),
                                    ),
                                ]
                            )
                        ),
                    ),
                )

                audio_data = response.candidates[0].content.parts[0].inline_data.data
                all_audio.extend(audio_data)
                if i < len(chunks) - 1:
                    all_audio.extend(silence)
                print(f"[PODCAST]   Chunk {i + 1} done: {len(audio_data)} bytes")
                chunk_success = True
                break

            except Exception as e:
                retry_count += 1
                err_str = str(e)
                print(f"[PODCAST]   ERROR on chunk {i + 1}: {err_str[:200]}")

                if retry_count < max_retries:
                    # Parse retry delay from error if available
                    wait_time = 65  # default: wait 65s for rate limit reset
                    delay_match = re.search(r'retryDelay.*?(\d+)s', err_str)
                    if delay_match:
                        wait_time = int(delay_match.group(1)) + 5  # add 5s buffer
                    elif '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str:
                        wait_time = 65  # rate limit: wait a full minute
                    else:
                        wait_time = 15 * retry_count  # non-rate-limit errors

                    print(f"[PODCAST]   Retrying in {wait_time}s (attempt {retry_count + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"[PODCAST]   FAILED after {max_retries} attempts on chunk {i + 1}")

        if not chunk_success:
            failed_chunks.append(i + 1)

        # Rate limiting delay between chunks (Gemini free tier: 10 RPM)
        # Wait 12s between chunks to stay safely under limit (~5 req/min)
        if i < len(chunks) - 1:
            time.sleep(12)

    if failed_chunks:
        print(f"[PODCAST] ERROR: {len(failed_chunks)} chunk(s) failed: {failed_chunks}")
        print(f"[PODCAST] Audio would be incomplete — aborting to avoid truncated podcast")
        return False

    if not all_audio:
        print("[PODCAST] ERROR: No audio generated")
        return False

    # Save as WAV
    wave_file(output_wav, bytes(all_audio))
    print(f"[PODCAST] WAV saved: {output_wav}")
    return True


def convert_to_mp3(wav_path: str, mp3_path: str, bitrate: str = "64k") -> bool:
    """Convert WAV to MP3 using ffmpeg."""
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", wav_path,
            "-codec:a", "libmp3lame", "-b:a", bitrate,
            mp3_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[PODCAST] ffmpeg error: {result.stderr}")
        return False

    # Get file info
    mp3_size = os.path.getsize(mp3_path) / (1024 * 1024)

    # Get duration
    probe = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            mp3_path,
        ],
        capture_output=True,
        text=True,
    )
    duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0

    print(f"[PODCAST] MP3 saved: {mp3_path}")
    print(f"[PODCAST]   Duration: {duration:.0f}s ({duration / 60:.1f} min)")
    print(f"[PODCAST]   Size: {mp3_size:.1f} MB")
    print(f"[PODCAST]   Bitrate: {bitrate}")

    return True


# ---------------------------------------------------------------------------
# Step 6: Upload to GitHub Releases (monthly release, daily append)
# ---------------------------------------------------------------------------
def upload_to_release(files: list, target_date: datetime, repo: str = "") -> bool:
    """Upload files to a monthly GitHub Release.

    Creates the release if it doesn't exist, otherwise appends files.

    Args:
        files: List of file paths to upload
        target_date: The date of the podcast
        repo: GitHub repo in owner/repo format (auto-detected if empty)
    """
    tag = f"podcast-{target_date.strftime('%Y-%m')}"
    title = f"HN Podcast - {target_date.strftime('%B %Y')}"
    body = (
        f"Daily HN podcast audio and transcripts for {target_date.strftime('%B %Y')}.\n\n"
        "Each day includes:\n"
        "- MP3 audio (Chinese, 64kbps)\n"
        "- Markdown transcript (Chinese-English mixed)\n\n"
        "Files are named `hn-podcast-YYYY-MM-DD.*`"
    )

    repo_flag = f"--repo {repo}" if repo else ""

    # Check if release already exists
    check_cmd = f"gh release view {tag} {repo_flag} 2>/dev/null"
    result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        # Create new release
        print(f"[PODCAST] Creating new release: {tag}")
        file_args = " ".join(f'"{f}"' for f in files)
        create_cmd = (
            f'gh release create {tag} {file_args} '
            f'--title "{title}" '
            f'--notes "{body}" '
            f'{repo_flag}'
        )
        result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[PODCAST] ERROR creating release: {result.stderr}")
            return False
        print(f"[PODCAST] Release created: {tag}")
    else:
        # Upload to existing release (overwrite if same filename exists)
        print(f"[PODCAST] Uploading to existing release: {tag}")
        file_args = " ".join(f'"{f}"' for f in files)
        upload_cmd = f"gh release upload {tag} {file_args} --clobber {repo_flag}"
        result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[PODCAST] ERROR uploading: {result.stderr}")
            return False
        print(f"[PODCAST] Files uploaded to release: {tag}")

    # Print download URLs
    for f in files:
        fname = os.path.basename(f)
        # Determine repo for URL
        if repo:
            url_repo = repo
        else:
            # Try to detect from git remote
            detect = subprocess.run(
                "gh repo view --json nameWithOwner -q .nameWithOwner",
                shell=True, capture_output=True, text=True,
            )
            url_repo = detect.stdout.strip() if detect.returncode == 0 else "OWNER/REPO"
        url = f"https://github.com/{url_repo}/releases/download/{tag}/{fname}"
        print(f"[PODCAST]   {fname}: {url}")

    return True


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def generate_daily_podcast(
    base_dir: str = BASE_DIR,
    target_date: datetime = None,
    skip_upload: bool = False,
    repo: str = "",
) -> dict:
    """Run the full podcast generation pipeline.

    Returns a dict with paths and metadata, or empty dict on failure.
    """
    t_start = time.time()

    if target_date is None:
        # Default to yesterday (since best stories are typically from yesterday)
        target_date = datetime.now() - timedelta(days=1)

    date_tag = target_date.strftime("%Y-%m-%d")
    print(f"\n{'=' * 60}")
    print(f"[PODCAST] Generating podcast for {date_tag}")
    print(f"{'=' * 60}")

    # Ensure work directory
    os.makedirs(WORK_DIR, exist_ok=True)

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

    # --- Step 2: Prepare news text ---
    print(f"\n[PODCAST] Step 2: Preparing news text...")
    news_text = prepare_news_text(items, date_str)
    print(f"[PODCAST] News text: {len(news_text)} characters")

    # --- Step 3: Generate transcript ---
    print(f"\n[PODCAST] Step 3: Generating transcript...")
    raw_transcript = generate_transcript(news_text)

    # Save raw transcript
    raw_path = os.path.join(WORK_DIR, f"transcript_raw_{date_tag}.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_transcript)

    # --- Step 4: Convert to Markdown ---
    print(f"\n[PODCAST] Step 4: Converting to Markdown transcript...")
    md_transcript = transcript_to_markdown(raw_transcript, date_str)

    transcript_filename = f"{PODCAST_PREFIX}-{date_tag}-transcript.md"
    transcript_path = os.path.join(WORK_DIR, transcript_filename)
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(md_transcript)
    print(f"[PODCAST] Transcript saved: {transcript_path}")

    # --- Step 5: Synthesize audio ---
    print(f"\n[PODCAST] Step 5: Synthesizing audio via Gemini TTS...")
    wav_path = os.path.join(WORK_DIR, f"podcast_{date_tag}.wav")
    success = synthesize_audio(raw_transcript, wav_path)
    if not success:
        print("[PODCAST] Audio synthesis failed")
        return {}

    # --- Step 6: Convert to MP3 ---
    print(f"\n[PODCAST] Step 6: Converting to MP3...")
    mp3_filename = f"{PODCAST_PREFIX}-{date_tag}.mp3"
    mp3_path = os.path.join(WORK_DIR, mp3_filename)
    success = convert_to_mp3(wav_path, mp3_path, bitrate=MP3_BITRATE)
    if not success:
        print("[PODCAST] MP3 conversion failed")
        return {}

    # Clean up WAV
    try:
        os.remove(wav_path)
    except OSError:
        pass

    # --- Step 7: Upload to GitHub Releases ---
    release_tag = f"podcast-{target_date.strftime('%Y-%m')}"
    upload_files = [mp3_path, transcript_path]

    if skip_upload:
        print(f"\n[PODCAST] Step 7: Skipping upload (--skip-upload)")
    else:
        print(f"\n[PODCAST] Step 7: Uploading to GitHub Releases...")
        upload_success = upload_to_release(upload_files, target_date, repo=repo)
        if not upload_success:
            print("[PODCAST] WARNING: Upload failed, files saved locally")

    # --- Step 8: Create .podcast marker file ---
    # This marker is used by index_updater and md_writer to know which dates
    # actually have a podcast available (avoids showing player for dates without audio)
    marker_dir = os.path.join(
        base_dir, target_date.strftime("%Y"), target_date.strftime("%m"),
        target_date.strftime("%d")
    )
    os.makedirs(marker_dir, exist_ok=True)
    marker_path = os.path.join(marker_dir, ".podcast")
    with open(marker_path, "w") as f:
        f.write(f"mp3={mp3_filename}\ntranscript={transcript_filename}\nrelease={release_tag}\n")
    print(f"[PODCAST] Marker created: {marker_path}")

    # --- Summary ---
    elapsed = time.time() - t_start
    mp3_size = os.path.getsize(mp3_path) / (1024 * 1024)

    print(f"\n{'=' * 60}")
    print(f"[PODCAST] DONE! Total time: {elapsed:.1f}s")
    print(f"[PODCAST]   MP3: {mp3_path} ({mp3_size:.1f} MB)")
    print(f"[PODCAST]   Transcript: {transcript_path}")
    print(f"{'=' * 60}")

    # Determine download URL
    detect = subprocess.run(
        "gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null",
        shell=True, capture_output=True, text=True,
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

    return {
        "date": date_tag,
        "mp3_path": mp3_path,
        "mp3_filename": mp3_filename,
        "mp3_url": mp3_url,
        "transcript_path": transcript_path,
        "transcript_filename": transcript_filename,
        "transcript_url": transcript_url,
        "release_tag": release_tag,
        "duration_sec": 0,  # filled by caller if needed
        "size_mb": mp3_size,
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

    print(f"\n[PODCAST] Success! MP3 URL: {result['mp3_url']}")


if __name__ == "__main__":
    main()
