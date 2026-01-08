import pdfplumber
import re
from pathlib import Path


# ----------------------------
# PDF Extraction
# ----------------------------

def extract_text_from_pdf(pdf_path: Path) -> str:
    text_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_pages.append(text)
    return "\n".join(text_pages)


# ----------------------------
# Cleaning Helpers
# ----------------------------

def remove_noise(text: str) -> str:
    cleaned_lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Remove page numbers like "Page 12"
        if re.match(r"^Page\s+\d+", line):
            continue

        # Remove standalone numbers
        if re.match(r"^\d+$", line):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def fix_line_breaks(text: str) -> str:
    # Join broken lines
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Normalize paragraph spacing
    text = re.sub(r"\n{2,}", "\n\n", text)

    return text


# ----------------------------
# Cleaning Pipeline
# ----------------------------

def clean_pdf(input_pdf: Path, output_txt: Path):
    raw_text = extract_text_from_pdf(input_pdf)
    no_noise = remove_noise(raw_text)
    cleaned_text = fix_line_breaks(no_noise)

    output_txt.parent.mkdir(parents=True, exist_ok=True)
    output_txt.write_text(cleaned_text, encoding="utf-8")


def clean_all_pdfs(raw_dir: Path, output_dir: Path):
    pdf_files = list(raw_dir.glob("*.pdf"))

    print(f"Found {len(pdf_files)} PDF file(s)")

    if not pdf_files:
        raise RuntimeError(f"No PDFs found in {raw_dir}")

    for pdf_file in pdf_files:
        output_file = output_dir / f"{pdf_file.stem}.txt"
        clean_pdf(pdf_file, output_file)
        print(f"Cleaned: {pdf_file.name} → {output_file.name}")


# ----------------------------
# Entry Point (IMPORTANT FIX)
# ----------------------------

if __name__ == "__main__":
    # Resolve paths relative to THIS file, not working directory
    BASE_DIR = Path(__file__).resolve().parents[1]  # backend/

    RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
    CLEAN_TEXT_DIR = BASE_DIR / "data" / "cleaned_text"

    print(f"Reading PDFs from: {RAW_PDF_DIR}")
    print(f"Writing cleaned text to: {CLEAN_TEXT_DIR}")

    clean_all_pdfs(RAW_PDF_DIR, CLEAN_TEXT_DIR)
