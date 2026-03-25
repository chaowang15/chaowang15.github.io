"""
Weekly Podcast Generator — Generate weekly CN + EN podcasts from HN Weekly Digest.

Pipeline:
  1. Load weekly digest JSON (hackernews/weekly/YYYY-WNN.json)
  2. Take the top 30 stories
  3. Randomly select voice pairs (CN + EN)
  4. Generate brief dialogue transcripts via LLM (one person says title, other comments)
  5. Convert raw transcripts to reading-friendly Markdown
  6. Synthesize CN audio via Azure Speech TTS, EN audio via OpenAI gpt-4o-mini-tts
  7. Upload MP3 + transcripts to GitHub Releases

Usage:
  python news_scraper/podcast_weekly_generator.py                  # auto-detect last week
  python news_scraper/podcast_weekly_generator.py --week 2026-W12  # specific week
  python news_scraper/podcast_weekly_generator.py --skip-upload     # no release upload
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
OPENAI_TTS_KEY = os.environ.get("OPENAI_TTS_KEY", "")
AZURE_SPEECH_KEY = os.environ.get("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.environ.get("AZURE_SPEECH_REGION", "westus")

LLM_MODEL = "gpt-4.1-mini"
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 4000

TTS_MODEL = "gpt-4o-mini-tts"

WEEKLY_DIR = "hackernews/weekly"
WORK_DIR = "/tmp/podcast_work"

# Weekly podcast: top 30 stories, brief format
WEEKLY_STORIES_COUNT = 30

# ---------------------------------------------------------------------------
# Chinese Voice Pairs (Azure TTS) — same pool as daily podcast
# ---------------------------------------------------------------------------
CN_VOICE_PAIRS = [
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
        "male_style": "chat",
    },
    {
        "female_voice": "zh-CN-XiaoyouMultilingualNeural",
        "female_name": "晓悠",
        "female_style": "chat",
        "male_voice": "zh-CN-YunjianNeural",
        "male_name": "云健",
        "male_style": "chat",
    },
    {
        "female_voice": "zh-CN-XiaoyiNeural",
        "female_name": "晓伊",
        "female_style": "chat",
        "male_voice": "zh-CN-YunyeNeural",
        "male_name": "云野",
        "male_style": "chat",
    },
    {
        "female_voice": "zh-CN-XiaoxiaoNeural",
        "female_name": "晓晓",
        "female_style": "chat",
        "male_voice": "zh-CN-YunfengNeural",
        "male_name": "云枫",
        "male_style": "chat",
    },
    {
        "female_voice": "zh-CN-XiaochenNeural",
        "female_name": "晓辰",
        "female_style": "chat",
        "male_voice": "zh-CN-YunyeNeural",
        "male_name": "云野",
        "male_style": "chat",
    },
    {
        "female_voice": "zh-CN-XiaoxiaoNeural",
        "female_name": "晓晓",
        "female_style": "chat",
        "male_voice": "zh-CN-YunyiMultilingualNeural",
        "male_name": "云逸",
        "male_style": "chat",
    },
    {
        "female_voice": "zh-CN-XiaoyuMultilingualNeural",
        "female_name": "晓语",
        "female_style": "chat",
        "male_voice": "zh-CN-YunjianNeural",
        "male_name": "云健",
        "male_style": "chat",
    },
]

# ---------------------------------------------------------------------------
# English Voice Pairs (OpenAI gpt-4o-mini-tts) — same pool as daily EN podcast
# ---------------------------------------------------------------------------
EN_VOICE_PAIRS = [
    {
        "female_voice": "marin",
        "female_name": "Marin",
        "female_instructions": (
            "You are a female podcast co-host. Speak in a warm, upbeat, "
            "conversational tone like you're chatting with a close friend about tech news. "
            "Be enthusiastic and expressive. Vary your pacing naturally."
        ),
        "male_voice": "cedar",
        "male_name": "Cedar",
        "male_instructions": (
            "You are a male podcast co-host. Speak in a relaxed, thoughtful, "
            "conversational tone. React naturally to topics with genuine interest. "
            "Sound like you're having a real conversation."
        ),
    },
    {
        "female_voice": "nova",
        "female_name": "Nova",
        "female_instructions": (
            "You are a female podcast co-host. Speak in a warm, upbeat, "
            "conversational tone. Be enthusiastic and expressive. "
            "Vary your pacing naturally — speed up when excited, slow down for emphasis."
        ),
        "male_voice": "onyx",
        "male_name": "Onyx",
        "male_instructions": (
            "You are a male podcast co-host. Speak in a deep, relaxed, "
            "conversational tone. React naturally with genuine interest and occasional humor. "
            "Vary your intonation and add natural pauses."
        ),
    },
    {
        "female_voice": "coral",
        "female_name": "Coral",
        "female_instructions": (
            "You are a female podcast co-host. Speak in a bright, engaging, "
            "conversational tone. Be curious and enthusiastic about tech topics. "
            "Use natural pauses between thoughts."
        ),
        "male_voice": "ash",
        "male_name": "Ash",
        "male_instructions": (
            "You are a male podcast co-host. Speak in a calm, thoughtful, "
            "conversational tone. Offer insightful observations with a touch of wit. "
            "Sound natural and unrehearsed."
        ),
    },
]


# ---------------------------------------------------------------------------
# Voice pair selection (deterministic per week)
# ---------------------------------------------------------------------------
def _select_pair(pairs: list, week_tag: str, salt: str = "") -> dict:
    """Select a voice pair deterministically based on week tag."""
    h = int(hashlib.md5(f"{week_tag}{salt}".encode()).hexdigest(), 16)
    idx = h % len(pairs)
    pair = pairs[idx]
    return pair


# ---------------------------------------------------------------------------
# Step 1: Load weekly digest data
# ---------------------------------------------------------------------------
def load_weekly_json(weekly_dir: str, iso_week: str) -> tuple:
    """Load weekly digest JSON and return (items, meta)."""
    json_path = os.path.join(weekly_dir, f"{iso_week}.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Weekly digest JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    meta = data.get("meta", {})
    return items, meta


# ---------------------------------------------------------------------------
# Step 2: Prepare news text for LLM
# ---------------------------------------------------------------------------
def prepare_weekly_news_text(items: list, iso_week: str, meta: dict) -> str:
    """Format weekly news items into a text block for LLM input."""
    date_start = meta.get("date_start", "")
    date_end = meta.get("date_end", "")
    date_range = f"{date_start} to {date_end}" if date_start else iso_week

    lines = [
        f"Hacker News Weekly Digest — {iso_week} ({date_range})",
        f"The following are the top {len(items)} stories from Hacker News this week.",
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
# Step 3: Generate dialogue transcripts via LLM
# ---------------------------------------------------------------------------
def _build_cn_weekly_prompt(voice_pair: dict) -> str:
    """Build Chinese weekly podcast system prompt — brief format with role switching."""
    fn = voice_pair["female_name"]
    mn = voice_pair["male_name"]

    return f"""你是一个专业的播客脚本编剧。你需要将一组 Hacker News 每周精选新闻转化为一段双人对话形式的播客脚本。

播客名称：HN Weekly Digest（HN 每周精选）
主持人：{fn}（女，活泼开朗）和{mn}（男，沉稳有见解）

这是一个快节奏的"速览"式播客，每条新闻只需要简短提及：
- 一个人用一句话介绍新闻标题和核心内容
- 另一个人用一句话做简短评论或补充

重要：对于每条新闻，随机切换谁先介绍标题、谁做评论。不要总是同一个人先说。大约一半的新闻由{fn}先介绍，另一半由{mn}先介绍。

语言风格要求：
1. 主体语言用中文，语气自然、口语化
2. 新闻标题用中文说，不保留英文原标题
3. 技术关键词保留英文：GDPR、API、AI、LLM、RSS、Git 等
4. 中英文之间加空格

内容要求：
1. 开场：简短介绍本周精选概况（2-3 句）
2. 主体：逐条快速过新闻，每条新闻只需 2 句话（一人介绍 + 一人评论）
3. 结尾：简短总结并告别（2-3 句）
4. 从第二条新闻开始，介绍标题的人必须先说一个简短的过渡词再引出标题，例如"接下来"、"下一条"、"然后是"、"再来看看"、"说到这个"等。过渡词要自然多样，不要每次都用同一个。第一条新闻不需要过渡词。
5. 总字数严格控制在 3000 字以内（约 8 分钟音频）

输出格式：
严格使用 <Person1> 和 <Person2> 标签包裹每段对话。
Person1 = {fn}（女主持）
Person2 = {mn}（男主持）

关键格式规则（必须严格遵守）：
- 每一行对话必须同时有开始标签和结束标签
- 开始和结束标签必须匹配：<Person1>文字</Person1> 或 <Person2>文字</Person2>
- 绝对不要遗漏结束标签
- 绝对不要使用不匹配的标签
- 对话内容中不要重复说出主持人的名字，只在开场自我介绍时提一次即可

示例：
<Person1>大家好，欢迎收听 HN Weekly Digest！我是{fn}。</Person1>
<Person2>我是{mn}。这周的 Hacker News 精选非常丰富，我们来快速过一遍！</Person2>
<Person1>第一条，关于 Polymarket 赌徒威胁记者的事件，真的挺震惊的。</Person1>
<Person2>是啊，这说明预测市场的影响力已经远超金融领域了。</Person2>
<Person2>接下来，Astral 宣布加入 OpenAI，这在 Python 社区引起了不小的讨论。</Person2>
<Person1>确实，很多人担心开源工具的未来走向。</Person1>
<Person1>再来看看，有个关于 Rust 重写系统组件的热门讨论。</Person1>
<Person2>这个话题每次都能引发激烈争论。</Person2>
"""


def _build_en_weekly_prompt(voice_pair: dict) -> str:
    """Build English weekly podcast system prompt — brief format with role switching."""
    fn = voice_pair["female_name"]
    mn = voice_pair["male_name"]

    return (
        "You are a professional podcast script writer. Transform a set of "
        "Hacker News weekly top stories into a fast-paced two-host podcast script.\n\n"
        f"Podcast name: HN Weekly Digest\n"
        f"Hosts: {fn} (female, energetic) and {mn} (male, thoughtful)\n\n"
        "This is a quick-fire 'roundup' style podcast. For each story:\n"
        "- One person introduces the story title and key point in ONE sentence\n"
        "- The other person gives a brief comment or reaction in ONE sentence\n\n"
        f"IMPORTANT: For each story, randomly alternate who introduces the title "
        f"and who comments. Don't always have the same person go first. "
        f"Roughly half the stories should be introduced by {fn}, half by {mn}.\n\n"
        "Style: Conversational, natural, like two tech friends doing a quick weekly recap.\n\n"
        "Content requirements:\n"
        "1. Brief intro (2-3 sentences)\n"
        "2. Cover each story in exactly 2 lines (one intro + one comment)\n"
        "3. Brief sign-off (2-3 sentences)\n"
        "4. Starting from the SECOND story, the person introducing the title MUST begin "
        "with a brief transition phrase before stating the title, such as 'Next up', "
        "'Moving on', 'Now let's look at', 'Also making waves', 'Speaking of which', "
        "'Another interesting one', etc. Vary the transitions naturally — do NOT repeat "
        "the same phrase. The first story does NOT need a transition.\n"
        "5. STRICT word limit: under 2500 words total (~7 minutes audio)\n"
        "6. Do NOT repeat speaker names in dialogue. Names only in intro/sign-off.\n\n"
        "Output format:\n"
        "Use <Person1> and <Person2> XML tags.\n"
        f"Person1 = {fn} (female host)\n"
        f"Person2 = {mn} (male host)\n\n"
        "CRITICAL FORMAT RULES:\n"
        "- EVERY line MUST have BOTH opening AND closing tags on the SAME line\n"
        "- Tags MUST match: <Person1>text</Person1> or <Person2>text</Person2>\n"
        "- NEVER omit closing tags or use mismatched tags\n\n"
        "Example:\n"
        f"<Person1>Hey everyone, welcome to HN Weekly Digest! I'm {fn}.</Person1>\n"
        f"<Person2>And I'm {mn}. Packed week — let's jump right in!</Person2>\n"
        "<Person1>First up, Polymarket gamblers are threatening journalists over an Iran missile story.</Person1>\n"
        "<Person2>Wild stuff. Prediction markets are getting way too personal.</Person2>\n"
        "<Person2>Moving on, Astral is joining OpenAI, which has the Python community buzzing.</Person2>\n"
        "<Person1>Yeah, a lot of folks are worried about what happens to their open-source tools.</Person1>\n"
        "<Person1>Also making waves, there's a heated debate about rewriting system components in Rust.</Person1>\n"
        "<Person2>Classic topic — never fails to spark strong opinions.</Person2>\n"
    )


def _fix_transcript_tags(text: str) -> str:
    """Fix common LLM formatting issues in transcript tags."""
    fixed_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            fixed_lines.append(line)
            continue
        open_match = re.match(r"^<(Person[12])>", stripped)
        if open_match:
            speaker = open_match.group(1)
            close_match = re.search(r"</(Person[12])>\s*$", stripped)
            if close_match:
                close_speaker = close_match.group(1)
                if close_speaker != speaker:
                    stripped = re.sub(r"</(Person[12])>\s*$", f"</{speaker}>", stripped)
            else:
                stripped = f"{stripped.rstrip()}</{speaker}>"
        fixed_lines.append(stripped)
    return "\n".join(fixed_lines)


def _parse_dialogue_segments(text: str) -> list:
    """Parse dialogue segments from transcript. Returns list of (speaker, content)."""
    pattern = r"<(Person[12])>(.*?)</\1>"
    segments = re.findall(pattern, text, re.DOTALL)
    segments = [(s, c.strip()) for s, c in segments if c.strip()]

    if len(segments) >= 5:
        return segments

    # Fallback parser
    print(f"[WEEKLY-PODCAST] WARNING: Only {len(segments)} matched, trying fallback")
    fallback = []
    parts = re.split(r"<(Person[12])>", text)
    i = 1
    while i < len(parts) - 1:
        speaker = parts[i]
        content = re.sub(r"</(Person[12])>", "", parts[i + 1]).strip()
        if content:
            fallback.append((speaker, content))
        i += 2
    return fallback


def generate_transcript(news_text: str, voice_pair: dict, lang: str) -> str:
    """Generate podcast transcript using LLM."""
    from openai import OpenAI

    client = OpenAI()  # Uses OPENAI_API_KEY env var

    if lang == "cn":
        system_prompt = _build_cn_weekly_prompt(voice_pair)
        user_prompt = (
            "请根据以下 Hacker News 每周精选新闻数据，"
            "生成一段快节奏的中文双人播客对话脚本：\n\n"
            f"{news_text}"
        )
        label = "WEEKLY-CN"
    else:
        system_prompt = _build_en_weekly_prompt(voice_pair)
        user_prompt = (
            "Please generate a fast-paced English two-host podcast dialogue "
            "based on the following Hacker News weekly top stories:\n\n"
            f"{news_text}"
        )
        label = "WEEKLY-EN"

    print(f"[{label}] Generating transcript via LLM...")
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

    # Fix tags
    transcript = _fix_transcript_tags(transcript)

    print(f"[{label}] Transcript: {len(transcript)} chars in {elapsed:.1f}s")
    print(f"[{label}] Tokens: in={usage.prompt_tokens}, out={usage.completion_tokens}")
    cost = usage.prompt_tokens * 0.4 / 1e6 + usage.completion_tokens * 1.6 / 1e6
    print(f"[{label}] LLM cost: ${cost:.4f}")

    # LLM post-validation
    from transcript_validator import validate_transcript
    transcript = validate_transcript(transcript, label=label)

    segments = _parse_dialogue_segments(transcript)
    print(f"[{label}] Parsed {len(segments)} dialogue segments")

    return transcript


# ---------------------------------------------------------------------------
# Step 4: Convert to Markdown
# ---------------------------------------------------------------------------
def transcript_to_markdown(raw: str, iso_week: str, voice_pair: dict, lang: str) -> str:
    """Convert tagged transcript to readable Markdown."""
    fn = voice_pair["female_name"]
    mn = voice_pair["male_name"]

    if lang == "cn":
        lines = [
            f"# HN 每周精选播客 — {iso_week}",
            "",
            f"> HN Weekly Digest Podcast — {iso_week}",
            f"> 主持人：{fn} & {mn}",
        ]
        footer = "*本播客由 AI 自动生成，内容基于 Hacker News 每周精选新闻。*"
    else:
        lines = [
            f"# HN Weekly Digest Podcast (English) — {iso_week}",
            "",
            f"> HN Weekly Digest English Podcast — {iso_week}",
            f"> Hosts: {fn} & {mn}",
        ]
        footer = "*This podcast is auto-generated by AI based on Hacker News weekly digest.*"

    lines.extend(["", "---", ""])

    segments = _parse_dialogue_segments(raw)
    for speaker, content in segments:
        name = fn if speaker == "Person1" else mn
        sep = "：" if lang == "cn" else ":"
        lines.append(f"**{name}{sep}** {content}")
        lines.append("")

    lines.extend(["---", "", footer])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 5a: Synthesize Chinese audio via Azure TTS
# ---------------------------------------------------------------------------
def _build_ssml_chunk(segments: list, voice_pair: dict) -> str:
    """Build SSML for Azure TTS."""
    ssml_parts = [
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">'
    ]
    for speaker, content in segments:
        content = content.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if speaker == "Person1":
            voice_id = voice_pair["female_voice"]
            style = voice_pair["female_style"]
        else:
            voice_id = voice_pair["male_voice"]
            style = voice_pair["male_style"]
        ssml_parts.append(
            f'  <voice name="{voice_id}">\n'
            f'    <mstts:express-as xmlns:mstts="http://www.w3.org/2001/mstts" style="{style}">\n'
            f'      {content}\n'
            f'    </mstts:express-as>\n'
            f'  </voice>'
        )
    ssml_parts.append('</speak>')
    return '\n'.join(ssml_parts)


def synthesize_cn_audio(raw_transcript: str, output_mp3: str, voice_pair: dict) -> bool:
    """Synthesize Chinese audio via Azure Speech TTS."""
    MAX_SEGMENTS_PER_CHUNK = 25

    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        print("[WEEKLY-CN] ERROR: azure-cognitiveservices-speech not installed")
        return False

    if not AZURE_SPEECH_KEY:
        print("[WEEKLY-CN] ERROR: AZURE_SPEECH_KEY not set")
        return False

    segments = _parse_dialogue_segments(raw_transcript)
    if not segments:
        print("[WEEKLY-CN] WARNING: No dialogue segments")
        return False

    total = len(segments)
    print(f"[WEEKLY-CN] Total segments: {total}")

    t0 = time.time()

    if total <= MAX_SEGMENTS_PER_CHUNK:
        ssml = _build_ssml_chunk(segments, voice_pair)
        print(f"[WEEKLY-CN] SSML: {len(ssml)} chars (single chunk)")

        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
        )
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_mp3)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            cancellation = result.cancellation_details
            print(f"[WEEKLY-CN] ERROR: {cancellation.reason} — {cancellation.error_details}")
            return False
    else:
        # Chunked synthesis
        chunks = [segments[i:i + MAX_SEGMENTS_PER_CHUNK] for i in range(0, total, MAX_SEGMENTS_PER_CHUNK)]
        chunk_files = []

        for idx, chunk_segs in enumerate(chunks):
            ssml = _build_ssml_chunk(chunk_segs, voice_pair)
            chunk_path = os.path.join(WORK_DIR, f"weekly_cn_chunk_{idx:02d}.mp3")
            print(f"[WEEKLY-CN] Chunk {idx + 1}/{len(chunks)}: {len(chunk_segs)} segments")

            speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
            )
            audio_config = speechsdk.audio.AudioOutputConfig(filename=chunk_path)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            result = synthesizer.speak_ssml_async(ssml).get()

            if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
                cancellation = result.cancellation_details
                print(f"[WEEKLY-CN] ERROR chunk {idx + 1}: {cancellation.reason} — {cancellation.error_details}")
                return False
            chunk_files.append(chunk_path)

        # Concatenate
        concat_list = os.path.join(WORK_DIR, "weekly_cn_concat.txt")
        with open(concat_list, "w") as f:
            for cf in chunk_files:
                f.write(f"file '{cf}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", output_mp3],
            capture_output=True, text=True,
        )
        for cf in chunk_files:
            os.remove(cf)
        os.remove(concat_list)

    elapsed = time.time() - t0
    mp3_size = os.path.getsize(output_mp3) / (1024 * 1024)
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", output_mp3],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
    print(f"[WEEKLY-CN] Azure TTS done in {elapsed:.1f}s — {duration:.0f}s ({duration/60:.1f} min), {mp3_size:.1f} MB")
    return True


# ---------------------------------------------------------------------------
# Step 5b: Synthesize English audio via OpenAI gpt-4o-mini-tts
# ---------------------------------------------------------------------------
def synthesize_en_audio(raw_transcript: str, output_mp3: str, voice_pair: dict) -> bool:
    """Synthesize English audio via OpenAI TTS (per-segment concat)."""
    from openai import OpenAI
    from pydub import AudioSegment

    if not OPENAI_TTS_KEY:
        print("[WEEKLY-EN] ERROR: OPENAI_TTS_KEY not set")
        return False

    client = OpenAI(api_key=OPENAI_TTS_KEY, base_url="https://api.openai.com/v1")

    segments = _parse_dialogue_segments(raw_transcript)
    if not segments:
        print("[WEEKLY-EN] WARNING: No dialogue segments")
        return False

    total = len(segments)
    total_chars = sum(len(c) for _, c in segments)
    print(f"[WEEKLY-EN] Segments: {total}, chars: {total_chars}")

    seg_dir = os.path.join(WORK_DIR, "weekly_en_segments")
    os.makedirs(seg_dir, exist_ok=True)

    t0 = time.time()
    ok = 0

    for i, (speaker, content) in enumerate(segments):
        voice = voice_pair["female_voice"] if speaker == "Person1" else voice_pair["male_voice"]
        inst = voice_pair["female_instructions"] if speaker == "Person1" else voice_pair["male_instructions"]
        seg_path = os.path.join(seg_dir, f"seg_{i:03d}.mp3")

        try:
            with client.audio.speech.with_streaming_response.create(
                model=TTS_MODEL,
                voice=voice,
                input=content,
                instructions=inst,
                response_format="mp3",
            ) as response:
                response.stream_to_file(seg_path)
            ok += 1
            if (i + 1) % 10 == 0 or i == total - 1:
                print(f"[WEEKLY-EN] Progress: {i + 1}/{total}")
        except Exception as e:
            print(f"[WEEKLY-EN] ERROR seg {i + 1}: {e}")

    gen_time = time.time() - t0
    print(f"[WEEKLY-EN] TTS: {gen_time:.1f}s ({ok}/{total} ok)")

    if ok < total * 0.8:
        print(f"[WEEKLY-EN] ERROR: Too many failures")
        return False

    # Concatenate
    combined = AudioSegment.empty()
    pause = AudioSegment.silent(duration=300)
    for i in range(total):
        seg_path = os.path.join(seg_dir, f"seg_{i:03d}.mp3")
        if os.path.exists(seg_path) and os.path.getsize(seg_path) > 0:
            if len(combined) > 0:
                combined += pause
            combined += AudioSegment.from_mp3(seg_path)

    combined.export(output_mp3, format="mp3", bitrate="160k")

    # Cleanup
    for i in range(total):
        seg_path = os.path.join(seg_dir, f"seg_{i:03d}.mp3")
        if os.path.exists(seg_path):
            os.remove(seg_path)

    duration = len(combined) / 1000
    mp3_size = os.path.getsize(output_mp3) / (1024 * 1024)
    tts_cost = total_chars * 15 / 1_000_000
    print(f"[WEEKLY-EN] Done: {duration:.0f}s ({duration/60:.1f} min), {mp3_size:.1f} MB, cost=${tts_cost:.4f}")
    return True


# ---------------------------------------------------------------------------
# Step 6: Upload to GitHub Releases
# ---------------------------------------------------------------------------
def upload_to_release(files: list, iso_week: str, repo: str = "") -> bool:
    """Upload files to a monthly GitHub Release (using the week's month)."""
    # Use the Monday of the week to determine the month
    m = re.match(r"^(\d{4})-W(\d{2})$", iso_week)
    if not m:
        return False
    year, week = int(m.group(1)), int(m.group(2))
    jan4 = datetime(year, 1, 4)
    mon_w1 = jan4 - timedelta(days=jan4.weekday())
    monday = mon_w1 + timedelta(weeks=week - 1)

    tag = f"podcast-{monday.strftime('%Y-%m')}"
    title = f"HN Podcast - {monday.strftime('%B %Y')}"
    body = (
        f"HN podcast audio and transcripts for {monday.strftime('%B %Y')}.\n\n"
        "Includes daily and weekly editions in Chinese and English."
    )

    repo_args = ["--repo", repo] if repo else []

    check = subprocess.run(["gh", "release", "view", tag] + repo_args, capture_output=True, text=True)

    if check.returncode != 0:
        print(f"[WEEKLY-PODCAST] Creating release: {tag}")
        result = subprocess.run(
            ["gh", "release", "create", tag] + list(files) + ["--title", title, "--notes", body] + repo_args,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"[WEEKLY-PODCAST] ERROR: {result.stderr}")
            return False
    else:
        print(f"[WEEKLY-PODCAST] Uploading to release: {tag}")
        result = subprocess.run(
            ["gh", "release", "upload", tag] + list(files) + ["--clobber"] + repo_args,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"[WEEKLY-PODCAST] ERROR: {result.stderr}")
            return False

    # Print URLs
    detect = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True, text=True,
    )
    url_repo = detect.stdout.strip() if detect.returncode == 0 else repo or "chaowang15/chaowang15.github.io"
    for f in files:
        fname = os.path.basename(f)
        print(f"[WEEKLY-PODCAST] {fname}: https://github.com/{url_repo}/releases/download/{tag}/{fname}")

    return True


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def generate_weekly_podcast(
    iso_week: str = None,
    weekly_dir: str = WEEKLY_DIR,
    skip_upload: bool = False,
    repo: str = "",
) -> dict:
    """Run the full weekly podcast generation pipeline (CN + EN).

    Returns a dict with paths and metadata, or empty dict on failure.
    """
    t_start = time.time()

    if iso_week is None:
        # Auto-detect last full week
        today = datetime.utcnow()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        iso_year, iso_wk, _ = last_monday.isocalendar()
        iso_week = f"{iso_year}-W{iso_wk:02d}"

    print(f"\n{'=' * 60}")
    print(f"[WEEKLY-PODCAST] Generating weekly podcast for {iso_week}")
    print(f"{'=' * 60}")

    os.makedirs(WORK_DIR, exist_ok=True)

    # --- Load data ---
    try:
        items, meta = load_weekly_json(weekly_dir, iso_week)
    except FileNotFoundError as e:
        print(f"[WEEKLY-PODCAST] {e}")
        return {}

    if not items:
        print("[WEEKLY-PODCAST] No items found, skipping")
        return {}

    print(f"[WEEKLY-PODCAST] Loaded {len(items)} stories")
    items = items[:WEEKLY_STORIES_COUNT]
    print(f"[WEEKLY-PODCAST] Using top {len(items)} stories")

    # --- Select voice pairs ---
    cn_pair = _select_pair(CN_VOICE_PAIRS, iso_week, salt="cn")
    en_pair = _select_pair(EN_VOICE_PAIRS, iso_week, salt="en")
    print(f"[WEEKLY-PODCAST] CN voices: {cn_pair['female_name']} + {cn_pair['male_name']}")
    print(f"[WEEKLY-PODCAST] EN voices: {en_pair['female_name']} + {en_pair['male_name']}")

    # --- Prepare news text ---
    news_text = prepare_weekly_news_text(items, iso_week, meta)

    # --- Generate CN transcript ---
    cn_raw = generate_transcript(news_text, cn_pair, lang="cn")
    cn_raw_path = os.path.join(WORK_DIR, f"weekly_cn_raw_{iso_week}.txt")
    with open(cn_raw_path, "w", encoding="utf-8") as f:
        f.write(cn_raw)

    cn_md = transcript_to_markdown(cn_raw, iso_week, cn_pair, lang="cn")
    cn_transcript_fn = f"hn-weekly-podcast-{iso_week}-transcript.md"
    cn_transcript_path = os.path.join(WORK_DIR, cn_transcript_fn)
    with open(cn_transcript_path, "w", encoding="utf-8") as f:
        f.write(cn_md)

    # --- Generate EN transcript ---
    en_raw = generate_transcript(news_text, en_pair, lang="en")
    en_raw_path = os.path.join(WORK_DIR, f"weekly_en_raw_{iso_week}.txt")
    with open(en_raw_path, "w", encoding="utf-8") as f:
        f.write(en_raw)

    en_md = transcript_to_markdown(en_raw, iso_week, en_pair, lang="en")
    en_transcript_fn = f"hn-weekly-podcast-en-{iso_week}-transcript.md"
    en_transcript_path = os.path.join(WORK_DIR, en_transcript_fn)
    with open(en_transcript_path, "w", encoding="utf-8") as f:
        f.write(en_md)

    # --- Synthesize CN audio ---
    cn_mp3_fn = f"hn-weekly-podcast-{iso_week}.mp3"
    cn_mp3_path = os.path.join(WORK_DIR, cn_mp3_fn)
    print(f"\n[WEEKLY-PODCAST] Synthesizing Chinese audio...")
    cn_ok = synthesize_cn_audio(cn_raw, cn_mp3_path, cn_pair)

    # --- Synthesize EN audio ---
    en_mp3_fn = f"hn-weekly-podcast-en-{iso_week}.mp3"
    en_mp3_path = os.path.join(WORK_DIR, en_mp3_fn)
    print(f"\n[WEEKLY-PODCAST] Synthesizing English audio...")
    en_ok = synthesize_en_audio(en_raw, en_mp3_path, en_pair)

    if not cn_ok and not en_ok:
        print("[WEEKLY-PODCAST] Both audio syntheses failed")
        return {}

    # --- Upload ---
    upload_files = []
    if cn_ok:
        upload_files.extend([cn_mp3_path, cn_transcript_path])
    if en_ok:
        upload_files.extend([en_mp3_path, en_transcript_path])

    if skip_upload:
        print("[WEEKLY-PODCAST] Skipping upload")
    else:
        upload_to_release(upload_files, iso_week, repo=repo)

    # --- Determine URLs ---
    m = re.match(r"^(\d{4})-W(\d{2})$", iso_week)
    year, week = int(m.group(1)), int(m.group(2))
    jan4 = datetime(year, 1, 4)
    mon_w1 = jan4 - timedelta(days=jan4.weekday())
    monday = mon_w1 + timedelta(weeks=week - 1)
    release_tag = f"podcast-{monday.strftime('%Y-%m')}"

    detect = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True, text=True,
    )
    url_repo = detect.stdout.strip() if detect.returncode == 0 else repo or "chaowang15/chaowang15.github.io"

    # --- Write .podcast-weekly marker ---
    marker_path = os.path.join(weekly_dir, f".podcast-{iso_week}")
    marker_lines = [f"week={iso_week}", f"release={release_tag}"]
    if cn_ok:
        marker_lines.extend([
            f"cn_mp3={cn_mp3_fn}",
            f"cn_transcript={cn_transcript_fn}",
            f"cn_female={cn_pair['female_name']}",
            f"cn_male={cn_pair['male_name']}",
        ])
    if en_ok:
        marker_lines.extend([
            f"en_mp3={en_mp3_fn}",
            f"en_transcript={en_transcript_fn}",
            f"en_female={en_pair['female_name']}",
            f"en_male={en_pair['male_name']}",
        ])
    with open(marker_path, "w") as f:
        f.write("\n".join(marker_lines) + "\n")
    print(f"[WEEKLY-PODCAST] Marker: {marker_path}")

    # --- Summary ---
    elapsed = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"[WEEKLY-PODCAST] DONE! Total time: {elapsed:.1f}s")
    if cn_ok:
        cn_size = os.path.getsize(cn_mp3_path) / (1024 * 1024)
        cn_url = f"https://github.com/{url_repo}/releases/download/{release_tag}/{cn_mp3_fn}"
        print(f"[WEEKLY-PODCAST]   CN: {cn_mp3_fn} ({cn_size:.1f} MB) — {cn_url}")
    if en_ok:
        en_size = os.path.getsize(en_mp3_path) / (1024 * 1024)
        en_url = f"https://github.com/{url_repo}/releases/download/{release_tag}/{en_mp3_fn}"
        print(f"[WEEKLY-PODCAST]   EN: {en_mp3_fn} ({en_size:.1f} MB) — {en_url}")
    print(f"{'=' * 60}")

    result = {"week": iso_week, "release_tag": release_tag}
    if cn_ok:
        result["cn_mp3_url"] = f"https://github.com/{url_repo}/releases/download/{release_tag}/{cn_mp3_fn}"
    if en_ok:
        result["en_mp3_url"] = f"https://github.com/{url_repo}/releases/download/{release_tag}/{en_mp3_fn}"
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate HN Weekly Podcast (CN + EN)")
    parser.add_argument("--week", type=str, default="", help="ISO week YYYY-WNN (default: last full week)")
    parser.add_argument("--skip-upload", action="store_true", help="Skip uploading to GitHub Releases")
    parser.add_argument("--weekly-dir", type=str, default=WEEKLY_DIR)
    parser.add_argument("--repo", type=str, default="")
    args = parser.parse_args()

    result = generate_weekly_podcast(
        iso_week=args.week or None,
        weekly_dir=args.weekly_dir,
        skip_upload=args.skip_upload,
        repo=args.repo,
    )

    if not result:
        print("[WEEKLY-PODCAST] Pipeline failed")
        sys.exit(1)

    print(f"\n[WEEKLY-PODCAST] Success!")


if __name__ == "__main__":
    main()
