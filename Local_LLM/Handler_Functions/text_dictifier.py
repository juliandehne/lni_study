import re
from pathlib import Path

from pypdf import PdfReader


REQUIRED_PUBLICATION_FIELDS = ("title", "abstract", "text", "references")


def extract_between(text, start_pattern, end_pattern=None):
    """Extract and trim text between two regular-expression patterns."""
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
    """Extract the four publication fields required by the priming template."""
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)

    reader = PdfReader(str(pdf_path))

    pages = [
        page.extract_text() or ""
        for page in reader.pages
    ]

    full_text = "\n\n".join(pages).strip()
    metadata = reader.metadata or {}

    title = str(metadata.get("/Title", "") or "").strip()

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

    publication = {
        "title": title,
        "abstract": abstract,
        "text": body_text,
        "references": references
    }

    return validate_publication_dict(publication)


def validate_publication_dict(publication):
    """Validate and normalize the row contract shared with the prompt handler."""
    if not isinstance(publication, dict):
        raise TypeError("publication must be a dictionary.")

    missing = [
        field for field in REQUIRED_PUBLICATION_FIELDS
        if field not in publication
    ]
    if missing:
        raise KeyError(
            f"publication is missing required fields: {', '.join(missing)}"
        )

    return {
        field: "" if publication[field] is None else str(publication[field]).strip()
        for field in REQUIRED_PUBLICATION_FIELDS
    }
