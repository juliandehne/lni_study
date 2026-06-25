"""
check_schema_integrity.py

Fail-loud tripwire for a corrupted typology schema (prompts/category_schema.yaml).

A concurrent / clobbering schema write can leave one dimension's `active` list
holding ANOTHER dimension's categories (observed: `software_lifecycle.active`
ended up carrying `software_type` entries, so a coder was shown a pick-list mixing
two dimensions). Once that lands on disk, every downstream reader — the model
prompt, `build_goldstandard`'s pick-list, `compute_icr` — silently trusts it.

This check is meant to run BEFORE the interactive `gold` coding session (and is
cheap enough to run anywhere). It exits non-zero with a precise message on any
violation, so corruption stops the session instead of feeding a coder the wrong
categories. Writes nothing.

Invariants enforced (all HARD failures):
  1. The dimension set is exactly the five expected dimensions.
  2. Within a dimension, no `active` key is duplicated or blank.
  3. `software_lifecycle.active` is a subset of the six canonical lifecycle
     phases. This dimension is seed-stable (the classical SE lifecycle); a key
     outside this set is corruption. If a NEW lifecycle phase is ever added on
     purpose (via the narrowing loop), extend CANONICAL_LIFECYCLE below.

NOTE on cross-dimension keys: the same human-readable key legitimately appears in
more than one dimension here (e.g. `conceptual` is a valid `software_type` AND
`techstack` category; `testing` a valid `evaluation` AND `research_position` one),
so a global "key unique across dimensions" rule would false-positive. The precise
tripwire for the observed corruption is invariant 3: the seed-stable
`software_lifecycle` dimension must not absorb another dimension's vocabulary.

Usage (from the lni_study repo root):
    python src/check_schema_integrity.py            # exit 0 = clean, 1 = corrupt
    python src/check_schema_integrity.py --quiet    # only print on failure
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema_io  # noqa: E402

EXPECTED_DIMENSIONS = {
    "research_position",
    "software_lifecycle",
    "software_type",
    "techstack",
    "evaluation",
}

# The six classical software-lifecycle phases this dimension is seeded with (see
# the `software_lifecycle` block in category_schema.yaml). If a genuinely new
# phase is curated in via the narrowing loop, add its key here so the tripwire
# keeps passing.
CANONICAL_LIFECYCLE = {
    "projektdefinition",
    "anforderungen",
    "entwurf",
    "implementierung",
    "testen_qualitaetssicherung",
    "deployment_betrieb",
}


def _active_keys(spec) -> list[str]:
    """The `active` bucket's keys for one dimension spec, in file order."""
    return [str(e.get("key")) for e in (spec.get("active") or []) if e.get("key") is not None]


def check_schema(schema) -> list[str]:
    """Return a list of human-readable problem strings (empty = schema is sound)."""
    problems: list[str] = []
    dims = schema.get("dimensions") or {}

    # 1. Dimension set.
    present = set(dims.keys())
    if present != EXPECTED_DIMENSIONS:
        missing = EXPECTED_DIMENSIONS - present
        extra = present - EXPECTED_DIMENSIONS
        if missing:
            problems.append(f"missing dimension(s): {sorted(missing)}")
        if extra:
            problems.append(f"unexpected dimension(s): {sorted(extra)}")

    # 2. Per-dimension key uniqueness (no duplicate / blank active keys).
    for dim in sorted(dims.keys()):
        seen: set[str] = set()
        for k in _active_keys(dims[dim] or {}):
            if not k or k == "None":
                problems.append(f"[{dim}] active entry with blank/None key")
                continue
            if k in seen:
                problems.append(f"[{dim}] duplicate active key {k!r}")
            seen.add(k)

    # 3. software_lifecycle stays within the canonical phase set.
    lc = dims.get("software_lifecycle")
    if lc is not None:
        stray = [k for k in _active_keys(lc) if k not in CANONICAL_LIFECYCLE]
        if stray:
            problems.append(
                "software_lifecycle.active contains non-lifecycle key(s): "
                f"{stray}. Expected a subset of {sorted(CANONICAL_LIFECYCLE)}. "
                "If a new phase was added on purpose, extend CANONICAL_LIFECYCLE "
                "in check_schema_integrity.py; otherwise the schema is corrupted "
                "(likely a clobbered concurrent write).")

    return problems


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Fail-loud integrity check for the typology schema.")
    ap.add_argument("--schema", default=str(schema_io.SCHEMA_PATH),
                    help="Path to category_schema.yaml (defaults to the repo schema).")
    ap.add_argument("--quiet", action="store_true",
                    help="Only print on failure (no 'OK' line).")
    args = ap.parse_args()

    schema = schema_io.load_schema(args.schema)
    problems = check_schema(schema)

    if problems:
        print(f"[schema-integrity] FAIL — {len(problems)} problem(s) in {args.schema}:",
              file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print("[schema-integrity] Refusing to proceed. Restore a clean schema "
              "(e.g. git checkout prompts/category_schema.yaml or a backup) before "
              "coding.", file=sys.stderr)
        raise SystemExit(1)

    if not args.quiet:
        print(f"[schema-integrity] OK — {len(EXPECTED_DIMENSIONS)} dimensions, "
              "no duplicate keys, software_lifecycle within canonical phases.")


if __name__ == "__main__":
    main()
