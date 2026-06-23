"""
annotate_lni.py

Startup script for the LNI RSE-typology study (notes steps 1, 3, 4, 5, 6).

Given a folder of LNI publication PDFs and a KISSKI SAIA API token, this script:

  1. recursively finds every *.pdf in the folder,
  2. extracts (title, authors, abstract, text, references) from each PDF
     using the vendored `pdf_text_extraction` module (reused from the
     DeLFI / rse-elearning-evaluation pipeline),
  3. builds the RSE-typology prompt from `prompts/rse_typology_prompt_v1.md`
     and the typology defined in `categories.py`,
  4. calls the SAIA chat-completions API (rate-limited, OpenAI-compatible),
  5. parses the JSON answer (RSE gate + typology + per-dimension certainty +
     suggested new subcategories),
  6. appends one row per paper to a checkpoint CSV (resumable), and
  7. logs every paper for which the model suggested a NEW subcategory
     (notes step 7: bootstrap until ~100 papers with new suggestions).

This is the *machine annotation* half of the bootstrap phase. The human
goldstandard half lives in `build_goldstandard.py`.

Designed to be run from IntelliJ / the command line. Reuses the proven
RateLimiter, JSON extraction, and checkpoint/resume logic from
`rse-elearning-evaluation/experiments/experiments/experiments.py`.

Usage (from the lni_study repo root):

    Windows:
        python src/annotate_lni.py ^
            --lni_folder "../rse-elearning-evaluation/data/data/lni132" ^
            --model mistral-large-3-675b-instruct-2512 ^
            --run run_1

    The SAIA token and endpoint are read from a .env file (see .env.example)
    or can be passed explicitly with --saia_token / --saia_endpoint.

    Add --test to annotate only the first 5 PDFs end-to-end.
"""

import argparse
import json
import logging
import os
import random
import re
import shutil
import sys
import time
from collections import Counter, deque
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import (OpenAI, APIError, APIConnectionError, APITimeoutError,
                    APIStatusError, AuthenticationError, InternalServerError,
                    RateLimitError)
from tqdm import tqdm

# Local imports (vendored / project modules)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as cat  # noqa: E402
from sampling import stratified_sample, format_allocation, volume_under, paper_id  # noqa: E402
from pdf_text_extraction import (  # noqa: E402
    extract_text_from_pdf,
    extract_main_content,
    extract_references,
    extract_title_from_pdf,
    extract_authors_from_pdf,
    extract_abstract_from_pdf,
)

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
# Data root for all GENERATED data (results/, .workingset/, goldstandard/). Defaults
# to the repo, but LNI_DATA_ROOT supersedes it so everything can live in an external
# working dir (e.g. a shared drive). Prompts/schema stay in the repo (committed config).
DATA_ROOT = Path(os.environ.get("LNI_DATA_ROOT") or REPO_ROOT).resolve()
DEFAULT_PROMPT = REPO_ROOT / "prompts" / "rse_typology_prompt_v1.md"
DEFAULT_WORKROOT = DATA_ROOT / ".workingset"

# Rolling per-call response log. Captures every SAIA completion (raw content,
# finish_reason, retries) so a live run can be inspected after the fact -- in
# particular the empty/parse-failure cases that only flashed past on the console.
# Rotating (5 MB x 3) so it can't grow unbounded across long runs.
RESPONSE_LOG_PATH = DATA_ROOT / "logs" / "annotate_lni_responses.log"
RESPONSE_LOG_MAX_CHARS = 6000  # per-response body cap in the log (prompts/texts are huge)
_response_logger: logging.Logger | None = None


def response_log() -> logging.Logger:
    """Lazily create the rolling response logger (so import / preview / dry-run
    don't create a logs dir until an actual annotation run logs something)."""
    global _response_logger
    if _response_logger is not None:
        return _response_logger
    logger = logging.getLogger("annotate_lni.responses")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # don't spam the console; tqdm.write handles that
    if not logger.handlers:
        RESPONSE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            RESPONSE_LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3,
            encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    _response_logger = logger
    return logger


def _clip(text, limit: int = RESPONSE_LOG_MAX_CHARS) -> str:
    """Render a possibly-None response body for the log, capped so one giant
    answer can't bloat the file. Notes how much was clipped."""
    s = "" if text is None else str(text)
    if len(s) <= limit:
        return s
    return f"{s[:limit]}… [+{len(s) - limit} chars clipped]"

# KISSKI SAIA endpoint (OpenAI-compatible). Fixed service URL; can still be
# overridden via --saia_endpoint or SAIA_API_ENDPOINT.
# https://docs.hpc.gwdg.de/services/saia/index.html
DEFAULT_SAIA_ENDPOINT = "https://chat-ai.academiccloud.de/v1"


# =============================================================================
# Rate limiter (KISSKI SAIA API: 10 req/min, 200 req/hour) — reused from DeLFI
# =============================================================================

class RateLimiter:
    """Proactive sliding-window rate limiter for the KISSKI SAIA API."""

    def __init__(self, max_per_minute: int = 10, max_per_hour: int = 200):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self._timestamps: deque = deque()

    def wait_if_needed(self) -> None:
        while True:
            now = time.time()
            while self._timestamps and self._timestamps[0] < now - 3600:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_per_hour:
                oldest = self._timestamps[0]
                wait_s = (oldest + 3600) - now + 1.0
                reset = datetime.fromtimestamp(oldest + 3600).strftime("%H:%M:%S")
                print(f"\nHourly limit reached ({self.max_per_hour}/h). "
                      f"Waiting {wait_s / 60:.1f} min (until ~{reset})...", flush=True)
                time.sleep(wait_s)
                continue

            recent = sum(1 for t in self._timestamps if t >= now - 60)
            if recent >= self.max_per_minute:
                oldest_in_window = min(t for t in self._timestamps if t >= now - 60)
                wait_s = (oldest_in_window + 60) - now + 0.5
                print(f"\nMinute limit reached ({self.max_per_minute}/min). "
                      f"Waiting {wait_s:.1f} s...", flush=True)
                time.sleep(wait_s)
                continue
            break

    def record(self) -> None:
        self._timestamps.append(time.time())


# =============================================================================
# Prompt handling
# =============================================================================

def load_prompt_template(path: str | Path) -> tuple[str, str]:
    """Parse a prompt template markdown file into (system_prompt, user_prompt).

    Same '#### 1) System prompt' / '#### 2) User prompt' structure as the
    DeLFI prompt templates.
    """
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    system_match = re.search(r"#### 1\) System prompt\s*\n(.*?)(?=#### 2\))", content, re.DOTALL)
    user_match = re.search(r"#### 2\) User prompt\s*\n(.*?)$", content, re.DOTALL)
    if not system_match or not user_match:
        raise ValueError(f"Could not parse system/user prompt sections from: {path}")
    return system_match.group(1).strip(), user_match.group(1).strip()


def fill_user_prompt(template: str, paper: dict) -> str:
    """Substitute paper fields and the categories/RSE-definition blocks."""
    result = template
    for field in ["title", "authors", "year", "abstract", "text", "references"]:
        value = paper.get(field)
        result = result.replace(f"{{row['{field}']}}", "" if value is None else str(value))
    result = result.replace("{rse_definition}", cat.RSE_DEFINITION)
    result = result.replace("{categories_block}", cat.render_categories_block())
    # Curated white/blacklist guidance from the narrowing step (narrow_categories.py).
    # Empty string until that step has been run, so existing prompts are unchanged.
    result = result.replace("{category_guidance_block}", cat.render_category_guidance_block())
    return result


# =============================================================================
# PDF -> paper dict
# =============================================================================

def pdf_to_paper(pdf_path: Path, lni_folder: Path, max_text_chars: int) -> dict:
    """Extract the fields needed for annotation from a single LNI PDF.

    LNI papers in this corpus have no separate metadata file, so title/authors/
    abstract are extracted heuristically (same extractors as the DeLFI study).
    `year` is unknown from the folder name (folders are LNI volume numbers, not
    years); it is left blank unless a future mapping is added.
    """
    raw = extract_text_from_pdf(pdf_path)
    if raw is None:
        raw = ""

    pid = paper_id(pdf_path, lni_folder)
    text = extract_main_content(raw)
    if text and max_text_chars and len(text) > max_text_chars:
        text = text[:max_text_chars]

    return {
        "id": pid,
        "source_folder": volume_under(lni_folder)(pdf_path),
        "filename": pdf_path.name,
        "rel_path": Path(pid + pdf_path.suffix).as_posix(),
        "title": extract_title_from_pdf(raw),
        "authors": extract_authors_from_pdf(raw),
        "year": "",  # unknown from folder name; fill via mapping if available
        "abstract": extract_abstract_from_pdf(raw),
        "text": text,
        "references": extract_references(raw),
        "extraction_failed": raw == "" or text is None,
    }


# =============================================================================
# JSON extraction from LLM response — reused from DeLFI experiments.py
# =============================================================================

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


def flatten_annotation(result: dict) -> dict:
    """Flatten the nested typology JSON into flat CSV columns.

    Produces, per dimension: <dim>_category, <dim>_certainty,
    <dim>_new_suggestion, <dim>_explanation.
    """
    flat: dict = {
        "label_research_software": result.get("label_research_software"),
        "label_research_software_certainty": result.get("label_research_software_certainty"),
        "label_research_software_explanation": result.get("label_research_software_explanation"),
    }
    typ = result.get("typology")
    for dim in cat.DIMENSIONS:
        d = (typ or {}).get(dim, {}) if isinstance(typ, dict) else {}
        if cat.TYPOLOGY.get(dim, {}).get("multi"):
            # Multi-value dimensions may arrive as a `categories` list (techstack's
            # schema key) or a `category` that is itself a list. Join to a single
            # `;`-separated cell so downstream code can split it uniformly.
            cats = d.get("categories")
            if not isinstance(cats, list):
                cats = d.get("category")
            flat[f"{dim}_category"] = ";".join(cats) if isinstance(cats, list) else cats
        else:
            flat[f"{dim}_category"] = d.get("category")
        flat[f"{dim}_certainty"] = d.get("certainty")
        flat[f"{dim}_new_suggestion"] = d.get("new_suggestion")
        flat[f"{dim}_explanation"] = d.get("explanation")
    return flat


# Canonical checkpoint columns. EVERY row (successful annotation OR llm_error
# row) is written with exactly these columns in this order, so the appended CSV
# stays rectangular and is safe to resume from. Without this, error rows carry
# only {llm_error, llm_raw_response} while success rows carry the full typology,
# the header is fixed from whatever the first row happened to be, and later wider
# rows make the file ragged ("Expected N fields, saw N+1" on read).
CHECKPOINT_COLUMNS: list[str] = (
    ["id", "source_folder", "filename", "rel_path", "title", "authors",
     "model", "prompt_template", "run"]
    + list(flatten_annotation({}).keys())   # deterministic typology columns
    + ["llm_error", "llm_raw_response"]
)


# =============================================================================
# Annotation
# =============================================================================

# Cap the completion length. A COMPLETE typology answer (all 6 explanations +
# every classification) measured at ~885 tokens median / ~1350 tokens max over
# 279 real annotations; the worst malformed one was ~1490. 2048 sits ~50% above
# that worst case, so a well-formed answer is never truncated, while a runaway
# generation is bounded. If the cap ever IS hit, finish_reason == "length" is
# detected below and the paper is recorded as a truncation error (NOT silently
# parsed as a half-filled JSON, which would drop dimensions). Set to None to
# leave the completion uncapped (the old behaviour).
DEFAULT_MAX_TOKENS = 2048


def _complete_with_retries(client, paper_id, model, system_prompt, user_prompt,
                           temperature, seed, top_p, rate_limiter, max_tokens):
    """Shared SAIA chat-completion + retry/backoff + JSON parse core. Returns the
    parsed response dict on success, or an {'llm_error', 'llm_raw_response'} dict
    on any failure (timeout, retries exhausted, truncation, bad JSON)."""
    MAX_RETRIES = 5
    BASE_DELAY = 1.0
    log = response_log()
    log.info("REQUEST id=%s model=%s prompt_chars=%d max_tokens=%s",
             paper_id, model, len(user_prompt or ""), max_tokens)

    def _retry_or_give_up(kind: str, detail: str, raw):
        """Shared backoff for a transient condition. Returns an llm_error dict on
        the final attempt (caller should return it), or None to keep retrying."""
        if attempt == MAX_RETRIES - 1:
            tqdm.write(f"id={paper_id}: {kind} x{MAX_RETRIES}, giving up on this paper")
            log.warning("GIVE-UP id=%s %s x%d detail=%s raw=%r",
                        paper_id, kind, MAX_RETRIES, detail, _clip(raw))
            return {"llm_error": f"{kind} x{MAX_RETRIES}: {detail}", "llm_raw_response": raw}
        backoff = BASE_DELAY * (2 ** attempt)
        wait_s = backoff + backoff * 0.25 * random.random()
        tqdm.write(f"id={paper_id}: {kind} ({attempt + 1}/{MAX_RETRIES}), "
                   f"retry in {wait_s:.1f}s...")
        log.warning("RETRY id=%s %s attempt=%d/%d detail=%s",
                    paper_id, kind, attempt + 1, MAX_RETRIES, detail)
        time.sleep(wait_s)
        return None

    for attempt in range(MAX_RETRIES):
        rate_limiter.wait_if_needed()
        try:
            rate_limiter.record()
            response = client.chat.completions.create(
                model=model, temperature=temperature, top_p=top_p, seed=seed,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except AuthenticationError as e:
            # Bad/expired token affects every call -- stop the whole run now.
            raise SystemExit(f"SAIA authentication failed (check your token): {e}")
        except APITimeoutError:
            # A single call already waited the full client timeout (300s); don't
            # burn 5x that retrying -- record and move on to the next paper.
            tqdm.write(f"id={paper_id}: timeout after 300s, skipping")
            log.warning("TIMEOUT id=%s after 300s, skipping", paper_id)
            return {"llm_error": "APITimeoutError", "llm_raw_response": None}
        except (RateLimitError, InternalServerError, APIConnectionError) as e:
            # Transient: 429 rate limit, 5xx server error (e.g. the 500 that used
            # to crash the run), or a network blip. Retry with exp backoff+jitter.
            gave_up = _retry_or_give_up(type(e).__name__, str(e), None)
            if gave_up is not None:
                return gave_up
            continue
        except APIStatusError as e:
            # Other non-retryable HTTP errors (e.g. 400 bad request): record + skip.
            tqdm.write(f"id={paper_id}: APIStatusError {e.status_code}, skipping paper")
            log.warning("HTTP id=%s status=%s skipping: %s", paper_id, e.status_code, e)
            return {"llm_error": f"APIStatusError {e.status_code}: {e}",
                    "llm_raw_response": None}
        except APIError as e:
            # Catch-all for any other OpenAI-client error so one odd paper can't
            # kill a multi-hour batch.
            tqdm.write(f"id={paper_id}: {type(e).__name__}, skipping paper")
            log.warning("APIError id=%s %s skipping: %s", paper_id, type(e).__name__, e)
            return {"llm_error": f"{type(e).__name__}: {e}", "llm_raw_response": None}

        choice = response.choices[0]
        raw_content = choice.message.content
        finish = getattr(choice, "finish_reason", None)
        log.info("RESPONSE id=%s attempt=%d finish=%s chars=%d body=%r",
                 paper_id, attempt + 1, finish, len(raw_content or ""),
                 _clip(raw_content))
        # If the cap bit, the JSON is cut off mid-structure: don't try to parse it
        # as a complete answer (that would silently drop the unfilled dimensions).
        # Flag it distinctly so it's visible in the checkpoint as a truncation, not
        # a generic parse error -- the fix is a larger max_tokens, not a re-run.
        if finish == "length":
            tqdm.write(f"id={paper_id}: response hit max_tokens ({max_tokens}); "
                       "truncated before all fields were filled")
            log.warning("TRUNCATED id=%s finish=length max_tokens=%s", paper_id, max_tokens)
            return {"llm_error": f"truncated (finish_reason=length, max_tokens={max_tokens})",
                    "llm_raw_response": raw_content}
        # The endpoint intermittently returns a successful (finish_reason != length)
        # but EMPTY/whitespace completion -- no error, no content. That's a transient
        # hiccup, not a malformed answer: retry it like a 5xx instead of mis-reporting
        # it as a permanent "No valid JSON object found" parse failure (which left the
        # cell blank and gave no hint a re-run would fix it).
        if not (raw_content or "").strip():
            gave_up = _retry_or_give_up(
                "empty response", f"finish_reason={finish}", raw_content)
            if gave_up is not None:
                return gave_up
            continue
        try:
            result = extract_json_from_response(raw_content)
            if not isinstance(result, dict):
                log.warning("NON-DICT id=%s parsed to %s", paper_id, type(result).__name__)
                return {"llm_error": f"JSON parsed to {type(result).__name__}",
                        "llm_raw_response": raw_content}
            log.info("OK id=%s parsed JSON on attempt %d", paper_id, attempt + 1)
            return result
        except json.JSONDecodeError as e:
            tqdm.write(f"id={paper_id}: {e}")
            log.warning("PARSE-FAIL id=%s %s raw=%r", paper_id, e, _clip(raw_content))
            return {"llm_error": f"JSON parse error: {e}", "llm_raw_response": raw_content}

    # Defensive: the loop only falls through here if every attempt hit a retryable
    # path without _retry_or_give_up returning a give-up dict (shouldn't happen).
    return {"llm_error": "retries exhausted", "llm_raw_response": None}


def classify_paper(client, paper, model, system_prompt, user_prompt_template,
                   temperature, seed, top_p, rate_limiter,
                   max_tokens: int | None = DEFAULT_MAX_TOKENS) -> dict:
    """Full annotation: one SAIA call covering the RSE gate + every dimension.
    Returns a flat typology dict, or an {'llm_error', ...} dict on failure."""
    user_prompt = fill_user_prompt(user_prompt_template, paper)
    out = _complete_with_retries(client, paper["id"], model, system_prompt,
                                 user_prompt, temperature, seed, top_p,
                                 rate_limiter, max_tokens)
    if "llm_error" in out:
        return out
    return flatten_annotation(out)


def _fill_json_skeleton(dims: list[str]) -> str:
    """The compact JSON the model must return for a targeted per-dimension fill
    (only the requested dimensions, wrapped in `typology`)."""
    inner = []
    for d in dims:
        if cat.TYPOLOGY[d].get("multi"):
            cat_line = '      "categories": ["<subkategorie-key>", "..."],'
        else:
            cat_line = '      "category": "<subkategorie-key oder Freitext>",'
        inner.append(
            f'    "{d}": {{\n'
            f'{cat_line}\n'
            '      "certainty": 0.0,\n'
            '      "new_suggestion": "",\n'
            '      "explanation": "kurze Erklärung"\n'
            '    }')
    return '{\n  "typology": {\n' + ",\n".join(inner) + "\n  }\n}"


def build_fill_user_prompt(paper: dict, dims: list[str]) -> str:
    """Build a TARGETED user prompt that asks the model to annotate ONLY `dims`
    for a paper already confirmed as research software. Renders just those
    dimensions' active subcategories + rejected-key guidance, so the completion
    stays small and focused (used by --fill-missing)."""
    labels = ", ".join(f"{cat.TYPOLOGY[d]['label']} (`{d}`)" for d in dims)
    parts = [
        "Hier ist der Titel, die Autoren, das Jahr, der Abstract, der Text und das "
        "Literaturverzeichnis einer LNI-Publikation:",
        "",
        f"Titel: {paper.get('title') or ''}",
        "",
        f"Autoren: {paper.get('authors') or ''}",
        "",
        f"Jahr: {paper.get('year') or ''}",
        "",
        f"Abstract: {paper.get('abstract') or ''}",
        "",
        f"Text: {paper.get('text') or ''}",
        "",
        f"Literaturverzeichnis: {paper.get('references') or ''}",
        "",
        "Diese Publikation wurde bereits als Forschungssoftware (RSE) klassifiziert "
        "(label_research_software = 1).",
        f"Annotiere AUSSCHLIESSLICH die folgende(n) Dimension(en): {labels}. "
        "Ignoriere alle anderen Dimensionen.",
        "",
        "Wähle für jede Dimension die am besten passende Subkategorie aus den unten "
        "vorgegebenen Subkategorien. Wenn KEINE gut passt, wähle die am ehesten "
        "passende und schlage im Feld `new_suggestion` eine NEUE, präzise benannte "
        "Subkategorie vor (sonst lasse `new_suggestion` leer: \"\"). Gib je Dimension "
        "deine Sicherheit (`certainty`, 0.0–1.0) und eine kurze Begründung an.",
        "",
        "WICHTIG — keine Spekulation: Vergib eine Subkategorie NUR, wenn sie durch den "
        "Text der Publikation EXPLIZIT belegt ist; schließe NICHT aus dem "
        "Anwendungskontext, was \"typischerweise\" verwendet wird. Ist ein Merkmal "
        "nicht ausdrücklich belegt, wähle die am ehesten belegte Kategorie und mache "
        "die Unsicherheit über `certainty` und die Begründung kenntlich.",
        "",
        cat.render_categories_block(dims=dims),
    ]
    guidance = cat.render_category_guidance_block(dims=dims)
    if guidance:
        parts += ["", guidance]
    parts += [
        "",
        "Antworte AUSSCHLIESSLICH in diesem JSON-Format (kein anderer Text):",
        "",
        _fill_json_skeleton(dims),
    ]
    return "\n".join(parts)


def classify_paper_dims(client, paper, model, dims, rate_limiter, system_prompt,
                        temperature, seed, top_p,
                        max_tokens: int | None = DEFAULT_MAX_TOKENS) -> dict:
    """Like classify_paper but asks ONLY about `dims`. Returns a flat dict with
    just those dimensions' columns (<dim>_category/_certainty/_new_suggestion/
    _explanation), or an {'llm_error', ...} dict on failure."""
    user_prompt = build_fill_user_prompt(paper, dims)
    out = _complete_with_retries(client, paper["id"], model, system_prompt,
                                 user_prompt, temperature, seed, top_p,
                                 rate_limiter, max_tokens)
    if "llm_error" in out:
        return out
    flat = flatten_annotation(out)
    keep: dict = {}
    for d in dims:
        for suffix in ("_category", "_certainty", "_new_suggestion", "_explanation"):
            keep[f"{d}{suffix}"] = flat.get(f"{d}{suffix}")
    return keep


def log_new_suggestions(paper_id: str, flat: dict, suggestions_path: Path) -> bool:
    """Append a row per dimension that proposed a new subcategory. Returns True
    if this paper produced at least one new suggestion (notes step 7 counter)."""
    rows = []
    for dim in cat.DIMENSIONS:
        sugg = flat.get(f"{dim}_new_suggestion")
        if sugg and str(sugg).strip():
            rows.append({
                "id": paper_id,
                "dimension": dim,
                "new_suggestion": str(sugg).strip(),
                "certainty": flat.get(f"{dim}_certainty"),
                "explanation": flat.get(f"{dim}_explanation"),
            })
    if rows:
        df = pd.DataFrame(rows)
        header = not suggestions_path.exists()
        df.to_csv(suggestions_path, mode="a", header=header, index=False)
        return True
    return False


# =============================================================================
# --fill-missing: incrementally update an existing gold checkpoint (one row per
# paper) without re-annotating the whole thing. Two regimes, decided per paper by
# whether a human coder has already coded it (any goldstandard/coding_*.csv):
#   * paper NOT yet coded by either coder -> FULL REFRESH: re-query every
#     dimension, so newly-added subcategories are picked up even where a model
#     answer already exists (a human hasn't compared against it yet).
#   * paper already coded by a coder       -> ABSENT-ONLY: fill just the
#     dimensions whose category cell is blank (e.g. software_lifecycle, added
#     after methodology was retired); the coded model baseline is left intact so
#     the ICR comparison isn't churned.
# Independently of those regimes, papers NO coder keeps (rejected rs=0 by some
# coder, confirmed rs=1 by none) are skipped by default (--skip-rejected): they
# never enter any goldstandard, so filling their typology dimensions would be
# wasted work. A paper one coder rejects but another confirms is NOT skipped.
# =============================================================================

def _is_blank(v) -> bool:
    """True if a checkpoint cell counts as ABSENT for the gap rule: None, NaN, or
    an empty / 'nan' / 'none' string. Stale or retired present values are NOT
    blank (only absent dimensions are filled — the locked gap rule)."""
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    return str(v).strip().lower() in ("", "nan", "none")


def _missing_dims(row) -> list[str]:
    """The active dimensions whose `<dim>_category` cell is absent in this row."""
    return [d for d in cat.DIMENSIONS if _is_blank(row.get(f"{d}_category"))]


def _is_rse(row) -> bool:
    """True if the paper is labelled research software (gate passed). Only RSE
    papers carry a typology, so non-RSE rows have nothing to fill."""
    return str(row.get("label_research_software")).strip() in ("1", "1.0", "true", "True")


def _archive(path: Path) -> Path:
    """Copy `path` to a fresh .bak/.bakN sibling (a restore point before rewrite)."""
    bak = path.parent / (path.name + ".bak")
    n = 1
    while bak.exists():
        n += 1
        bak = path.parent / (path.name + f".bak{n}")
    shutil.copy2(path, bak)
    return bak


def _write_checkpoint(df, path: Path, columns) -> None:
    """Crash-safe write of the checkpoint DataFrame: serialize to a sibling .tmp
    file then os.replace() it over the target. os.replace is atomic on the same
    filesystem, so an interruption mid-write leaves the previous checkpoint intact
    rather than a half-written / truncated CSV. Used for the periodic flushes in
    fill-missing so a long run's progress survives a kill."""
    tmp = path.parent / (path.name + ".tmp")
    df.to_csv(tmp, columns=columns, index=False)
    os.replace(tmp, path)


def _coded_paper_ids(goldstandard_dir: Path) -> set[str]:
    """Paper ids any coder has already coded — the union of the `id` column of
    every goldstandard/coding_*.csv. A paper appearing here has a human baseline
    that fill-missing must not churn (absent-only); papers absent here are still
    uncoded and may be fully refreshed."""
    ids: set[str] = set()
    if not goldstandard_dir.is_dir():
        return ids
    for f in sorted(goldstandard_dir.glob("coding_*.csv")):
        try:
            col = pd.read_csv(f, usecols=["id"], dtype={"id": str})["id"]
        except (pd.errors.EmptyDataError, ValueError, KeyError):
            continue
        ids.update(col.dropna().astype(str).str.strip())
    return ids


def _rejected_paper_ids(goldstandard_dir: Path) -> set[str]:
    """Paper ids fill-missing should skip because NO coder keeps them in their
    goldstandard: rejected (rs=0) by at least one coder AND confirmed (rs=1) by
    none. Filling their typology dimensions would be wasted work.

    The confirmed-by-none guard matters in a multi-coder (ICR) study: the model
    checkpoint is SHARED, but each coder keeps their own goldstandard slice. A
    paper one coder rejects but another confirms must stay fillable — otherwise
    the confirming coder loses the model suggestion for it. (Unioning rejections
    across coders, the previous behaviour, wrongly skipped those papers.)

    Decisions are read from two source pairs, all tolerant of missing / empty /
    oddly-shaped files:
      * coding_*.csv rows whose dimension == `label_research_software`:
        final_category 0/false -> a rejection, 1/true -> a confirmation
        (build_goldstandard writes one such row per coded paper).
      * gold_human_rejected_*.csv / gold_human_confirmed_*.csv (the explicit
        partition lists `topup` emits)."""
    rejected: set[str] = set()
    confirmed: set[str] = set()
    if not goldstandard_dir.is_dir():
        return set()
    falsey = {"0", "0.0", "false", "no", ""}
    truthy = {"1", "1.0", "true", "yes"}
    for f in sorted(goldstandard_dir.glob("coding_*.csv")):
        try:
            df = pd.read_csv(f, usecols=["id", "dimension", "final_category"],
                             dtype=str, keep_default_na=False)
        except (pd.errors.EmptyDataError, ValueError, KeyError):
            continue
        rs_rows = df[df["dimension"].astype(str).str.strip() == "label_research_software"]
        fc = rs_rows["final_category"].astype(str).str.strip().str.lower()
        rejected.update(rs_rows.loc[fc.isin(falsey), "id"].dropna().astype(str).str.strip())
        confirmed.update(rs_rows.loc[fc.isin(truthy), "id"].dropna().astype(str).str.strip())
    for f in sorted(goldstandard_dir.glob("gold_human_rejected_*.csv")):
        try:
            col = pd.read_csv(f, usecols=["id"], dtype={"id": str})["id"]
        except (pd.errors.EmptyDataError, ValueError, KeyError):
            continue
        rejected.update(col.dropna().astype(str).str.strip())
    for f in sorted(goldstandard_dir.glob("gold_human_confirmed_*.csv")):
        try:
            col = pd.read_csv(f, usecols=["id"], dtype={"id": str})["id"]
        except (pd.errors.EmptyDataError, ValueError, KeyError):
            continue
        confirmed.update(col.dropna().astype(str).str.strip())
    # Skip only papers no coder keeps: rejected somewhere, confirmed nowhere.
    skip = rejected - confirmed
    skip.discard("")
    return skip


def run_fill_missing(pdfs, lni_folder, args, checkpoint_path, suggestions_path,
                     client, rate_limiter, system_prompt) -> None:
    """Incrementally update the gold checkpoint per paper (see the section header):
    by DEFAULT papers no coder has coded yet are FULLY re-queried (all dimensions,
    picking up new subcategories even where a model answer exists); papers a coder
    has already coded get only their ABSENT dimensions filled, so their coded
    baseline / ICR comparison is never churned. With --absent-only EVERY paper
    (uncoded ones too) is held to absent-only: only genuinely-blank cells are
    filled and existing answers are kept -- the fast way to finish the gaps.
    Non-RSE rows and papers not in the checkpoint are skipped. Unless
    --no-skip-rejected is given, papers NO coder keeps (rejected rs=0 by some
    coder, confirmed by none) are also skipped — they never enter any goldstandard, so
    filling their typology dimensions is wasted work."""
    if not checkpoint_path.exists():
        raise SystemExit(
            f"--fill-missing needs an existing gold checkpoint to update, but none "
            f"was found at:\n  {checkpoint_path}\nRun the gold annotation first.")

    # Read the whole checkpoint as strings (no NaN coercion) so existing cells are
    # preserved verbatim and the blank test sees real emptiness, not pandas NaN.
    df = pd.read_csv(checkpoint_path, dtype=str, keep_default_na=False)

    # A schema change may have ADDED columns the old checkpoint never had (the new
    # dimension's <dim>_* cells). Ensure every canonical column exists so the gap
    # detector finds them blank rather than KeyError-ing.
    extra = [c for c in df.columns if c not in CHECKPOINT_COLUMNS]
    for col in CHECKPOINT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[CHECKPOINT_COLUMNS + extra]

    # One row per paper id. Drop accidental duplicates defensively (keep first) so
    # df.at[pid, ...] addresses a single cell, not a Series.
    df = df.drop_duplicates(subset="id", keep="first").set_index("id", drop=False)

    # Papers a human has already coded keep the absent-only regime so their model
    # baseline stays comparable; uncoded papers are fully refreshed by default
    # unless --absent-only holds everyone to gap-fill.
    coded_ids = _coded_paper_ids(DATA_ROOT / "goldstandard")
    if getattr(args, "absent_only", False):
        print(f"  --absent-only: EVERY paper (incl. {len(coded_ids)} coded) fills only "
              f"its blank dimension cells; no full refresh of uncoded papers.")
    else:
        print(f"  default: {len(coded_ids)} coded paper(s) -> absent-only; uncoded gold "
              f"papers -> FULL refresh (all dimensions re-queried). Pass --absent-only "
              f"to fill only blank cells everywhere.")

    # Papers no coder keeps (rejected rs=0 by some coder, confirmed by none) never
    # enter any goldstandard; skip them by default so we don't spend the model
    # filling dimensions for them. A paper one coder rejects but another confirms
    # is kept (its confirming coder still needs the model suggestion).
    skip_rejected = getattr(args, "skip_rejected", True)
    rejected_ids = _rejected_paper_ids(DATA_ROOT / "goldstandard") if skip_rejected else set()
    if skip_rejected:
        print(f"  {len(rejected_ids)} paper(s) rejected by all coders (confirmed by "
              f"none) -> skipped (disable with --no-skip-rejected).")

    # Back up the pre-fill checkpoint ONCE, up front, so the restore point captures
    # the true starting state even though we now rewrite the checkpoint repeatedly
    # (periodic flushes below). Subsequent flushes overwrite checkpoint_path in place
    # via an atomic temp+rename; the .bak keeps the original.
    bak = _archive(checkpoint_path)
    flush_every = max(1, getattr(args, "checkpoint_every", 5) or 5)
    n_since_flush = 0
    out_columns = CHECKPOINT_COLUMNS + extra

    temperature, seed, top_p = 0, 42, 1.0
    n_fill = n_skip_done = n_skip_notrse = n_skip_nopaper = n_err = 0
    n_refresh = n_skip_rejected = 0
    papers_with_new = 0
    pbar = tqdm(pdfs, desc="Filling gold dims", unit="paper")
    for pdf_path in pbar:
        paper = pdf_to_paper(pdf_path, lni_folder, args.max_text_chars)
        pid = paper["id"]

        if pid not in df.index:
            n_skip_nopaper += 1
            pbar.set_postfix_str(f"not in gold | fill {n_fill} err {n_err}")
            continue
        if pid in rejected_ids:
            n_skip_rejected += 1
            pbar.set_postfix_str(f"human-rejected | fill {n_fill} err {n_err}")
            continue
        row = df.loc[pid]
        if not _is_rse(row):
            n_skip_notrse += 1
            pbar.set_postfix_str(f"not RSE | fill {n_fill} err {n_err}")
            continue

        # By default papers no coder has touched yet get a FULL refresh (every
        # dimension re-queried, so new subcategories are reconsidered even where a
        # model answer exists); coded papers get only their absent dimensions, so
        # their coded baseline / ICR comparison is never churned. --absent-only
        # holds EVERYONE to absent-only: just finish the genuinely-blank cells.
        coded = pid in coded_ids
        refresh = (not coded) and not getattr(args, "absent_only", False)
        dims = list(cat.DIMENSIONS) if refresh else _missing_dims(row)
        if not dims:
            n_skip_done += 1
            pbar.set_postfix_str(f"complete | fill {n_fill} err {n_err}")
            continue
        if paper["extraction_failed"]:
            n_err += 1
            pbar.set_postfix_str(f"extract fail | fill {n_fill} err {n_err}")
            continue

        cells = classify_paper_dims(client, paper, args.model, dims, rate_limiter,
                                    system_prompt, temperature, seed, top_p,
                                    max_tokens=(args.max_tokens or None))
        if cells.get("llm_error"):
            n_err += 1
            pbar.set_postfix_str(f"llm err | fill {n_fill} err {n_err}")
            continue

        # Merge ONLY the requested dimensions' cells; never touch other columns
        # (label_research_software and metadata stay as they are).
        for col, val in cells.items():
            df.at[pid, col] = "" if val is None else str(val)
        if log_new_suggestions(pid, cells, suggestions_path):
            papers_with_new += 1
        n_fill += 1
        if refresh:
            n_refresh += 1
        mode = "refresh-all" if refresh else "fill-missing"
        pbar.set_postfix_str(
            f"{mode} {','.join(dims)} | fill {n_fill} err {n_err}")

        # Periodic crash-safe flush: persist progress every `flush_every` filled
        # papers so an interrupted long run resumes from the last flush instead of
        # losing everything. The write is atomic (temp + rename).
        n_since_flush += 1
        if n_since_flush >= flush_every:
            _write_checkpoint(df, checkpoint_path, out_columns)
            n_since_flush = 0

    # Final flush (also covers a tail of < flush_every papers since the last one).
    _write_checkpoint(df, checkpoint_path, out_columns)
    step(f"Done - updated {n_fill} paper(s) ({n_refresh} full-refresh uncoded / "
         f"{n_fill - n_refresh} absent-only coded); errors {n_err}; "
         f"skipped {n_skip_done} complete / {n_skip_notrse} non-RSE / "
         f"{n_skip_rejected} human-rejected / {n_skip_nopaper} not-in-gold")
    print(f"  Checkpoint updated: {checkpoint_path}")
    print(f"  Backup of the pre-fill checkpoint: {bak.name}")
    print(f"  Papers with >=1 new-category suggestion this run: {papers_with_new}")


def run_preview_prompt(args) -> None:
    """Print every prompt the annotation steps send to the model -- WITHOUT a
    corpus, a PDF, or a single SAIA token. Lets you inspect/shrink the prompts
    before paying for a run.

    Three prompts are shown, each with a character + approx-token size so you can
    see what dominates:
      * SYSTEM prompt                         (sent on every call)
      * FULL annotation USER prompt           (a-gold / full / confirm: all dims)
      * TARGETED fill USER prompt             (--fill-missing: only some dims)

    The paper-body fields are replaced with bracketed placeholders, so the output
    is the STATIC scaffolding (instructions + category catalogue). At run time the
    real paper text is spliced in, capped at --max_text_chars characters."""
    system_prompt, user_prompt_template = load_prompt_template(args.prompt_template)

    placeholder = {
        "title": "‹PAPER-TITEL›",
        "authors": "‹AUTOREN›",
        "year": "‹JAHR›",
        "abstract": "‹ABSTRACT›",
        "text": f"‹VOLLTEXT — zur Laufzeit eingesetzt, max. {args.max_text_chars} Zeichen›",
        "references": "‹LITERATURVERZEICHNIS›",
    }
    dims = list(cat.DIMENSIONS)

    full_user = fill_user_prompt(user_prompt_template, placeholder)
    fill_user = build_fill_user_prompt(placeholder, dims)
    cat_block = cat.render_categories_block()
    guide_block = cat.render_category_guidance_block()

    def approx_tokens(s: str) -> int:
        return round(len(s) / 4)

    sep = "=" * 78

    def section(title: str, body: str) -> str:
        return (f"{sep}\n=== {title}  "
                f"[{len(body):,} chars / ~{approx_tokens(body):,} tokens]\n{sep}\n"
                f"{body}\n")

    out = []
    out.append(f"PROMPT PREVIEW  (template: {Path(args.prompt_template).name})")
    out.append(f"  No SAIA call is made. The variable per-paper body is omitted; "
               f"its real text is capped at --max_text_chars={args.max_text_chars}.")
    out.append("")
    out.append("SIZE BREAKDOWN (static scaffolding only; paper body excluded)")
    rows = [
        ("system prompt", system_prompt),
        ("full annotation user prompt", full_user),
        ("  of which: category catalogue block", cat_block),
        ("  of which: curated guidance block", guide_block),
        (f"targeted fill user prompt (all {len(dims)} dims)", fill_user),
    ]
    for label, body in rows:
        out.append(f"  {label:<46} {len(body):>7,} chars  ~{approx_tokens(body):>6,} tok")
    out.append(f"  {'dimensions':<46} {len(dims):>7} ({', '.join(dims)})")
    out.append("  Note: a real fill call asks only about a paper's MISSING dims, so")
    out.append("  the targeted prompt is usually smaller than the all-dims size above.")
    out.append("")
    out.append(section("SYSTEM PROMPT (every call)", system_prompt))
    out.append(section("FULL ANNOTATION USER PROMPT (a-gold / full / confirm)", full_user))
    out.append(section(f"TARGETED FILL USER PROMPT (--fill-missing, all {len(dims)} dims)",
                       fill_user))
    text = "\n".join(out)

    results_dir = DATA_ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    preview_path = results_dir / "prompt_preview.txt"
    preview_path.write_text(text, encoding="utf-8")

    print(text)
    print(f"\n[written] {preview_path}")


def run_dry(pdfs, lni_folder, max_text_chars, system_prompt,
            user_prompt_template, results_dir, folder_name) -> None:
    """Offline dry run: extract each PDF, build its prompt, and write an
    extraction-quality report plus one sample prompt. No API calls, no token.

    The report contains only derived metadata (id, title, authors, text length,
    flags) — NOT the paper body — so it is safe to share for verification.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    report_path = results_dir / f"extraction_report_{folder_name}.csv"
    sample_prompt_path = results_dir / f"sample_prompt_{folder_name}.txt"

    rows = []
    first_prompt_written = False
    for pdf_path in tqdm(pdfs, desc="Dry-run extraction"):
        paper = pdf_to_paper(pdf_path, lni_folder, max_text_chars)
        rows.append({
            "id": paper["id"],
            "filename": paper["filename"],
            "title": paper["title"],
            "authors": paper["authors"],
            "has_abstract": bool(paper["abstract"]),
            "title_len": len(paper["title"] or ""),
            "text_len": len(paper["text"] or ""),
            "references_len": len(paper["references"] or ""),
            "extraction_failed": paper["extraction_failed"],
        })
        if not first_prompt_written and not paper["extraction_failed"]:
            filled = fill_user_prompt(user_prompt_template, paper)
            sample_prompt_path.write_text(
                "=== SYSTEM PROMPT ===\n" + system_prompt +
                "\n\n=== USER PROMPT (first OK paper) ===\n" + filled,
                encoding="utf-8")
            first_prompt_written = True

    df = pd.DataFrame(rows)
    df.to_csv(report_path, index=False)
    n_fail = int(df["extraction_failed"].sum())
    print(f"\nDry run complete. {len(df)} PDF(s), {n_fail} extraction failure(s).")
    print(f"Extraction report : {report_path}")
    print(f"Sample prompt     : {sample_prompt_path}")
    print("\nSafe to share the report CSV + sample prompt for verification "
          "(no paper body, only derived metadata).")


# =============================================================================
# Slow-mount mitigation: scan with progress, copy selected PDFs to fast disc
# =============================================================================

def step(msg: str) -> None:
    """Announce a major pipeline step as a clear banner between the tqdm bars,
    so the terminal always shows which phase is running next."""
    print(f"\n==> {msg}", flush=True)


def find_pdfs(lni_folder: Path) -> list[Path]:
    """Enumerate the corpus PDFs using its known shallow layout.

    The corpus root holds one volume folder per proceedings (lni13, lni132, ...
    plus some named conference folders), and every paper PDF sits DIRECTLY inside
    its volume folder, two path parts deep:

        <corpus_root>/<volume>/<paper>.pdf

    A recursive `rglob("*.pdf")` over the whole tree on a slow mounted disc walks
    every nested directory and runs silently for a long time (the run looks hung).
    Instead we list the volume folders once and do a single NON-recursive
    `glob("*.pdf")` per volume. tqdm then reports progress per volume, and the
    number of PDFs found in each volume is exactly that volume's stratum size for
    the proportional stratified sample downstream (`volume_under` keys on the same
    top-level folder).
    """
    print(f"Scanning {lni_folder} for volume folders (reads the mounted disc)...",
          flush=True)
    volumes = sorted(d for d in lni_folder.iterdir() if d.is_dir())
    pdfs: list[Path] = []
    pbar = tqdm(volumes, desc="Scanning volumes", unit="vol")
    for vol in pbar:
        pdfs.extend(vol.glob("*.pdf"))
        pbar.set_postfix_str(f"{len(pdfs)} pdfs")
    pdfs.sort()
    print(f"Found {len(pdfs)} PDF(s) across {len(volumes)} volume folder(s).",
          flush=True)
    return pdfs


def stage_pdfs(pdfs: list[Path], corpus_root: Path, stage_root: Path) -> list[Path]:
    """Copy the SELECTED PDFs to a fast local dir before extraction/annotation.

    Each PDF keeps its path relative to `corpus_root`, so the paper id and the
    LNI-volume stratum are identical to the full corpus — downstream code just
    uses `stage_root` as its folder. Idempotent: a destination of the same size
    is skipped, so an interrupted copy resumes. The slow mount is then touched
    only during this clearly-labelled copy phase; everything after reads locally.
    """
    corpus_root = corpus_root.resolve()
    stage_root = stage_root.resolve()
    # Safety: the corpus is read-only. Never copy into (or over) the corpus tree.
    if (stage_root == corpus_root or stage_root.is_relative_to(corpus_root)
            or corpus_root.is_relative_to(stage_root)):
        raise SystemExit(
            f"Refusing to stage: {stage_root} overlaps the corpus {corpus_root}. "
            f"Choose a --stage_dir outside the corpus.")
    stage_root.mkdir(parents=True, exist_ok=True)

    local: list[Path] = []
    copied = skipped = failed = 0
    copied_bytes = 0
    t_start = time.perf_counter()
    pbar = tqdm(pdfs, desc="Copying PDFs to fast disc", unit="pdf")
    for pdf in pbar:
        rel = pdf.resolve().relative_to(corpus_root)
        dst = stage_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            src_size = pdf.stat().st_size  # slow-mount stat
            if dst.exists() and dst.stat().st_size == src_size:
                skipped += 1
            else:
                shutil.copy2(pdf, dst)  # slow-mount read -> fast-disc write
                copied += 1
                copied_bytes += src_size
            local.append(dst)
        except OSError as e:
            failed += 1
            tqdm.write(f"  copy failed for {rel}: {e}")
        # Live throughput so it is obvious the time goes into the mounted-disc read.
        elapsed = time.perf_counter() - t_start
        mb = copied_bytes / 1e6
        mbps = mb / elapsed if elapsed > 0 else 0.0
        pbar.set_postfix_str(f"{mb:6.0f} MB @ {mbps:4.1f} MB/s | {rel.as_posix()[-30:]}")
    elapsed = time.perf_counter() - t_start
    mb = copied_bytes / 1e6
    mbps = mb / elapsed if elapsed > 0 else 0.0
    msg = (f"Staged {copied} new ({mb:.0f} MB in {elapsed:.0f}s, {mbps:.1f} MB/s), "
           f"{skipped} already present")
    if failed:
        msg += f", {failed} FAILED"
    print(f"{msg} -> {stage_root}", flush=True)
    return local


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Annotate LNI PDFs with RSE typology via the KISSKI SAIA API.")
    parser.add_argument("--lni_folder", default=None,
                        help="Folder containing LNI publication PDFs (searched recursively). "
                             "Required for every mode except --preview-prompt.")
    parser.add_argument("--model", default="mistral-large-3-675b-instruct-2512",
                        help="SAIA model name.")
    parser.add_argument("--run", default="run_1", help="Run identifier (e.g. run_1).")
    parser.add_argument("--prompt_template", default=str(DEFAULT_PROMPT),
                        help="Path to the prompt template markdown.")
    parser.add_argument("--saia_token", default=None,
                        help="SAIA API key (overrides SAIA_API_KEY env var).")
    parser.add_argument("--saia_endpoint", default=None,
                        help="SAIA API base URL (overrides SAIA_API_ENDPOINT env var).")
    parser.add_argument("--max_text_chars", type=int, default=40000,
                        help="Truncate extracted main text to this many characters.")
    parser.add_argument("--max_tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help="Cap the completion length (default %(default)s; a "
                             "complete answer is ~1350 tokens max). 0 = uncapped.")
    parser.add_argument("--test", action="store_true",
                        help="Process a stratified sample of 5 PDFs (proportional draw "
                             "across LNI volumes; equivalent to --sample 5).")
    parser.add_argument("--sample", type=int, default=None,
                        help="Process a STRATIFIED sample of this many PDFs, using the "
                             "LNI volume folders as strata (proportional, largest-remainder "
                             "allocation; reproducible via --shuffle_seed).")
    parser.add_argument("--no_shuffle", action="store_true",
                        help="For full runs only: disable the deterministic cross-volume "
                             "shuffle; process PDFs in sorted (volume-then-filename) order. "
                             "Ignored when --test/--sample request a stratified sample.")
    parser.add_argument("--shuffle_seed", type=int, default=42,
                        help="Seed for the deterministic shuffle / stratified draw "
                             "(reproducible runs).")
    parser.add_argument("--dry_run", action="store_true",
                        help="Offline: extract PDFs + build prompts, write an extraction "
                             "report and one sample prompt, make NO API calls (no token needed).")
    parser.add_argument("--preview-prompt", dest="preview_prompt", action="store_true",
                        help="Print every prompt the annotation steps send to the model "
                             "(system + full annotation + targeted fill) with their "
                             "char/token sizes, then exit. No corpus, no PDF and no SAIA "
                             "token needed; also written to results/prompt_preview.txt. "
                             "Use to inspect/shrink the prompts before paying for a run.")
    parser.add_argument("--no_stage", action="store_true",
                        help="Do NOT copy the selected PDFs to a fast local dir first; read "
                             "them directly from --lni_folder. By default the selected PDFs "
                             "are staged to .workingset/ (with a progress bar) to avoid "
                             "repeated slow-mount reads during extraction.")
    parser.add_argument("--stage_dir", default=None,
                        help="Where to stage the selected PDFs (default: "
                             ".workingset/_stage_<folder>). Must be outside the corpus.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-annotate ALL selected papers even if a checkpoint "
                             "already exists. The existing checkpoint AND the "
                             "new-suggestions CSV are archived to .bak files first, so "
                             "the run starts fresh (no skipped papers, no duplicate "
                             "rows). Default: resume - skip papers already checkpointed.")
    parser.add_argument("--fill-missing", dest="fill_missing", action="store_true",
                        help="Incrementally fill ONLY the typology dimensions whose "
                             "category cell is absent in the existing checkpoint "
                             "(one targeted SAIA call per paper, asking only about "
                             "the missing dimension[s]). Existing answers, non-RSE "
                             "rows and papers not in the checkpoint are left as-is; "
                             "the checkpoint is backed up before rewrite. Use after a "
                             "schema change adds a dimension (e.g. software_lifecycle).")
    parser.add_argument("--skip-rejected", dest="skip_rejected",
                        action=argparse.BooleanOptionalAction, default=True,
                        help="(fill-missing only) Skip papers NO coder keeps: "
                             "rejected as not research software (rs=0) by some coder "
                             "and confirmed by none (read from goldstandard/coding_*.csv "
                             "or gold_human_rejected_*.csv / gold_human_confirmed_*.csv); "
                             "they never enter any goldstandard. A paper one coder "
                             "rejects but another confirms is kept. On by default; pass "
                             "--no-skip-rejected to fill them anyway.")
    parser.add_argument("--absent-only", dest="absent_only", action="store_true",
                        help="(fill-missing only) Fill ONLY dimensions whose category "
                             "cell is blank, for EVERY paper -- including ones no coder "
                             "has touched yet. Without this flag uncoded papers are fully "
                             "re-annotated (all dimensions, picking up new subcategories); "
                             "with it a resume only fills the genuinely-missing cells "
                             "(much faster, but uncoded papers keep their existing answers "
                             "for dimensions that already have one).")
    parser.add_argument("--checkpoint-every", dest="checkpoint_every", type=int,
                        default=5, metavar="N",
                        help="(fill-missing only) Flush the checkpoint to disk after "
                             "every N papers that get filled, so a long run is "
                             "crash-safe and resumable (default 5). The write is "
                             "atomic (temp file + rename). Pass 1 to flush after every "
                             "paper, or a larger N for fewer disk writes. A final flush "
                             "always happens when the run completes.")
    parser.add_argument("--checkpoint", default=None,
                        help="Explicit path to the annotations checkpoint CSV to "
                             "read/update, OVERRIDING the folder-name-derived tag. "
                             "Needed when the live checkpoint's tag differs from the "
                             "PDF folder name -- e.g. fill-missing the confirmed gold "
                             "pool (.workingset/gold_confirmed) whose checkpoint is "
                             "tagged 'goldconfirm'. Mirrors build_goldstandard "
                             "--annotations so both target the same file.")
    args = parser.parse_args()

    # --preview-prompt is corpus-free: build and print the prompts, then exit
    # BEFORE any scan/stage. No --lni_folder, no PDFs, no SAIA token needed.
    if args.preview_prompt:
        run_preview_prompt(args)
        return

    if args.fill_missing and args.overwrite:
        raise SystemExit("--fill-missing and --overwrite are mutually exclusive: "
                         "fill-missing preserves existing answers, overwrite discards them.")

    if not args.lni_folder:
        raise SystemExit("--lni_folder is required (except for --preview-prompt).")
    lni_folder = Path(args.lni_folder).resolve()
    if not lni_folder.is_dir():
        raise SystemExit(f"--lni_folder is not a directory: {lni_folder}")
    # The corpus folder name identifies the run (tag, checkpoint, report names).
    # Capture it now: if we stage onto a fast disc below, `lni_folder` is
    # repointed at the stage dir, but the run identity must stay the corpus's.
    corpus_name = lni_folder.name

    step("Step 1/5 - Scan the corpus for PDF files")
    pdfs = find_pdfs(lni_folder)
    if not pdfs:
        raise SystemExit(f"No PDFs found under {lni_folder}")
    n_total = len(pdfs)
    vol_of = volume_under(lni_folder)
    # Single O(n) pass over the PDFs to count per-volume sizes. The previous
    # comprehension was O(volumes * pdfs) (~4.5M calls for this corpus) and each
    # vol_of() call hit the slow mount via Path.resolve() -- minutes of stalling.
    sizes = dict(Counter(vol_of(p) for p in pdfs))
    n_volumes = len(sizes)

    sample_n = 5 if args.test else args.sample
    if sample_n:
        step(f"Step 2/5 - Select a stratified sample of {sample_n} paper(s)")
        # STRATIFIED sample: the volume folders are the strata, drawn with
        # proportional (largest-remainder) allocation. Reproducible via the seed.
        pdfs, alloc = stratified_sample(pdfs, sample_n, seed=args.shuffle_seed, group_fn=vol_of)
        print(f"  Selected {len(pdfs)} of {n_total} PDF(s) across {n_volumes} volume(s) "
              f"(seed={args.shuffle_seed}).")
        print(f"  Allocation per volume: {format_allocation(alloc, sizes)}")
    else:
        step(f"Step 2/5 - Select ALL {n_total} paper(s) (no --sample limit)")
        # Full run: deterministic cross-volume shuffle so any partial/resumed run
        # spans many volumes rather than the first volume alphabetically.
        if not args.no_shuffle:
            random.Random(args.shuffle_seed).shuffle(pdfs)
        order = "sorted" if args.no_shuffle else f"shuffled (seed={args.shuffle_seed})"
        print(f"  Processing {len(pdfs)} PDF(s) across {n_volumes} volume(s) [{order}].")

    # Stage the SELECTED PDFs onto a fast local disc (default; --no_stage opts out).
    # The slow mount is then touched only during this clearly-labelled copy phase;
    # all extraction below reads locally. Staged paths mirror the corpus layout, so
    # paper ids and LNI-volume strata are unchanged once `lni_folder` is repointed.
    if not args.no_stage:
        stage_dir = (Path(args.stage_dir).resolve() if args.stage_dir
                     else DEFAULT_WORKROOT / f"_stage_{corpus_name}")
        step(f"Step 3/5 - Copy the {len(pdfs)} selected PDF(s) to a fast local disc")
        print("  One-time copy off the mounted corpus; re-runs skip files already staged.")
        pdfs = stage_pdfs(pdfs, corpus_root=lni_folder, stage_root=stage_dir)
        lni_folder = stage_dir
    else:
        step("Step 3/5 - Skip staging; read PDFs directly from the corpus (--no_stage)")

    step(f"Step 4/5 - Load the prompt template ({Path(args.prompt_template).name})")
    system_prompt, user_prompt_template = load_prompt_template(args.prompt_template)
    prompt_name = Path(args.prompt_template).stem

    # Output paths
    results_dir = DATA_ROOT / "results"
    checkpoint_dir = results_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{corpus_name}_{args.model}_{prompt_name}_{args.run}"
    checkpoint_path = checkpoint_dir / f"annotations_{tag}_checkpoint.csv"
    suggestions_path = results_dir / f"new_category_suggestions_{tag}.csv"
    # --checkpoint overrides the folder-derived path: the PDFs come from
    # --lni_folder but the checkpoint we read/update is the named one (whose tag
    # may not match the folder, e.g. gold_confirmed PDFs -> 'goldconfirm' tag).
    # Re-derive the suggestions path from the checkpoint's own tag so both stay
    # paired.
    if args.checkpoint:
        checkpoint_path = Path(args.checkpoint).resolve()
        ck_name = checkpoint_path.name
        if ck_name.startswith("annotations_") and ck_name.endswith("_checkpoint.csv"):
            ck_tag = ck_name[len("annotations_"):-len("_checkpoint.csv")]
        else:
            ck_tag = tag
        suggestions_path = results_dir / f"new_category_suggestions_{ck_tag}.csv"
        print(f"[config] checkpoint OVERRIDE (--checkpoint): tag '{ck_tag}'")
    print(f"[config] data root : {DATA_ROOT}"
          + ("  (in-repo default)" if DATA_ROOT == REPO_ROOT else "  (LNI_DATA_ROOT)"))
    print(f"[config] results   : {results_dir}")
    print(f"[config] checkpoint: {checkpoint_path}")
    print(f"  Results tag: {tag}")

    # --- Dry run: offline extraction + prompt build, no SAIA credentials ---
    if args.dry_run:
        step("Step 5/5 - Dry run: extract PDFs and build prompts, NO API calls")
        run_dry(pdfs, lni_folder, args.max_text_chars, system_prompt,
                user_prompt_template, results_dir, corpus_name)
        return

    step(f"Step 5/5 - Annotate via the SAIA API (model: {args.model})")
    saia_api_key = args.saia_token or os.getenv("SAIA_API_KEY")
    base_url = args.saia_endpoint or os.getenv("SAIA_API_ENDPOINT") or DEFAULT_SAIA_ENDPOINT
    if not saia_api_key:
        raise SystemExit("Missing SAIA token. Set SAIA_API_KEY in .env or pass --saia_token.")
    print(f"  endpoint: {base_url}")

    # --overwrite: archive the existing checkpoint + suggestions CSV so the run
    # re-annotates every paper. Renaming (not deleting) keeps a restore point, and
    # because the originals no longer exist the loop below builds an EMPTY done_ids
    # and writes a fresh header - no skipped papers, no duplicate appended rows.
    if args.overwrite:
        for p in (checkpoint_path, suggestions_path):
            if p.exists():
                bak = p.parent / (p.name + ".bak")
                n = 1
                while bak.exists():
                    n += 1
                    bak = p.parent / (p.name + f".bak{n}")
                p.rename(bak)
                print(f"  --overwrite: archived existing {p.name} -> {bak.name}")

    done_ids: set[str] = set()
    if checkpoint_path.exists():
        # Only the id column is needed to resume. Read it tolerantly: usecols keeps
        # this cheap, and on_bad_lines="skip" means a legacy ragged checkpoint (from
        # before the canonical-columns fix) degrades to re-annotating a few rows
        # instead of crashing the whole run.
        ck = pd.read_csv(checkpoint_path, usecols=["id"], dtype={"id": str},
                         on_bad_lines="skip")
        done_ids = set(ck["id"].dropna().tolist())
        print(f"  resuming: {len(done_ids)} paper(s) already in the checkpoint will be skipped.")

    client = OpenAI(api_key=saia_api_key, base_url=base_url, timeout=300.0)
    rate_limiter = RateLimiter()
    temperature, seed, top_p = 0, 42, 1.0

    # --fill-missing: targeted incremental update of the existing checkpoint (only
    # the absent dimensions per paper). Does not append/resume like the full loop;
    # it rewrites the one-row-per-paper checkpoint in place (after a backup).
    if args.fill_missing:
        run_fill_missing(pdfs, lni_folder, args, checkpoint_path, suggestions_path,
                         client, rate_limiter, system_prompt)
        return

    # The loop: for each selected paper, extract its text then make one SAIA
    # classification call. The bar's postfix shows where time goes per paper.
    print(f"  Looping over {len(pdfs)} selected paper(s): extract PDF text -> 1 SAIA call each.")
    print("  Bar postfix = per-paper extract/api seconds (api avg) and ok/err/skip counts.")

    papers_with_new = 0
    n_ok = n_err = n_skip = 0
    api_times: deque = deque(maxlen=20)  # rolling window -> stable rate estimate
    pbar = tqdm(pdfs, desc="Annotating LNI papers", unit="paper")
    for pdf_path in pbar:
        t0 = time.perf_counter()
        paper = pdf_to_paper(pdf_path, lni_folder, args.max_text_chars)
        t_extract = time.perf_counter() - t0  # PDF read (local now) + parse

        if paper["id"] in done_ids:
            n_skip += 1
            pbar.set_postfix_str(f"skip done | ok {n_ok} err {n_err} skip {n_skip}")
            continue

        if paper["extraction_failed"]:
            flat = {"llm_error": "pdf_extraction_failed", "llm_raw_response": None}
            t_api = 0.0
            n_err += 1
        else:
            t1 = time.perf_counter()
            flat = classify_paper(client, paper, args.model, system_prompt,
                                  user_prompt_template, temperature, seed, top_p, rate_limiter,
                                  max_tokens=(args.max_tokens or None))
            t_api = time.perf_counter() - t1  # SAIA round-trip (incl. retries/backoff)
            api_times.append(t_api)
            if flat.get("llm_error"):
                n_err += 1
            else:
                n_ok += 1
            if log_new_suggestions(paper["id"], flat, suggestions_path):
                papers_with_new += 1

        # Split the per-paper time so it is clear where it goes: PDF extraction
        # vs. the SAIA API call (the API is normally the dominant cost).
        avg_api = sum(api_times) / len(api_times) if api_times else 0.0
        pbar.set_postfix_str(
            f"extract {t_extract:4.1f}s | api {t_api:5.1f}s (avg {avg_api:4.1f}s) "
            f"| ok {n_ok} err {n_err} skip {n_skip}")

        row = {
            "id": paper["id"],
            "source_folder": paper["source_folder"],
            "filename": paper["filename"],
            "rel_path": paper["rel_path"],
            "title": paper["title"],
            "authors": paper["authors"],
            "model": args.model,
            "prompt_template": prompt_name,
            "run": args.run,
            **flat,
        }
        # Force the canonical column set/order so every appended row is the same
        # width (missing fields -> empty); keeps the checkpoint resume-safe.
        pd.DataFrame([row], columns=CHECKPOINT_COLUMNS).to_csv(
            checkpoint_path, mode="a", header=not checkpoint_path.exists(), index=False)

    step(f"Done - annotated ok {n_ok}, errors {n_err}, skipped {n_skip}")
    print(f"  Checkpoint: {checkpoint_path}")
    print(f"  Papers with >=1 new-category suggestion this run: {papers_with_new}")
    if suggestions_path.exists():
        total = len(pd.read_csv(suggestions_path)["id"].unique())
        print(f"  Cumulative papers with new suggestions (notes step 7 target ~100): {total}")


if __name__ == "__main__":
    main()
