"""
sampling.py

Stratified sampling over the LNI corpus, using the LNI **volume folders**
(lni37, lni52, lni132, ...) as the strata (groups).

Why stratified rather than a single global shuffle: the corpus is split into
LNI volumes of very different sizes (e.g. lni169 ~27 PDFs vs lni338 ~200 PDFs).
A plain random/`first-N` draw can over- or under-represent whole volumes. A
stratified draw with **proportional (largest-remainder) allocation** gives every
volume a share of the sample proportional to its size, so a test/narrowing
sample spans the corpus in a balanced, reproducible way.

Used by:
  - `annotate_lni.py`  (the `--test` / `--sample N` draws), and
  - `narrow_categories.py` (the 50-paper subcategory-narrowing sample).

Determinism: allocation is purely a function of the group sizes and N; the
within-group draw is seeded per group (`f"{seed}:{group}"`), so re-runs select
the same papers (resume-safe), and the seed string makes it stable across
processes (unlike the salted built-in `hash()`).
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable


def volume_of(pdf_path: Path) -> str:
    """Fallback grouping key: the immediate parent folder. Correct only when the
    corpus is flat (PDFs directly inside each volume folder). For the real LNI
    corpus, where PDFs nest deeper inside the volume folders, use
    `volume_under(corpus_root)` instead so the stratum is the top-level LNI volume."""
    return pdf_path.parent.name


def paper_id(pdf_path: Path, root: Path) -> str:
    """Collision-free paper id: the PDF's path relative to `root`, without the
    .pdf suffix, as a posix string — e.g. 'lni132/SimpleArchiveFormat/item_10/125'.

    Using the full relative path (rather than just '<parent>/<stem>') avoids
    collisions when several LNI volumes export PDFs under an identical DSpace
    `SimpleArchiveFormat/item_N/` tree. Because the working copy preserves each
    PDF's path relative to the corpus root, this id is identical on the full
    corpus and on the local `.workingset/<name>` copy. Falls back to
    '<parent>/<stem>' if the PDF is somehow not under `root`.
    """
    pdf_path = Path(pdf_path).resolve()
    root = Path(root).resolve()
    try:
        rel = pdf_path.relative_to(root)
    except ValueError:
        return f"{pdf_path.parent.name}/{pdf_path.stem}"
    return rel.with_suffix("").as_posix()


def volume_under(corpus_root: Path) -> Callable[[Path], str]:
    """Return a grouping function whose key is the **top-level folder under
    `corpus_root`** — i.e. the LNI volume (lni37, lni132, ...), regardless of how
    deeply the PDF is nested inside that volume's subfolders.

    Papers outside `corpus_root` (shouldn't happen) fall back to the immediate
    parent name.
    """
    corpus_root = Path(corpus_root).resolve()

    def _key(pdf_path: Path) -> str:
        try:
            rel = pdf_path.resolve().relative_to(corpus_root)
        except ValueError:
            return pdf_path.parent.name
        # parts[0] is the volume folder; if the PDF sits directly in corpus_root
        # (no volume folder), fall back to the parent name.
        return rel.parts[0] if len(rel.parts) > 1 else pdf_path.parent.name

    return _key


def group_by(pdfs: Iterable[Path], group_fn: Callable[[Path], str]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for p in pdfs:
        groups[group_fn(p)].append(p)
    return dict(groups)


def allocate_proportional(group_sizes: dict[str, int], n: int) -> dict[str, int]:
    """Largest-remainder proportional allocation of `n` slots across groups.

    Each group g gets floor(n * size_g / total) slots, then the leftover slots
    are handed out one at a time to the groups with the largest fractional
    remainders (ties broken by larger group, then group name — deterministic).
    A group never receives more slots than it has papers; if N exceeds the
    corpus size the whole corpus is returned.
    """
    sizes = {g: s for g, s in group_sizes.items() if s > 0}
    total = sum(sizes.values())
    if total == 0:
        return {g: 0 for g in group_sizes}
    n = min(n, total)

    raw = {g: n * s / total for g, s in sizes.items()}
    alloc = {g: min(int(math.floor(v)), sizes[g]) for g, v in raw.items()}

    # Order for handing out leftovers: largest fractional remainder first.
    order = sorted(sizes, key=lambda g: (-(raw[g] - math.floor(raw[g])), -sizes[g], g))
    remaining = n - sum(alloc.values())
    i = 0
    # Guard against an impossible loop (cannot exceed total capacity by construction).
    while remaining > 0 and i < 100 * max(1, len(order)):
        g = order[i % len(order)]
        if alloc[g] < sizes[g]:
            alloc[g] += 1
            remaining -= 1
        i += 1

    # Groups that were empty keep a 0 entry so callers can log them.
    for g in group_sizes:
        alloc.setdefault(g, 0)
    return alloc


def stratified_sample(
    pdfs: list[Path],
    n: int,
    seed: int = 42,
    group_fn: Callable[[Path], str] = volume_of,
) -> tuple[list[Path], dict[str, int]]:
    """Draw a stratified sample of `n` paths, grouped by `group_fn`.

    Returns (selected_paths, allocation) where allocation maps each group to the
    number of papers drawn from it. Selection within a group is a seeded shuffle
    of the group's papers (sorted first for a stable base order), so the draw is
    reproducible.
    """
    groups = group_by(pdfs, group_fn)
    sizes = {g: len(v) for g, v in groups.items()}
    alloc = allocate_proportional(sizes, n)

    selected: list[Path] = []
    for g in sorted(groups):
        items = sorted(groups[g])
        random.Random(f"{seed}:{g}").shuffle(items)
        selected.extend(items[: alloc[g]])
    return selected, alloc


def format_allocation(alloc: dict[str, int], sizes: dict[str, int] | None = None) -> str:
    """One-line human summary, e.g. 'lni132: 8/77, lni338: 21/200, ...'."""
    parts = []
    for g in sorted(alloc):
        if sizes is not None:
            parts.append(f"{g}: {alloc[g]}/{sizes.get(g, '?')}")
        else:
            parts.append(f"{g}: {alloc[g]}")
    return ", ".join(parts)