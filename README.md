# lni_study — A Typology of Research Software in LNI Publications

Classifying the types of Research Software Engineering (RSE) found in CS-related
research, using the **Lecture Notes in Informatics (LNI)** corpus for availability
and legal access. Target venue: **ICSE 2027**.

The annotation pipeline reuses the DeLFI study pipeline from the sibling repo
`../rse-elearning-evaluation` (SAIA API client, rate limiting, JSON parsing,
checkpoint/resume, LNI PDF text extraction, majority-vote aggregation, ICR).

See **[`TASKS.md`](TASKS.md)** for the full, resumable subtask breakdown and
**[`METHOD.md`](METHOD.md)** for the method-section draft. Which models annotate the
study is decided empirically — see [LLM selection](#llm-selection--picking-the-annotation-panel-bench)
below; **[`README_FABIAN.md`](README_FABIAN.md)** is the run-it-yourself walkthrough for
that step and the final-study pretest.

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
src/benchmark_models.py             LLM selection: score SAIA models vs the goldstandard -> top-3 voting panel
src/confirm_positives.py            Confirm-on-the-fly annotation; merges the panel's answers by majority vote
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
  --model mistral-medium-3.5-128b --run run_1
```

`--model` defaults to `preflight.DEFAULT_MODEL`, so you only pass it to override.
GWDG retires SAIA models without notice; `python src/preflight.py --list_models`
prints the catalogue that is actually served right now.

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

## LLM selection — picking the annotation panel (`bench`)

The final study is **not** annotated by one hand-picked model. Which models annotate it
is decided empirically by the `bench` step, and the three best of them annotate it
**together**: every paper is classified by all three and their answers are merged by
**majority vote**. This section is the reference for that step; `README_FABIAN.md`
covers running it end to end together with the final-study pretest.

Run from the `lni_study` folder; `menu.cmd` has it as the **`bench`** entry under
*Final study*, directly above `full`.

### What it measures

The humans coded ~150 papers by hand into `goldstandard\coding_<coder>.csv`. Every
candidate model re-annotates **exactly those papers**, and we measure how close each one
comes to the humans:

* **gate** (`label_research_software`, "is there research software in this paper?") —
  scored as **macro-F1**, so a model that answers "yes" to everything cannot win by
  riding the base rate.
* **typology** (the five dimensions) — over the papers the humans *accepted*:
  `research_position` is single-valued, so it is scored by exact match; the other four
  are multi-valued, so they are scored as **micro-F1 over the label sets** (a model that
  names three lifecycle phases where the human named two is partly right, not wrong).
* **overall** = `0.5 × gate + 0.5 × mean(dimensions)` — a model that is perfect at
  gating and useless at typing is not usable for this study, and vice versa.
* **coverage** — the share of papers a model answered at all. Papers that timed out or
  came back as non-JSON are *excluded* from the scores above and reported separately; a
  model below **90 % coverage is disqualified** no matter how well it scored on the rest.

### How the panel is picked

**One F score over the whole goldstandard.** Nothing is trained and nothing is held out —
every model annotates every gold paper exactly once and is scored against the humans on
all of them. There is no cross-validation and no averaging over splits, on purpose: the
ranking should be the simplest thing that can be checked by hand, and the tables below
are how you check it.

The **three highest scorers above the coverage floor become the panel** (`--panel_size`,
default 3). The best of them is the **lead**: it breaks ties during the vote and it is
the model whose family names the checkpoint files. The report also prints the margin
between the last panel seat and the first model that missed it — under 0.02 that seat is
effectively a coin flip and is flagged as such.

Three, not one, because a single model's confident mistake is indistinguishable from a
correct answer; three is the smallest odd panel where one such mistake can be outvoted.
Three, not five, because the study is ~500 papers and each extra seat is another full
pass over all of them.

### How the vote works

The final study calls all panel models per paper and merges their answers
(`majority_vote` in `src/confirm_positives.py`):

* **gate** — majority of the votes actually **cast**; a model that errored *abstains*, it
  does not count as a "no". A tie goes to the lead.
* **single-valued dimension** (`research_position`) — the most frequent key; tie → lead.
* **multi-valued dimensions** — a key is kept when at least `n_cast // 2 + 1` models
  named it, so the merged set is per *key*, not per whole answer. If no key reaches that
  bar the lead's set is used and the row is flagged `<dim>:no_majority`.
* **certainty / explanation / new_suggestion** are copied from the vote that agrees most
  with the merged value, so the prose never argues for a category the row is not filed
  under.
* If **every** seat errored the row is an error row, flagged `panel_dissent=all_failed`,
  exactly like a failed single-model annotation.

Three extra columns land in the checkpoint: `panel_models`, `panel_gate_votes`
(e.g. `1|1|0`, `-` for an abstention) and `panel_dissent` (which fields were split).
The **raw per-model answers** are kept next to the checkpoint in
`annotations_<tag>_votes.csv` — that file is also the input for the inter-model
agreement numbers in the paper. A panel of one degenerates to the plain single-model
path, so nothing forks.

### Run it

```cmd
:: 0) see the plan and what it will cost - calls nothing, writes nothing
run_pipeline.cmd bench "" "" dry

:: 1) cheap trial: only 30 goldstandard papers per model
run_pipeline.cmd bench <token> 30

:: 2) the real thing: every coded paper that has a local PDF
run_pipeline.cmd bench <token>

:: 3) re-score what is already on disk - free, no API calls
run_pipeline.cmd bench "" "" score
```

It **asks for confirmation** before the first API call and prints the expected number of
calls and hours first. It is **resumable**: every answer is written to
`results\model_selection\predictions_<model>.csv` immediately, and a re-run skips papers
that already have an answer — so killing it and starting again later costs nothing.
Rate limits (10 calls/min, 200 calls/h) are handled automatically; the step simply waits.
Expect roughly **half an hour per candidate model** for a full pass.

> `bench` reads PDFs from `.workingset\gold_confirmed`, a local cache — **no VPN / Z:
> drive needed**. The final study does need the corpus.

### What it writes — `results\model_selection\`

| file | for |
|---|---|
| `model_selection.json` | **the machine**: the `panel` (ranked) + `winner` (the lead), read by the final-study step |
| `model_selection.md` | **you**: the ranking, per-dimension and per-category tables |
| `model_scores.csv` | every metric in long format, for plotting / the paper |
| `category_scores.csv` | one row per (model, dimension, **category**) — see below |
| `paper_comparison.csv` | one row per (model, **paper**, dimension) — see below |
| `predictions_<model>.csv` | each model's raw answers (resume data + error inspection) |

Read `model_selection.md` first. The summary line to look at is e.g.

```
Panel: qwen3.5-122b-a10b (0.741), mistral-medium-3.5-128b (0.698), llama-3.3-70b (0.681)
       ; last panel seat +0.012 over gemma-3-27b (0.669) - NARROW, that seat is
       effectively a coin flip
```

In the overall table, `*` marks the lead and `+` the other panel seats.

### Inspecting the result by hand

The overall number is one number, so it hides a lot. The two extra tables are there to
make it checkable:

* **`category_scores.csv`** — per *category*, not just per dimension: `tp/fp/fn`,
  precision/recall/F1, and **`support_human` vs `support_model`**. This is where you see
  a model that scores .70 on `software_type` while **never once** producing a category
  the humans used nine times (recall 0), or one that tags half the corpus with
  `insufficient_information`. `in_schema = False` marks keys the model invented; they
  count as false positives, but if one is a real synonym it belongs in that category's
  `examples:` in `category_schema.yaml` rather than being punished.
* **`paper_comparison.csv`** — per *paper*: the human value, the model value, a status
  (`agree` / `partial` / `disagree` / `no_answer`) and which keys were **`missed`** vs
  added **`extra`**. Filter it to one category and you have the list of papers to read.

`model_selection.md` already prints the lead's worst 40 categories. For anything beyond
that:

```cmd
run_pipeline.cmd bench "" "" score        :: regenerate the tables, free
jupyter lab notebooks\model_selection.ipynb
```

The notebook is a **stub** — it loads the three CSVs and gives you the ranking,
per-dimension and per-category views, a drill-down into one category, the papers *no*
model got right, and the gate confusion matrix. Extend it as you like; nothing else
reads it.

### Changing which models compete, and how many win

Edit `DEFAULT_CANDIDATES` at the top of `src\benchmark_models.py`, or bypass the .cmd:

```cmd
python src\benchmark_models.py --models mistral-medium-3.5-128b,qwen3.5-122b-a10b
python src\benchmark_models.py --panel_size 5        :: bigger panel, 5x the study cost
```

Model ids are verified against the live SAIA catalogue before anything is spent —
retired ids are dropped with a warning instead of failing 100 calls in. If fewer models
than `--panel_size` clear the coverage floor the panel is simply shorter, and the report
says so (an even panel needs unanimity on ties, so expect the lead to decide more often).

### Which human is the reference?

`goldstandard\` holds the main coding plus the second coders' smaller double-coding
subsets (used for intercoder reliability) and dated `.backup-` snapshots. Left alone,
the step picks the file with the **most decided papers** and prints which one it chose.
To score against a specific coder:

```cmd
run_pipeline.cmd bench <token> "" "" bob
```

### One caveat worth knowing

Only coded papers whose PDF sits in `.workingset\gold_confirmed` can be re-annotated.
That cache is skewed toward *accepted* papers, so the step prints a note like

```
[config] NOTE : 38 of 148 coded papers have no PDF under --pdf_folder, so the gate is
measured on a subset that is 75% accepted vs 56% in the full goldstandard.
```

The typology scores are unaffected (they only use accepted papers anyway). For a gate
measured on the study's real class mix, point the step at the corpus:

```cmd
python src\benchmark_models.py --pdf_folder Z:\path\to\corpus
```

### How `bench` and the final study are connected

`bench` writes the panel; the final study reads it. Nothing else in the pipeline changes
model:

```
bench ──► results\model_selection\model_selection.json ──► full  (annotates with all
                                                                 three, majority vote)

           everything else (narrowing loop, goldstandard steps)
           keeps the pinned model in src\preflight.py
```

The pinned model stays pinned on purpose: annotation checkpoints are named after the
model *family*, so repointing the goldstandard steps mid-study would orphan the
annotations already collected. The final study is the one place where the model choice
is still an open question, so that is the only place the selection applies.

To see what the final study *would* use, without running anything:

```cmd
python src\preflight.py --print_selected_panel     :: lead first, comma separated
python src\preflight.py --print_selected_model     :: just the lead / tie-breaker
```

**To override the selection:** delete (or rename) `model_selection.json` and the pipeline
falls back to the pinned model alone; or edit the `"panel"` list in that file to force
specific ids (`"winner"` must stay the lead). Bypassing the .cmd entirely:

```cmd
python src\confirm_positives.py --set final --pool pool --models a,b,c
```

## What needs the SAIA token

| Phase | Needs | Notes |
|-------|-------|-------|
| Prepare working copy (`prepare_workingset.py`) | full corpus | reads the slow corpus once per sample; copies to `.workingset/` |
| A — machine annotation (`annotate_lni.py`) | PDFs + token | `--dry_run` needs PDFs only (no token); run on `.workingset/<name>` for samples |
| A2 — narrowing collect (`narrow_categories.py --mode collect`) | PDFs only | reuses Phase A checkpoints; `--annotate_missing` adds token |
| A2 — narrowing review (`narrow_categories.py --mode review`) | nothing | reads the candidates CSV; pure human curation |
| B — goldstandard coding (`build_goldstandard.py`, `compute_icr.py`) | PDFs only | reads Phase A annotations; opens PDFs in browser |
| C — LLM selection (`benchmark_models.py`) | PDFs + token | one pass over the coded papers per candidate; `--dry_run`/`--score_only` are free |
| C — full-corpus annotation + aggregation | PDFs + token | the 3-model panel, one call per paper per model, majority vote |

The offline path (PDF extraction + prompt building, `--dry_run`) runs without a
token; only the SAIA annotation calls need credentials.
