"""Text utilities for agent-fm streaming TTS."""

import re


# Abbreviations that end with a period but aren't sentence boundaries
_ABBREVS = {
    "dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "ave", "blvd",
    "vs", "etc", "inc", "ltd", "co", "corp", "dept", "univ",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "fig", "approx", "govt", "intl",
}

# Regex: sentence-ending punctuation followed by whitespace and an uppercase letter or end
_SPLIT_RE = re.compile(r'([.!?]+)\s+(?=[A-Z"\']|$)')

MIN_SENTENCE_LENGTH = 10


def split_sentences(text: str) -> list[str]:
    """Split text into sentences suitable for TTS streaming.

    Splits on .!? followed by whitespace + uppercase letter.
    Handles common abbreviations (Dr., Mr., U.S., etc.) and
    decimal numbers (3.14). Merges short fragments into neighbors.

    Returns at least one sentence (the full text if no splits found).
    """
    text = text.strip()
    if not text:
        return []

    # Protect abbreviations: replace "Dr." with "Dr§" temporarily
    protected = text
    for abbr in _ABBREVS:
        for pattern in [abbr.capitalize() + ".", abbr.upper() + ".", abbr + "."]:
            protected = protected.replace(pattern, pattern[:-1] + "§")

    # Protect decimal numbers: "3.14" → "3§14"
    protected = re.sub(r'(\d)\.(\d)', r'\1§\2', protected)

    # Protect U.S.-style abbreviations: "U.S." → "U§S§"
    protected = re.sub(r'\b([A-Z])\.([A-Z])\.', r'\1§\2§', protected)

    # Split on sentence boundaries
    parts = _SPLIT_RE.split(protected)

    # Reassemble: parts alternate between text and punctuation
    sentences = []
    i = 0
    while i < len(parts):
        sentence = parts[i]
        # Attach trailing punctuation
        if i + 1 < len(parts) and re.match(r'^[.!?]+$', parts[i + 1]):
            sentence += parts[i + 1]
            i += 2
        else:
            i += 1
        sentence = sentence.strip()
        if sentence:
            # Restore protected characters
            sentence = sentence.replace("§", ".")
            sentences.append(sentence)

    if not sentences:
        return [text]

    # Merge short fragments into previous sentence
    merged = [sentences[0]]
    for s in sentences[1:]:
        if len(merged[-1]) < MIN_SENTENCE_LENGTH:
            merged[-1] = merged[-1] + " " + s
        else:
            merged.append(s)

    # If last sentence is too short, merge it with the previous
    if len(merged) > 1 and len(merged[-1]) < MIN_SENTENCE_LENGTH:
        merged[-2] = merged[-2] + " " + merged[-1]
        merged.pop()

    return merged
