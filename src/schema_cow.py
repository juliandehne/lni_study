"""
schema_cow.py

Copy-on-write + 3-way merge for prompts/category_schema.yaml, so two processes
can evolve the typology concurrently without a file lock and without a
last-writer-wins clobber.

Why not a lock? The schema edits the loop makes are local and mostly additive:
`collect` appends candidates (and bumps a `count` on ones it re-sees), `review`
moves candidates into active/rejected, `synccats` folds coder categories into
active. These rarely touch the SAME entry from two processes at once, so they
can be merged instead of serialised. Each writer:

  1. work_copy()  -> snapshots the canonical YAML to a NUMBERED working copy
                     (category_schema.work.<N>.yaml) PLUS a pristine base
                     snapshot (category_schema.base.<N>.yaml), and does all its
                     mutations on the working copy.
  2. merge_back()  -> RE-READS the canonical fresh (picking up any other
                     writer's changes in the meantime) and 3-way-merges
                     work-vs-base-vs-canonical, keyed by (dimension, section,
                     category key). The base snapshot is what makes this a true
                     merge rather than a clobber: it lets us tell "the work copy
                     CHANGED this" from "the work copy just didn't touch it".

3-way rules, per (dimension, section, key):
  - changed in work only      -> take work's version (covers adds + count bumps)
  - changed in canonical only -> keep canonical (covers a concurrent writer)
  - deleted in work, untouched in canonical -> delete (covers review's promote)
  - changed/deleted in BOTH differently -> CONFLICT: keep canonical, flag it

Canonical's own sequences are mutated in place (entries replaced/removed/appended
by key) so untouched entries keep their ruamel comments and layout. The merged
result is written back atomically (temp sibling + os.replace). merge_back never
raises on a divergence — conflicts are reported, not resolved.

This module is standalone and additive — it does not modify schema_io.py.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import schema_io

WORK_DIR = schema_io.SCHEMA_PATH.parent / ".schema_work"
SECTIONS = ("active", "rejected", "candidates")


def work_copy(canonical: str | Path = schema_io.SCHEMA_PATH) -> Path:
    """Snapshot the canonical schema to a fresh numbered working copy (+ a
    pristine base snapshot for the later 3-way merge) and return the working
    copy's path. Numbering is the next free integer so concurrent callers don't
    collide."""
    canonical = Path(canonical)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    existing = [int(p.stem.split(".")[-1])
                for p in WORK_DIR.glob("category_schema.work.*.yaml")
                if p.stem.split(".")[-1].isdigit()]
    n = (max(existing) + 1) if existing else 1
    work = WORK_DIR / f"category_schema.work.{n}.yaml"
    base = WORK_DIR / f"category_schema.base.{n}.yaml"
    # Two independent loads so the work copy and base snapshot are separate
    # object graphs (editing one never aliases the other).
    schema_io.save_schema(schema_io.load_schema(canonical), work)
    schema_io.save_schema(schema_io.load_schema(canonical), base)
    return work


def _base_for(work_path: Path) -> Path:
    """The base snapshot path paired with a working copy by number."""
    return work_path.with_name(work_path.name.replace(".work.", ".base.", 1))


def discard(work_path: str | Path) -> None:
    """Delete a working copy and its base snapshot without merging — for the
    case where a writer made a work copy but ended up changing nothing."""
    work_path = Path(work_path)
    for p in (work_path, _base_for(work_path)):
        try:
            p.unlink()
        except OSError:
            pass


def _by_key(seq) -> dict:
    """key -> item for a schema list section (items without `key` are skipped)."""
    out = {}
    for item in (seq or []):
        try:
            k = item.get("key")
        except AttributeError:
            continue
        if k is not None:
            out[k] = item
    return out


def _plain(obj):
    """Recursively convert a ruamel object to plain dict/list/scalar for value
    comparison (ignoring comments/formatting)."""
    if hasattr(obj, "items"):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


def _eq(a, b) -> bool:
    return _plain(a) == _plain(b)


def _index_of(seq, key) -> int:
    for i, item in enumerate(seq or []):
        try:
            if item.get("key") == key:
                return i
        except AttributeError:
            continue
    return -1


@dataclass
class MergeReport:
    added: dict = field(default_factory=dict)        # "dim/section" -> [keys]
    updated: dict = field(default_factory=dict)      # "dim/section" -> [keys]
    deleted: dict = field(default_factory=dict)      # "dim/section" -> [keys]
    conflicts: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def _n(self, d) -> int:
        return sum(len(v) for v in d.values())

    @property
    def changed(self) -> int:
        return self._n(self.added) + self._n(self.updated) + self._n(self.deleted)

    def summary(self) -> str:
        lines = [f"[schema-cow] merged: +{self._n(self.added)} added, "
                 f"~{self._n(self.updated)} updated, -{self._n(self.deleted)} deleted"]
        for label, d in (("+", self.added), ("~", self.updated), ("-", self.deleted)):
            for loc, keys in d.items():
                if keys:
                    lines.append(f"  {label} {loc}: {', '.join(map(str, keys))}")
        for c in self.conflicts:
            lines.append(f"  ! conflict (canonical kept): {c}")
        for n in self.notes:
            lines.append(f"  . {n}")
        return "\n".join(lines)


def merge_back(work_path: str | Path,
               canonical: str | Path = schema_io.SCHEMA_PATH,
               *, base_path: str | Path | None = None,
               keep_work_copy: bool = True) -> MergeReport:
    """3-way merge a working copy back into a FRESH read of the canonical and
    write the result atomically. Returns a MergeReport; never raises on a
    content divergence (those are flagged, not resolved)."""
    work_path = Path(work_path)
    canonical = Path(canonical)
    base_path = Path(base_path) if base_path else _base_for(work_path)
    report = MergeReport()

    work = schema_io.load_schema(work_path)
    canon = schema_io.load_schema(canonical)   # re-read: pick up concurrent edits
    base = schema_io.load_schema(base_path) if base_path.is_file() else None
    if base is None:
        report.notes.append(
            "base snapshot missing; additive merge only (deletions not applied)")

    wdims = work.get("dimensions") or {}
    cdims = canon.get("dimensions")
    if cdims is None:
        canon["dimensions"] = cdims = schema_io.new_map()
    bdims = (base.get("dimensions") or {}) if base is not None else {}

    for dim, wdim in wdims.items():
        if dim not in cdims:
            cdims[dim] = wdim
            report.notes.append(f"added whole new dimension '{dim}' from work copy")
            continue
        cdim = cdims[dim]
        bdim = bdims.get(dim) or {}
        for sec in SECTIONS:
            wmap = _by_key(wdim.get(sec))
            bmap = _by_key(bdim.get(sec))
            if cdim.get(sec) is None and wmap:
                cdim[sec] = schema_io.new_seq()
            cseq = cdim.get(sec)
            cmap = _by_key(cseq)

            # ---- additions & updates coming FROM the work copy ----
            for k, witem in wmap.items():
                work_changed = (k not in bmap) or not _eq(witem, bmap[k])
                if not work_changed:
                    continue
                if k not in cmap:
                    cseq.append(witem)
                    report.added.setdefault(f"{dim}/{sec}", []).append(k)
                    continue
                canon_changed = (k not in bmap) or not _eq(cmap[k], bmap[k])
                if not canon_changed:
                    cseq[_index_of(cseq, k)] = witem      # safe: only work edited
                    report.updated.setdefault(f"{dim}/{sec}", []).append(k)
                elif not _eq(witem, cmap[k]):
                    report.conflicts.append(
                        f"{dim}/{sec}: '{k}' edited in both; canonical kept")

            # ---- deletions made in the work copy (needs the base snapshot) ----
            if base is not None:
                for k, bitem in bmap.items():
                    if k in wmap or k not in cmap:
                        continue                          # not deleted, or already gone
                    if not _eq(cmap[k], bitem):
                        report.conflicts.append(
                            f"{dim}/{sec}: '{k}' deleted in work but edited in "
                            "canonical; canonical kept")
                        continue
                    del cseq[_index_of(cseq, k)]
                    report.deleted.setdefault(f"{dim}/{sec}", []).append(k)

    # Atomic write-back: dump to a temp sibling, then os.replace onto canonical.
    tmp = canonical.with_suffix(canonical.suffix + ".cowtmp")
    schema_io.save_schema(canon, tmp)
    os.replace(tmp, canonical)

    if not keep_work_copy:
        for p in (work_path, base_path):
            try:
                p.unlink()
            except OSError:
                pass
    return report


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Schema copy-on-write helper.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("copy", help="make a numbered working copy (+ base snapshot)")
    mp = sub.add_parser("merge", help="3-way merge a working copy back into canonical")
    mp.add_argument("work_path")
    mp.add_argument("--drop", action="store_true",
                    help="delete the work copy + base snapshot after merge")
    args = ap.parse_args()

    if args.cmd == "copy":
        print(work_copy())
    elif args.cmd == "merge":
        print(merge_back(args.work_path, keep_work_copy=not args.drop).summary())
