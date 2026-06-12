# lni_study — A Typology of Research Software in LNI Publications

Classifying the types of Research Software Engineering (RSE) found in CS-related
research, using the **Lecture Notes in Informatics (LNI)** corpus for availability
and legal access. Target venue: **ICSE 2027**.

The annotation pipeline reuses the DeLFI study pipeline from the sibling repo
`../rse-elearning-evaluation` (SAIA API client, rate limiting, JSON parsing,
checkpoint/resume, LNI PDF text extraction, majority-vote aggregation, ICR).

See **[`TASKS.md`](TASKS.md)** for the full, resumable subtask breakdown and
**[`METHOD.md`](METHOD.md)** for the method-section draft.

## Layout

```
prompts/rse_typology_prompt_v1.md   RSE gate + typology annotation prompt (DE)
prompts/category_whitelist.json     Curated subcategory white/blacklist (from narrowing; created by narrow_categories.py)
src/categories.py                   Typology + RSE definition + white/blacklist rendering (single source of truth)
src/sampling.py                     Stratified sampling over LNI volumes (strata = lni* folders)
src/prepare_workingset.py           Copy a stratified sample to a local fast .workingset/ (off the slow corpus)
src/pdf_text_extraction.py          LNI PDF extractor (vendored from rse-elearning-evaluation)
src/annotate_lni.py                 Machine annotation: folder of PDFs -> typology CSV  (notes 1-7)
src/narrow_categories.py            Subcategory narrowing: 50-paper stratified sample -> white/blacklist (notes 7b)
src/build_goldstandard.py           Interactive two-coder goldstandard session         (notes 8-11)
src/compute_icr.py                  Intercoder reliability                             (notes 12)
results/                            Annotation checkpoints + suggestions + category candidates
goldstandard/                       Coders' decision files + ICR output
.workingset/                        Local fast copy of sampled PDFs (gitignored; off the slow corpus)
```

## Local working copy (slow corpus → fast disc)

The full corpus lives on a **slow mounted disc**. The human-annotation cycles
(narrowing review, goldstandard coding) open the same PDFs repeatedly, so the
sampled PDFs are copied once to a local `.workingset/` (gitignored) and every
step after the draw runs against that fast copy. The full corpus is read only
**twice**: when drawing the samples, and for the final full-corpus annotation.

```
# Narrowing set: 50 papers (stratified by LNI volume)
python src/prepare_workingset.py --corpus <SLOW_CORPUS> --name narrow --sample 50

# Goldstandard set: 100 papers, DISJOINT from the narrowing set
python src/prepare_workingset.py --corpus <SLOW_CORPUS> --name gold --sample 100 ^
  --exclude .workingset/narrow/manifest.csv
```

PDFs are copied preserving their path under the corpus root, so paper ids and the
volume stratum are identical to the full corpus — the steps below just point their
folder argument at `.workingset/narrow` or `.workingset/gold`.

## Setup

Use the standard cmd Python on this machine:
`C:\Users\julian.dehne\AppData\Local\Programs\Python\Python313\python.exe`

```
pip install -r requirements.txt
copy .env.example .env       # then add your SAIA token
```

## IntelliJ run configurations

Three shared runners are committed at the project root
(`.idea/runConfigurations/`), all pointing at the Python313 interpreter and using
`publications/lni_study` as the working directory:

- **annotate_lni (dry-run, no token)** — `--test --dry_run`; extraction + prompt
  only, no API call.
- **annotate_lni (test, 5 papers)** — `--test`; live, needs the token.
- **annotate_lni (full run)** — full volume, model `mistral-...`, `run_1`.

To adapt: open *Run → Edit Configurations…*, change `--lni_folder` to your corpus
path, and (full run) `--model`/`--run`. The **SAIA token is NOT in the run config** —
it is read from `lni_study/.env` (`load_dotenv` runs with the working dir set here),
so the token never lands in a committed XML. If IntelliJ flags the interpreter,
pick your Python313 in the *Python interpreter* dropdown.

## Usage (command line)

Machine annotation (test on 5 papers first):

```
python src/annotate_lni.py --lni_folder ../rse-elearning-evaluation/data/data/lni132 --test
```

Full volume, specific model/run:

```
python src/annotate_lni.py ^
  --lni_folder ../rse-elearning-evaluation/data/data/lni132 ^
  --model mistral-large-3-675b-instruct-2512 --run run_1
```

Subcategory narrowing (Phase A2) — over the local `.workingset/narrow` copy.
First run Phase A on the 50-paper working copy, then collect candidates and
review them into the white/blacklist. `collect` reuses the Phase A checkpoints
(no token); `review` needs neither PDFs nor token:

```
python src/annotate_lni.py --lni_folder .workingset/narrow            # Phase A on the 50
python src/narrow_categories.py --mode collect --corpus .workingset/narrow --sample 50
python src/narrow_categories.py --mode review
```

The resulting `prompts/category_whitelist.json` is then injected into the
annotation prompt (`{category_guidance_block}`) and shown to coders in
`build_goldstandard.py`.

Stratified sampling also drives the annotator's test/sample draws (strata = LNI
volume folders, proportional allocation):

```
python src/annotate_lni.py --lni_folder ../rse-elearning-evaluation/data/data --sample 30
```

Goldstandard coding (two coders) over the local `.workingset/gold` copy. Run
Phase A on the 100-paper working copy first (it now picks up the narrowed
white/blacklist), then the coders annotate against the local PDFs — **no token
needed** for the coding/ICR step:

```
python src/annotate_lni.py --lni_folder .workingset/gold              # Phase A on the 100
python src/build_goldstandard.py --username alice --pdf_folder .workingset/gold
python src/compute_icr.py --shared_folder goldstandard
```

## What needs the SAIA token

| Phase | Needs | Notes |
|-------|-------|-------|
| Prepare working copy (`prepare_workingset.py`) | full corpus | reads the slow corpus once per sample; copies to `.workingset/` |
| A — machine annotation (`annotate_lni.py`) | PDFs + token | `--dry_run` needs PDFs only (no token); run on `.workingset/<name>` for samples |
| A2 — narrowing collect (`narrow_categories.py --mode collect`) | PDFs only | reuses Phase A checkpoints; `--annotate_missing` adds token |
| A2 — narrowing review (`narrow_categories.py --mode review`) | nothing | reads the candidates CSV; pure human curation |
| B — goldstandard coding (`build_goldstandard.py`, `compute_icr.py`) | PDFs only | reads Phase A annotations; opens PDFs in browser |
| C — full-corpus annotation + aggregation | PDFs + token | 3 models × runs, majority vote |

The offline path (PDF extraction + prompt building, `--dry_run`) runs without a
token; only the SAIA annotation calls need credentials.
