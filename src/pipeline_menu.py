r"""
pipeline_menu.py

Interactive front door for the lni_study pipeline. The pipeline grew a lot of
run configurations (token resolution, LNI_DATA_ROOT redirection, a read-only
corpus, per-stage positional extras like round labels / confirm targets), and
remembering the exact `run_pipeline.cmd <step> <token> "" "" r2` incantation for
each stage is error-prone. This launcher replaces that recall with a dialog:

  1. Pick a STAGE by number (same numbered-prompt style as the project's other
     interactive sessions: build_goldstandard, narrow_categories review, ...).
  2. AFFIRM (and optionally edit) the two paths that decide where data comes from
     and goes to:
        - working dir  (LNI_DATA_ROOT)  -> results/, .workingset/, goldstandard/
        - corpus PDFs  (LNI_CORPUS)     -> the read-only source volumes
  3. The SAIA token is taken from the environment (SAIA_TOKEN / SAIA_API_KEY) and
     ONLY prompted for when the chosen stage needs one and none is found. It is
     handed to the child via the environment, never echoed and never placed on
     THIS launcher's command line.
  4. Any per-stage extras (sample size, confirm set/target, round label, ...) are
     asked for inline, then the whole thing is dispatched to run_pipeline.cmd.

The launcher itself spends no token and runs no network call unless you opt into
the SAIA reachability check at the end (default: no), so it is safe to poke at.

    python src/pipeline_menu.py
"""

import getpass
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight  # noqa: E402  (reuse the path/SAIA checks + default endpoint)

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_CMD = REPO_ROOT / "run_pipeline.cmd"
DEFAULT_CORPUS = r"Z:\Publikationen\LNI\Proceedings"

# --- models ------------------------------------------------------------------
# DEFAULT_MODEL mirrors run_pipeline.cmd's MODEL (the full final-grade model).
# The narrowing-loop steps below only MINE candidate subcategories, so they may
# run on a faster/smaller model; affirmed per-run and exported as
# LNI_ADVANCE_MODEL (picked up by run_pipeline.cmd's ADVANCE_MODEL knob).
DEFAULT_MODEL = "mistral-large-3-675b-instruct-2512"
LOOP_MODEL_STAGES = {"advance", "round", "reannotate"}

# --- token env vars, in the priority order run_pipeline.cmd uses -------------
TOKEN_ENV_VARS = ("SAIA_TOKEN", "SAIA_API_KEY")
PLACEHOLDER_TOKEN = "<SAIA_TOKEN>"  # the cmd's unset placeholder; treat as "no token"


# --- the stages, grouped exactly like run_pipeline.cmd's usage block ---------
# needs_token: stage spends / requires a SAIA token.
# uses_corpus: stage reads the read-only corpus PDFs (so the corpus path matters).
# extras:      ordered list of per-stage prompts, each (argpos, prompt_fn) where
#              argpos is the run_pipeline.cmd positional slot (2..5) it fills.
class Stage:
    def __init__(self, key, group, desc, *, needs_token=False, uses_corpus=False,
                 extras=None):
        self.key = key
        self.group = group
        self.desc = desc
        self.needs_token = needs_token
        self.uses_corpus = uses_corpus
        self.extras = extras or []  # list of (argpos:int, ask:callable->str)


def _ask_sample_n():
    v = input("    final-study sample size (arg3, blank = pipeline default): ").strip()
    return v


def _ask_overwrite():
    v = input("    re-annotate ALL gold papers? overwrite existing? [y/N]: ").strip().lower()
    return "overwrite" if v in ("y", "yes") else ""


def _ask_absent_only():
    v = input("    absent-only? fill ONLY blank cells for EVERY paper "
              "(no full refresh of uncoded; much faster) [y/N]: ").strip().lower()
    return "absent-only" if v in ("y", "yes") else ""


def _ask_confirm_set():
    v = input("    working set to confirm (arg4, blank = gold): ").strip()
    return v


def _ask_confirm_target():
    v = input("    target count (arg5, blank = set size): ").strip()
    return v


def _ask_reannotate_set():
    v = input("    set to re-annotate (arg4, blank = narrow): ").strip()
    return v


def _ask_reannotate_cap():
    v = input("    cap on how many to redo (arg5, blank = all): ").strip()
    return v


def _ask_advance_batch():
    v = input("    advance batch size (arg5, blank = default NARROW): ").strip()
    return v


def _ask_round_label():
    v = input("    round label for saturation tracking, e.g. r2 (arg5, blank = none): ").strip()
    return v


def _ask_export_dest():
    v = input("    destination (arg2, blank = default P: shared folder): ").strip().strip('"')
    return v


def _ask_export_dry():
    v = input("    dry run? preview the copy, copy nothing [y/N]: ").strip().lower()
    return "dry" if v in ("y", "yes") else ""


STAGES = [
    # ---- Setup ----
    Stage("deps", "Setup", "pip install -r requirements.txt (one-time)"),
    Stage("dry", "Setup", "Step 0 - offline dry run: extraction + prompt, NO token",
          uses_corpus=True),
    Stage("preview", "Setup",
          "PRINT all prompts (system + annotation + fill) with sizes, NO token/corpus"),
    Stage("test", "Setup", "Step 1 - 5-paper live test (needs token)",
          needs_token=True, uses_corpus=True),
    # ---- Estimator ----
    Stage("estimate", "Estimator (non-LLM)",
          "stream corpus, fill .workingset narrow/gold/final/pool, NO token",
          uses_corpus=True, extras=[(3, _ask_sample_n)]),
    Stage("manifests", "Estimator (non-LLM)",
          "RECOVERY: rebuild .workingset/*/manifest.csv, NO token",
          uses_corpus=True, extras=[(3, _ask_sample_n)]),
    Stage("confirm", "Estimator (non-LLM)",
          "OPTIONAL: LLM-confirm a working set, top up from pool (needs token)",
          needs_token=True, extras=[(4, _ask_confirm_set), (5, _ask_confirm_target)]),
    # ---- Narrowing loop ----
    Stage("round", "Narrowing loop",
          "ONE iteration: advance -> collect -> review (needs token)",
          needs_token=True, extras=[(5, _ask_round_label)]),
    Stage("reannotate", "Narrowing loop",
          "FORCE-REDO confirmed papers under the current schema (needs token)",
          needs_token=True,
          extras=[(4, _ask_reannotate_set), (5, _ask_reannotate_cap)]),
    Stage("advance", "Narrowing loop",
          "LLM-confirm the next NARROW papers, grow narrow_confirmed (needs token)",
          needs_token=True, extras=[(5, _ask_advance_batch)]),
    Stage("collect", "Narrowing loop",
          "mine new_suggestion candidates into category_schema.yaml, NO token",
          extras=[(5, _ask_round_label)]),
    Stage("review", "Narrowing loop",
          "human accept/decline of pending candidates, NO token"),
    # ---- Goldstandard ----
    Stage("a-gold", "Goldstandard",
          "re-annotate gold papers with the enriched prompt (needs token)",
          needs_token=True, extras=[(3, _ask_overwrite)]),
    Stage("fill-gold", "Goldstandard",
          "uncoded papers: re-query all dims (catch new subcats); coded papers: "
          "fill only missing dims; skip human-rejected (rs=0); keep existing "
          "answers (needs token)",
          needs_token=True, extras=[(3, _ask_absent_only)]),
    Stage("gold", "Goldstandard",
          "interactive two-coder goldstandard (auto-runs synccats first), NO token"),
    Stage("synccats", "Goldstandard",
          "merge coder-created categories into the schema, NO token"),
    Stage("topup", "Goldstandard",
          "separate confirmed/rejected + refill to target (token only if given)",
          needs_token=True, extras=[(4, _ask_confirm_set)]),
    Stage("icr", "Goldstandard",
          "intercoder reliability over the shared goldstandard, NO token"),
    # ---- Final study ----
    Stage("full", "Final study",
          "annotate the .workingset/final set, per model (needs token)",
          needs_token=True, extras=[(3, _ask_sample_n)]),
    # ---- Utilities ----
    Stage("export", "Utilities",
          "copy .workingset/results/goldstandard -> shared folder (additive), NO token",
          extras=[(2, _ask_export_dest), (3, _ask_export_dry)]),
]


def resolve_token():
    """First non-placeholder token found in the env, with the var name; else (None, None)."""
    for var in TOKEN_ENV_VARS:
        val = os.environ.get(var, "").strip()
        if val and val != PLACEHOLDER_TOKEN:
            return val, var
    return None, None


def resolve_data_root():
    v = os.environ.get("LNI_DATA_ROOT", "").strip()
    return v if v else str(REPO_ROOT)


def resolve_corpus():
    v = os.environ.get("LNI_CORPUS", "").strip()
    return v if v else DEFAULT_CORPUS


def resolve_advance_model():
    v = os.environ.get("LNI_ADVANCE_MODEL", "").strip()
    return v if v else DEFAULT_MODEL


def affirm_advance_model(current):
    """For the narrowing-loop stages: let the user keep the full model [Enter] or
    type a faster SAIA model id (which mostly cuts the per-paper latency that
    dominates the loop). Returns the chosen model id."""
    print("\n  Loop model  (advance / round / reannotate only -> LNI_ADVANCE_MODEL):")
    print(f"    {current}")
    print("    These steps only MINE candidate subcategories, so a faster/smaller")
    print("    model is fine and cuts the per-paper latency. a-gold/full keep the full model.")
    new = input("    Press Enter to keep, or type a faster SAIA model id: ").strip().strip('"')
    return new if new else current


def print_menu():
    print("\n====================== lni_study pipeline ======================")
    print("  Pick a stage to run (one step at a time; inspect its artifact).\n")
    last_group = None
    for i, st in enumerate(STAGES, 1):
        if st.group != last_group:
            print(f"  --- {st.group} ---")
            last_group = st.group
        tok = " [token]" if st.needs_token else ""
        print(f"   {i:>2}. {st.key:<11}{tok:<8} {st.desc}")
    print("\n    0. quit")
    print("================================================================")


def choose_stage():
    while True:
        raw = input("\nStage number > ").strip()
        if raw in ("0", "q", "quit", "exit"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(STAGES):
            return STAGES[int(raw) - 1]
        print(f"  Please enter a number 1-{len(STAGES)} (or 0 to quit).")


def affirm_path(label, current, *, must_exist, note=""):
    """Show a path, let the user keep [Enter] or type a replacement. When
    must_exist, re-prompt until the path resolves to an existing directory."""
    while True:
        suffix = f"  {note}" if note else ""
        print(f"\n  {label}:\n    {current}{suffix}")
        new = input(f"    Press Enter to keep, or type a new path: ").strip().strip('"')
        chosen = new if new else current
        if not must_exist:
            return chosen
        if Path(chosen).is_dir():
            return chosen
        print(f"    !! not an existing directory: {chosen}")
        again = input("    Use it anyway? [y/N] ").strip().lower()
        if again in ("y", "yes"):
            return chosen
        current = chosen  # keep the typo visible so the user can fix it


def collect_extras(stage):
    """Run each per-stage prompt; return {argpos: value} for non-empty answers."""
    if not stage.extras:
        return {}
    print(f"\n  --- '{stage.key}' options (press Enter to accept the default) ---")
    out = {}
    for argpos, ask in stage.extras:
        val = ask()
        if val:
            out[argpos] = val
    return out


def build_cmd_args(stage, extras):
    """run_pipeline.cmd positional args after the step.
       arg2 = token (left empty here; token goes via the environment),
       arg3..arg5 = stage extras. Trailing empties are trimmed."""
    slots = {2: "", 3: "", 4: "", 5: ""}
    slots.update(extras)
    ordered = [slots[2], slots[3], slots[4], slots[5]]
    while ordered and ordered[-1] == "":
        ordered.pop()
    return ordered


def main():
    if not RUN_CMD.is_file():
        raise SystemExit(f"run_pipeline.cmd not found at {RUN_CMD}")

    print_menu()
    stage = choose_stage()
    if stage is None:
        print("Nothing selected. Bye.")
        return

    print(f"\nSelected stage: {stage.key}  ({stage.desc})")

    # --- affirm the two paths ------------------------------------------------
    data_root = resolve_data_root()
    in_repo = Path(data_root).resolve() == REPO_ROOT.resolve()
    data_root = affirm_path(
        "Working dir  (LNI_DATA_ROOT -> results/, .workingset/, goldstandard/)",
        data_root, must_exist=False,
        note="(in-repo default; set LNI_DATA_ROOT to redirect)" if in_repo else "")

    corpus = resolve_corpus()
    if stage.uses_corpus:
        corpus = affirm_path(
            "Corpus PDFs  (LNI_CORPUS -> read-only source volumes)",
            corpus, must_exist=True)
    else:
        print(f"\n  Corpus PDFs  (not read by '{stage.key}'):\n    {corpus}")

    # --- token: env first, prompt only if the stage needs one and none found -
    token, token_var = resolve_token()
    if stage.needs_token:
        if token:
            print(f"\n  SAIA token   : found in ${token_var} (passed to the stage).")
        else:
            print("\n  SAIA token   : not found in SAIA_TOKEN / SAIA_API_KEY.")
            token = getpass.getpass(
                "    Paste SAIA token (input hidden, blank = abort): ").strip()
            if not token:
                print("No token provided; aborting (this stage needs one).")
                return
    else:
        note = "available" if token else "not set"
        print(f"\n  SAIA token   : {note} (this stage does not need one).")

    # --- loop model: faster model for the candidate-mining stages ------------
    advance_model = None
    if stage.key in LOOP_MODEL_STAGES:
        advance_model = affirm_advance_model(resolve_advance_model())

    # --- child environment: redirect paths + supply token via env ------------
    env = os.environ.copy()
    env["LNI_DATA_ROOT"] = data_root
    env["LNI_CORPUS"] = corpus
    if token:
        env["SAIA_TOKEN"] = token  # run_pipeline.cmd picks this up (line ~115)
    if advance_model:
        env["LNI_ADVANCE_MODEL"] = advance_model  # -> ADVANCE_MODEL knob

    extras = collect_extras(stage)
    cmd_args = build_cmd_args(stage, extras)

    # --- optional, opt-in SAIA reachability check (the only network call) ----
    if stage.needs_token and token:
        do_check = input(
            "\n  Run a quick SAIA reachability/auth check first? "
            "(near-free models.list call) [y/N]: ").strip().lower()
        if do_check in ("y", "yes"):
            chk = preflight.check_saia(env.get("SAIA_API_ENDPOINT"), token)
            print("  " + chk.line())
            if not chk.ok:
                go = input("  Check failed. Run the stage anyway? [y/N]: ").strip().lower()
                if go not in ("y", "yes"):
                    print("Aborted before launch.")
                    return

    # --- confirm and dispatch ------------------------------------------------
    shown_args = " ".join(f'"{a}"' if (a == "" or " " in a) else a for a in cmd_args)
    print("\n  ----------------------------------------------------------------")
    print(f"  About to run:  run_pipeline.cmd {stage.key} {shown_args}".rstrip())
    print(f"    working dir : {data_root}")
    print(f"    corpus      : {corpus}")
    if advance_model:
        print(f"    loop model  : {advance_model}")
    print(f"    token       : {'via $SAIA_TOKEN (not on command line)' if token else 'none'}")
    print("  ----------------------------------------------------------------")
    go = input("  Launch this stage now? [Y/n]: ").strip().lower()
    if go in ("n", "no"):
        print("Not launched.")
        return

    full = ["cmd", "/c", str(RUN_CMD), stage.key, *cmd_args]
    print(f"\n>>> launching '{stage.key}' ...\n", flush=True)
    completed = subprocess.run(full, env=env, cwd=str(REPO_ROOT))
    print(f"\n>>> '{stage.key}' finished with exit code {completed.returncode}.")
    sys.exit(completed.returncode)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
