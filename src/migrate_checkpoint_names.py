"""One-off migration: rename result files from full model id to model family.

Checkpoints and their paired suggestion files used to embed the exact model id:

    results/checkpoints/annotations_goldconfirm_mistral-large-3-675b-instruct-2512_rse_typology_prompt_v1_run_1_checkpoint.csv
    results/new_category_suggestions_gold_mistral-large-3-675b-instruct-2512_rse_typology_prompt_v1_run_1.csv

That made the filename a version pin. When GWDG retired
mistral-large-3-675b-instruct-2512 the path stopped resolving, and the coding
step would have opened an empty checkpoint and lost all stored annotations.
Names now carry only the family (`mistral`), which survives a version bump; the
exact id of every call is already recorded per row in the `model` column, which
is the better place for it anyway -- a file that spans two versions can say so
row by row, a filename cannot.

Renames every file under results/ (including .bak/.legacy sidecars) whose name
contains a known full model id, replacing that id with its family slug. Refuses
to overwrite an existing target. Dry-run by default.

    python src/migrate_checkpoint_names.py            # show what would happen
    python src/migrate_checkpoint_names.py --apply    # do it
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight  # noqa: E402

RESULTS = preflight.DATA_ROOT / "results"

def known_model_ids(root: Path) -> set[str]:
    """The exact model ids that actually appear in this results folder.

    Read from the checkpoints' own `model` column rather than guessed from the
    filenames. Pattern-matching filenames is not safe here: sidecars like
    `...run_1.legacy-2026-06-15.bak` contain hyphen-plus-digits runs that look
    exactly like a versioned model id, and a regex happily renames the date away.
    Substituting only ids the data itself vouches for cannot do that.
    """
    ids: set[str] = {preflight.DEFAULT_MODEL}
    for ck in root.rglob("annotations_*_checkpoint.csv"):
        try:
            col = pd.read_csv(ck, usecols=["model"])["model"]
        except Exception:
            continue
        ids.update(str(v) for v in col.dropna().unique() if str(v).strip())
    # A bare family slug is already migrated; substituting it would be a no-op
    # anyway, but drop it so the plan stays honest.
    return {i for i in ids if i != preflight.model_family(i)}


def rename_in(name: str, ids: set[str]) -> str:
    """Replace each known full model id in `name` with its family slug."""
    # Longest first: if two ids share a prefix, the specific one must win.
    for mid in sorted(ids, key=len, reverse=True):
        name = name.replace(mid, preflight.model_family(mid))
    return name


def plan(root: Path, ids: set[str]) -> list[tuple[Path, Path]]:
    moves = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        new = rename_in(path.name, ids)
        if new != path.name:
            moves.append((path, path.with_name(new)))
    return moves


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="Actually rename (default: dry run).")
    ap.add_argument("--results", default=str(RESULTS),
                    help=f"Results folder to migrate (default {RESULTS}).")
    args = ap.parse_args()

    root = Path(args.results).resolve()
    if not root.is_dir():
        sys.exit(f"no such results folder: {root}")

    ids = known_model_ids(root)
    print(f"model ids found in the checkpoints' `model` column: "
          + (", ".join(f"{i} -> {preflight.model_family(i)}" for i in sorted(ids))
             or "(none)"))
    moves = plan(root, ids)
    if not moves:
        print(f"nothing to migrate under {root} (already family-named).")
        return

    clashes = [(a, b) for a, b in moves if b.exists()]
    for src, dst in moves:
        mark = "  !! TARGET EXISTS" if dst.exists() else ""
        print(f"  {src.relative_to(root)}\n    -> {dst.name}{mark}")
    print(f"\n{len(moves)} file(s) to rename under {root}")

    if clashes:
        sys.exit(f"\nABORT: {len(clashes)} target name(s) already exist. "
                 "Resolve by hand -- refusing to overwrite annotations.")
    if not args.apply:
        print("\nDry run. Re-run with --apply to rename.")
        return

    for src, dst in moves:
        src.rename(dst)
    print(f"\nrenamed {len(moves)} file(s).")


if __name__ == "__main__":
    main()
