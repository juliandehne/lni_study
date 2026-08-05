r"""
preflight.py

Fail-fast environment checks for the LNI pipeline's network/IO dependencies, so
a multi-hour batch dies in the first second with a clear message instead of
either (a) loading hundreds of candidates and only THEN hitting "Missing SAIA
token", or (b) discovering halfway through that a mounted drive went away.

Two independent checks, both cheap and side-effect-free:

  check_saia(base_url, token)  -> Preflight
      Is the SAIA endpoint reachable AND does the token authenticate? Uses a
      short-timeout models.list() (an authenticated, near-free call):
        - reachable + 2xx           -> ok
        - reachable + 401/403       -> reachable but token bad  (fail)
        - connection/timeout error  -> endpoint unreachable     (fail)

  check_paths(paths)           -> list[Preflight]
      Does each required directory/file exist (and is it the expected kind)?
      Use for mounted corpus drives (Z:\...) and the LNI_DATA_ROOT subtree
      (results/, .workingset/) that a run appends to.

Both return small Preflight records (ok: bool, detail: str) rather than raising,
so callers decide whether a given check is fatal. `require(...)` raises
SystemExit on the first failure for the common fail-fast case.

Standalone use (handy as a manual pre-run check; needs a token to test auth):

    python src/preflight.py --saia_token <TOKEN>
    python src/preflight.py --saia_token <TOKEN> --check_corpus
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.environ.get("LNI_DATA_ROOT") or REPO_ROOT).resolve()
DEFAULT_SAIA_ENDPOINT = "https://chat-ai.academiccloud.de/v1"

# The one place the pipeline's model id lives. Every script's --model default
# reads it from here so a retirement is a one-line change, not a grep.
#
# 2026-07-28: repinned from `mistral-large-3-675b-instruct-2512`, which GWDG
# retired. Chosen from the live catalogue as the nearest same-family successor
# that emits plain text: the pipeline demands strict JSON with no surrounding
# prose, and several larger options (qwen3.5-397b-a17b, qwen3.5-122b-a10b) also
# emit a "thought" channel this code does not parse. Note it is a much smaller
# model than the retired 675B pin, so annotations produced with it are NOT
# directly comparable with the existing checkpoints -- those record the model in
# their filename for exactly this reason.
DEFAULT_MODEL = "mistral-medium-3.5-128b"

def model_family(model_id: str) -> str:
    """The vendor/family slug a checkpoint filename is named after.

    Checkpoints used to embed the FULL model id
    (annotations_goldconfirm_mistral-large-3-675b-instruct-2512_..._checkpoint.csv).
    That made the filename a version pin: GWDG retires a model, the id changes,
    and the path silently points at a file that does not exist -- so the coding
    step opens an empty checkpoint and every stored annotation disappears.

    The family is the stable part. Version drift within a family
    (mistral-large-3-675b -> mistral-medium-3.5-128b) keeps writing to the same
    file, and the EXACT id of every call is preserved per row in the checkpoint's
    `model` column, which is what a later validity check actually needs -- it can
    tell you which rows came from which version, something a filename never could
    for a file that holds more than one run.

    Rule: first hyphen-segment, trailing version digits stripped.
        mistral-medium-3.5-128b       -> mistral
        mistral-large-3-675b-...-2512 -> mistral
        qwen3.5-397b-a17b             -> qwen
        glm-4.7                       -> glm
        deepseek-v4-flash             -> deepseek
    For vendor-prefixed ids (meta-llama-3.1-8b -> meta, openai-gpt-oss-120b ->
    openai) this yields the vendor rather than the family. That is fine: the slug
    only has to be stable and collision-free, and the `model` column carries the
    truth.
    """
    head = model_id.strip().lower().split("-")[0]
    m = re.match(r"[a-z]+", head)
    return m.group(0) if m else (head or "model")


# Family of the current pin, i.e. the slug new checkpoints are named after.
DEFAULT_MODEL_FAMILY = model_family(DEFAULT_MODEL)


# =============================================================================
# Empirical model selection (written by benchmark_models.py, the `bench` step)
# =============================================================================
#
# DEFAULT_MODEL above is the PIN: the model every schema/goldstandard artefact in
# this repo was produced with, and the one the narrowing loop and the gold steps
# keep using (their checkpoint filenames are named after its family — repointing
# them mid-study would orphan existing annotations).
#
# The FINAL STUDY is the one step where the model is an open question, so it is
# chosen empirically: `benchmark_models.py` scores several SAIA models against the
# human-coded goldstandard and writes the winner to
#
#     <DATA_ROOT>/results/model_selection/model_selection.json
#
# `selected_model()` reads that file. It is deliberately NOT wired into
# DEFAULT_MODEL: only callers that ask for it (run_pipeline.cmd's `full` step)
# switch models, so a bake-off can never silently invalidate the gold checkpoints.
MODEL_SELECTION_RELPATH = Path("results") / "model_selection" / "model_selection.json"


def selection_path(data_root: str | Path | None = None) -> Path:
    """Where the bake-off writes / the final study reads the chosen model."""
    root = Path(data_root).resolve() if data_root else DATA_ROOT
    return root / MODEL_SELECTION_RELPATH


def load_model_selection(data_root: str | Path | None = None) -> dict | None:
    """The parsed selection file, or None if it is absent/unreadable/malformed.

    Never raises: a missing or half-written selection must degrade to "use the
    pin", not abort a study run."""
    import json
    p = selection_path(data_root)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("winner"), dict):
        return None
    if not str(data["winner"].get("model") or "").strip():
        return None
    return data


def selected_model(data_root: str | Path | None = None) -> tuple[str, str]:
    """(model_id, source) for the FINAL STUDY.

    source is 'selection' when it came from the bake-off file, 'pin' when it fell
    back to DEFAULT_MODEL (no bake-off run yet, or the file is unusable)."""
    sel = load_model_selection(data_root)
    if sel is None:
        return DEFAULT_MODEL, "pin"
    return str(sel["winner"]["model"]).strip(), "selection"


@dataclass
class Preflight:
    name: str
    ok: bool
    detail: str

    def line(self) -> str:
        return f"[preflight] {'OK ' if self.ok else 'FAIL'} {self.name}: {self.detail}"


def check_saia(base_url: str | None, token: str | None,
               timeout: float = 15.0) -> Preflight:
    """Reachable + authenticating? A short-timeout models.list() call."""
    name = "SAIA"
    base_url = base_url or os.getenv("SAIA_API_ENDPOINT") or DEFAULT_SAIA_ENDPOINT
    if not token:
        return Preflight(name, False,
                         "no token (set SAIA_API_KEY or pass --saia_token)")
    try:
        from openai import (OpenAI, AuthenticationError, APIConnectionError,
                            APITimeoutError, APIStatusError)
    except Exception as e:  # noqa: BLE001
        return Preflight(name, False, f"openai client import failed: {e}")
    try:
        client = OpenAI(api_key=token, base_url=base_url, timeout=timeout)
        client.models.list()
        return Preflight(name, True, f"reachable + authenticated ({base_url})")
    except AuthenticationError:
        return Preflight(name, False,
                         f"reachable but token REJECTED (401/403) at {base_url}")
    except (APIConnectionError, APITimeoutError) as e:
        return Preflight(name, False,
                         f"UNREACHABLE within {timeout:.0f}s: {type(e).__name__} ({base_url})")
    except APIStatusError as e:
        # Reachable, but /models returned a non-auth HTTP error (e.g. 404 if this
        # endpoint doesn't expose model listing). Don't hard-fail on that — the
        # token wasn't rejected and the host answered. Report as a soft pass.
        return Preflight(name, True,
                         f"reachable; auth not verified (/models -> {e.status_code}) ({base_url})")
    except Exception as e:  # noqa: BLE001 - any other error: report, don't crash
        return Preflight(name, False, f"{type(e).__name__}: {e} ({base_url})")


def list_models(base_url: str | None, token: str | None,
                timeout: float = 20.0) -> list[str]:
    """The model ids SAIA currently serves, via GET /v1/models.

    GWDG retires models without notice (the study's original
    `mistral-large-3-675b-instruct-2512` disappeared from the catalogue between
    the goldconfirm run and the top-up), so the id is looked up live rather than
    trusted from a hard-coded list. Needs a token — /v1/models is 401 without
    one. Returns [] if the call fails for any reason; callers treat that as
    "unknown", never as "empty catalogue"."""
    base_url = base_url or os.getenv("SAIA_API_ENDPOINT") or DEFAULT_SAIA_ENDPOINT
    if not token:
        return []
    try:
        from openai import OpenAI
        client = OpenAI(api_key=token, base_url=base_url, timeout=timeout)
        return sorted(m.id for m in client.models.list().data)
    except Exception:  # noqa: BLE001 - unreachable/401/404 all mean "unknown"
        return []


def check_model(model: str, base_url: str | None, token: str | None,
                timeout: float = 20.0) -> Preflight:
    """Is `model` actually served right now? Fails BEFORE the slow candidate
    load, so a retired id costs a second rather than a whole batch."""
    name = f"SAIA model {model}"
    available = list_models(base_url, token, timeout)
    if not available:
        return Preflight(name, True, "catalogue unavailable (no token or /models "
                                     "unreachable) - NOT verified")
    if model in available:
        return Preflight(name, True, f"served ({len(available)} models available)")
    near = [m for m in available if m.split("-")[0].lower() in model.lower()]
    hint = f"; closest by family: {', '.join(near)}" if near else ""
    return Preflight(name, False,
                     f"NOT in the SAIA catalogue. Available: {', '.join(available)}{hint}")


def check_path(path: str | Path, *, kind: str = "dir",
               label: str | None = None) -> Preflight:
    """Existence (and dir/file kind) of one required path."""
    p = Path(path)
    name = label or str(p)
    if not p.exists():
        return Preflight(name, False, f"missing: {p}")
    if kind == "dir" and not p.is_dir():
        return Preflight(name, False, f"exists but is not a directory: {p}")
    if kind == "file" and not p.is_file():
        return Preflight(name, False, f"exists but is not a file: {p}")
    return Preflight(name, True, f"present: {p}")


def check_paths(paths, *, kind: str = "dir") -> list[Preflight]:
    """check_path over an iterable of (path) or (label, path) items."""
    out = []
    for item in paths:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            label, path = item
            out.append(check_path(path, kind=kind, label=label))
        else:
            out.append(check_path(item, kind=kind))
    return out


def check_data_root() -> list[Preflight]:
    """The generated-data subtree a confirm/annotate run appends to."""
    return check_paths([
        ("LNI_DATA_ROOT", DATA_ROOT),
        ("results", DATA_ROOT / "results"),
        (".workingset", DATA_ROOT / ".workingset"),
    ])


def require(checks, *, exit_on_fail: bool = True) -> bool:
    """Print each check; on any failure print a summary and (by default) raise
    SystemExit so a batch aborts in the first second. Returns True if all ok."""
    checks = list(checks)
    all_ok = True
    for c in checks:
        print(c.line(), flush=True)
        all_ok = all_ok and c.ok
    if not all_ok and exit_on_fail:
        failed = ", ".join(c.name for c in checks if not c.ok)
        raise SystemExit(f"[preflight] aborting: failed checks -> {failed}")
    return all_ok


def main() -> None:
    ap = argparse.ArgumentParser(description="Fail-fast preflight checks (SAIA "
                                             "reachability/auth + required paths).")
    ap.add_argument("--saia_token", default=None,
                    help="SAIA token (default: SAIA_API_KEY env)")
    ap.add_argument("--saia_endpoint", default=None)
    ap.add_argument("--check_corpus", action="store_true",
                    help="also check the read-only LNI corpus mount (Z:\\...)")
    ap.add_argument("--corpus", default=os.getenv("LNI_CORPUS",
                                                  r"Z:\Publikationen\LNI\Proceedings"))
    ap.add_argument("--no_exit", action="store_true",
                    help="report only; do not exit non-zero on failure")
    ap.add_argument("--model", default=None,
                    help="also verify this model id is in the live SAIA catalogue")
    ap.add_argument("--list_models", action="store_true",
                    help="print the model ids SAIA currently serves and exit "
                         "(needs a token; /v1/models is 401 without one)")
    ap.add_argument("--data_root", default=None,
                    help="override LNI_DATA_ROOT for the selection-file lookup")
    ap.add_argument("--print_selected_model", action="store_true",
                    help="print the FINAL-STUDY model id and exit: the bake-off "
                         "winner from results/model_selection/model_selection.json, "
                         "else the pin. Machine-readable (one bare line, stdout); "
                         "the provenance note goes to stderr. Used by "
                         "run_pipeline.cmd's `full` step.")
    ap.add_argument("--print_selected_family", action="store_true",
                    help="same, but print the checkpoint family slug of that model")
    args = ap.parse_args()

    if args.print_selected_model or args.print_selected_family:
        model, source = selected_model(args.data_root)
        note = (f"[preflight] final-study model from {selection_path(args.data_root)}"
                if source == "selection" else
                "[preflight] no model selection file - falling back to the pin "
                "(run `run_pipeline.cmd bench` to choose empirically)")
        print(note, file=sys.stderr)
        print(model_family(model) if args.print_selected_family else model)
        return

    token = args.saia_token or os.getenv("SAIA_API_KEY")
    if args.list_models:
        models = list_models(args.saia_endpoint, token)
        if not models:
            raise SystemExit("[preflight] could not read the model catalogue "
                             "(set SAIA_API_KEY or pass --saia_token).")
        print("\n".join(models))
        return

    checks = [check_saia(args.saia_endpoint, token)]
    if args.model:
        checks.append(check_model(args.model, args.saia_endpoint, token))
    checks += check_data_root()
    if args.check_corpus:
        checks.append(check_path(args.corpus, label="corpus"))

    require(checks, exit_on_fail=not args.no_exit)
    print("[preflight] all checks passed.")


if __name__ == "__main__":
    main()
