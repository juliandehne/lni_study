#!/usr/bin/env python3
"""Replay the a-gold response log through the (fixed) JSON parser to prove the
fix worked.

This is a FORK of annotate_lni's `extract_json_from_response`: a verbatim copy of
the committed parser (kept self-contained so it runs without the SAIA / pandas /
pdf-extraction deps, and without `load_dotenv()` side effects). It does NOT call
the model -- it re-parses the bodies that a real `--fill-gold` / a-gold run
already captured in `logs/annotate_lni_responses.log`.

What it checks
--------------
The log records, per SAIA call, the raw `body=` and the verdict the LIVE run
reached (`OK` / `PARSE-FAIL` / `TRUNCATED` / empty-retry). We re-run the current
parser over every logged body and cross-reference:

  RECOVERED   live PARSE-FAIL  -> now parses     (the fix did its job)
  STILL-BROKEN  live PARSE-FAIL -> still fails    (fix incomplete)   [FAIL]
  REGRESSION  live OK          -> now fails       (fix broke a case) [FAIL]
  STILL-OK    live OK          -> still parses    (no regression)

Exit code is non-zero if any STILL-BROKEN or REGRESSION row is found, so this
doubles as a CI/sanity gate.

Usage:
    python src/check_fill_gold_parsing.py [path/to/annotate_lni_responses.log] [-v]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# FORK: verbatim copy of annotate_lni.extract_json_from_response (commit 40edabf).
# Keep in sync if the live parser changes -- this script exists to prove THIS
# logic parses the real logged answers.
# --------------------------------------------------------------------------- #
def extract_json_from_response(raw: str) -> dict:
    cleaned = raw.strip()
    # strict=False allows literal control characters (newlines, tabs) INSIDE string
    # values. The model frequently formats the `explanation` field as a multi-line
    # bullet list with real line breaks rather than escaped \n -- strict JSON rejects
    # that with "No valid JSON object found", which used to silently drop the whole
    # (otherwise valid) answer. Tolerating it recovers the parse losslessly.
    decoder = json.JSONDecoder(strict=False)
    brace_idx = cleaned.find("{")
    if brace_idx != -1:
        try:
            obj, _ = decoder.raw_decode(cleaned, brace_idx)
            return obj
        except json.JSONDecodeError:
            pass
    code_block = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n\s*```", cleaned)
    if code_block:
        try:
            return decoder.decode(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass
    raise json.JSONDecodeError("No valid JSON object found", cleaned, 0)


# --------------------------------------------------------------------------- #
# Log replay
# --------------------------------------------------------------------------- #
DEFAULT_LOG = Path(__file__).resolve().parent.parent / "logs" / "annotate_lni_responses.log"
CLIP_MARKER = "chars clipped]"  # _clip() appends "… [+N chars clipped]" when truncated

# Each record is one physical line: "<ts> <LEVEL> <TAG> id=... ...".
RESPONSE_RE = re.compile(
    r"\bRESPONSE id=(?P<id>\S+) attempt=(?P<attempt>\d+) "
    r"(?:api_s=(?P<api_s>\S+) )?"   # added 2026-06-26; optional so old logs still parse
    r"finish=(?P<finish>\S+) "
    r"chars=(?P<chars>\d+) body=(?P<body>.*)$"
)
VERDICT_RES = {
    "OK": re.compile(r"\bOK id=(?P<id>\S+) parsed JSON on attempt (?P<attempt>\d+)"),
    "PARSE-FAIL": re.compile(r"\bPARSE-FAIL id=(?P<id>\S+) "),
    "TRUNCATED": re.compile(r"\bTRUNCATED id=(?P<id>\S+) "),
    "NON-DICT": re.compile(r"\bNON-DICT id=(?P<id>\S+) "),
    "EMPTY": re.compile(r"\bempty response .*id=(?P<id>\S+)"),
}


def _decode_body(repr_str: str):
    """Recover the original string from its logged `%r` repr. Returns (text, error)."""
    try:
        val = ast.literal_eval(repr_str.strip())
        return (val, None) if isinstance(val, str) else (None, f"repr was {type(val).__name__}")
    except (ValueError, SyntaxError) as e:
        return None, f"repr decode failed: {e}"


def parse_log(path: Path):
    """Walk the log in order. Each RESPONSE is followed by the verdict line that
    the live run reached for it (the run is sequential: REQUEST/RESPONSE/verdict
    per paper), so we pair them up."""
    records = []
    pending = None  # the most recent RESPONSE awaiting its live verdict
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = RESPONSE_RE.search(line)
        if m:
            if pending is not None:
                records.append(pending)  # no explicit verdict line seen; keep it
            text, err = _decode_body(m.group("body"))
            pending = {
                "id": m.group("id"),
                "attempt": int(m.group("attempt")),
                "finish": m.group("finish"),
                "chars": int(m.group("chars")),
                "body": text,
                "decode_error": err,
                "live_verdict": None,
            }
            continue
        if pending is not None:
            for tag, rx in VERDICT_RES.items():
                vm = rx.search(line)
                if vm and vm.group("id") == pending["id"]:
                    pending["live_verdict"] = tag
                    records.append(pending)
                    pending = None
                    break
    if pending is not None:
        records.append(pending)
    return records


def classify(rec):
    """Re-run the forked parser over a logged body and bucket the outcome."""
    if rec["finish"] == "length":
        return "TRUNCATED-INPUT", "response hit max_tokens; not a parse case"
    if rec["body"] is None:
        return "UNDECODABLE", rec["decode_error"] or "could not recover body from log"
    if CLIP_MARKER in rec["body"]:
        return "CLIPPED", "body was clipped in the log; cannot verify full parse"

    try:
        obj = extract_json_from_response(rec["body"])
        now_ok = isinstance(obj, dict)
        now_err = None if now_ok else f"parsed to {type(obj).__name__}"
    except json.JSONDecodeError as e:
        now_ok, now_err = False, str(e)

    live = rec["live_verdict"]
    if live == "PARSE-FAIL":
        return ("RECOVERED", None) if now_ok else ("STILL-BROKEN", now_err)
    if live == "OK":
        return ("STILL-OK", None) if now_ok else ("REGRESSION", now_err)
    # No live OK/PARSE-FAIL verdict (e.g. empty/retry record) -- just report parse state.
    return ("PARSES" if now_ok else "FAILS", now_err)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log", nargs="?", default=str(DEFAULT_LOG),
                    help=f"response log to replay (default: {DEFAULT_LOG})")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="print every RECOVERED row too, not just failures")
    args = ap.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        print(f"ERROR: log not found: {log_path}", file=sys.stderr)
        return 2

    records = parse_log(log_path)
    if not records:
        print(f"No RESPONSE records found in {log_path}", file=sys.stderr)
        return 2

    buckets: dict[str, list] = {}
    for rec in records:
        bucket, detail = classify(rec)
        buckets.setdefault(bucket, []).append((rec, detail))

    order = ["RECOVERED", "STILL-OK", "PARSES", "STILL-BROKEN", "REGRESSION",
             "FAILS", "TRUNCATED-INPUT", "CLIPPED", "UNDECODABLE"]
    print(f"Replayed {len(records)} logged response(s) from {log_path}\n")
    print(f"{'bucket':<16} count")
    print("-" * 24)
    for b in order:
        if b in buckets:
            print(f"{b:<16} {len(buckets[b])}")
    for b in buckets:
        if b not in order:
            print(f"{b:<16} {len(buckets[b])}")
    print()

    # Detail the ones that matter: the recovered cases (proof the fix worked) and
    # any failures (proof it didn't, or regressed).
    def dump(bucket, header):
        rows = buckets.get(bucket)
        if not rows:
            return
        print(f"{header}:")
        for rec, detail in rows:
            extra = f"  [{detail}]" if detail else ""
            print(f"  id={rec['id']} attempt={rec['attempt']} finish={rec['finish']}{extra}")
        print()

    if args.verbose:
        dump("RECOVERED", "RECOVERED (live PARSE-FAIL -> now parses)")
    dump("STILL-BROKEN", "STILL-BROKEN (live PARSE-FAIL -> STILL fails)")
    dump("REGRESSION", "REGRESSION (live OK -> now FAILS)")
    dump("FAILS", "FAILS (no live verdict, still unparseable)")
    dump("UNDECODABLE", "UNDECODABLE (could not recover body from log)")

    recovered = len(buckets.get("RECOVERED", []))
    still_broken = len(buckets.get("STILL-BROKEN", []))
    regressions = len(buckets.get("REGRESSION", []))

    if still_broken or regressions:
        print(f"FIX VERDICT: PROBLEM - {still_broken} still-broken, "
              f"{regressions} regression(s).")
        return 1
    print(f"FIX VERDICT: OK - fix recovered {recovered} previously-failing "
          f"response(s); no regressions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
