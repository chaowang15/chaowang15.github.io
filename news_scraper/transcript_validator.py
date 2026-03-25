"""
Transcript Validator — LLM-based post-validation for podcast transcripts.

After the initial LLM generates a podcast transcript, this module sends it
through a second LLM pass to fix formatting issues:
  - Missing or mismatched <Person1>/<Person2> tags
  - Tag text leaking into spoken content (e.g., "Person1" said aloud)
  - Incomplete closing tags
  - Any other structural issues

Works for both Chinese and English transcripts.
Cost: ~$0.002-0.003 per validation (gpt-4.1-mini).
"""

import re
import time


VALIDATION_PROMPT = """You are a strict XML format validator and fixer. Your ONLY job is to fix the formatting of a podcast transcript.

The transcript uses <Person1> and <Person2> XML tags to mark dialogue turns.

RULES:
1. Every dialogue line MUST have BOTH an opening AND closing tag: <Person1>text</Person1> or <Person2>text</Person2>
2. Opening and closing tags MUST match (no <Person1>text</Person2>)
3. The words "Person1", "Person2" must NEVER appear inside the spoken content — they are only XML tag names
4. Remove any stray tag fragments, partial tags, or malformed tags from the content
5. Do NOT change the actual dialogue content, word choice, or meaning — only fix the XML structure
6. Do NOT add new dialogue or remove existing dialogue
7. Do NOT add any commentary, explanation, or markdown — output ONLY the fixed transcript
8. Every non-empty line should either be a properly tagged dialogue line or a blank line
9. Preserve the original language (Chinese, English, or mixed)

OUTPUT: Return ONLY the fixed transcript with proper <Person1>...</Person1> and <Person2>...</Person2> tags. Nothing else."""


def validate_transcript(raw_transcript: str, label: str = "PODCAST") -> str:
    """Validate and fix a podcast transcript using a second LLM pass.

    Args:
        raw_transcript: The raw transcript with <Person1>/<Person2> tags.
        label: Log prefix for print statements (e.g., "PODCAST" or "EN-PODCAST").

    Returns:
        The validated/fixed transcript string.
    """
    from openai import OpenAI

    # Quick pre-check: if transcript looks clean, skip validation
    issues = _count_issues(raw_transcript)
    if issues == 0:
        print(f"[{label}] Transcript validation: no issues detected, skipping LLM pass")
        return raw_transcript

    print(f"[{label}] Transcript validation: {issues} potential issue(s) found, running LLM fix...")

    client = OpenAI()
    t0 = time.time()

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": VALIDATION_PROMPT},
            {"role": "user", "content": f"Please fix the formatting of this podcast transcript:\n\n{raw_transcript}"},
        ],
        temperature=0.0,  # Deterministic — we want exact fixes, no creativity
        max_tokens=5000,
    )

    fixed = response.choices[0].message.content
    usage = response.usage
    elapsed = time.time() - t0

    cost = usage.prompt_tokens * 0.4 / 1e6 + usage.completion_tokens * 1.6 / 1e6
    print(f"[{label}] Validation done in {elapsed:.1f}s")
    print(f"[{label}]   Tokens: input={usage.prompt_tokens}, output={usage.completion_tokens}, total={usage.total_tokens}")
    print(f"[{label}]   Validation cost: ${cost:.4f}")

    # Verify the fix actually improved things
    old_segments = len(re.findall(r"<(Person[12])>(.*?)</\1>", raw_transcript, re.DOTALL))
    new_segments = len(re.findall(r"<(Person[12])>(.*?)</\1>", fixed, re.DOTALL))
    new_issues = _count_issues(fixed)

    print(f"[{label}]   Before: {old_segments} segments, {issues} issues")
    print(f"[{label}]   After:  {new_segments} segments, {new_issues} issues")

    # Only use the fixed version if it's actually better
    if new_segments >= old_segments * 0.8 and new_issues <= issues:
        print(f"[{label}]   Using validated transcript")
        return fixed
    else:
        print(f"[{label}]   WARNING: Validation made things worse, keeping original")
        return raw_transcript


def _count_issues(text: str) -> int:
    """Count potential formatting issues in a transcript.

    Checks for:
      1. Opening tag without matching closing tag on the same line
      2. Mismatched opening/closing tags (e.g., <Person1>...</Person2>)
      3. "Person1" or "Person2" appearing as spoken content (not as XML tags)
    """
    issues = 0

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # Only check lines that start with a Person tag
        open_match = re.match(r"^<(Person[12])>", stripped)
        if open_match:
            speaker = open_match.group(1)

            # Issue 1: opening tag without proper closing tag
            if not re.search(rf"</{speaker}>\s*$", stripped):
                issues += 1
                continue

            # Issue 2: mismatched closing tag
            close_match = re.search(r"</(Person[12])>\s*$", stripped)
            if close_match and close_match.group(1) != speaker:
                issues += 1
                continue

        # Issue 3: "Person1" or "Person2" appearing as spoken text (not as tags)
        # Remove all proper tags first, then check for leftover Person references
        content_only = re.sub(r"</?Person[12]>", "", stripped)
        if re.search(r"\bPerson\s*[12]\b", content_only, re.IGNORECASE):
            issues += 1

    return issues
