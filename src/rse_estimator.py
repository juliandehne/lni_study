"""
rse_estimator.py

Non-LLM heuristic estimator for "does this paper present research software?".

Purpose: a cheap PRE-FILTER so the expensive LLM annotation (SAIA API) only runs
on papers that are *likely* to contain research software. It scores the extracted
PDF text by counting weighted textual signals that co-occur with released or used
research software, in BOTH German and English LNI papers (code-repository URLs,
availability phrases, software licenses, package managers, source-code
vocabulary, programming languages, ...).

This is deliberately high-recall and approximate. It does NOT decide the final
`label_research_software` — the LLM annotation and the human goldstandard do. It
only RANKS papers so we annotate the most promising ~500 instead of the whole
corpus, which is the point: fewer hits on the SAIA API.

Usage:
    from rse_estimator import estimate
    result = estimate(text)        # {'score': float, 'signals': {...}, 'hits': {...}}

Each signal GROUP contributes ``weight * min(distinct_matches, cap)`` to the
score, so one repeated keyword cannot dominate and a single strong signal (a
GitHub URL) outweighs many weak ones (the word "software"). The groups, weights
and patterns below are intentionally easy to tune.
"""

from __future__ import annotations

import re

# (name, weight, cap, [patterns]) -- patterns are alternation members matched
# case-insensitively. `cap` bounds how many DISTINCT matches in a group can count,
# so a word repeated 50 times does not swamp the score.
SIGNAL_GROUPS: list[tuple[str, float, int, list[str]]] = [
    # Strongest signal: an actual code/artifact repository or archive link.
    ("repo_url", 5.0, 3, [
        r"github\.com", r"gitlab\.(?:com|org|[a-z]{2,})", r"bitbucket\.org",
        r"sourceforge\.net", r"codeberg\.org", r"\bgitea\b",
        r"zenodo\.org", r"figshare\.com", r"doi\.org/10\.5281/zenodo",
        r"\bgit\s+clone\b", r"\.git\b", r"huggingface\.co",
    ]),
    # Explicit "the software is available / open source / reproducible" claims.
    ("availability", 4.0, 2, [
        # EN
        r"\b(?:source\s+)?code\s+is\s+(?:publicly\s+|freely\s+)?available",
        r"\bpublicly\s+available\b", r"\bfreely\s+available\b",
        r"\bavailable\s+(?:at|on|from|under|via|online)\b",
        r"\bopen[\s-]?source(?:d)?\b", r"\breproducib(?:le|ility)\b",
        # DE
        r"\bverf(?:ü|ue)gbar\s+(?:unter|auf|über|ueber)\b",
        r"\bfrei\s+verf(?:ü|ue)gbar\b",
        r"\b(?:öffentlich|oeffentlich)\s+(?:verf(?:ü|ue)gbar|zug(?:ä|ae)nglich)\b",
        r"\bzu\s+finden\s+unter\b", r"\bquelloffen\b",
    ]),
    # A named software license is a strong tell that something was released.
    ("license", 3.0, 2, [
        r"\bMIT\s+Licen[sc]e\b", r"\bApache\s+Licen[sc]e\b", r"\bApache-2\.0\b",
        r"\bGNU\s+General\s+Public\b", r"\bGPL(?:\s*v?\s*[23])?\b", r"\bLGPL\b",
        r"\bBSD\b", r"\bMozilla\s+Public\s+Licen[sc]e\b", r"\bMPL\b",
        r"\bCreative\s+Commons\b", r"\bCC[\s-]BY\b", r"\bApache\s+2\b",
    ]),
    # Build / install / containerization commands -> runnable software.
    ("package_manager", 3.0, 2, [
        r"\bpip\s+install\b", r"\bconda\s+(?:install|env)\b", r"\bnpm\s+(?:install|i)\b",
        r"\byarn\s+add\b", r"\bdocker\s+(?:run|pull|build|compose)\b",
        r"\bDockerfile\b", r"\bdocker-compose\b", r"\bapt-get\s+install\b",
        r"\bmaven\b", r"\bgradle\b", r"\brequirements\.txt\b",
        r"\bpackage\.json\b", r"\bpom\.xml\b", r"\bMakefile\b", r"\bvirtualenv\b",
    ]),
    # Core "we wrote/ran code" vocabulary.
    ("source_vocab", 2.0, 3, [
        # EN
        r"\bsource\s+code\b", r"\bcode\s*base\b", r"\brepositor(?:y|ies)\b",
        r"\bimplement(?:ation|ed|s)\b", r"\bcommand[\s-]line\b", r"\bAPI\b",
        r"\bunit\s+tests?\b", r"\bcontinuous\s+integration\b", r"\bSDK\b",
        # DE
        r"\bQuellcode\b", r"\bQuelltext\b", r"\bImplementier(?:ung|t)\b",
        r"\bRepositorium\b", r"\bKommandozeile\b", r"\bSchnittstelle\b",
    ]),
    # Weaker artifact nouns: present in lots of papers, so low weight.
    ("artifact_vocab", 1.0, 3, [
        # EN
        r"\bframework\b", r"\blibrar(?:y|ies)\b", r"\btoolkit\b", r"\btool\b",
        r"\bprototype\b", r"\bplug[\s-]?in\b", r"\bsoftware\b", r"\bapplication\b",
        r"\bweb[\s-]?app\b", r"\bplatform\b",
        # DE
        r"\bBibliothek\b", r"\bWerkzeug\b", r"\bPrototyp\b", r"\bAnwendung\b",
        r"\bSoftware\b", r"\bPlattform\b",
    ]),
    # Programming languages / well-known frameworks.
    ("prog_lang", 1.0, 3, [
        r"\bPython\b", r"\bJava(?:Script)?\b", r"\bTypeScript\b", r"\bC\+\+",
        r"\bC#", r"\bMatlab\b", r"\bMATLAB\b", r"\bHaskell\b", r"\bScala\b",
        r"\bKotlin\b", r"\bGolang\b", r"\bRust\b", r"\bPHP\b", r"\bRuby\b",
        r"\bReact\b", r"\bAngular\b", r"\bNode\.js\b", r"\bFlask\b",
        r"\bDjango\b", r"\bTensorFlow\b", r"\bPyTorch\b",
    ]),
]

# Pre-compile one alternation regex per group (non-capturing members, so
# `findall` yields whole-match strings).
_COMPILED: list[tuple[str, float, int, "re.Pattern[str]"]] = [
    (name, weight, cap, re.compile("|".join(f"(?:{p})" for p in pats), re.IGNORECASE))
    for name, weight, cap, pats in SIGNAL_GROUPS
]

# Maximum reachable score (all groups saturated) — useful to normalize if needed.
MAX_SCORE = sum(weight * cap for _, weight, cap, _ in _COMPILED)


def estimate(text: str | None) -> dict:
    """Score ``text`` for research-software signals.

    Returns ``{'score': float, 'signals': {group: capped_count}, 'hits':
    {group: [example_matches]}}``. Empty/None text scores 0.0.
    """
    if not text:
        return {"score": 0.0, "signals": {}, "hits": {}}

    score = 0.0
    signals: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    for name, weight, cap, rx in _COMPILED:
        found = rx.findall(text)
        if not found:
            continue
        # Non-capturing alternation -> each element is the matched substring.
        distinct = sorted({m.lower() if isinstance(m, str) else str(m) for m in found})
        n = min(len(distinct), cap)
        score += weight * n
        signals[name] = n
        hits[name] = distinct[:cap]
    return {"score": round(score, 3), "signals": signals, "hits": hits}


def score_only(text: str | None) -> float:
    """Convenience: just the numeric score."""
    return estimate(text)["score"]