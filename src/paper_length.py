"""
paper_length.py

Page-length helpers, the "short paper" constraint for goldstandard selection,
and the "this is not a single paper" filter.

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

The other end of the length scale is `is_non_paper`: some LNI volume folders
contain the WHOLE proceedings volume as one PDF next to its individual papers
(e.g. `lni300/SE-2020-Komplettband.pdf`, 254 pages: front matter plus every
contribution of the conference, its tracks and five satellite events). Such a
file is not a unit of analysis — no single research position, software type or
evaluation can be coded for it, and coding it would double-count the papers that
are also sampled individually. `select_candidates.py` therefore drops these at
the `estimate` step, before a candidate is ever placed into a working set.

The same problem comes in a smaller disguise: a bundled workshop TRACK, short
enough and innocently enough named to pass every length- and name-based test
(`lni352/KB_9th_Workshop_Enterprise_Architecture_Management.pdf`: 41 pages, three
contributions, three DOIs). `count_contributions` catches those by counting the
per-contribution title-page stamps instead of measuring the file.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdf_text_extraction import get_page_count  # noqa: E402

# A paper with fewer than this many pages is "short".
SHORT_PAGE_THRESHOLD = 6
# At most this fraction of a capped set may be short papers.
MAX_SHORT_FRACTION = 0.20

# A PDF with MORE than this many pages is not a single contribution. Deliberately
# generous: normal LNI papers run 4-14 pages, doctoral-symposium and survey
# contributions can reach ~40, while collected volumes start around 150 and run
# into the hundreds. The gap is wide, so a high threshold costs no recall.
MAX_PAPER_PAGES = 60

# Filename / title words that announce a collected volume or pure front matter,
# rather than a contribution. Matched case-insensitively as substrings of the
# file NAME and of the first page of text.
NON_PAPER_NAME_PATTERNS = [
    r"komplettband", r"tagungsband", r"gesamtband", r"sammelband",
    r"gesamtdokument", r"proceedings[\s_-]*band", r"komplett[\s_-]*ausgabe",
    r"front[\s_-]*matter", r"frontmatter", r"titelei", r"backmatter",
    r"inhaltsverzeichnis", r"table[\s_-]*of[\s_-]*contents",
    r"complete[\s_-]*(?:volume|proceedings)", r"full[\s_-]*proceedings",
    r"book[\s_-]*of[\s_-]*abstracts", r"gesamtes[\s_-]*proceedings",
]
_NON_PAPER_NAME_RX = re.compile("|".join(NON_PAPER_NAME_PATTERNS), re.IGNORECASE)

# Front-matter fingerprint: the LNI series page of a collected volume carries the
# series line together with the editor/board block. An individual paper never
# does. Only checked on the first ~4000 characters, so a paper that merely CITES
# an LNI volume in its bibliography is not caught.
_FRONTMATTER_HEAD_CHARS = 4000
_SERIES_RX = re.compile(
    r"Lecture\s+Notes\s+in\s+Informatics|Gesellschaft\s+f(?:ü|ue)r\s+Informatik\s+e\.?\s?V", re.I)
_EDITORIAL_RX = re.compile(
    r"Volume\s+Editors|Series\s+Editorial\s+Board|Herausgeberband", re.I)

# Since ~2018 every LNI contribution carries a stamp on ITS OWN first page: the
# CC licence badge ("cba") plus the paper's own DOI. Count the DISTINCT DOIs and
# you count the contributions in the file -- two or more means the PDF bundles a
# whole workshop track, even when it is short enough and innocently enough named
# to pass every other rule
# (`lni352/KB_9th_Workshop_Enterprise_Architecture_Management.pdf`: 41 pages,
# three papers, three DOIs).
#
# The licence badge in front of the DOI is what makes this safe: a paper that
# CITES another LNI paper prints a bare "doi: 10.18420/..." in its bibliography,
# with no badge (`lni352/Neuroth_et_al_Nachhaltiges_Forschungsdatenmanagement`).
#
# NOT used, though it looks tempting: counting the "<editors> (Hrsg.): ...
# Lecture Notes in Informatics" footer. Several volumes repeat that footer on
# EVERY page, so ordinary single papers score 2-6 on it (`lni220/736` 6x,
# `lni197/83` 2x, `lni285/3032414_GI_P_285_23` 2x, `lni327/PVM2022_8` 6x -- all
# genuine single papers). Known limitation of the DOI-only rule: volumes older
# than the per-paper DOI carry no stamp, so a bundle there is not detected by
# this rule (the page-length and filename rules still apply).
_CONTRIB_DOI_RX = re.compile(r"\bc[byndas]{1,3}\s*doi:\s*(10\.\d{4,9}/\S+)", re.I)


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


def count_contributions(text) -> int:
    """How many LNI contributions does `text` contain, counted by the distinct
    per-paper DOIs stamped on their title pages? 0 when the volume carries no
    such stamp at all (anything older than the per-paper DOI) — which is NOT
    evidence of a bundle, so callers must treat 0 and 1 alike."""
    if not text:
        return 0
    return len({m.rstrip(".,;") for m in _CONTRIB_DOI_RX.findall(text)})


def is_non_paper(pdf_path=None, pages=None, text=None,
                 max_pages: int = MAX_PAPER_PAGES) -> str | None:
    """Is this PDF clearly NOT a single contribution (a collected volume / front
    matter)? Returns a short reason string if so, else None.

    Three independent, deliberately conservative tests — any one is enough:

    1. `pages` above `max_pages` (default 60). An unknown page count never
       triggers this, exactly as in `is_short`.
    2. the file NAME contains a collected-volume word ("Komplettband",
       "Tagungsband", "front matter", "Inhaltsverzeichnis", ...).
    3. the FIRST page of `text` carries the LNI series line AND an editor/board
       block ("Volume Editors" / "Series Editorial Board"). A contribution that
       merely cites an LNI volume is not caught: only the head of the text is
       inspected, and both fingerprints must be present.
    4. `text` carries TWO OR MORE contribution title-page stamps (see
       `count_contributions`) — a bundled workshop track. This is the rule that
       catches a short, harmlessly named bundle the first three miss.

    All arguments are optional, so a caller with just a page count or just a
    filename can still use it."""
    try:
        if pages is not None and pages != "" and int(pages) > max_pages:
            return f"volume-length ({int(pages)} pages > {max_pages})"
    except (TypeError, ValueError):
        pass                                  # unmeasurable length: not a reason

    if pdf_path is not None:
        m = _NON_PAPER_NAME_RX.search(Path(pdf_path).name)
        if m:
            return f"filename says {m.group(0).lower()!r}"

    if text:
        head = text[:_FRONTMATTER_HEAD_CHARS]
        if _SERIES_RX.search(head) and _EDITORIAL_RX.search(head):
            return "front matter (series page + editor block)"

        n = count_contributions(text)
        if n > 1:
            return f"{n} contributions in one PDF (title-page stamps)"

    return None


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
