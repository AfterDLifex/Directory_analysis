#!/usr/bin/env python3
"""Fix mojibake (encoding-gremlin) characters left in the UI sources.

The originals were UTF-8 bytes mis-decoded as cp1252, so e.g. the em-dash
(-) became the three characters "â€”" / "…" etc. Pass 1 replaced only the
"â€" prefix and left a stale tail byte behind (", …,  …, …, ").
This pass repairs all remaining tails and arrow sequences.
"""
import os

BASE_DIR = r'd:\SKILL_UP\TEST_APPS\Directory_analysis'

# (broken sequence, correct character) - applied in this order.
REPLACEMENTS = [
    ("\u2014\u201d", "\u2014"),          # " —  + leftover " (U+201D) -> em-dash
    ("\u2014\u00a6", "\u2026"),          # " + leftover (U+00A6) -> ellipsis
    ("\u2014\u00a2", "\u2022"),          # " + leftover (U+00A2) -> bullet
    ("\u2014\u2122", "\u2122"),          # possible leftover trademark tail
    ("\u00e2\u2020\u2019", "\u2192"),    # â†’ -> right arrow
    ("\u00e2\u2020\u2018", "\u2191"),    # â†‘ -> up arrow
    ("\u00e2\u2020\u201c", "\u2193"),    # â†“ -> down arrow
    ("\u00e2\u0161\u00a0", "\u26a0"),    # âš   -> warning sign
    ("\u00c2\u00b7", "\u00b7"),          # Â· -> middle dot
]


def fix_text(text: str) -> str:
    for broken, good in REPLACEMENTS:
        text = text.replace(broken, good)
    return text


def scan_residual(text: str, path: str) -> None:
    """Print any remaining suspicious characters for verification."""
    suspect = set("\u00e2\u20ac\u2020\u00a6\u00a2\u0161\u00c2\u2018\u2019\u201c\u201d")
    for i, line in enumerate(text.splitlines(), 1):
        if any(ch in suspect for ch in line):
            print(f"  REMAINS {path}:{i}: {line.strip()[:90]}")


def main() -> None:
    fixed: list[str] = []
    for sub in ("ui", "folder_analyzer"):
        for root, dirs, files in os.walk(os.path.join(BASE_DIR, sub)):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(root, name)
                with open(path, "rb") as fh:
                    raw = fh.read()
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    print(f"  NON-UTF8 {path}")
                    continue
                new = fix_text(text)
                if new != text:
                    with open(path, "w", encoding="utf-8", newline="") as fh:
                        fh.write(new)
                    fixed.append(path)
                    print(f"Fixed: {path}")
                scan_residual(new, path)
    print(f"\n{len(fixed)} file(s) updated.")


if __name__ == "__main__":
    main()
