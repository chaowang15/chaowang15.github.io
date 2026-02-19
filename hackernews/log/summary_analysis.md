# Current Summary Quality Analysis

## Key Problems Identified

1. **Repetitive boilerplate filler**: Almost every summary ends with "The summary uses only the title and URL context" or similar disclaimers. This wastes space and adds zero value.

2. **Stating the obvious**: Many summaries just restate the title in slightly different words. E.g., "The linked post highlights GrapheneOS as a means to break free from Google and Apple" — this is literally the title.

3. **Mentioning the URL/source unnecessarily**: "The URL points to a blog post about GrapheneOS in English" — readers can see the link themselves.

4. **Vague filler sentences**: "The article linked in the item provides context for that claim" — this says nothing useful.

5. **No added context or insight**: The summaries don't explain WHY a story matters, what the technology is, or provide any background that a reader wouldn't get from the title alone.

6. **Chinese translations mirror the same problems**: Since summary_zh is a translation of summary_en, all the above issues carry over.

## Root Cause

The prompt says "Use only the title and URL context. Do NOT invent specific claims." This is too restrictive — it forces the model to pad summaries with disclaimers and restatements instead of providing useful context from its knowledge.

## Improved Approach

- Allow the model to use its general knowledge to provide brief background context
- Explicitly forbid boilerplate disclaimers
- Ask for WHY the story matters / what the key takeaway is
- Keep it concise: 2-3 sentences max instead of 3-5
- Chinese summary should be an independent write-up, not a literal translation
