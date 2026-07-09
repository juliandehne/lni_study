#!/usr/bin/env python
"""
check_annotations.py  --  user-facing runner for the rse_code_annotations testbed.

Run this from the lni_study repo root:

    python check_annotations.py

What it does
------------
1. Runs the rse_annotations checker over the two annotated modules
   (``src/compute_icr.py`` and ``src/krippendorff_reference.py``):
     - verifies each annotation is placed correctly
       (@functional is pure; @data_input reads; @data_output writes),
     - checks docstrings document the declared fields,
     - invokes the boundary functions in a sandbox to confirm real I/O
       (using the fixtures in ``src/annotation_fixtures.py``),
     - prints the source of every @functional as a review snippet, and
     - **infers the mathematical formula** of every @functional and prints it
       for human inspection (this is where Krippendorff's alpha shows up).

2. Runs the Krippendorff **differential verification**: the transparent
   reference implementation is compared against the trusted ``krippendorff``
   library on random reliability matrices.

Flags (forwarded to the checker):
    --json          machine-readable output instead of text
    --no-stubs      never call Fable for pytest stubs (default here: on)
    --stubs         allow Fable stub generation (needs ANTHROPIC_API_KEY)
    --effort L      Fable effort {low,medium,high,xhigh,max}
    --skip-verify   don't run the Krippendorff differential check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
# Make the annotated modules importable as top-level names.
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Make the framework importable even if it isn't pip-installed: fall back to
# the sibling submodule checkout, exactly like src/rse_annotations_shim.py does.
_SIBLING = HERE.resolve().parents[1] / "rse_code_annotations"
if _SIBLING.is_dir() and str(_SIBLING) not in sys.path:
    sys.path.insert(0, str(_SIBLING))

try:
    from rse_annotations import Runner, render_json, render_text
except Exception as exc:  # noqa: BLE001
    print("Could not import the rse_annotations framework.")
    print(f"  reason: {exc}")
    print("Install it with:  pip install -e ../rse_code_annotations")
    raise SystemExit(2)

# Modules to check (top-level importable now that src/ is on the path).
TARGETS = ["compute_icr", "krippendorff_reference"]


def _run_checker(args) -> bool:
    import annotation_fixtures as fx

    all_ok = True
    reports = []
    for target in TARGETS:
        runner = Runner(
            target,
            fixtures=fx.FIXTURES,
            generate_stubs=args.stubs,
            probe=True,
            effort=args.effort,
        )
        report = runner.run()
        reports.append((target, report))
        all_ok = all_ok and report.ok

    if args.json:
        import json
        print(json.dumps(
            {t: r.to_dict() for t, r in reports}, indent=2))
        return all_ok

    for target, report in reports:
        print("#" * 70)
        print(f"# module: {target}")
        print("#" * 70)
        print(render_text(report, show_snippets=True))
        print()
    return all_ok


def _run_verification() -> bool:
    import krippendorff_reference as kr

    result = kr.verify_against_library()
    print("=" * 70)
    print("Krippendorff nominal alpha -- differential verification")
    print("=" * 70)
    print(f"  closed form   : alpha = 1 - (n - 1) * (n - A) / (n**2 - B)")
    print(f"  trials checked: {result['checked']}")
    print(f"  trials skipped: {result['skipped']} (degenerate / library-rejected)")
    print(f"  worst |delta| : {result['worst_delta']:.3e}")
    if result["ok"]:
        print("  RESULT: PASS -- reference matches the krippendorff library.")
        return True
    if result["checked"] == 0:
        print("  RESULT: INCONCLUSIVE -- krippendorff library not installed.")
        return True  # not a failure of our code
    print(f"  RESULT: FAIL -- {len(result['failures'])} disagreement(s).")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    stub = parser.add_mutually_exclusive_group()
    stub.add_argument("--stubs", dest="stubs", action="store_true",
                      help="allow Fable pytest-stub generation (needs ANTHROPIC_API_KEY)")
    stub.add_argument("--no-stubs", dest="stubs", action="store_false",
                      help="never call Fable (default)")
    parser.set_defaults(stubs=False)
    parser.add_argument("--effort", default="medium",
                        choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--skip-verify", action="store_true",
                        help="skip the Krippendorff differential verification")
    args = parser.parse_args()

    checks_ok = _run_checker(args)

    verify_ok = True
    if not args.skip_verify and not args.json:
        print()
        verify_ok = _run_verification()

    raise SystemExit(0 if (checks_ok and verify_ok) else 1)


if __name__ == "__main__":
    main()
