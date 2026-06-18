"""
topup_goldstandard.py

Optional pipeline step `topup` — runs AFTER a `gold` coding pass to keep the
goldstandard at its target size of HUMAN-confirmed research-software papers.

The `gold` step shows the coder the LLM-confirmed papers (`.workingset/
<set>_confirmed`, i.e. the papers the model labelled research software). The
human re-validates each one: some are confirmed (`rs=1`), some are rejected
(`rs=0`, not actually research software). Rejections shrink the usable
goldstandard below the target, so this step:

  1. Reads the coder's decisions (`goldstandard/coding_<user>.csv`) and
     PARTITIONS them into human-confirmed (rs=1) / human-rejected (rs=0) /
     still-uncoded, writing the confirmed set (with its full typology coding)
     and the rejected set to separate, shareable CSVs under `goldstandard/`.

  2. Computes how many LLM-confirmed papers must exist so that — after the
     human rejections — the coder can still reach the target:

         effective_target = target, bumped up by --bump_by every time the
                            human-confirmed count comes within --bump_threshold
                            of it (so as confirmations approach e.g. 90/100 the
                            goal grows to 120, making it likely that enough
                            actual-RSE papers are found);
         confirm_target   = effective_target + (# human-rejected)

     i.e. we ask the LLM-confirm step for enough positives that, once the
     already-rejected ones are set aside, `effective_target` codeable papers
     remain.

  3. Tops up `.workingset/<set>_confirmed` to `confirm_target` by invoking
     `confirm_positives.py --set <set> --target <confirm_target>`. That step is
     cumulative and cached: it only annotates NEW papers drawn from the `pool`
     reservoir, appending them to the same `goldconfirm` checkpoint that `gold`
     reads. The coder then re-runs `gold`, which resumes at the first uncoded
     paper (the freshly added ones).

Token: the top-up spends SAIA API quota (it annotates new pool papers). It is
only invoked when a token is available (--saia_token or SAIA_API_KEY) AND
--dry_run is not set. Otherwise this step just writes the separation CSVs and
PRINTS the exact `confirm` command to run — no quota is spent.

Usage (from the lni_study repo root):

    # report + separate only, no token spent:
    python src/topup_goldstandard.py --username alice --dry_run

    # separate AND top up the gold set back to the (bumped) target:
    python src/topup_goldstandard.py --username alice --saia_token $TOKEN

Worked example (target 100, bump_threshold 10, bump_by 20):
    coder coded 100 -> 60 confirmed, 40 rejected.
      effective_target = 100 (60 is not within 10 of 100)
      confirm_target   = 100 + 40 = 140  -> confirm tops up to 140 LLM-positives
    ...later, 90 confirmed, 70 rejected:
      effective_target = 120 (90 is within 10 of 100 -> bump once)
      confirm_target   = 120 + 70 = 190
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))
import categories as cat  # noqa: E402
from build_goldstandard import load_decisions, RS_DIM  # noqa: E402,F401
from annotate_lni import DEFAULT_PROMPT  # noqa: E402
import paper_length  # noqa: E402  (short-paper cap defaults forwarded to confirm)

REPO_ROOT = SRC_DIR.parent
# LNI_DATA_ROOT supersedes the in-repo default so generated data lives in an
# external working dir. See annotate_lni.DATA_ROOT.
DATA_ROOT = Path(os.environ.get("LNI_DATA_ROOT") or REPO_ROOT).resolve()
DEFAULT_WORKROOT = DATA_ROOT / ".workingset"
DEFAULT_SHARED = DATA_ROOT / "goldstandard"


def compute_effective_target(base: int, confirmed: int, threshold: int, by: int) -> int:
    """Grow the target by `by` each time `confirmed` is within `threshold` of it.

    As the human-confirmed count approaches the target (e.g. 90 of 100), the goal
    is bumped (to 120) so the coder keeps getting fresh candidates and enough
    actual-RSE papers are likely to be found. Terminates because each bump raises
    the (target - threshold) bar above the fixed `confirmed`."""
    if by <= 0:
        return base
    t = base
    while confirmed >= t - threshold:
        t += by
    return t


def load_manifest(workroot: Path, set_name: str) -> pd.DataFrame:
    """Read `.workingset/<set>_confirmed/manifest.csv` (the current LLM-confirmed
    set the coder is walking). Empty frame if it does not exist yet."""
    manifest = workroot / f"{set_name}_confirmed" / "manifest.csv"
    if not manifest.is_file():
        return pd.DataFrame(columns=["id", "volume", "rel_path", "title", "certainty", "dst"])
    return pd.read_csv(manifest, dtype={"id": str})


def write_partition(shared: Path, username: str, state: dict, meta: dict) -> dict:
    """Write the confirmed (with typology coding) and rejected CSVs; return counts.

    `meta` maps id -> {title, volume} from the working-set manifest (best effort).
    The confirmed CSV is the actual goldstandard slice: one row per rs=1 paper with
    its per-dimension final categories. The rejected CSV records the rs=0 ids."""
    confirmed_rows, rejected_rows = [], []
    for pid, st in state.items():
        if st.get("rs") == "1":
            row = {"id": pid,
                   "title": meta.get(pid, {}).get("title"),
                   "volume": meta.get(pid, {}).get("volume")}
            for dim in cat.DIMENSIONS:
                d = st["dims"].get(dim) or {}
                row[dim] = d.get("final_category", "")
            confirmed_rows.append(row)
        elif st.get("rs") == "0":
            rejected_rows.append({"id": pid,
                                  "title": meta.get(pid, {}).get("title"),
                                  "volume": meta.get(pid, {}).get("volume")})

    conf_cols = ["id", "title", "volume"] + list(cat.DIMENSIONS)
    conf_path = shared / f"gold_human_confirmed_{username}.csv"
    rej_path = shared / f"gold_human_rejected_{username}.csv"
    pd.DataFrame(confirmed_rows, columns=conf_cols).to_csv(conf_path, index=False)
    pd.DataFrame(rejected_rows, columns=["id", "title", "volume"]).to_csv(rej_path, index=False)
    return {"confirmed_path": conf_path, "rejected_path": rej_path,
            "confirmed": len(confirmed_rows), "rejected": len(rejected_rows)}


def build_confirm_argv(args, confirm_target: int, token: str | None) -> list[str]:
    """The confirm_positives invocation that grows <set>_confirmed to confirm_target.

    Model / run / prompt MUST match what produced the existing goldconfirm
    checkpoint, otherwise confirm would write a different checkpoint and `gold`
    would not see the new papers."""
    argv = [sys.executable, str(SRC_DIR / "confirm_positives.py"),
            "--set", args.set, "--target", str(confirm_target),
            "--pool", args.pool, "--batch", str(args.batch),
            "--workroot", str(Path(args.workroot).resolve()),
            "--model", args.model, "--run", args.run,
            "--prompt_template", str(args.prompt_template),
            "--short_pages", str(args.short_pages),
            "--max_short_frac", str(args.max_short_frac)]
    if token:
        argv += ["--saia_token", token]
    if args.saia_endpoint:
        argv += ["--saia_endpoint", args.saia_endpoint]
    return argv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Separate human-confirmed/rejected goldstandard papers and top "
                    "the LLM-confirmed set back up to the (bump-adjusted) target.")
    parser.add_argument("--username", required=True,
                        help="Coder whose progress drives the top-up.")
    parser.add_argument("--shared_folder", default=str(DEFAULT_SHARED),
                        help="Folder with coding_<user>.csv (default <root>/goldstandard).")
    parser.add_argument("--set", default="gold",
                        help="Working set whose *_confirmed the coder is walking (default gold).")
    parser.add_argument("--pool", default="pool",
                        help="Overflow reservoir confirm draws fresh candidates from.")
    parser.add_argument("--target", type=int, default=100,
                        help="Target number of HUMAN-confirmed RSE papers (default 100).")
    parser.add_argument("--bump_threshold", type=int, default=10,
                        help="Bump the target when confirmed comes within this many of it.")
    parser.add_argument("--bump_by", type=int, default=20,
                        help="How much to grow the target per bump (default 20).")
    parser.add_argument("--workroot", default=str(DEFAULT_WORKROOT),
                        help="Root for working sets (default <root>/.workingset).")
    parser.add_argument("--batch", type=int, default=50, help="confirm batch size.")
    parser.add_argument("--short_pages", type=int, default=paper_length.SHORT_PAGE_THRESHOLD,
                        help="Forwarded to confirm: a paper with fewer than this many "
                             f"pages is 'short' (default {paper_length.SHORT_PAGE_THRESHOLD}).")
    parser.add_argument("--max_short_frac", type=float, default=paper_length.MAX_SHORT_FRACTION,
                        help="Forwarded to confirm: cap the pool top-up draw so at most "
                             f"this fraction is short (default {paper_length.MAX_SHORT_FRACTION} "
                             "= 20%%).")
    parser.add_argument("--model", default="mistral-large-3-675b-instruct-2512",
                        help="SAIA model (MUST match the goldconfirm checkpoint).")
    parser.add_argument("--run", default="run_1",
                        help="Run id (MUST match the goldconfirm checkpoint).")
    parser.add_argument("--prompt_template", default=str(DEFAULT_PROMPT),
                        help="Prompt template (MUST match the goldconfirm checkpoint).")
    parser.add_argument("--saia_token", default=None, help="SAIA API key (overrides env).")
    parser.add_argument("--saia_endpoint", default=None, help="SAIA base URL (overrides env).")
    parser.add_argument("--dry_run", action="store_true",
                        help="Separate + report only; never call confirm (no quota spent).")
    args = parser.parse_args()

    shared = Path(args.shared_folder).resolve()
    out_path = shared / f"coding_{args.username}.csv"
    if not out_path.is_file():
        raise SystemExit(
            f"No coder decisions at {out_path}. Run the 'gold' step first so there "
            "is progress to top up.")

    workroot = Path(args.workroot).resolve()
    manifest = load_manifest(workroot, args.set)
    meta = {str(r["id"]): {"title": r.get("title"), "volume": r.get("volume")}
            for r in manifest.to_dict("records")}
    llm_confirmed_now = len(manifest)

    state = load_decisions(out_path)
    decided = {pid: st for pid, st in state.items() if st.get("rs") is not None}
    confirmed = sum(1 for st in decided.values() if st["rs"] == "1")
    rejected = sum(1 for st in decided.values() if st["rs"] == "0")
    # Codeable papers in the current set the coder has not decided yet.
    uncoded = sum(1 for pid in meta if state.get(pid, {}).get("rs") is None)

    effective_target = compute_effective_target(
        args.target, confirmed, args.bump_threshold, args.bump_by)
    confirm_target = effective_target + rejected

    part = write_partition(shared, args.username, state, meta)

    bumped = effective_target > args.target
    print(f"[config] data root   : {DATA_ROOT}"
          + ("  (in-repo default)" if DATA_ROOT == REPO_ROOT else "  (LNI_DATA_ROOT)"))
    print(f"[config] coder       : {args.username}  ({out_path.name})")
    print(f"[config] working set : {workroot / (args.set + '_confirmed')}")
    print("-" * 64)
    print(f"  human-confirmed (rs=1) : {confirmed}")
    print(f"  human-rejected  (rs=0) : {rejected}")
    print(f"  uncoded in current set : {uncoded}")
    print(f"  LLM-confirmed available: {llm_confirmed_now}")
    print("-" * 64)
    print(f"  base target            : {args.target}")
    print(f"  effective target       : {effective_target}"
          + (f"  (bumped +{effective_target - args.target}: confirmed is within "
             f"{args.bump_threshold} of target)" if bumped else "  (no bump)"))
    print(f"  confirm target         : {effective_target} + {rejected} rejected "
          f"= {confirm_target} LLM-positives")
    print("-" * 64)
    print(f"  separated -> {part['confirmed_path'].name} ({part['confirmed']} papers, "
          f"with typology coding)")
    print(f"  separated -> {part['rejected_path'].name} ({part['rejected']} papers)")
    print("-" * 64)

    need = confirm_target - llm_confirmed_now
    if need <= 0:
        print(f"Already have {llm_confirmed_now} LLM-confirmed >= confirm target "
              f"{confirm_target}. No top-up needed - keep coding with the 'gold' step "
              f"({uncoded} uncoded remain).")
        return

    token = args.saia_token or os.getenv("SAIA_API_KEY")
    argv = build_confirm_argv(args, confirm_target, token)
    # Redact the token value (the arg right after --saia_token) before printing.
    redacted = list(argv)
    if "--saia_token" in redacted:
        ti = redacted.index("--saia_token")
        if ti + 1 < len(redacted):
            redacted[ti + 1] = "<TOKEN>"
    printable = " ".join(redacted)
    if args.dry_run or not token:
        why = "dry run" if args.dry_run else "no SAIA token (set SAIA_API_KEY or --saia_token)"
        print(f"Need {need} more LLM-confirmed paper(s) to reach {confirm_target}. "
              f"NOT topping up ({why}). Run:\n  {printable}")
        return

    print(f"Topping up: need {need} more LLM-confirmed paper(s) -> running confirm "
          f"to target {confirm_target} (annotates new '{args.pool}' papers only)...")
    proc = subprocess.run(argv)
    if proc.returncode != 0:
        raise SystemExit(f"confirm_positives exited with {proc.returncode}.")
    print(f"\nTop-up done. Re-run the 'gold' step as {args.username} to code the "
          f"newly added papers (it resumes at the first uncoded one).")


if __name__ == "__main__":
    main()
