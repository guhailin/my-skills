#!/usr/bin/env python3
"""Count an English reading draft containing only body text and page headings."""
import json
import re
import sys
from pathlib import Path

WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*(?:-[A-Za-z]+(?:['’][A-Za-z]+)*)*|\d+(?:[.,]\d+)*")
PAGE = re.compile(r"^\s*#{1,3}\s*Page\s+(\d+)\s*$", re.IGNORECASE)


def main():
    if len(sys.argv) != 2:
        print("Usage: count_reading.py BODY_TEXT_FILE", file=sys.stderr)
        return 2
    lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    pages = []
    current = None
    for line in lines:
        match = PAGE.fullmatch(line)
        if match:
            current = {"page": int(match.group(1)), "text": []}
            pages.append(current)
        elif line.strip():
            if current is None:
                print("Body text must follow a ## Page N heading", file=sys.stderr)
                return 2
            current["text"].append(line)
    if not pages or any(not p["text"] for p in pages):
        print("Every draft must contain non-empty ## Page N sections", file=sys.stderr)
        return 2
    if [p["page"] for p in pages] != list(range(1, len(pages) + 1)):
        print("Page numbers must be consecutive and start at 1", file=sys.stderr)
        return 2
    counts = [len(WORD.findall(" ".join(p["text"]))) for p in pages]
    print(json.dumps({"body_words": sum(counts), "pages": len(pages),
                      "words_per_page": counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
