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

# The model id that NAMES the checkpoint lineage already on disk
# (results/checkpoints/annotations_<tag>_<model>_<prompt>_<run>_checkpoint.csv).
# Deliberately NOT DEFAULT_MODEL: the 124-paper goldconfirm checkpoint the `gold`
# coding step reads was written by the retired 675B model, and repointing the path
# at the new pin would make `gold` open an empty file and lose every stored
# annotation. DEFAULT_MODEL picks who answers NEW calls; this picks which file we
# read or append to.
#
# OPEN DECISION before any further token run on this lineage: appending
# mistral-medium answers to a file named after mistral-large mixes two models in
# one checkpoint and misstates provenance. Either start a fresh lineage under
# DEFAULT_MODEL and re-annotate, or accept the mix and record the cut-over in the
# paper's method section.
CHECKPOINT_MODEL = "mistral-large-3-675b-instruct-2512"


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
    args = ap.parse_args()

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
