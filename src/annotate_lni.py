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
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, APITimeoutError, RateLimitError
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
        except APITimeoutError:
            print(f"id={paper['id']}: timeout after 300s, skipping")
            return {"llm_error": "APITimeoutError", "llm_raw_response": None}
        except RateLimitError as e:
            if attempt == MAX_RETRIES - 1:
                return {"llm_error": f"RateLimitError x{MAX_RETRIES}: {e}", "llm_raw_response": None}
            backoff = BASE_DELAY * (2 ** attempt)
            wait_s = backoff + backoff * 0.25 * random.random()
            print(f"id={paper['id']}: RateLimitError ({attempt + 1}/{MAX_RETRIES}), "
                  f"retry in {wait_s:.1f}s...", flush=True)
            time.sleep(wait_s)

    raw_content = response.choices[0].message.content
    try:
        result = extract_json_from_response(raw_content)
        if not isinstance(result, dict):
            return {"llm_error": f"JSON parsed to {type(result).__name__}", "llm_raw_response": raw_content}
        return flatten_annotation(result)
    except json.JSONDecodeError as e:
        print(f"id={paper['id']}: {e}")
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
    args = parser.parse_args()

    lni_folder = Path(args.lni_folder).resolve()
    if not lni_folder.is_dir():
        raise SystemExit(f"--lni_folder is not a directory: {lni_folder}")

    pdfs = sorted(lni_folder.rglob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found under {lni_folder}")
    n_total = len(pdfs)
    vol_of = volume_under(lni_folder)
    sizes = {v: sum(1 for p in pdfs if vol_of(p) == v)
             for v in {vol_of(p) for p in pdfs}}
    n_volumes = len(sizes)

    sample_n = 5 if args.test else args.sample
    if sample_n:
        # STRATIFIED sample: the LNI volume folders are the strata, drawn with
        # proportional (largest-remainder) allocation. Reproducible via the seed.
        pdfs, alloc = stratified_sample(pdfs, sample_n, seed=args.shuffle_seed, group_fn=vol_of)
        print(f"Found {n_total} PDF(s) across {n_volumes} volume(s) under {lni_folder}; "
              f"stratified sample of {len(pdfs)} (seed={args.shuffle_seed}).")
        print(f"  Allocation per volume: {format_allocation(alloc, sizes)}")
    else:
        # Full run: deterministic cross-volume shuffle so any partial/resumed run
        # spans many LNI volumes rather than the first volume alphabetically.
        if not args.no_shuffle:
            random.Random(args.shuffle_seed).shuffle(pdfs)
        order = "sorted" if args.no_shuffle else f"shuffled (seed={args.shuffle_seed})"
        print(f"Found {n_total} PDF(s) across {n_volumes} volume(s) under {lni_folder} "
              f"[{order}]; processing {len(pdfs)}.")

    system_prompt, user_prompt_template = load_prompt_template(args.prompt_template)
    prompt_name = Path(args.prompt_template).stem

    # Output paths
    results_dir = REPO_ROOT / "results"
    checkpoint_dir = results_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{lni_folder.name}_{args.model}_{prompt_name}_{args.run}"
    checkpoint_path = checkpoint_dir / f"annotations_{tag}_checkpoint.csv"
    suggestions_path = results_dir / f"new_category_suggestions_{tag}.csv"

    # --- Dry run: offline extraction + prompt build, no SAIA credentials ---
    if args.dry_run:
        run_dry(pdfs, lni_folder, args.max_text_chars, system_prompt,
                user_prompt_template, results_dir, lni_folder.name)
        return

    saia_api_key = args.saia_token or os.getenv("SAIA_API_KEY")
    base_url = args.saia_endpoint or os.getenv("SAIA_API_ENDPOINT") or DEFAULT_SAIA_ENDPOINT
    if not saia_api_key:
        raise SystemExit("Missing SAIA token. Set SAIA_API_KEY in .env or pass --saia_token.")
    print(f"SAIA endpoint: {base_url}")

    done_ids: set[str] = set()
    if checkpoint_path.exists():
        done_ids = set(pd.read_csv(checkpoint_path, dtype={"id": str})["id"].tolist())
        print(f"Checkpoint: {len(done_ids)} already annotated.")

    client = OpenAI(api_key=saia_api_key, base_url=base_url, timeout=300.0)
    rate_limiter = RateLimiter()
    temperature, seed, top_p = 0, 42, 1.0

    papers_with_new = 0
    for pdf_path in tqdm(pdfs, desc="Annotating LNI papers"):
        paper = pdf_to_paper(pdf_path, lni_folder, args.max_text_chars)
        if paper["id"] in done_ids:
            continue

        if paper["extraction_failed"]:
            flat = {"llm_error": "pdf_extraction_failed", "llm_raw_response": None}
        else:
            flat = classify_paper(client, paper, args.model, system_prompt,
                                  user_prompt_template, temperature, seed, top_p, rate_limiter)
            if log_new_suggestions(paper["id"], flat, suggestions_path):
                papers_with_new += 1

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
        pd.DataFrame([row]).to_csv(
            checkpoint_path, mode="a", header=not checkpoint_path.exists(), index=False)

    print(f"\nDone. Checkpoint: {checkpoint_path}")
    print(f"Papers with >=1 new-category suggestion this run: {papers_with_new}")
    if suggestions_path.exists():
        total = len(pd.read_csv(suggestions_path)["id"].unique())
        print(f"Cumulative papers with new suggestions (notes step 7 target ~100): {total}")


if __name__ == "__main__":
    main()
