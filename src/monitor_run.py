"""
monitor_run.py

READ-ONLY heartbeat for a running confirm/annotate batch — the "glacial but
working" reporter. It never writes anything the pipeline depends on, so it is
safe to run against a live round at any time (including while PID is mid-paper).

It answers, at a glance: how far along is the run, how fast is it going, and
when will it finish? Two independent signals are combined so the report is
useful even if one is missing:

  1. The CHECKPOINT CSV (results/checkpoints/annotations_*_checkpoint.csv): the
     ground truth of how many papers have actually been written to disk. Row
     count + the file's mtime tell us how many are done and when the last one
     landed. Parsed with on_bad_lines='skip' so a half-written final row (the
     run may be mid-append) never crashes the monitor.

  2. round.log's tqdm progress line (if present): tqdm already computes
     s/paper, elapsed and ETA, so we surface its latest estimate verbatim.
     The file is UTF-16 with \r-separated bar redraws; we decode + split both.

Usage (read-only; from the lni_study repo root):

    python src/monitor_run.py
    python src/monitor_run.py --log round.log
    python src/monitor_run.py --checkpoint results/checkpoints/annotations_..._checkpoint.csv
    python src/monitor_run.py --watch 60        # re-print every 60s until Ctrl-C
"""

import argparse
import os
import re
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.environ.get("LNI_DATA_ROOT") or REPO_ROOT).resolve()
CHECKPOINT_DIR = DATA_ROOT / "results" / "checkpoints"


def newest_checkpoint(explicit: str | None) -> Path | None:
    """The checkpoint to report on: --checkpoint if given, else the most recently
    modified annotations_*_checkpoint.csv under the data root's checkpoints dir."""
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    if not CHECKPOINT_DIR.is_dir():
        return None
    cands = sorted(CHECKPOINT_DIR.glob("annotations_*_checkpoint.csv"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None


def read_checkpoint_stats(path: Path) -> dict:
    """Row count + label/error breakdown, tolerant of a mid-append final row."""
    import pandas as pd
    try:
        df = pd.read_csv(path, on_bad_lines="skip", engine="python")
    except Exception as e:  # noqa: BLE001 - report, never crash the monitor
        return {"error": f"could not read checkpoint: {e}"}
    n = len(df)
    confirmed = errors = None
    if "label_research_software" in df.columns:
        confirmed = int((pd.to_numeric(df["label_research_software"],
                                       errors="coerce") == 1).sum())
    if "llm_error" in df.columns:
        errors = int(df["llm_error"].notna().sum())
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return {"rows": n, "confirmed": confirmed, "errors": errors, "mtime": mtime}


def _decode(path: Path) -> str:
    """round.log is typically UTF-16 (PowerShell redirect). Sniff and decode."""
    raw = path.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or raw[:200].count(b"\x00") > 20:
        for enc in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                return raw.decode(enc)
            except UnicodeError:
                pass
    return raw.decode("utf-8", errors="replace")


_PROG = re.compile(
    r"(\d+)\s*/\s*(\d+)\s*\[([\d:]+)<([\d:?]+),\s*([\d.]+)s/(?:paper|it|confirmed)")


def parse_progress(log_path: Path) -> dict | None:
    """Pull the LAST tqdm progress line out of round.log: (done, total, elapsed,
    eta, s_per_item) plus any annotated/confirmed/errors postfix counters."""
    if not log_path.is_file():
        return None
    text = _decode(log_path)
    # tqdm redraws the same bar with \r; treat \r and \n as line breaks.
    lines = re.split(r"[\r\n]+", text)
    last = None
    for ln in lines:
        m = _PROG.search(ln)
        if m:
            last = (m, ln)
    if not last:
        return None
    m, ln = last
    out = {
        "done": int(m.group(1)), "total": int(m.group(2)),
        "elapsed": m.group(3), "eta": m.group(4), "s_per_item": float(m.group(5)),
    }
    for key in ("annotated", "confirmed", "errors", "reused"):
        mm = re.search(rf"{key}=(\d+)", ln)
        if mm:
            out[key] = int(mm.group(1))
    return out


def report(args) -> None:
    print(f"[monitor] {datetime.now():%Y-%m-%d %H:%M:%S}  data root: {DATA_ROOT}")

    log_path = Path(args.log) if args.log else (Path.cwd() / "round.log")
    prog = parse_progress(log_path)
    if prog:
        pct = 100.0 * prog["done"] / prog["total"] if prog["total"] else 0.0
        extra = "  ".join(f"{k}={prog[k]}" for k in
                          ("annotated", "confirmed", "errors", "reused") if k in prog)
        print(f"[round.log] {log_path.name}: {prog['done']}/{prog['total']} "
              f"({pct:.0f}%)  {prog['s_per_item']:.0f}s/paper  "
              f"elapsed {prog['elapsed']}  ETA {prog['eta']}"
              + (f"  | {extra}" if extra else ""))
    else:
        print(f"[round.log] no tqdm progress line found in {log_path}")

    cp = newest_checkpoint(args.checkpoint)
    if cp is None:
        print("[checkpoint] none found under "
              f"{CHECKPOINT_DIR} (and no --checkpoint given)")
        return
    stats = read_checkpoint_stats(cp)
    if "error" in stats:
        print(f"[checkpoint] {cp.name}: {stats['error']}")
        return
    age = (datetime.now() - stats["mtime"]).total_seconds()
    bits = [f"{stats['rows']} rows written"]
    if stats["confirmed"] is not None:
        bits.append(f"confirmed(label==1)={stats['confirmed']}")
    if stats["errors"] is not None:
        bits.append(f"errors={stats['errors']}")
    print(f"[checkpoint] {cp.name}")
    print(f"             {'  '.join(bits)}")
    print(f"             last write {stats['mtime']:%H:%M:%S} "
          f"({age:.0f}s ago)" + ("  <- looks STALLED" if age > 900 else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description="Read-only progress monitor for a "
                                             "running confirm/annotate batch.")
    ap.add_argument("--log", default=None,
                    help="path to round.log (default: ./round.log)")
    ap.add_argument("--checkpoint", default=None,
                    help="path to the checkpoint CSV (default: newest under "
                         "results/checkpoints/)")
    ap.add_argument("--watch", type=int, default=0, metavar="SECONDS",
                    help="re-print every N seconds until Ctrl-C (default: once)")
    args = ap.parse_args()

    if args.watch > 0:
        try:
            while True:
                report(args)
                print("-" * 60, flush=True)
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n[monitor] stopped.")
    else:
        report(args)


if __name__ == "__main__":
    main()
