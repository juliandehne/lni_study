"""
Regression test for the rse_estimator signal groups and their goldstandard
calibration (2026-07-28, 98 human-coded papers).

Locks in the three things that calibration actually decided, so a later edit to
the pattern list cannot silently undo them:

  * the two groups added because the goldstandard exposed them
    (`first_person_artifact`, `code_listing`) fire on the phrasing they were
    derived from and stay quiet on obvious non-software prose;
  * `artifact_vocab` keeps its reduced weight — it fires on 94.8% of the corpus
    and separates almost nothing, so restoring weight 1.0 would re-inflate every
    score by up to 3 points;
  * a repo URL still outranks a pile of weak artifact nouns, which is the whole
    ordering premise of the score.

No corpus, no PDFs, no network. Run with the analysis Python from the repo root:

    python tests/test_rse_estimator.py

Exits non-zero on the first failed assertion.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import rse_estimator as est  # noqa: E402

ok = 0


def check(cond, msg):
    global ok
    assert cond, f"FAIL: {msg}"
    ok += 1


def groups_of(text):
    return set(est.estimate(text)["signals"])


# --- the groups the goldstandard added -------------------------------------
FIRST_PERSON = [
    "We implemented a parser for the corpus.",
    "we have developed a small tool",
    "Our prototype runs on commodity hardware.",
    "we present a framework for teaching modelling",
    "Unser Werkzeug unterstuetzt die Modellierung.",
    "Dazu haben wir einen Generator implementiert.",
]
for t in FIRST_PERSON:
    check("first_person_artifact" in groups_of(t), f"first_person missed: {t!r}")

NOT_FIRST_PERSON = [
    "The authors of [3] implemented a parser.",
    "Studierende entwickeln im Praktikum eigene Konzepte.",
    "This position paper argues for a curriculum revision.",
]
for t in NOT_FIRST_PERSON:
    check("first_person_artifact" not in groups_of(t), f"first_person false hit: {t!r}")

for t in ["See Listing 3 for the grammar.", "Algorithmus 1 zeigt das Vorgehen.",
          "A code example is given below.", "Ein Code-Beispiel folgt."]:
    check("code_listing" in groups_of(t), f"code_listing missed: {t!r}")
check("code_listing" not in groups_of("Table 1 lists the participants."),
      "code_listing fired on a plain table reference")

# --- calibrated weights -----------------------------------------------------
weights = {name: (w, cap) for name, w, cap, _ in est.SIGNAL_GROUPS}
check(weights["artifact_vocab"][0] == 0.5,
      "artifact_vocab weight must stay 0.5 (fires on 94.8% of the corpus)")
check(weights["repo_url"][0] == 5.0, "repo_url must stay the strongest group")
check(weights["first_person_artifact"] == (3.0, 2), "first_person_artifact weight/cap changed")
check(weights["code_listing"][1] == 1, "code_listing cap must stay 1 (presence, not count)")
check(len(est.SIGNAL_GROUPS) == len(est._COMPILED) == 9, "unexpected number of signal groups")
check(est.MAX_SCORE == sum(w * c for w, c in weights.values()), "MAX_SCORE out of sync")

# --- ordering premise -------------------------------------------------------
repo = est.score_only("Code at https://github.com/example/proj and zenodo.org/record/1")
nouns = est.score_only("This framework, library, toolkit, platform and application "
                       "is a software prototype plug-in.")
check(repo > nouns, f"a repo URL ({repo}) must outrank weak artifact nouns ({nouns})")
check(est.score_only(None) == 0.0 and est.score_only("") == 0.0, "empty text must score 0.0")

# a paper with no software vocabulary at all should stay near the floor
prose = ("In diesem Beitrag diskutieren wir Ergebnisse einer Befragung unter "
         "Lehrenden. Die Teilnehmenden bewerteten die Aussagen auf einer Skala.")
check(est.score_only(prose) <= 2.0, f"pure survey prose scored {est.score_only(prose)}")

print(f"OK - {ok} checks passed.")
