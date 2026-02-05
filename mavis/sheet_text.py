"""Sheet Text parser -- converts raw buffered characters into structured tokens."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SheetTextToken:
    """A parsed unit of Sheet Text with prosody annotations."""

    text: str
    emphasis: str = "none"  # "none" | "soft" | "loud" | "shout"
    sustain: bool = False
    harmony: bool = False
    duration_modifier: float = 1.0


def _is_uppercase(char: str) -> bool:
    return char.isalpha() and char.isupper()


def parse(chars: List[Dict]) -> List[SheetTextToken]:
    """Parse a list of buffered character dicts into SheetTextTokens.

    Recognises the following Sheet Text markup:
    - Shift held / uppercase letters -> "loud" emphasis
    - Consecutive all-uppercase word (len >= 2) -> "shout" emphasis
    - _underscores_ wrapping -> "soft" emphasis
    - ... (three consecutive dots) -> sustain, duration_modifier = 2.0
    - [brackets] wrapping or ctrl held -> harmony
    """
    if not chars:
        return []

    # First pass: group characters into words separated by spaces / punctuation
    groups: List[List[Dict]] = []
    current: List[Dict] = []

    for ch in chars:
        c = ch["char"]
        if c == " ":
            if current:
                groups.append(current)
                current = []
        else:
            current.append(ch)

    if current:
        groups.append(current)

    tokens: List[SheetTextToken] = []

    for group in groups:
        text = "".join(ch["char"] for ch in group)

        # --- Detect sustain (ellipsis) ---
        # An ellipsis may be attached to the preceding word, e.g. "hold..."
        sustain = False
        duration_modifier = 1.0
        if text.endswith("..."):
            sustain = True
            duration_modifier = 2.0
            text = text[:-3]  # strip the dots
            if not text:
                # standalone "..." -- emit a sustain-only token
                tokens.append(
                    SheetTextToken(
                        text="...",
                        emphasis="none",
                        sustain=True,
                        duration_modifier=2.0,
                    )
                )
                continue

        # --- Detect harmony (brackets or ctrl) ---
        harmony = False
        if text.startswith("[") and text.endswith("]"):
            harmony = True
            text = text[1:-1]
        elif any(ch.get("ctrl", False) for ch in group):
            harmony = True

        # --- Detect soft emphasis (underscores) ---
        emphasis = "none"
        if text.startswith("_") and text.endswith("_") and len(text) > 2:
            emphasis = "soft"
            text = text[1:-1]
        else:
            # --- Detect loud / shout emphasis ---
            alpha_chars = [c for c in text if c.isalpha()]
            if alpha_chars:
                all_upper = all(c.isupper() for c in alpha_chars)
                any_shift = any(ch.get("shift", False) for ch in group if ch["char"].isalpha())

                if all_upper and (any_shift or len(alpha_chars) >= 1):
                    emphasis = "loud"  # promoted to "shout" in post-pass
                elif any_shift and any(c.isupper() for c in alpha_chars):
                    emphasis = "loud"

        tokens.append(
            SheetTextToken(
                text=text,
                emphasis=emphasis,
                sustain=sustain,
                harmony=harmony,
                duration_modifier=duration_modifier,
            )
        )

    # Post-pass: promote runs of consecutive "loud" tokens (2+) to "shout"
    _promote_shout(tokens)

    return tokens


def _promote_shout(tokens: List[SheetTextToken]) -> None:
    """Promote consecutive runs of 2+ 'loud' tokens to 'shout'."""
    i = 0
    while i < len(tokens):
        if tokens[i].emphasis == "loud":
            run_start = i
            while i < len(tokens) and tokens[i].emphasis == "loud":
                i += 1
            if i - run_start >= 2:
                for j in range(run_start, i):
                    tokens[j].emphasis = "shout"
        else:
            i += 1


def text_to_chars(text: str) -> List[Dict]:
    """Convenience function: convert a plain string into the char-dict format
    expected by parse(), inferring shift from uppercase letters.

    Bracket and underscore characters pass through as-is.
    """
    chars: List[Dict] = []
    for c in text:
        chars.append(
            {
                "char": c,
                "shift": c.isupper(),
                "ctrl": False,
                "alt": False,
                "timestamp_ms": 0,
            }
        )
    return chars
