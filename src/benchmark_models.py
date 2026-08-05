r"""
benchmark_models.py — the "three-fold test": which SAIA model codes most like our humans?

The final study annotates hundreds of papers with ONE model. Which one that is has
so far been a pin in `preflight.DEFAULT_MODEL` (chosen for availability, not for
accuracy). This step decides it empirically: every candidate model annotates the
papers the humans have already coded by hand, is scored against that goldstandard,
and the winner is written to a file the final study reads.

  goldstandard/coding_<coder>.csv   (human truth)
              +                          -> results/model_selection/model_selection.json
  .workingset/gold_confirmed/*.pdf  (the same papers)        (the winner)
              x  N candidate models                          -> ...model_selection.md
                                                             -> ...model_scores.csv
                                                             -> ...predictions_<model>.csv

WHAT "THREE-FOLD" MEANS HERE
    Nothing is trained, so this is not cross-validation in the fitting sense. Each
    model annotates each gold paper exactly ONCE; the gold set is then split into
    `--folds` (default 3) disjoint, gate-stratified folds and every model is scored
    SEPARATELY on each fold. The point is stability: a model that wins on all three
    thirds of the goldstandard is genuinely better, whereas a model that wins overall
    on the strength of one lucky fold is a coin toss. The report therefore carries
    both the mean score and the per-fold spread + fold wins, and ties are broken
    toward the model that won more folds and varied less.

WHAT IS SCORED
    gate       label_research_software over every human-DECIDED paper (rs 0 or 1):
               macro-F1, so a model that says "yes" to everything cannot win by
               riding the base rate.
    typology   the five dimensions, over the human-ACCEPTED papers (rs = 1) only —
               the typology only describes papers that contain research software:
                 single-valued (research_position)  -> accuracy (exact match)
                 multi-valued  (the other four)     -> micro-F1 over the label sets,
                                                       plus mean Jaccard, reported
               Both sides are compared as normalised category keys; a `;`-joined
               cell is a SET, so order and duplicates do not matter.
    overall    --gate_weight * gate_macro_f1 + (1 - --gate_weight) * mean(dimension
               scores). Default 0.5: gating and typing are both load-bearing for the
               study, and a model that is perfect at one and useless at the other is
               not usable.
    coverage   share of papers the model returned a parseable answer for. Papers that
               errored (timeout, truncation, non-JSON) are EXCLUDED from the metrics
               above rather than counted as wrong — mixing "wrong" and "no answer"
               flatters nothing but hides the reason. Instead, a model below
               --min_coverage (default 0.9) is DISQUALIFIED outright, because a model
               that cannot answer 1 paper in 10 cannot run the study.

COST — this step spends tokens
    One SAIA call per (paper x model), rate-limited to 10/min and 200/h by the shared
    limiter. 146 gold papers x 4 models ~ 584 calls ~ 3 h wall clock. Use `--limit`
    for a smaller stratified subset while trying the step out, `--dry_run` to see the
    plan and the ETA without spending anything, and `--score_only` to re-score
    predictions already on disk (free). Annotation is RESUMABLE: predictions land in
    results/model_selection/predictions_<model>.csv after every paper, and a re-run
    skips ids already present.

USAGE (from the lni_study repo root)
    python src/benchmark_models.py --dry_run
    python src/benchmark_models.py --models mistral-medium-3.5-128b,qwen3.5-122b-a10b
    python src/benchmark_models.py --limit 30 --yes
    python src/benchmark_models.py --score_only          # re-score, no API calls
    run_pipeline.cmd bench <token>                       # the same via the pipeline

The winner is consumed by `preflight.selected_model()`, which run_pipeline.cmd's
`full` step calls. Nothing else repoints: the narrowing loop and the goldstandard
steps keep the pin, so a bake-off can never orphan the existing checkpoints.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import annotate_lni as alni  # noqa: E402  (prompt handling, PDF->paper, classify_paper)
import categories as cat  # noqa: E402
import preflight  # noqa: E402
from build_goldstandard import load_decisions, RS_DIM  # noqa: E402

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.environ.get("LNI_DATA_ROOT") or REPO_ROOT).resolve()

DEFAULT_PDF_FOLDER = DATA_ROOT / ".workingset" / "gold_confirmed"
DEFAULT_SHARED_FOLDER = DATA_ROOT / "goldstandard"
DEFAULT_OUT_DIR = DATA_ROOT / "results" / "model_selection"
SELECTION_FILENAME = "model_selection.json"

# Candidate slate. Deliberately short: every entry costs one full pass over the
# goldstandard. The current pin is always included so the bake-off answers the
# question that matters ("is there anything better than what we already use?").
# Ids that SAIA no longer serves are dropped with a warning (GWDG retires models
# without notice), so a stale entry here degrades to a skip, never to a crash.
DEFAULT_CANDIDATES = [
    preflight.DEFAULT_MODEL,      # the incumbent pin
    "qwen3.5-122b-a10b",
    "openai-gpt-oss-120b",
    "llama-3.3-70b-instruct",
]

# Decoding parameters — identical to annotate_lni/confirm_positives, so a model's
# benchmark score is produced under exactly the settings the study will use.
TEMPERATURE, SEED, TOP_P = 0, 42, 1.0

SINGLE_DIMS = [d for d in cat.DIMENSIONS if not cat.TYPOLOGY[d].get("multi")]
MULTI_DIMS = [d for d in cat.DIMENSIONS if cat.TYPOLOGY[d].get("multi")]


# =============================================================================
# Goldstandard side
# =============================================================================

def n_decided(path: Path) -> int:
    """How many papers this coder file has a gate decision for."""
    try:
        state = load_decisions(path)
    except (OSError, ValueError):
        return 0
    return sum(1 for st in state.values() if st.get("rs") in ("0", "1"))


def resolve_coder(shared_folder: Path, coder: str | None) -> str:
    """Which coding_<coder>.csv is the human truth for this bake-off.

    Explicit --coder wins (and may name a backup file). Otherwise the file with
    the MOST decided papers is used and the choice is printed: the goldstandard
    folder also holds the second coders' double-coding subsets (used for ICR) and
    dated `.backup-` snapshots, all of which are strict subsets of the main
    coding. Silently scoring against a 27-paper ICR subset instead of the
    146-paper goldstandard would quietly halve the benchmark's evidence."""
    files = sorted(shared_folder.glob("coding_*.csv"))
    all_names = [f.stem.replace("coding_", "") for f in files]
    if coder:
        if coder not in all_names:
            raise SystemExit(f"[bench] no coding_{coder}.csv in {shared_folder} "
                             f"(found: {', '.join(all_names) or 'none'})")
        return coder
    live = [(n, n_decided(shared_folder / f"coding_{n}.csv"))
            for n in all_names if "backup" not in n and "." not in n]
    live = [(n, c) for n, c in live if c]
    if not live:
        raise SystemExit(f"[bench] no usable coding_*.csv in {shared_folder} - code "
                         f"the goldstandard first (run_pipeline.cmd gold).")
    live.sort(key=lambda x: (-x[1], x[0]))
    best = live[0][0]
    if len(live) > 1:
        others = ", ".join(f"{n} ({c})" for n, c in live[1:])
        print(f"[bench] reference coder: `{best}` ({live[0][1]} decided papers); "
              f"also present: {others}. Override with --coder.")
    return best


def load_gold(shared_folder: Path, coder: str) -> tuple[dict, dict]:
    """(gate, dims) from the human decisions.

    gate : {id: 1|0}                       every paper the human decided
    dims : {id: {dimension: raw_value}}    only for accepted (rs=1) papers
    """
    state = load_decisions(shared_folder / f"coding_{coder}.csv")
    gate: dict[str, int] = {}
    dims: dict[str, dict] = {}
    for pid, st in state.items():
        if st.get("rs") not in ("0", "1"):
            continue
        gate[pid] = int(st["rs"])
        if st["rs"] == "1":
            dims[pid] = {d: v.get("final_category")
                         for d, v in (st.get("dims") or {}).items()}
    return gate, dims


def assign_folds(ids: list[str], gate: dict, k: int, seed: int) -> dict[str, int]:
    """Deterministic gate-stratified fold assignment.

    Within each gate class the ids are shuffled with a fixed seed and dealt
    round-robin, so every fold holds ~the same accepted/rejected mix and the same
    seed always yields the same split (the report is reproducible, and a re-score
    of old predictions lands in the same folds)."""
    import random
    folds: dict[str, int] = {}
    for label in (1, 0):
        members = sorted(pid for pid in ids if gate.get(pid) == label)
        random.Random(seed + label).shuffle(members)
        for i, pid in enumerate(members):
            folds[pid] = i % k
    return folds


# =============================================================================
# Value normalisation + metrics
# =============================================================================

def _norm(value) -> str:
    """One category key, comparably normalised (case/space/underscore-insensitive)."""
    if value is None:
        return ""
    s = str(value).strip().lower()
    if s in ("", "nan", "none", "null"):
        return ""
    return re.sub(r"[\s-]+", "_", s)


def _as_set(value) -> set[str]:
    """A `;`-joined multi-value cell as a set of normalised keys."""
    if value is None:
        return set()
    parts = re.split(r"[;,]", str(value))
    return {n for n in (_norm(p) for p in parts) if n}


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return prec, rec, f1


def gate_scores(pairs: list[tuple[int, int]]) -> dict:
    """Macro-F1 (+ accuracy and per-class F1) for the research-software gate.

    `pairs` are (human, model) 0/1 labels. Macro rather than plain accuracy: ~55 %
    of the gold set is accepted, so an always-yes model would score .55 accuracy
    for free while being useless as a gate."""
    if not pairs:
        return {"n": 0}
    n = len(pairs)
    acc = sum(1 for h, m in pairs if h == m) / n
    per_class = {}
    for cls in (1, 0):
        tp = sum(1 for h, m in pairs if h == cls and m == cls)
        fp = sum(1 for h, m in pairs if h != cls and m == cls)
        fn = sum(1 for h, m in pairs if h == cls and m != cls)
        per_class[cls] = _prf(tp, fp, fn)
    macro_f1 = (per_class[1][2] + per_class[0][2]) / 2
    return {
        "n": n,
        "accuracy": round(acc, 4),
        "f1_rs": round(per_class[1][2], 4),
        "f1_not_rs": round(per_class[0][2], 4),
        "precision_rs": round(per_class[1][0], 4),
        "recall_rs": round(per_class[1][1], 4),
        "macro_f1": round(macro_f1, 4),
        "score": round(macro_f1, 4),
    }


def dimension_scores(dim: str, pairs: list[tuple[str, str]]) -> dict:
    """Per-dimension agreement between human and model on the SAME paper.

    Single-valued dimensions score exact-match accuracy. Multi-valued ones score
    micro-F1 over the union of label sets (a model that lists three lifecycle
    phases where the human listed two is partly right, and exact-string equality —
    what compute_icr.py uses for human-vs-human — would call that a total miss).
    Mean Jaccard is reported alongside as the per-paper view."""
    if not pairs:
        return {"dimension": dim, "n": 0, "score": None}
    if dim in SINGLE_DIMS:
        hits = sum(1 for h, m in pairs if _norm(h) == _norm(m) and _norm(h) != "")
        n = len(pairs)
        return {"dimension": dim, "n": n, "multi": False,
                "accuracy": round(hits / n, 4), "score": round(hits / n, 4)}
    tp = fp = fn = 0
    jaccards = []
    for h_raw, m_raw in pairs:
        h, m = _as_set(h_raw), _as_set(m_raw)
        tp += len(h & m)
        fp += len(m - h)
        fn += len(h - m)
        union = h | m
        jaccards.append(len(h & m) / len(union) if union else 1.0)
    prec, rec, f1 = _prf(tp, fp, fn)
    return {"dimension": dim, "n": len(pairs), "multi": True,
            "precision": round(prec, 4), "recall": round(rec, 4),
            "micro_f1": round(f1, 4),
            "mean_jaccard": round(sum(jaccards) / len(jaccards), 4),
            "score": round(f1, 4)}


def score_subset(ids: list[str], gate: dict, dims: dict, pred: dict,
                 gate_weight: float) -> dict:
    """Score one model over one set of paper ids (a fold, or the whole gold set).

    `pred` is {id: prediction row}; ids whose prediction errored or is missing are
    skipped by the metrics and counted in `n_missing` (see the module docstring on
    why errors are not scored as wrong)."""
    gate_pairs: list[tuple[int, int]] = []
    dim_pairs: dict[str, list[tuple[str, str]]] = {d: [] for d in cat.DIMENSIONS}
    n_missing = 0
    for pid in ids:
        row = pred.get(pid)
        if row is None or row.get("_error"):
            n_missing += 1
            continue
        m_gate = row.get("gate")
        if m_gate is None:
            n_missing += 1
            continue
        gate_pairs.append((gate[pid], m_gate))
        if gate.get(pid) != 1:
            continue  # typology only describes accepted papers
        for d in cat.DIMENSIONS:
            human = (dims.get(pid) or {}).get(d)
            if human is None or _norm(human) == "":
                continue  # the human left this dimension uncoded
            dim_pairs[d].append((human, row.get(d)))

    g = gate_scores(gate_pairs)
    per_dim = {d: dimension_scores(d, dim_pairs[d]) for d in cat.DIMENSIONS}
    scored = [v["score"] for v in per_dim.values() if v.get("score") is not None]
    typology = round(sum(scored) / len(scored), 4) if scored else None

    if typology is None:
        overall = g.get("score")
    else:
        overall = round(gate_weight * g.get("score", 0.0)
                        + (1 - gate_weight) * typology, 4)
    return {
        "n_papers": len(ids),
        "n_scored": len(gate_pairs),
        "n_missing": n_missing,
        "gate": g,
        "dimensions": per_dim,
        "typology_score": typology,
        "overall": overall,
    }


# =============================================================================
# Prediction side (the SAIA calls)
# =============================================================================

def model_slug(model_id: str) -> str:
    """Filesystem-safe per-model prediction filename part.

    Unlike the annotation checkpoints (named after the model FAMILY so version
    drift keeps appending to one file), a bake-off must keep candidates apart to
    the exact id — two models of the same family are precisely what is being
    compared."""
    return re.sub(r"[^a-z0-9]+", "_", model_id.strip().lower()).strip("_")


def predictions_path(out_dir: Path, model_id: str) -> Path:
    return out_dir / f"predictions_{model_slug(model_id)}.csv"


def load_predictions(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=alni.CHECKPOINT_COLUMNS)
    try:
        return pd.read_csv(path, dtype={"id": str})
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=alni.CHECKPOINT_COLUMNS)


def gate_value(v) -> int | None:
    """A model's gate cell as 0/1, or None if it is absent/uninterpretable.

    Models answer the gate as 1/0, true/false or ja/nein depending on the day;
    pandas then reads a numeric column back as 1.0. All of those mean the same
    thing. Anything else is treated as no answer (and counted against coverage)
    rather than silently as a rejection."""
    s = str(v).strip().lower()
    if s in ("1", "1.0", "true", "yes", "ja"):
        return 1
    if s in ("0", "0.0", "false", "no", "nein"):
        return 0
    return None


def to_pred_map(df: pd.DataFrame) -> dict[str, dict]:
    """The prediction CSV as {id: {gate, <dim>, _error}} for the scorer."""
    out: dict[str, dict] = {}
    for _, r in df.iterrows():
        err = r.get("llm_error")
        rec: dict = {"_error": bool(err) and str(err).strip().lower() not in ("", "nan")}
        rec["gate"] = gate_value(r.get("label_research_software"))
        if rec["gate"] is None:
            rec["_error"] = True
        for d in cat.DIMENSIONS:
            rec[d] = r.get(f"{d}_category")
        out[str(r["id"])] = rec
    return out


def extract_papers(pdf_paths: list[Path], root: Path, max_text_chars: int) -> dict[str, dict]:
    """Parse every gold PDF ONCE and reuse the text for all candidate models.

    Extraction is the expensive local step (seconds per PDF); doing it per model
    would multiply it by the size of the slate for no gain — every model sees the
    identical prompt input, which is also what makes the comparison fair."""
    papers: dict[str, dict] = {}
    for p in tqdm(pdf_paths, desc="Extracting PDFs", unit="pdf"):
        paper = alni.pdf_to_paper(p, root, max_text_chars)
        if paper.get("extraction_failed"):
            tqdm.write(f"  [skip] extraction failed: {paper['id']}")
            continue
        papers[paper["id"]] = paper
    return papers


def annotate_with_model(client, model: str, papers: dict[str, dict], ids: list[str],
                        system_prompt: str, user_prompt_template: str,
                        rate_limiter, out_path: Path, prompt_name: str,
                        max_tokens: int | None, run: str) -> pd.DataFrame:
    """One candidate model over the gold papers. Resumable, one row per paper.

    Writes after EVERY paper: at 10 requests/minute a full slate runs for hours,
    and a run that dies at paper 300 must not throw away 299 answers."""
    df = load_predictions(out_path)
    done = set(df["id"].astype(str)) if len(df) else set()
    todo = [pid for pid in ids if pid not in done]
    print(f"\n[{model}] {len(done)} already predicted, {len(todo)} to go "
          f"-> {out_path.name}")
    if not todo:
        return df

    rows = []
    pbar = tqdm(todo, desc=f"{model}", unit="paper")
    for pid in pbar:
        paper = papers[pid]
        flat = alni.classify_paper(client, paper, model, system_prompt,
                                   user_prompt_template, TEMPERATURE, SEED, TOP_P,
                                   rate_limiter, max_tokens=max_tokens)
        row = {
            "id": pid,
            "source_folder": paper.get("source_folder"),
            "filename": paper.get("filename"),
            "rel_path": paper.get("rel_path"),
            "title": paper.get("title"),
            "authors": paper.get("authors"),
            "model": model,
            "prompt_template": prompt_name,
            "run": run,
        }
        row.update(flat)
        rows.append(row)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        alni._write_checkpoint(df, out_path, alni.CHECKPOINT_COLUMNS)
        if flat.get("llm_error"):
            pbar.set_postfix_str("last: ERROR")
    return df


# =============================================================================
# Ranking + reports
# =============================================================================

def rank_models(results: list[dict], min_coverage: float) -> tuple[dict | None, str]:
    """Pick the winner and say why in one line.

    Order: coverage gate first (a model that cannot answer cannot run the study),
    then mean fold score, then fold wins, then the smaller spread. The incumbent
    pin wins exact ties — switching models invalidates nothing but costs a
    re-annotation, so it needs a strictly better number."""
    eligible = [r for r in results if r["coverage"] >= min_coverage
                and r["overall_mean"] is not None]
    if not eligible:
        return None, (f"no model reached the {min_coverage:.0%} coverage floor "
                      f"- nothing selected")
    def key(r):
        return (round(r["overall_mean"], 4), r["fold_wins"], -round(r["overall_std"], 4),
                1 if r["model"] == preflight.DEFAULT_MODEL else 0)
    ranked = sorted(eligible, key=key, reverse=True)
    best = ranked[0]
    if len(ranked) == 1:
        why = (f"only candidate above the {min_coverage:.0%} coverage floor; "
               f"overall {best['overall_mean']:.3f}")
    else:
        second = ranked[1]
        margin = best["overall_mean"] - second["overall_mean"]
        why = (f"overall {best['overall_mean']:.3f} +/- {best['overall_std']:.3f}, "
               f"won {best['fold_wins']}/{best['n_folds']} folds; "
               f"{margin:+.3f} over {second['model']} ({second['overall_mean']:.3f})")
        if margin < 0.02:
            why += " - NARROW margin, treat the two as tied"
    return best, why


def write_reports(out_dir: Path, payload: dict, results: list[dict]) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    sel_path = out_dir / SELECTION_FILENAME
    sel_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    # Long scores table: one row per (model, fold/all, dimension|gate|overall).
    rows = []
    for r in results:
        for fold_name, s in r["by_fold"].items():
            rows.append({"model": r["model"], "fold": fold_name, "metric": "overall",
                         "n": s["n_scored"], "value": s["overall"]})
            rows.append({"model": r["model"], "fold": fold_name, "metric": "gate_macro_f1",
                         "n": s["gate"].get("n"), "value": s["gate"].get("score")})
            for d, dv in s["dimensions"].items():
                rows.append({"model": r["model"], "fold": fold_name,
                             "metric": f"dim:{d}", "n": dv.get("n"),
                             "value": dv.get("score")})
    scores_path = out_dir / "model_scores.csv"
    pd.DataFrame(rows).to_csv(scores_path, index=False)

    # Human summary.
    w = payload.get("winner") or {}
    lines = [
        f"# Model selection - three-fold test against the goldstandard",
        "",
        f"- generated: {payload['generated']}",
        f"- reference coder: `{payload['gold_coder']}` "
        f"({payload['n_papers']} decided papers, {payload['n_accepted']} accepted as RS)",
        f"- folds: {payload['folds']} (gate-stratified, seed {payload['seed']})",
        f"- prompt: `{payload['prompt_template']}` | schema: `category_schema.yaml`",
        f"- score: {payload['gate_weight']:.2f} x gate macro-F1 + "
        f"{1 - payload['gate_weight']:.2f} x mean dimension score",
        "",
        f"**Winner: `{w.get('model', '- none -')}`** - {payload.get('winner_reason', '')}",
        "",
        "## Overall",
        "",
        "| model | coverage | overall (mean) | +/- | fold wins | gate macro-F1 | typology |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: (x["overall_mean"] is not None,
                                            x["overall_mean"] or 0), reverse=True):
        all_s = r["by_fold"]["all"]
        flag = "" if r["coverage"] >= payload["min_coverage"] else " (DISQUALIFIED)"
        mean = "-" if r["overall_mean"] is None else f"{r['overall_mean']:.3f}"
        lines.append(
            f"| `{r['model']}`{flag} | {r['coverage']:.0%} | {mean} | "
            f"{r['overall_std']:.3f} | {r['fold_wins']}/{r['n_folds']} | "
            f"{all_s['gate'].get('score')} | {all_s['typology_score']} |")
    lines += ["", "## Per dimension (whole goldstandard)", "",
              "| model | " + " | ".join(cat.DIMENSIONS) + " |",
              "|---" * (len(cat.DIMENSIONS) + 1) + "|"]
    for r in results:
        dv = r["by_fold"]["all"]["dimensions"]
        cells = [f"{dv[d]['score']:.3f}" if dv[d].get("score") is not None else "-"
                 for d in cat.DIMENSIONS]
        lines.append(f"| `{r['model']}` | " + " | ".join(cells) + " |")
    lines += ["", "## Per fold (overall score)", "",
              "| model | " + " | ".join(f"fold {i}" for i in range(payload["folds"])) + " |",
              "|---" * (payload["folds"] + 1) + "|"]
    for r in results:
        cells = []
        for i in range(payload["folds"]):
            s = r["by_fold"].get(f"fold_{i}")
            cells.append("-" if not s or s["overall"] is None else f"{s['overall']:.3f}")
        lines.append(f"| `{r['model']}` | " + " | ".join(cells) + " |")
    lines += ["",
              "Papers a model failed to answer (timeout / non-JSON / truncation) are "
              "excluded from its metrics and reflected in `coverage`; a model below "
              f"{payload['min_coverage']:.0%} coverage is disqualified.",
              ""]
    md_path = out_dir / "model_selection.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return sel_path, scores_path, md_path


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Three-fold test: score SAIA models against the human "
                    "goldstandard and write the final study's model selection.")
    ap.add_argument("--models", default=None,
                    help="comma-separated SAIA model ids (default: the built-in "
                         "candidate slate incl. the current pin)")
    ap.add_argument("--folds", type=int, default=3,
                    help="how many gate-stratified folds to score on (default 3)")
    ap.add_argument("--coder", default=os.getenv("LNI_CODER") or None,
                    help="which coding_<coder>.csv is the human truth "
                         "(default: the only one present)")
    ap.add_argument("--shared_folder", default=str(DEFAULT_SHARED_FOLDER))
    ap.add_argument("--pdf_folder", default=str(DEFAULT_PDF_FOLDER),
                    help="the PDFs of the coded papers (.workingset/gold_confirmed)")
    ap.add_argument("--out_dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--prompt_template", default=str(alni.DEFAULT_PROMPT))
    ap.add_argument("--limit", type=int, default=None,
                    help="score only N gold papers (gate-stratified draw) - for "
                         "trying the step out cheaply")
    ap.add_argument("--gate_weight", type=float, default=0.5,
                    help="weight of the gate in the composite score (default 0.5)")
    ap.add_argument("--min_coverage", type=float, default=0.9,
                    help="a model answering fewer than this share of papers is "
                         "disqualified (default 0.9)")
    ap.add_argument("--seed", type=int, default=20260805,
                    help="fold-assignment / sampling seed (fixed = reproducible)")
    ap.add_argument("--max_text_chars", type=int, default=20000)
    ap.add_argument("--max_tokens", type=int, default=alni.DEFAULT_MAX_TOKENS)
    ap.add_argument("--run", default="bench_1", help="run label stored in each row")
    ap.add_argument("--saia_token", default=None)
    ap.add_argument("--saia_endpoint", default=None)
    ap.add_argument("--score_only", action="store_true",
                    help="do not call SAIA; score the predictions already on disk")
    ap.add_argument("--dry_run", action="store_true",
                    help="print the plan (models, papers, ETA) and exit - no calls")
    ap.add_argument("--yes", action="store_true",
                    help="skip the cost confirmation prompt (for unattended runs)")
    args = ap.parse_args()

    shared_folder = Path(args.shared_folder).resolve()
    pdf_folder = Path(args.pdf_folder).resolve()
    out_dir = Path(args.out_dir).resolve()

    coder = resolve_coder(shared_folder, args.coder)
    gate, dims = load_gold(shared_folder, coder)
    if not gate:
        raise SystemExit(f"[bench] coding_{coder}.csv holds no decided papers.")

    # Only papers whose PDF is actually present can be re-annotated.
    available = {alni.paper_id(p, pdf_folder): p
                 for p in sorted(pdf_folder.rglob("*.pdf"))}
    ids = sorted(pid for pid in gate if pid in available)
    missing_pdf = sorted(pid for pid in gate if pid not in available)

    if args.limit and args.limit < len(ids):
        import random
        rng = random.Random(args.seed)
        picked: list[str] = []
        for label in (1, 0):
            members = sorted(p for p in ids if gate[p] == label)
            rng.shuffle(members)
            share = round(args.limit * len(members) / len(ids))
            picked += members[:max(1, share)]
        ids = sorted(picked[:args.limit])

    n_acc = sum(1 for p in ids if gate[p] == 1)
    models = ([m.strip() for m in args.models.split(",") if m.strip()]
              if args.models else list(DEFAULT_CANDIDATES))

    print(f"[config] goldstandard : {shared_folder}  (coder `{coder}`)")
    print(f"[config] gold PDFs    : {pdf_folder}")
    print(f"[config] output       : {out_dir}")
    print(f"[config] papers       : {len(ids)} decided ({n_acc} accepted as RS, "
          f"{n_acc / len(ids):.0%})" if ids else "[config] papers       : none")
    if missing_pdf:
        # The gate metric is only as representative as the PDFs on disk. The local
        # gold cache holds the papers that went through confirmation, which skews
        # accepted; say so rather than let a 74%-accepted benchmark read as if it
        # measured the gate on the study's real 55/45 mix.
        full_acc = sum(1 for p in gate if gate[p] == 1) / len(gate)
        print(f"[config] NOTE         : {len(missing_pdf)} of {len(gate)} coded papers "
              f"have no PDF under --pdf_folder, so the gate is measured on a subset "
              f"that is {n_acc / len(ids):.0%} accepted vs {full_acc:.0%} in the full "
              f"goldstandard. Point --pdf_folder at the corpus (VPN) for the full mix.")
    print(f"[config] folds        : {args.folds} (seed {args.seed})")
    print(f"[config] models       : {', '.join(models)}")

    token = args.saia_token or os.getenv("SAIA_API_KEY")
    if not args.score_only:
        # Drop retired ids before spending an hour discovering them one 404 at a time.
        catalogue = preflight.list_models(args.saia_endpoint, token)
        if catalogue:
            unknown = [m for m in models if m not in catalogue]
            if unknown:
                print(f"[bench] NOT served by SAIA, skipping: {', '.join(unknown)}")
                models = [m for m in models if m in catalogue]
            if not models:
                raise SystemExit("[bench] none of the requested models is served; "
                                 "see `python src/preflight.py --list_models`.")
        else:
            print("[bench] model catalogue unavailable - candidates NOT verified.")

        calls = len(ids) * len(models)
        # 200 requests/hour is the binding limit for anything past the first 20 min.
        eta_h = calls / 200.0
        print(f"\n[cost] {calls} SAIA calls ({len(ids)} papers x {len(models)} models) "
              f"~ {eta_h:.1f} h at the 200 req/h limit (already-predicted papers are "
              f"skipped, so a resumed run is shorter).")

    if args.dry_run:
        print("[bench] --dry_run: nothing called, nothing written.")
        return

    folds = assign_folds(ids, gate, args.folds, args.seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.score_only:
        if not token:
            raise SystemExit("[bench] missing SAIA token (SAIA_API_KEY or --saia_token).")
        if not args.yes:
            ans = input("Proceed and spend these tokens? [y/N]: ").strip().lower()
            if ans not in ("y", "yes"):
                print("[bench] aborted; nothing called.")
                return
        preflight.require([preflight.check_saia(args.saia_endpoint, token)])
        system_prompt, user_prompt_template = alni.load_prompt_template(args.prompt_template)
        papers = extract_papers([available[p] for p in ids], pdf_folder, args.max_text_chars)
        ids = [p for p in ids if p in papers]  # extraction failures drop out for everyone
        client = OpenAI(api_key=token,
                        base_url=(args.saia_endpoint or os.getenv("SAIA_API_ENDPOINT")
                                  or preflight.DEFAULT_SAIA_ENDPOINT),
                        timeout=300.0)
        limiter = alni.RateLimiter()  # ONE limiter: the quota is per token, not per model
        for model in models:
            annotate_with_model(client, model, papers, ids, system_prompt,
                                user_prompt_template, limiter,
                                predictions_path(out_dir, model),
                                Path(args.prompt_template).stem,
                                args.max_tokens or None, args.run)

    # ---- score -------------------------------------------------------------
    results = []
    for model in models:
        path = predictions_path(out_dir, model)
        df = load_predictions(path)
        if not len(df):
            print(f"[bench] no predictions for {model} ({path.name}) - skipped.")
            continue
        pred = to_pred_map(df)
        scored_ids = [p for p in ids if p in pred]
        coverage = (sum(1 for p in scored_ids
                        if not pred[p]["_error"] and pred[p]["gate"] is not None)
                    / len(ids)) if ids else 0.0
        by_fold = {"all": score_subset(ids, gate, dims, pred, args.gate_weight)}
        for i in range(args.folds):
            fold_ids = [p for p in ids if folds.get(p) == i]
            by_fold[f"fold_{i}"] = score_subset(fold_ids, gate, dims, pred, args.gate_weight)
        fold_overalls = [by_fold[f"fold_{i}"]["overall"] for i in range(args.folds)
                         if by_fold[f"fold_{i}"]["overall"] is not None]
        mean = sum(fold_overalls) / len(fold_overalls) if fold_overalls else None
        std = ((sum((x - mean) ** 2 for x in fold_overalls) / len(fold_overalls)) ** 0.5
               if fold_overalls else 0.0)
        results.append({
            "model": model,
            "family": preflight.model_family(model),
            "coverage": round(coverage, 4),
            "n_predicted": len(scored_ids),
            "n_errors": sum(1 for p in scored_ids if pred[p]["_error"]),
            "n_folds": args.folds,
            "fold_overalls": [round(x, 4) for x in fold_overalls],
            "overall_mean": round(mean, 4) if mean is not None else None,
            "overall_std": round(std, 4),
            "fold_wins": 0,
            "by_fold": by_fold,
        })

    if not results:
        raise SystemExit("[bench] nothing scored - run without --score_only first.")

    # Fold wins are contested only among models that cleared the coverage floor: a
    # model that answered half the papers can post a great score on what it did
    # answer, and letting it take a fold would understate a usable rival's record.
    contenders = [r for r in results if r["coverage"] >= args.min_coverage]
    for i in range(args.folds):
        best_v, best_m = None, None
        for r in contenders:
            v = r["by_fold"][f"fold_{i}"]["overall"]
            if v is not None and (best_v is None or v > best_v):
                best_v, best_m = v, r["model"]
        for r in contenders:
            if r["model"] == best_m:
                r["fold_wins"] += 1

    winner, why = rank_models(results, args.min_coverage)
    payload = {
        "schema_version": 1,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "produced_by": "src/benchmark_models.py",
        "gold_coder": coder,
        "goldstandard": str(shared_folder / f"coding_{coder}.csv"),
        "n_papers": len(ids),
        "n_accepted": n_acc,
        "folds": args.folds,
        "seed": args.seed,
        "gate_weight": args.gate_weight,
        "min_coverage": args.min_coverage,
        "prompt_template": Path(args.prompt_template).name,
        "dimensions": list(cat.DIMENSIONS),
        "models": results,
        "winner": ({"model": winner["model"], "family": winner["family"],
                    "overall_mean": winner["overall_mean"],
                    "overall_std": winner["overall_std"],
                    "fold_wins": winner["fold_wins"],
                    "coverage": winner["coverage"]} if winner else None),
        "winner_reason": why,
        "pin": preflight.DEFAULT_MODEL,
    }
    sel_path, scores_path, md_path = write_reports(out_dir, payload, results)

    print("\n" + "=" * 72)
    for r in sorted(results, key=lambda x: x["overall_mean"] or -1, reverse=True):
        mark = "*" if winner and r["model"] == winner["model"] else " "
        mean = "-" if r["overall_mean"] is None else f"{r['overall_mean']:.3f}"
        dq = "  DISQUALIFIED (coverage)" if r["coverage"] < args.min_coverage else ""
        print(f" {mark} {r['model']:<32} overall {mean} +/-{r['overall_std']:.3f}  "
              f"folds won {r['fold_wins']}/{r['n_folds']}  "
              f"coverage {r['coverage']:.0%}{dq}")
    print("=" * 72)
    print(f"Winner: {winner['model'] if winner else '(none)'} - {why}")
    if winner and winner["model"] != preflight.DEFAULT_MODEL:
        print(f"Note: this differs from the pin ({preflight.DEFAULT_MODEL}). The final "
              f"study will now use the winner; the goldstandard/narrowing steps keep "
              f"the pin so their checkpoints stay valid.")
    print(f"\nSaved: {sel_path}\nSaved: {md_path}\nSaved: {scores_path}")


if __name__ == "__main__":
    main()
