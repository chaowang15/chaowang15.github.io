"""
English Podcast Generator — Generate daily English podcast from HN Daily Best stories.

Pipeline:
  1. Load today's best_stories JSON
  2. Take the top 20 stories
  3. Randomly select an English voice pair for today
  4. Generate English dialogue transcript via LLM (gpt-4.1-mini)
  5. Convert raw transcript to reading-friendly Markdown
  6. Synthesize audio via Azure Speech TTS (SSML multi-speaker, en-US)
  7. Upload MP3 + transcript to GitHub Releases (monthly release, daily append)

Usage:
  python news_scraper/podcast_en_generator.py              # auto-detect today's best JSON
  python news_scraper/podcast_en_generator.py --date 2026-03-22
  python news_scraper/podcast_en_generator.py --skip-upload
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

LLM_MODEL = "gpt-4.1-mini"
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 4000

PODCAST_PREFIX = "hn-podcast-en"
BASE_DIR = "hackernews"
WORK_DIR = "/tmp/podcast_work"

# English podcast: single episode, top 20 stories
EN_STORIES_COUNT = 20

# ---------------------------------------------------------------------------
# English Voice Pairs — 8 female-male pairs for daily rotation
# ---------------------------------------------------------------------------
EN_VOICE_PAIRS = [
    {
        "female_voice": "en-US-AriaNeural",
        "female_name": "Aria",
        "female_style": "chat",
        "male_voice": "en-US-DavisNeural",
        "male_name": "Davis",
        "male_style": "chat",
    },
    {
        "female_voice": "en-US-JennyNeural",
        "female_name": "Jenny",
        "female_style": "chat",
        "male_voice": "en-US-GuyNeural",
        "male_name": "Guy",
        "male_style": "newscast",
    },
    {
        "female_voice": "en-US-AvaMultilingualNeural",
        "female_name": "Ava",
        "female_style": "chat",
        "male_voice": "en-US-AndrewMultilingualNeural",
        "male_name": "Andrew",
        "male_style": "chat",
    },
    {
        "female_voice": "en-US-EmmaMultilingualNeural",
        "female_name": "Emma",
        "female_style": "chat",
        "male_voice": "en-US-BrianMultilingualNeural",
        "male_name": "Brian",
        "male_style": "chat",
    },
    {
        "female_voice": "en-US-NancyMultilingualNeural",
        "female_name": "Nancy",
        "female_style": "chat",
        "male_voice": "en-US-ChristopherMultilingualNeural",
        "male_name": "Christopher",
        "male_style": "chat",
    },
    {
        "female_voice": "en-US-AriaNeural",
        "female_name": "Aria",
        "female_style": "cheerful",
        "male_voice": "en-US-DavisNeural",
        "male_name": "Davis",
        "male_style": "cheerful",
    },
    {
        "female_voice": "en-US-EmmaMultilingualNeural",
        "female_name": "Emma",
        "female_style": "chat",
        "male_voice": "en-US-DerekMultilingualNeural",
        "male_name": "Derek",
        "male_style": "chat",
    },
    {
        "female_voice": "en-US-AriaNeural",
        "female_name": "Aria",
        "female_style": "chat",
        "male_voice": "en-US-DustinMultilingualNeural",
        "male_name": "Dustin",
        "male_style": "chat",
    },
]


def select_en_voice_pair(date_tag: str) -> dict:
    """Select an English voice pair deterministically based on the date."""
    h = int(hashlib.md5(f"en-{date_tag}".encode()).hexdigest(), 16)
    idx = h % len(EN_VOICE_PAIRS)
    pair = EN_VOICE_PAIRS[idx]
    print(f"[EN-PODCAST] Voice pair selected: {pair['female_name']} + {pair['male_name']} (pair {idx + 1})")
    return pair


# ---------------------------------------------------------------------------
# Step 1: Load news data
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
def prepare_news_text(items: list, date_str: str) -> str:
    """Format news items into a text block for LLM input."""
    lines = [
        f"Hacker News Daily Best Stories — {date_str}",
        f"The following are the top {len(items)} stories from Hacker News on {date_str}.",
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
# Step 3: Generate English dialogue transcript via LLM
# ---------------------------------------------------------------------------
def build_en_system_prompt(voice_pair: dict) -> str:
    """Build the LLM system prompt for English podcast."""
    female_name = voice_pair["female_name"]
    male_name = voice_pair["male_name"]

    return (
        "You are a professional podcast script writer. Your task is to transform "
        "a set of Hacker News daily best stories into a two-host conversational "
        "podcast script in English.\n\n"
        "Podcast name: HN Daily Best\n"
        f"Hosts: {female_name} (female, energetic and curious) and "
        f"{male_name} (male, thoughtful and insightful)\n\n"
        "Style requirements:\n"
        "1. Conversational and natural — like two tech enthusiasts chatting over coffee\n"
        "2. Keep technical terms as-is (e.g., GDPR, API, GrapheneOS, RSS, Git, FPGA, AI, LLM)\n"
        "3. Be engaging with back-and-forth banter, occasional humor, and genuine reactions\n"
        f"4. Each host should have distinct personality — {female_name} is more enthusiastic, "
        f"{male_name} is more analytical\n\n"
        "Content requirements:\n"
        "1. Try to cover ALL given stories — breadth over depth\n"
        "2. Keep discussion of each story very concise: top stories get 2-3 sentences, "
        "lower-ranked ones get 1 sentence\n"
        "3. Include a brief intro and a brief sign-off\n"
        "4. STRICT word limit: under 2500 words total (approximately 6-7 minutes of audio). "
        "This is a hard limit — better to say less about each story than to exceed it.\n\n"
        "Output format:\n"
        "Use <Person1> and <Person2> XML tags to wrap each dialogue segment.\n"
        f"Person1 = {female_name} (female host)\n"
        f"Person2 = {male_name} (male host)\n\n"
        "CRITICAL FORMAT RULES — you MUST follow these exactly:\n"
        "- EVERY dialogue line MUST have BOTH an opening AND a closing tag on the SAME line\n"
        "- Opening and closing tags MUST match: <Person1>text</Person1> or <Person2>text</Person2>\n"
        "- NEVER omit the closing tag\n"
        "- NEVER use mismatched tags like <Person1>text</Person2>\n"
        "- Each tag pair contains exactly one speaker's turn\n"
        "- Do NOT use any other format (no markdown bold, no name prefixes)\n\n"
        "Example (follow this format exactly):\n"
        f"<Person1>Hey everyone, welcome to HN Daily Best! I'm {female_name}.</Person1>\n"
        f"<Person2>And I'm {male_name}. We've got a packed show today — let's dive right in!</Person2>\n"
        "<Person1>Our first story today is about a supply-chain attack on a popular Python package.</Person1>\n"
        "<Person2>That's right. It's a stark reminder to always verify your dependencies.</Person2>\n"
    )


def _fix_transcript_tags(text: str) -> str:
    """Fix common LLM formatting issues in transcript tags.

    Handles:
    - Missing closing tags: <Person1>text  ->  <Person1>text</Person1>
    - Mismatched tags: <Person1>text</Person2>  ->  <Person1>text</Person1>
    - Lines with only opening tag spanning to next line
    """
    fixed_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            fixed_lines.append(line)
            continue

        # Check if line starts with a Person tag
        open_match = re.match(r"^<(Person[12])>", stripped)
        if open_match:
            speaker = open_match.group(1)
            # Check if it has ANY closing tag
            close_match = re.search(r"</(Person[12])>\s*$", stripped)
            if close_match:
                # Has a closing tag — fix if mismatched
                close_speaker = close_match.group(1)
                if close_speaker != speaker:
                    stripped = re.sub(
                        r"</(Person[12])>\s*$",
                        f"</{speaker}>",
                        stripped,
                    )
            else:
                # Missing closing tag — add it
                # Remove any trailing whitespace
                stripped = stripped.rstrip()
                stripped = f"{stripped}</{speaker}>"

        fixed_lines.append(stripped)

    return "\n".join(fixed_lines)


def _parse_dialogue_segments(text: str) -> list:
    """Parse dialogue segments from transcript, with fallback for edge cases.

    Returns list of (speaker, content) tuples.
    """
    # Primary: match properly tagged segments
    pattern = r"<(Person[12])>(.*?)</\1>"
    segments = re.findall(pattern, text, re.DOTALL)
    segments = [(s, c.strip()) for s, c in segments if c.strip()]

    if len(segments) >= 5:
        return segments

    # Fallback: try matching any <PersonX> opening tag and grab content until next tag
    print(f"[EN-PODCAST] WARNING: Only {len(segments)} matched segments, trying fallback parser")
    fallback_segments = []
    parts = re.split(r"<(Person[12])>", text)
    # parts[0] is before first tag, then alternating: tag, content, tag, content...
    i = 1
    while i < len(parts) - 1:
        speaker = parts[i]
        content = parts[i + 1]
        # Remove any closing tags from content
        content = re.sub(r"</(Person[12])>", "", content).strip()
        if content:
            fallback_segments.append((speaker, content))
        i += 2

    print(f"[EN-PODCAST] Fallback parser found {len(fallback_segments)} segments")
    return fallback_segments


def generate_en_transcript(news_text: str, voice_pair: dict) -> str:
    """Generate English podcast transcript using OpenAI LLM."""
    from openai import OpenAI

    client = OpenAI()

    system_prompt = build_en_system_prompt(voice_pair)
    user_prompt = (
        "Please generate an English two-host podcast dialogue script "
        "based on the following Hacker News daily best stories:\n\n"
        f"{news_text}"
    )

    print("[EN-PODCAST] Generating English transcript via LLM...")
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

    # Fix common LLM formatting issues: missing/mismatched closing tags
    transcript = _fix_transcript_tags(transcript)

    print(f"[EN-PODCAST] Transcript generated: {len(transcript)} chars in {elapsed:.1f}s")
    print(
        f"[EN-PODCAST] Tokens: input={usage.prompt_tokens}, "
        f"output={usage.completion_tokens}, total={usage.total_tokens}"
    )
    cost = usage.prompt_tokens * 0.4 / 1e6 + usage.completion_tokens * 1.6 / 1e6
    print(f"[EN-PODCAST] Estimated LLM cost: ${cost:.4f}")

    # LLM post-validation: fix any remaining tag issues
    from transcript_validator import validate_transcript
    transcript = validate_transcript(transcript, label="EN-PODCAST")

    # Verify tag quality
    segments = _parse_dialogue_segments(transcript)
    print(f"[EN-PODCAST] Parsed {len(segments)} dialogue segments")

    return transcript


# ---------------------------------------------------------------------------
# Step 4: Convert raw transcript to reading-friendly Markdown
# ---------------------------------------------------------------------------
def transcript_to_markdown(raw_transcript: str, date_str: str, voice_pair: dict) -> str:
    """Convert <Person1>/<Person2> tagged transcript to readable Markdown."""
    female_name = voice_pair["female_name"]
    male_name = voice_pair["male_name"]

    lines = [
        f"# HN Daily Best Podcast (English) — {date_str}",
        "",
        f"> HN Daily Best English Podcast — {date_str}",
        f"> Hosts: {female_name} & {male_name}",
        "",
        "---",
        "",
    ]

    segments = _parse_dialogue_segments(raw_transcript)

    for speaker, content in segments:
        content = content.strip()
        if not content:
            continue
        name = female_name if speaker == "Person1" else male_name
        lines.append(f"**{name}:** {content}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "*This podcast is auto-generated by AI based on Hacker News daily best stories.*",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 5: Synthesize audio via Azure Speech TTS (en-US)
# ---------------------------------------------------------------------------
def _build_en_ssml_chunk(segments: list, voice_pair: dict) -> str:
    """Build a single SSML document for English voices."""
    female_voice = voice_pair["female_voice"]
    female_style = voice_pair["female_style"]
    male_voice = voice_pair["male_voice"]
    male_style = voice_pair["male_style"]

    ssml_parts = [
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">'
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
    """Synthesize a single SSML chunk to an MP3 file."""
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
        print(f"[EN-PODCAST] ERROR: Azure TTS canceled: {cancellation.reason}")
        if cancellation.error_details:
            print(f"[EN-PODCAST]   Details: {cancellation.error_details}")
        return False
    else:
        print(f"[EN-PODCAST] ERROR: Azure TTS unexpected result: {result.reason}")
        return False


def synthesize_en_audio(raw_transcript: str, output_mp3: str, voice_pair: dict) -> bool:
    """Synthesize English audio from transcript using Azure Speech TTS."""
    MAX_SEGMENTS_PER_CHUNK = 25

    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        print("[EN-PODCAST] ERROR: azure-cognitiveservices-speech not installed.")
        return False

    speech_key = AZURE_SPEECH_KEY
    speech_region = AZURE_SPEECH_REGION
    if not speech_key:
        print("[EN-PODCAST] ERROR: AZURE_SPEECH_KEY not set")
        return False

    all_segments = _parse_dialogue_segments(raw_transcript)

    if not all_segments:
        print("[EN-PODCAST] WARNING: No dialogue segments found in transcript")
        return False

    total_segments = len(all_segments)
    print(f"[EN-PODCAST] Total dialogue segments: {total_segments}")

    if total_segments <= MAX_SEGMENTS_PER_CHUNK:
        ssml = _build_en_ssml_chunk(all_segments, voice_pair)
        print(f"[EN-PODCAST] SSML built: {len(ssml)} chars, {total_segments} segments (single chunk)")
        print("[EN-PODCAST] Starting Azure TTS synthesis...")
        t0 = time.time()
        success = _synthesize_one_chunk(ssml, output_mp3, speech_key, speech_region)
        elapsed = time.time() - t0
    else:
        chunks = []
        for i in range(0, total_segments, MAX_SEGMENTS_PER_CHUNK):
            chunks.append(all_segments[i:i + MAX_SEGMENTS_PER_CHUNK])
        num_chunks = len(chunks)
        print(f"[EN-PODCAST] Splitting into {num_chunks} chunks ({MAX_SEGMENTS_PER_CHUNK} segments each)")

        chunk_files = []
        t0 = time.time()
        for idx, chunk_segments in enumerate(chunks):
            chunk_ssml = _build_en_ssml_chunk(chunk_segments, voice_pair)
            chunk_path = os.path.join(WORK_DIR, f"en_chunk_{idx:02d}.mp3")
            print(f"[EN-PODCAST]   Chunk {idx + 1}/{num_chunks}: {len(chunk_segments)} segments, {len(chunk_ssml)} chars")

            if not _synthesize_one_chunk(chunk_ssml, chunk_path, speech_key, speech_region):
                print(f"[EN-PODCAST] ERROR: Chunk {idx + 1} failed")
                return False

            chunk_files.append(chunk_path)
            print(f"[EN-PODCAST]   Chunk {idx + 1}/{num_chunks} done: {os.path.getsize(chunk_path) / (1024*1024):.1f} MB")

        elapsed = time.time() - t0

        print(f"[EN-PODCAST] Concatenating {num_chunks} chunks with ffmpeg...")
        concat_list = os.path.join(WORK_DIR, "en_concat_list.txt")
        with open(concat_list, "w") as f:
            for cf in chunk_files:
                f.write(f"file '{cf}'\n")

        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list, "-c", "copy", output_mp3,
        ]
        concat_result = subprocess.run(concat_cmd, capture_output=True, text=True)
        if concat_result.returncode != 0:
            print(f"[EN-PODCAST] ERROR: ffmpeg concat failed: {concat_result.stderr}")
            return False

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
        print(f"[EN-PODCAST] Azure TTS completed in {elapsed:.1f}s")
        print(f"[EN-PODCAST]   Duration: {duration:.0f}s ({duration / 60:.1f} min)")
        print(f"[EN-PODCAST]   Size: {mp3_size:.1f} MB")
        return True

    return False


# ---------------------------------------------------------------------------
# Step 6: Upload to GitHub Releases
# ---------------------------------------------------------------------------
def upload_to_release(files: list, target_date: datetime, repo: str = "") -> bool:
    """Upload files to a monthly GitHub Release."""
    tag = f"podcast-{target_date.strftime('%Y-%m')}"
    title = f"HN Podcast - {target_date.strftime('%B %Y')}"
    body = (
        f"Daily HN podcast audio and transcripts for {target_date.strftime('%B %Y')}.\n\n"
        "Includes Chinese (two parts) and English editions.\n\n"
        "Audio: Azure Speech TTS"
    )

    repo_args = ["--repo", repo] if repo else []

    check_cmd = ["gh", "release", "view", tag] + repo_args
    result = subprocess.run(check_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[EN-PODCAST] Creating new release: {tag}")
        create_cmd = (
            ["gh", "release", "create", tag]
            + list(files)
            + ["--title", title, "--notes", body]
            + repo_args
        )
        result = subprocess.run(create_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[EN-PODCAST] ERROR creating release: {result.stderr}")
            return False
        print(f"[EN-PODCAST] Release created: {tag}")
    else:
        print(f"[EN-PODCAST] Uploading to existing release: {tag}")
        upload_cmd = (
            ["gh", "release", "upload", tag]
            + list(files)
            + ["--clobber"]
            + repo_args
        )
        result = subprocess.run(upload_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[EN-PODCAST] ERROR uploading: {result.stderr}")
            return False
        print(f"[EN-PODCAST] Files uploaded to release: {tag}")

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
        print(f"[EN-PODCAST]   {fname}: {url}")

    return True


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def generate_en_podcast(
    base_dir: str = BASE_DIR,
    target_date: datetime = None,
    skip_upload: bool = False,
    repo: str = "",
) -> dict:
    """Run the full English podcast generation pipeline.

    Returns a dict with paths and metadata, or empty dict on failure.
    """
    t_start = time.time()

    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)

    date_tag = target_date.strftime("%Y-%m-%d")
    print(f"\n{'=' * 60}")
    print(f"[EN-PODCAST] Generating English podcast for {date_tag}")
    print(f"{'=' * 60}")

    os.makedirs(WORK_DIR, exist_ok=True)

    # --- Select voice pair ---
    print(f"\n[EN-PODCAST] Selecting voice pair...")
    voice_pair = select_en_voice_pair(date_tag)

    # --- Load news data ---
    print(f"\n[EN-PODCAST] Loading news data...")
    try:
        json_path = find_best_json(base_dir, target_date)
    except FileNotFoundError as e:
        print(f"[EN-PODCAST] {e}")
        return {}

    items, date_str = load_news_items(json_path)
    if not items:
        print("[EN-PODCAST] No news items found, skipping")
        return {}
    print(f"[EN-PODCAST] Loaded {len(items)} stories from {json_path}")

    # Take top 20 stories
    items = items[:EN_STORIES_COUNT]
    print(f"[EN-PODCAST] Using top {len(items)} stories")

    # --- Prepare news text ---
    news_text = prepare_news_text(items, date_str)
    print(f"[EN-PODCAST] News text: {len(news_text)} characters")

    # --- Generate transcript ---
    raw_transcript = generate_en_transcript(news_text, voice_pair)

    raw_path = os.path.join(WORK_DIR, f"en_transcript_raw_{date_tag}.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_transcript)

    # --- Convert to Markdown ---
    md_transcript = transcript_to_markdown(raw_transcript, date_str, voice_pair)

    transcript_filename = f"{PODCAST_PREFIX}-{date_tag}-transcript.md"
    transcript_path = os.path.join(WORK_DIR, transcript_filename)
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(md_transcript)
    print(f"[EN-PODCAST] Transcript saved: {transcript_path}")

    # --- Synthesize audio ---
    print(f"\n[EN-PODCAST] Synthesizing audio via Azure Speech TTS (en-US)...")
    mp3_filename = f"{PODCAST_PREFIX}-{date_tag}.mp3"
    mp3_path = os.path.join(WORK_DIR, mp3_filename)
    success = synthesize_en_audio(raw_transcript, mp3_path, voice_pair)
    if not success:
        print("[EN-PODCAST] Audio synthesis failed")
        return {}

    # --- Upload ---
    release_tag = f"podcast-{target_date.strftime('%Y-%m')}"
    upload_files = [mp3_path, transcript_path]

    if skip_upload:
        print("[EN-PODCAST] Skipping upload (--skip-upload)")
    else:
        print("[EN-PODCAST] Uploading to GitHub Releases...")
        upload_success = upload_to_release(upload_files, target_date, repo=repo)
        if not upload_success:
            print("[EN-PODCAST] WARNING: Upload failed, files saved locally")

    # Determine download URL
    detect = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True, text=True,
    )
    url_repo = detect.stdout.strip() if detect.returncode == 0 else repo
    if not url_repo:
        url_repo = "chaowang15/chaowang15.github.io"

    mp3_url = f"https://github.com/{url_repo}/releases/download/{release_tag}/{mp3_filename}"
    mp3_size = os.path.getsize(mp3_path) / (1024 * 1024)

    # --- Update .podcast marker to include English info ---
    marker_dir = os.path.join(
        base_dir, target_date.strftime("%Y"), target_date.strftime("%m"),
        target_date.strftime("%d")
    )
    os.makedirs(marker_dir, exist_ok=True)
    marker_path = os.path.join(marker_dir, ".podcast")

    # Read existing marker and append English info
    existing_lines = []
    if os.path.exists(marker_path):
        with open(marker_path, "r") as f:
            existing_lines = [l.strip() for l in f if l.strip()]
        # Remove old English entries if re-running
        existing_lines = [l for l in existing_lines if not l.startswith("en_")]

    existing_lines.append(f"en_mp3={mp3_filename}")
    existing_lines.append(f"en_transcript={transcript_filename}")
    existing_lines.append(f"en_female={voice_pair['female_name']}")
    existing_lines.append(f"en_male={voice_pair['male_name']}")

    with open(marker_path, "w") as f:
        f.write("\n".join(existing_lines) + "\n")
    print(f"[EN-PODCAST] Marker updated: {marker_path}")

    # --- Summary ---
    elapsed = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"[EN-PODCAST] DONE! Total time: {elapsed:.1f}s")
    print(f"[EN-PODCAST]   Voice: {voice_pair['female_name']} + {voice_pair['male_name']}")
    print(f"[EN-PODCAST]   File: {mp3_filename} ({mp3_size:.1f} MB)")
    print(f"[EN-PODCAST]   URL: {mp3_url}")
    print(f"{'=' * 60}")

    return {
        "date": date_tag,
        "release_tag": release_tag,
        "voice_pair": voice_pair,
        "mp3_path": mp3_path,
        "mp3_filename": mp3_filename,
        "mp3_url": mp3_url,
        "transcript_path": transcript_path,
        "size_mb": mp3_size,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate HN Daily English Podcast")
    parser.add_argument("--date", type=str, default="", help="Target date YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--skip-upload", action="store_true", help="Skip uploading to GitHub Releases")
    parser.add_argument("--base-dir", type=str, default=BASE_DIR, help="Base directory for hackernews data")
    parser.add_argument("--repo", type=str, default="", help="GitHub repo in owner/repo format")
    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        target_date = datetime.now() - timedelta(days=1)

    result = generate_en_podcast(
        base_dir=args.base_dir,
        target_date=target_date,
        skip_upload=args.skip_upload,
        repo=args.repo,
    )

    if not result:
        print("[EN-PODCAST] Pipeline failed")
        sys.exit(1)

    print(f"\n[EN-PODCAST] Success! MP3: {result['mp3_url']}")


if __name__ == "__main__":
    main()
