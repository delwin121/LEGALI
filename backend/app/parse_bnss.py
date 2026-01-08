import re
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RAW_FILE = BASE_DIR.parent / "data/cleaned_text/bnss.txt"
OUT_FILE = BASE_DIR.parent / "data/structured/bnss.json"


# ---------------------------
# 1. Remove TOC safely
# ---------------------------
def remove_toc(text: str) -> str:
    """
    BNSS body ALWAYS starts from:
    'CHAPTER I PRELIMINARY'
    """
    marker = re.search(
        r"CHAPTER\s+I\s+PRELIMINARY",
        text,
        re.IGNORECASE,
    )
    if not marker:
        raise RuntimeError("Cannot find start of BNSS body (CHAPTER I PRELIMINARY)")

    return text[marker.start():]


# ---------------------------
# 2. Clause extraction
# ---------------------------
CLAUSE_REGEX = re.compile(
    r"""
    (\d{1,3})\.                      # Clause number
    \s+
    ([A-Z][A-Za-z0-9 ,–\-()']+?)     # Clause title
    \.                               # Title ends with dot
    \s*
    (.*?)                            # Clause body
    (?=
        \s+\d{1,3}\.\s+[A-Z]         # Next clause
        |
        \s+CHAPTER\s+[IVXLCDM]+      # Next chapter
        |
        \Z
    )
    """,
    re.DOTALL | re.VERBOSE,
)


CHAPTER_REGEX = re.compile(
    r"CHAPTER\s+([IVXLCDM]+)\s+([A-Z ].+)"
)


# ---------------------------
# 3. Parse chapters
# ---------------------------
def map_chapters(text: str):
    chapters = []
    for m in CHAPTER_REGEX.finditer(text):
        chapters.append(
            {
                "start": m.start(),
                "roman": m.group(1),
                "title": m.group(2).strip(),
            }
        )

    for i in range(len(chapters) - 1):
        chapters[i]["end"] = chapters[i + 1]["start"]

    chapters[-1]["end"] = len(text)
    return chapters


# ---------------------------
# 4. Main
# ---------------------------
def main():
    raw_text = RAW_FILE.read_text(encoding="utf-8", errors="ignore")
    body = remove_toc(raw_text)

    chapters = map_chapters(body)
    structured = []

    for ch in chapters:
        chunk = body[ch["start"]: ch["end"]]
        chapter_name = f"CHAPTER {ch['roman']} {ch['title']}"

        for m in CLAUSE_REGEX.finditer(chunk):
            structured.append(
                {
                    "chapter": chapter_name,
                    "clause_number": int(m.group(1)),
                    "clause_title": m.group(2).strip(),
                    "text": re.sub(r"\s+", " ", m.group(3)).strip(),
                }
            )

    # ---------------------------
    # 5. Validation
    # ---------------------------
    count = len(structured)
    if not (520 <= count <= 540):
        raise RuntimeError(f"Suspicious clause count: {count}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(structured, indent=2, ensure_ascii=False))

    print(f"Parsed {count} clauses")
    print(f"Saved to {OUT_FILE}")


if __name__ == "__main__":
    main()
