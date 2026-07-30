import re
from pypdf import PdfReader


def extract_between(text, start_pattern, end_pattern = None) :
    if end_pattern:
        pattern = rf"{start_pattern}\s*(.*?)(?={end_pattern})"
    else:
        pattern = rf"{start_pattern}\s*(.*)$"

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    return match.group(1).strip() if match else ""


def pdf_to_dict(pdf_path):
    reader = PdfReader(str(pdf_path))

    pages = [
        page.extract_text() or ""
        for page in reader.pages
    ]

    full_text = "\n\n".join(pages).strip()
    metadata = reader.metadata or {}

    title = metadata.get("/Title", "") or ""

    # Fallback: first non-empty line as title
    if not title:
        non_empty_lines = [
            line.strip()
            for line in full_text.splitlines()
            if line.strip()
        ]

        if non_empty_lines:
            title = non_empty_lines[0]

    abstract = extract_between(
        full_text,
        r"\bAbstract\b[:.]?",
        r"\n\s*(?:1[\s.]|Introduction\b|Einleitung\b)"
    )

    references = extract_between(
        full_text,
        r"\b(?:References|Bibliography|Literaturverzeichnis|Literatur)\b[:.]?"
    )

    body_text = full_text

    reference_heading = re.search(
        r"\n\s*(?:References|Bibliography|Literaturverzeichnis|Literatur)"
        r"\s*[:.]?\s*\n",
        full_text,
        flags=re.IGNORECASE
    )

    if reference_heading:
        body_text = full_text[:reference_heading.start()].strip()

    return {
        "title": title.strip(),
        "abstract": abstract,
        "text": body_text,
        "references": references
    }
