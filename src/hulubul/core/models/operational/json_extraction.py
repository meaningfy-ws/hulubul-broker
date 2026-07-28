"""Best-effort JSON-object extraction from LLM output.

Shared by every LF-70 boundary/adapter component that has to interpret an
Agent's raw text as JSON despite an explicit "JSON only" instruction: the
model sometimes "thinks out loud" with a fenced *draft* JSON block, then
produces the real (unfenced) final answer afterwards
("Now producing the final JSON.\\n\\n{...}"). A naive first-match regex
grabs the draft. This scans for every balanced top-level `{...}` block
(brace-depth tracking, so nested objects and fence markers don't confuse
it) and tries each from *last* to *first* -- the model's own "final answer
comes last" pattern -- returning the first one that's valid JSON.
"""

import json

__all__ = ["extract_json_object_text"]


def extract_json_object_text(text: str) -> str:
    """Extract the most likely JSON object from LLM output.

    A no-op on already-clean JSON text. Returns the original (stripped)
    text unchanged if no balanced `{...}` block parses as valid JSON.
    """
    text = text.strip()
    candidates: list[str] = []
    depth = 0
    start: int | None = None
    for i, char in enumerate(text):
        if char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start : i + 1])
    # Last-to-first, not first-to-last: the model's real final answer comes
    # after any fenced draft it thought out loud, so the last block that
    # actually parses is the one to trust.
    for candidate in reversed(candidates):
        try:
            json.loads(candidate)
        except json.JSONDecodeError:
            continue
        return candidate
    return text
