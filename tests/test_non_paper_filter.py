"""
Regression test for the "not a single paper" filter of the `estimate` step.

Some LNI volume folders hold the WHOLE proceedings volume as one PDF next to its
individual papers (`lni300/SE-2020-Komplettband.pdf`, 254 pages, reached the gold
set and had to be pulled out by hand on 2026-07-28). Such a file is not a unit of
analysis, so `select_candidates.py` now drops it before it can enter a working
set.

Covers `paper_length.is_non_paper`'s three rules (page count, filename, LNI front
matter) including their negative cases, plus an END-TO-END run of the real
select_candidates streaming gate asserting that a synthesized "Komplettband" and
an over-long PDF never appear in a manifest while normal papers do. NO SAIA
token, NO real corpus: PDFs are synthesized with PyMuPDF. Run with the analysis
Python from the lni_study repo root:

    python tests/test_non_paper_filter.py

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


# ------------------------------------------------------------------ page rule
print("[1] page-count rule")
check(pl.is_non_paper("lni300/x.pdf", 254), "254 pages -> non-paper")
check(pl.is_non_paper("lni300/x.pdf", 61), "61 pages -> non-paper (just over 60)")
check(pl.is_non_paper("lni300/x.pdf", 60) is None, "60 pages -> paper (boundary)")
check(pl.is_non_paper("lni300/x.pdf", 12) is None, "12-page paper -> paper")
check(pl.is_non_paper("lni300/x.pdf", 2) is None, "2-page abstract -> paper, not filtered here")
check(pl.is_non_paper("lni300/x.pdf", None) is None, "unknown length -> not filtered")
check(pl.is_non_paper("lni300/x.pdf", "") is None, "empty length -> not filtered")
check(pl.is_non_paper("lni300/x.pdf", "n/a") is None, "non-numeric length -> not filtered")
check(pl.is_non_paper("lni300/x.pdf", 254, max_pages=10 ** 9) is None,
      "page rule disabled (huge max_pages) -> not filtered")
check("254" in pl.is_non_paper("lni300/x.pdf", 254), "reason names the page count")

# ------------------------------------------------------------- filename rule
print("[2] filename rule")
for name in ["SE-2020-Komplettband.pdf", "PVM-Tagungsband2024-komplett.pdf",
             "Tagungsband_komplett.pdf", "KB_Inhaltsverzeichnis.pdf",
             "lni-p-221-komplett-frontmatter.pdf", "complete_proceedings.pdf",
             "Book of Abstracts.pdf", "Titelei.pdf"]:
    check(pl.is_non_paper(f"lni999/{name}", 10), f"{name!r} -> non-paper by name")
for name in ["B5-01.pdf", "257.pdf", "BTW2025-50.pdf", "GI.-.Proceedings.52-53.pdf",
             "band_structure_simulation.pdf", "content_extraction.pdf"]:
    check(pl.is_non_paper(f"lni999/{name}", 10) is None, f"{name!r} -> ordinary paper")

# --------------------------------------------------------- front-matter rule
print("[3] front-matter rule (series page + editor block, first 4000 chars)")
frontmatter = ("Lecture Notes in Informatics (LNI) - Proceedings\n"
               "Series of the Gesellschaft fuer Informatik (GI)\nVolume P-300\n"
               "ISBN 978-3-88579-694-7\nVolume Editors\nProf. Dr. Michael Felderer\n"
               "Series Editorial Board\nHeinrich C. Mayr\n")
check(pl.is_non_paper("lni300/x.pdf", 8, frontmatter), "series page + editors -> non-paper")
check(pl.is_non_paper("lni300/x.pdf", 8, "Lecture Notes in Informatics (LNI)") is None,
      "series line alone -> paper (both fingerprints required)")
check(pl.is_non_paper("lni300/x.pdf", 8, "Volume Editors: A. Meier") is None,
      "editor block alone -> paper")
citing = ("We implemented a prototype in Java and evaluated it.\n" + "body text. " * 900
          + "\nReferences\n[Fe20] Felderer, M. et al.: Software Engineering 2020, "
            "Lecture Notes in Informatics, Volume Editors, GI 2020.")
check(pl.is_non_paper("lni300/x.pdf", 12, citing) is None,
      "a paper CITING an LNI volume in its bibliography -> paper (head-only check)")
check(pl.is_non_paper("lni300/x.pdf", 12, "") is None, "empty text -> paper")
check(pl.is_non_paper() is None, "no arguments at all -> None, never crashes")


# -------------------------------------------------------------------- end-to-end
def make_pdf(path, n_pages, head_text=None):
    import pymupdf
    doc = pymupdf.open()
    for i in range(n_pages):
        page = doc.new_page()
        text = head_text if (i == 0 and head_text) else f"page {i+1} of {path.stem}"
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


print("[4] end-to-end select_candidates: no collected volume enters a set")
with tempfile.TemporaryDirectory() as td:
    tdp = Path(td)
    corpus, work = tdp / "corpus", tdp / "work"
    vol = corpus / "vol1"
    vol.mkdir(parents=True)
    for i in range(10):
        make_pdf(vol / f"paper_{i:02d}.pdf", 10)             # ordinary papers
    make_pdf(vol / "SE-2020-Komplettband.pdf", 12)           # caught by NAME
    make_pdf(vol / "collected.pdf", 70)                      # caught by PAGES
    make_pdf(vol / "series.pdf", 8,                          # caught by FRONT MATTER
             "Lecture Notes in Informatics (LNI) - Proceedings Volume Editors")

    res = subprocess.run(
        [sys.executable, str(SRC / "select_candidates.py"),
         "--corpus", str(corpus), "--min_score", "-1",
         "--narrow", "0", "--gold", "0", "--final", "0", "--cap", "50",
         "--workroot", str(work), "--scores_csv", str(tdp / "scores.csv")],
        capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout[-1500:])
        print(res.stderr[-2000:])
    check(res.returncode == 0, "select_candidates exited 0")

    import pandas as pd
    man = pd.read_csv(work / "pool" / "manifest.csv")
    ids = set(man["id"])
    check(len(ids) == 10, f"only the 10 ordinary papers were placed (got {len(ids)})")
    for bad in ["vol1/SE-2020-Komplettband", "vol1/collected", "vol1/series"]:
        check(bad not in ids, f"{bad} not in the pool manifest")
    on_disk = {p.name for p in (work / "pool").rglob("*.pdf")}
    check(not (on_disk & {"SE-2020-Komplettband.pdf", "collected.pdf", "series.pdf"}),
          "no collected-volume PDF was copied into the set folder")
    check("collected volume(s)/front matter skipped" in res.stdout,
          "the run reports how many non-papers it skipped")

    # --keep_non_papers turns the filter off again (debugging escape hatch).
    work2 = tdp / "work2"
    res2 = subprocess.run(
        [sys.executable, str(SRC / "select_candidates.py"),
         "--corpus", str(corpus), "--min_score", "-1", "--keep_non_papers",
         "--narrow", "0", "--gold", "0", "--final", "0", "--cap", "50",
         "--workroot", str(work2), "--scores_csv", str(tdp / "scores2.csv")],
        capture_output=True, text=True)
    check(res2.returncode == 0, "--keep_non_papers run exited 0")
    man2 = pd.read_csv(work2 / "pool" / "manifest.csv")
    check(len(set(man2["id"])) == 13, "--keep_non_papers places all 13 PDFs")

print(f"\nALL {ok} CHECKS PASSED")
