"""
Regression test for the short-paper (<6 pages, <=20%) pool/top-up cap.

Covers paper_length's pure invariants + order_within_cap, PyMuPDF page_count, and
an END-TO-END run of the real select_candidates streaming gate asserting the pool
manifest is <=20% short. NO SAIA token, NO real corpus: it synthesizes tiny PDFs
with PyMuPDF. Run with the analysis Python from the lni_study repo root:

    python tests/test_short_paper_cap.py

Exits non-zero on the first failed assertion.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import paper_length as pl  # noqa: E402

ok = 0


def check(cond, msg):
    global ok
    assert cond, f"FAIL: {msg}"
    ok += 1
    print(f"  ok: {msg}")


# ---------------------------------------------------------------- pure functions
print("[1] pure-function invariants")
check(pl.is_short(5), "5 pages is short (<6)")
check(not pl.is_short(6), "6 pages is NOT short (boundary)")
check(not pl.is_short(7), "7 pages is not short")
check(not pl.is_short(None), "unknown length (None) treated as not short")
check(not pl.is_short(""), "empty length treated as not short")
check(pl.is_short(3, threshold=4) and not pl.is_short(4, threshold=4), "custom threshold honored")

# short_allowed never lets the running ratio exceed frac. 0/0 -> 1/1 = 100%, so
# a set's FIRST paper may not be short under a 20% cap.
check(not pl.short_allowed(0, 0, 0.2), "a set's FIRST paper may not be short at 20% cap")
check(pl.short_allowed(0, 4, 0.2), "1 short of 5 (20%) is allowed")
check(not pl.short_allowed(1, 4, 0.2), "2 short of 5 (40%) is refused")

check(pl.fraction_ok(0, 0, 0.2), "empty set satisfies cap")
check(pl.fraction_ok(2, 10, 0.2), "2/10 satisfies 20%")
check(not pl.fraction_ok(3, 10, 0.2), "3/10 violates 20%")


def assert_prefix_capped(records, frac, threshold):
    """Every prefix of `records` must satisfy short/total <= frac."""
    ns = tot = 0
    for r in records:
        if pl.is_short(r["pages"], threshold):
            ns += 1
        tot += 1
        assert pl.fraction_ok(ns, tot, frac), \
            f"prefix {tot} has {ns} short ({ns/tot:.0%}) > {frac:.0%}"


print("[2] order_within_cap on <=20%-short input (the real pool): every prefix capped")
import random  # noqa: E402  (seeded; Math.random ban is for workflow scripts, not here)
rng = random.Random(7)
for trial in range(300):
    n_long = rng.randint(0, 50)
    # The real pool is already <=20% short (select_candidates guarantees it), so
    # build inputs that way: at most floor(0.2 * total) short papers.
    max_short = n_long // 4 if n_long else 0          # s/(s+L) <= 0.2  <=>  s <= L/4
    n_short = rng.randint(0, max_short)
    recs = ([{"pages": rng.choice([8, 10, 12, 20])} for _ in range(n_long)]
            + [{"pages": rng.choice([2, 3, 4, 5])} for _ in range(n_short)])
    rng.shuffle(recs)
    ordered = pl.order_within_cap(recs, lambda r: pl.is_short(r["pages"]), 0.2)
    assert len(ordered) == len(recs), "order_within_cap dropped/added records"
    assert_prefix_capped(ordered, 0.2, pl.SHORT_PAGE_THRESHOLD)
check(True, "300 randomized <=20%-short trials: every prefix capped, length-preserving")

# Degenerate OVER-cap input (>20% short, which the real pool never is): the cap
# cannot be honored without dropping, so the documented behavior is to interleave
# what it can and append the rest -- crucially WITHOUT dropping any record.
allshort = [{"pages": 2} for _ in range(10)]
out = pl.order_within_cap(allshort, lambda r: pl.is_short(r["pages"]), 0.2)
check(len(out) == 10, "all-short (over-cap) input preserved, nothing dropped")
half = [{"pages": 2}] * 10 + [{"pages": 10}] * 10
out2 = pl.order_within_cap(half, lambda r: pl.is_short(r["pages"]), 0.2)
check(len(out2) == 20, "50%-short (over-cap) input preserved, nothing dropped")


# ----------------------------------------------------- PyMuPDF page_count + e2e
def make_pdf(path, n_pages):
    import pymupdf
    doc = pymupdf.open()
    for i in range(n_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"page {i+1} of {path.stem}")
    doc.save(str(path))
    doc.close()


print("[3] PyMuPDF page_count on synthesized PDFs")
with tempfile.TemporaryDirectory() as td:
    tdp = Path(td)
    p3 = tdp / "p3.pdf"; make_pdf(p3, 3)
    p8 = tdp / "p8.pdf"; make_pdf(p8, 8)
    check(pl.page_count(p3) == 3, "page_count reads 3-page PDF")
    check(pl.page_count(p8) == 8, "page_count reads 8-page PDF")
    check(pl.page_count(tdp / "missing.pdf") is None, "missing PDF -> None (not short)")

print("[4] end-to-end select_candidates: pool manifest <=20% short")
with tempfile.TemporaryDirectory() as td:
    tdp = Path(td)
    corpus = tdp / "corpus"
    work = tdp / "work"
    # One volume folder, lots of SHORT papers + enough long ones. With min_score
    # negative every paper is a positive, so selection is decided purely by the
    # short cap. narrow/gold/final = 0 so everything flows into 'pool'.
    vol = corpus / "vol1"
    vol.mkdir(parents=True)
    for i in range(40):
        make_pdf(vol / f"short_{i:02d}.pdf", 2)   # 40 short
    for i in range(40):
        make_pdf(vol / f"long_{i:02d}.pdf", 10)    # 40 long
    res = subprocess.run(
        [sys.executable, str(SRC / "select_candidates.py"),
         "--corpus", str(corpus), "--min_score", "-1",
         "--narrow", "0", "--gold", "0", "--final", "0", "--cap", "60",
         "--short_pages", "6", "--max_short_frac", "0.20",
         "--workroot", str(work), "--scores_csv", str(tdp / "scores.csv")],
        capture_output=True, text=True)
    print(res.stdout[-1500:])
    if res.returncode != 0:
        print(res.stderr[-2000:])
    check(res.returncode == 0, "select_candidates exited 0")

    import pandas as pd
    man = pd.read_csv(work / "pool" / "manifest.csv")
    n_total = len(man)
    n_short = int((pd.to_numeric(man["pages"], errors="coerce") < 6).sum())
    frac = n_short / n_total if n_total else 0.0
    print(f"    pool: {n_total} papers, {n_short} short ({frac:.0%})")
    check(n_total > 0, "pool manifest is non-empty")
    check("pages" in man.columns, "manifest carries a pages column")
    check(frac <= 0.20 + 1e-9, f"pool is <=20% short (got {frac:.0%})")
    # With 40 long papers available and a 60 cap, the cap should fill mostly long;
    # the short count is bounded by floor(0.2/0.8 * longs)-ish via the interleave.
    check(n_short <= n_total * 0.20 + 1e-9, "short count within cap")

print(f"\nALL {ok} CHECKS PASSED.")
