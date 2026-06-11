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
src/categories.py                   Typology + RSE definition (single source of truth)
src/pdf_text_extraction.py          LNI PDF extractor (vendored from rse-elearning-evaluation)
src/annotate_lni.py                 Machine annotation: folder of PDFs -> typology CSV  (notes 1-7)
src/build_goldstandard.py           Interactive two-coder goldstandard session         (notes 8-11)
src/compute_icr.py                  Intercoder reliability                             (notes 12)
results/                            Annotation checkpoints + new-category suggestions
goldstandard/                       Coders' decision files + ICR output
```

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

Goldstandard coding (two coders) + reliability — **no token needed** (reads the
Phase A annotations, auto-discovered from the folder name):

```
python src/build_goldstandard.py --username alice ^
  --pdf_folder ../rse-elearning-evaluation/data/data/lni132
python src/compute_icr.py --shared_folder goldstandard
```

## What needs the SAIA token

| Phase | Needs | Notes |
|-------|-------|-------|
| A — machine annotation (`annotate_lni.py`) | PDFs + token | `--dry_run` needs PDFs only (no token) |
| B — goldstandard coding (`build_goldstandard.py`, `compute_icr.py`) | PDFs only | reads Phase A annotations; opens PDFs in browser |
| C — full-corpus annotation + aggregation | PDFs + token | 3 models × runs, majority vote |

The offline path (PDF extraction + prompt building, `--dry_run`) runs without a
token; only the SAIA annotation calls need credentials.
