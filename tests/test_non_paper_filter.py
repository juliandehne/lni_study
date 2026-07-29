"""
Regression test for the "not a single paper" filter of the `estimate` step.

Some LNI volume folders hold the WHOLE proceedings volume as one PDF next to its
individual papers (`lni300/SE-2020-Komplettband.pdf`, 254 pages, reached the gold
set and had to be pulled out by hand on 2026-07-28). Such a file is not a unit of
analysis, so `select_candidates.py` now drops it before it can enter a working
set.

Covers `paper_length.is_non_paper`'s four rules (page count, filename, LNI front
matter, bundled-track contribution count) including their negative cases, plus an
END-TO-END run of the real
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

# ------------------------------------------------ bundled-track rule (rule 4)
print("[3b] contribution-count rule (bundled workshop track)")


def stamp(doi, editors="M. Klein, D. Krupka (Hrsg.): INFORMATIK 2024, "
                      "Lecture Notes in Informatics (LNI), GI, Bonn 2024"):
    """The title-page stamp every LNI contribution carries."""
    return f"cba doi:10.18420/{doi}\n{editors}\n"


one = "Abstract: We built a tool.\n" + stamp("inf2024_181") + "body " * 200
three = ("9. Workshop Enterprise Architecture Management\n"
         + stamp("inf2024_134") + "body " * 200
         + stamp("inf2024_135") + "body " * 200
         + stamp("inf2024_136") + "body " * 200)
check(pl.count_contributions(one) == 1, "one stamp -> 1 contribution")
check(pl.count_contributions(three) == 3, "three stamps -> 3 contributions")
check(pl.count_contributions("") == 0, "no text -> 0 contributions")
check(pl.count_contributions("a paper with no stamp at all") == 0,
      "unstamped (pre-DOI) volume -> 0, not a bundle signal")
check(pl.is_non_paper("lni352/KB_9th_Workshop.pdf", 41, three),
      "41-page three-paper bundle -> non-paper (misses rules 1-3, caught by 4)")
check("3 contributions" in pl.is_non_paper("lni352/KB_9th_Workshop.pdf", 41, three),
      "reason names the contribution count")
check(pl.is_non_paper("lni352/paper.pdf", 8, one) is None,
      "single stamped paper -> paper")
check(pl.is_non_paper("lni352/paper.pdf", 8, "no stamps here") is None,
      "unstamped paper -> paper (rule 4 never fires on 0)")
# The real false-positive risk: a paper CITING another LNI paper by DOI. The
# citation has no licence badge and no editor line, so it is not a second stamp.
citing_doi = (one + "\nReferences\n[Me23] Mertzen, D. et al.: INFORMATIK 2023, "
                    "Bonn, S. 95-105, 2023, doi: 10.18420/inf2023_08.\n")
check(pl.count_contributions(citing_doi) == 1,
      "a bibliography DOI is not a contribution stamp")
check(pl.is_non_paper("lni352/Neuroth.pdf", 8, citing_doi) is None,
      "paper citing another LNI paper by DOI -> paper")
# The false positive that killed the footer-counting variant: several volumes
# repeat the "<editors> (Hrsg.): ... Lecture Notes in Informatics" footer on
# EVERY page, so single papers scored 2-6 on it (lni220/736, lni197/83,
# lni285/3032414_GI_P_285_23, lni327/PVM2022_8 -- all genuine single papers,
# none of them carrying a per-paper DOI at all).
repeated_footer = "Konkretisierung eines BPM-Oekosystems\nKonrad Walser\n" + (
    "Joern von Lucke et al. (Hrsg.): Auf dem Weg zu einer offenen Verwaltungskultur, "
    "Lecture Notes in Informatics (LNI), Gesellschaft fuer Informatik, Bonn 2012\n"
    "body text of the one and only paper. " * 30) * 6
check(pl.count_contributions(repeated_footer) == 0,
      "per-page repeated editor footer -> 0 contributions, not 6")
check(pl.is_non_paper("lni220/736.pdf", 14, repeated_footer) is None,
      "single paper with a per-page editor footer -> paper (regression)")


# -------------------------------------------------------------------- end-to-end
def make_pdf(path, n_pages, head_text=None, page_texts=None):
    """A synthetic PDF. `head_text` lands on page 1, `page_texts` is a
    {page_index: text} override used to place several contribution stamps."""
    import pymupdf
    doc = pymupdf.open()
    for i in range(n_pages):
        page = doc.new_page()
        text = (page_texts or {}).get(i) or (
            head_text if (i == 0 and head_text) else f"page {i+1} of {path.stem}")
        page.insert_text((50, 72), text[:90])
        for j, line in enumerate(text.split("\n")[:8]):
            page.insert_text((50, 120 + 14 * j), line[:95])
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
    make_pdf(vol / "KB_9th_Workshop.pdf", 12,                # caught by BUNDLE COUNT
             page_texts={0: stamp("inf2024_134"), 4: stamp("inf2024_135"),
                         8: stamp("inf2024_136")})

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
    for bad in ["vol1/SE-2020-Komplettband", "vol1/collected", "vol1/series",
                "vol1/KB_9th_Workshop"]:
        check(bad not in ids, f"{bad} not in the pool manifest")
    on_disk = {p.name for p in (work / "pool").rglob("*.pdf")}
    check(not (on_disk & {"SE-2020-Komplettband.pdf", "collected.pdf", "series.pdf",
                          "KB_9th_Workshop.pdf"}),
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
    check(len(set(man2["id"])) == 14, "--keep_non_papers places all 14 PDFs")

print(f"\nALL {ok} CHECKS PASSED")
