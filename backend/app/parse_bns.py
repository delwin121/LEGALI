import json
import re
from pathlib import Path

# --------------------------------------------------
# PATH SETUP
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "cleaned_text" / "bns.txt"
OUTPUT_FILE = DATA_DIR / "structured" / "bns.json"

# --------------------------------------------------
# NORMALIZATION (CRITICAL FIX)
# --------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Fix OCR-style inline formatting:
    - Ensure CHAPTER headings start on new lines
    - Ensure section numbers start on new lines
    """
    # Newline before CHAPTER
    text = re.sub(r"\s+(CHAPTER\s+[IVXLCDM]+)", r"\n\1", text)

    # Newline before SECTIONS
    text = re.sub(r"\s+(SECTIONS\s+\d+\.)", r"\n\1", text)

    # Newline before section numbers (1. 2. 3.)
    text = re.sub(r"\s+(\d{1,3}\.\s+[A-Z])", r"\n\1", text)

    return text


# --------------------------------------------------
# REGEX DEFINITIONS
# --------------------------------------------------

SECTION_REGEX = re.compile(
    r"""
    ^\s*
    (\d{1,3})\.                # Section number
    \s+
    ([A-Z][^\n—–-]+?)          # Section title
    (?:—|–|-)                  # Dash
    \s*
    (.*?)                      # Section body
    (?=^\s*\d{1,3}\.\s+[A-Z]|\Z)
    """,
    re.DOTALL | re.MULTILINE | re.VERBOSE,
)

CHAPTER_REGEX = re.compile(
    r"^CHAPTER\s+[IVXLCDM]+\s+[A-Z][A-Z\s]+",
    re.MULTILINE,
)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def remove_toc(text: str) -> str:
    marker = "THE BHARATIYA NYAYA SANHITA, 2023"
    occurrences = [m.start() for m in re.finditer(marker, text)]
    if len(occurrences) < 2:
        raise RuntimeError("Cannot locate Act body safely")
    return text[occurrences[1]:]


def build_chapter_index(text: str):
    chapters = []
    for m in CHAPTER_REGEX.finditer(text):
        chapters.append((m.start(), m.group().strip()))
    if not chapters:
        raise RuntimeError("No chapters detected")
    return chapters


def assign_chapter(pos: int, chapters):
    current = "UNKNOWN CHAPTER"
    for start, title in chapters:
        if pos >= start:
            current = title
        else:
            break
    return current


def parse_bns(text: str):
    structured = []
    chapters = build_chapter_index(text)

    for m in SECTION_REGEX.finditer(text):
        structured.append({
            "chapter": assign_chapter(m.start(), chapters),
            "section_number": int(m.group(1)),
            "section_title": m.group(2).strip(),
            "text": m.group(3).strip(),
        })

    return structured


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    raw_text = INPUT_FILE.read_text(encoding="utf-8")

    raw_text = normalize_text(raw_text)
    text = remove_toc(raw_text)

    structured_data = parse_bns(text)

    # HARD LEGAL CHECK
    if not (350 <= len(structured_data) <= 365):

        raise RuntimeError(f"Suspicious section count: {len(structured_data)}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(structured_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Parsed {len(structured_data)} sections")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
