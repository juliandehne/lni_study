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
import os
import random
import re
import shutil
import sys
import time
from collections import Counter, deque
from datetime import datetime
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
DEFAULT_PROMPT = REPO_ROOT / "prompts" / "rse_typology_prompt_v1.md"
DEFAULT_WORKROOT = REPO_ROOT / ".workingset"

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
    decoder = json.JSONDecoder()
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
        if dim == "techstack":
            cats = d.get("categories")
            flat[f"{dim}_category"] = ";".join(cats) if isinstance(cats, list) else d.get("category")
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

def classify_paper(client, paper, model, system_prompt, user_prompt_template,
                   temperature, seed, top_p, rate_limiter) -> dict:
    user_prompt = fill_user_prompt(user_prompt_template, paper)

    MAX_RETRIES = 5
    BASE_DELAY = 1.0
    response = None

    for attempt in range(MAX_RETRIES):
        rate_limiter.wait_if_needed()
        try:
            rate_limiter.record()
            response = client.chat.completions.create(
                model=model, temperature=temperature, top_p=top_p, seed=seed,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            break
        except AuthenticationError as e:
            # Bad/expired token affects every call -- stop the whole run now.
            raise SystemExit(f"SAIA authentication failed (check your token): {e}")
        except APITimeoutError:
            # A single call already waited the full client timeout (300s); don't
            # burn 5x that retrying -- record and move on to the next paper.
            tqdm.write(f"id={paper['id']}: timeout after 300s, skipping")
            return {"llm_error": "APITimeoutError", "llm_raw_response": None}
        except (RateLimitError, InternalServerError, APIConnectionError) as e:
            # Transient: 429 rate limit, 5xx server error (e.g. the 500 that used
            # to crash the run), or a network blip. Retry with exp backoff+jitter.
            kind = type(e).__name__
            if attempt == MAX_RETRIES - 1:
                tqdm.write(f"id={paper['id']}: {kind} x{MAX_RETRIES}, giving up on this paper")
                return {"llm_error": f"{kind} x{MAX_RETRIES}: {e}", "llm_raw_response": None}
            backoff = BASE_DELAY * (2 ** attempt)
            wait_s = backoff + backoff * 0.25 * random.random()
            tqdm.write(f"id={paper['id']}: {kind} ({attempt + 1}/{MAX_RETRIES}), "
                       f"retry in {wait_s:.1f}s...")
            time.sleep(wait_s)
        except APIStatusError as e:
            # Other non-retryable HTTP errors (e.g. 400 bad request): record + skip.
            tqdm.write(f"id={paper['id']}: APIStatusError {e.status_code}, skipping paper")
            return {"llm_error": f"APIStatusError {e.status_code}: {e}",
                    "llm_raw_response": None}
        except APIError as e:
            # Catch-all for any other OpenAI-client error so one odd paper can't
            # kill a multi-hour batch.
            tqdm.write(f"id={paper['id']}: {type(e).__name__}, skipping paper")
            return {"llm_error": f"{type(e).__name__}: {e}", "llm_raw_response": None}

    raw_content = response.choices[0].message.content
    try:
        result = extract_json_from_response(raw_content)
        if not isinstance(result, dict):
            return {"llm_error": f"JSON parsed to {type(result).__name__}", "llm_raw_response": raw_content}
        return flatten_annotation(result)
    except json.JSONDecodeError as e:
        tqdm.write(f"id={paper['id']}: {e}")
        return {"llm_error": f"JSON parse error: {e}", "llm_raw_response": raw_content}


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
    parser.add_argument("--lni_folder", required=True,
                        help="Folder containing LNI publication PDFs (searched recursively).")
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
    args = parser.parse_args()

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
    results_dir = REPO_ROOT / "results"
    checkpoint_dir = results_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{corpus_name}_{args.model}_{prompt_name}_{args.run}"
    checkpoint_path = checkpoint_dir / f"annotations_{tag}_checkpoint.csv"
    suggestions_path = results_dir / f"new_category_suggestions_{tag}.csv"
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
                                  user_prompt_template, temperature, seed, top_p, rate_limiter)
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
