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
    args = ap.parse_args()

    checks = [check_saia(args.saia_endpoint,
                         args.saia_token or os.getenv("SAIA_API_KEY"))]
    checks += check_data_root()
    if args.check_corpus:
        checks.append(check_path(args.corpus, label="corpus"))

    require(checks, exit_on_fail=not args.no_exit)
    print("[preflight] all checks passed.")


if __name__ == "__main__":
    main()
