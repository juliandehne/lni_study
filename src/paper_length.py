"""
paper_length.py

Page-length helpers + the "short paper" constraint for goldstandard selection.

A SHORT paper (< SHORT_PAGE_THRESHOLD pages, default 6) is a known quality risk
in the LNI corpus: 2-4 page abstracts / posters / front-matter often lack the
section structure the extractor and the human coders rely on (e.g. the 2-page
`lni52/GI.-.Proceedings.52-53.pdf` straggler, which has no section anchors and
fails extract_main_content). To keep the goldstandard codeable we cap the
fraction of short papers in the `pool` reservoir AND in the top-up drawn from it
(the "goldstandard pooling and topping off") at MAX_SHORT_FRACTION (default
0.20 = 20%).

The cap is maintained as a RUNNING invariant while a set is filled / drawn:

    allow ONE more short paper only if   (n_short + 1) <= frac * (n_total + 1)

so after every accepted paper  n_short / n_total <= frac  holds exactly. That
guarantee is independent of the final set size, so the assertion still holds even
when the corpus is exhausted before the target size is reached. Non-short papers
are always allowed (they only improve the ratio).

Page counts come from PyMuPDF via pdf_text_extraction.get_page_count; a PDF that
cannot be opened returns None and is treated as NOT short (an unknown length is
not charged against the short quota — the extraction-failure path handles broken
PDFs separately).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdf_text_extraction import get_page_count  # noqa: E402

# A paper with fewer than this many pages is "short".
SHORT_PAGE_THRESHOLD = 6
# At most this fraction of a capped set may be short papers.
MAX_SHORT_FRACTION = 0.20


def page_count(pdf_path) -> int | None:
    """Page count for a PDF, or None if it cannot be opened (broken PDF).

    A cheap operation (opens the document, reads the page count, closes it — no
    text extraction or rendering), so it is safe to call per candidate."""
    try:
        return get_page_count(pdf_path)
    except Exception:
        return None


def is_short(pages, threshold: int = SHORT_PAGE_THRESHOLD) -> bool:
    """True if `pages` (an int page count) is below `threshold`.

    Unknown page count (None, "" or non-numeric) is treated as NOT short — we do
    not charge a paper we could not measure against the short quota."""
    try:
        return pages is not None and pages != "" and int(pages) < threshold
    except (TypeError, ValueError):
        return False


def short_allowed(n_short: int, n_total: int, frac: float = MAX_SHORT_FRACTION) -> bool:
    """Running cap: may we add ONE more short paper to a set that currently holds
    `n_short` short of `n_total` total and keep short/total <= frac?

    Uses the POST-add counts so the invariant holds after the addition:
        (n_short + 1) <= frac * (n_total + 1)
    """
    return (n_short + 1) <= frac * (n_total + 1)


def fraction_ok(n_short: int, n_total: int, frac: float = MAX_SHORT_FRACTION) -> bool:
    """True if a set of `n_total` papers with `n_short` short ones satisfies the
    cap. An empty set trivially satisfies it."""
    return n_total == 0 or (n_short <= frac * n_total)


def short_fraction(n_short: int, n_total: int) -> float:
    """Short fraction as a float in [0, 1] (0.0 for an empty set)."""
    return (n_short / n_total) if n_total else 0.0


def order_within_cap(records, is_short_fn, frac: float = MAX_SHORT_FRACTION) -> list:
    """Reorder `records` so EVERY prefix satisfies the short cap.

    Used by the top-up: confirm draws the pool reservoir in candidate order, so
    emitting a short only when `short_allowed` keeps the cap true for the drawn
    prefix means whatever target the top-up stops at is itself <= frac short.

    A stable two-queue interleave that preserves the original relative order
    within the long and short queues: emit a short whenever the running counts
    allow one, otherwise emit the next long. If only shorts remain and the cap
    forbids more (the records are >frac short overall), the leftover shorts are
    appended at the end so NO record is dropped — the prefix guarantee still
    holds up to that point. `is_short_fn(record)` decides short-ness."""
    longs, shorts = [], []
    for r in records:
        (shorts if is_short_fn(r) else longs).append(r)

    out: list = []
    n_short = n_total = 0
    li = si = 0
    while li < len(longs) or si < len(shorts):
        if si < len(shorts) and short_allowed(n_short, n_total, frac):
            out.append(shorts[si]); si += 1
            n_short += 1; n_total += 1
        elif li < len(longs):
            out.append(longs[li]); li += 1
            n_total += 1
        else:
            # Only shorts remain and the cap forbids more: append them as-is.
            out.extend(shorts[si:])
            break
    return out
