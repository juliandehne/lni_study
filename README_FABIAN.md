# README_FABIAN — the LLM selection and the final-study test

Two steps, run in this order:

| # | step | what it decides | token cost |
|---|------|-----------------|-----------|
| 1 | **LLM selection** (`bench`) | *which* LLM annotates the study | ~1 call per paper per candidate model |
| 2 | **final-study test** (`full … test`) | whether the study run itself works, on a tiny isolated subset | ~1 call per pretest paper |
| 3 | final study (`full`) | the actual data | hundreds of calls, hours |

Everything below is run from the `lni_study` folder.

---

## 0. Once, before anything

```cmd
run_pipeline.cmd deps
```

You need a SAIA token (KISSKI / GWDG academic cloud). Either

* put `SAIA_API_KEY=...` into `.env` (copy `.env.example`), or
* pass the token as the **second** argument of every step: `run_pipeline.cmd bench <token>`.

Check that the token works and see what SAIA currently serves:

```cmd
python src\preflight.py --list_models
```

> The LLM selection reads PDFs from `.workingset\gold_confirmed`, which is a local
> cache — **no VPN / Z: drive needed**. The final study does need the corpus.

If you prefer a menu over remembering arguments, run `menu.cmd` (or
`python src\pipeline_menu.py`): it walks you through every step and asks for each
option. The LLM selection is the **`bench`** entry under *Final study*, directly above
`full`.

---

## 1. The LLM selection — `run_pipeline.cmd bench`

### What it does

Our humans coded ~150 papers by hand into `goldstandard\coding_<coder>.csv`. This step
lets **every candidate model re-annotate exactly those papers** and measures how close
each one comes to the humans:

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

**How the winner is picked:** one F score over the whole goldstandard, highest wins.
Nothing is trained and nothing is held out — every model annotates every gold paper
exactly once and is scored against the humans on all of them. There is no
cross-validation and no averaging over splits, on purpose: the ranking should be the
simplest thing that can be checked by hand, and the tables below are how you check it.

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

### What it writes — `results\model_selection\`

| file | for |
|---|---|
| `model_selection.json` | **the machine**: the winner, read by the final-study step |
| `model_selection.md` | **you**: the ranking, per-dimension and per-category tables |
| `model_scores.csv` | every metric in long format, for plotting / the paper |
| `category_scores.csv` | one row per (model, dimension, **category**) — see below |
| `paper_comparison.csv` | one row per (model, **paper**, dimension) — see below |
| `predictions_<model>.csv` | each model's raw answers (resume data + error inspection) |

Read `model_selection.md` first. The summary line to look at is e.g.

```
Winner: qwen3.5-122b-a10b - overall 0.741; +0.043 over mistral-medium-3.5-128b (0.698)
```

If the margin is under 0.02 the report says **"NARROW margin, treat the two as tied"** —
in that case pick on other grounds (speed, price, availability), don't read it as a
result.

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

`model_selection.md` already prints the winner's worst 40 categories. For anything
beyond that:

```cmd
run_pipeline.cmd bench "" "" score        :: regenerate the tables, free
jupyter lab notebooks\model_selection.ipynb
```

The notebook is a **stub** — it loads the three CSVs and gives you the ranking,
per-dimension and per-category views, a drill-down into one category, the papers *no*
model got right, and the gate confusion matrix. Extend it as you like; nothing else
reads it.

### Changing which models compete

Edit `DEFAULT_CANDIDATES` at the top of `src\benchmark_models.py`, or bypass the .cmd:

```cmd
python src\benchmark_models.py --models mistral-medium-3.5-128b,qwen3.5-122b-a10b
```

Model ids are verified against the live SAIA catalogue before anything is spent —
retired ids are dropped with a warning instead of failing 100 calls in.

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

---

## 2. The final-study test — `run_pipeline.cmd full <token> <n> test`

Before the multi-hour real run, do a **pretest**: the same code path, on a handful of
papers, in an isolated folder that can never touch the real study's data.

```cmd
run_pipeline.cmd full <token> 5 test
```

* draws 5 papers from `.workingset\final` into `.workingset\full_study_pretest`,
* annotates them with the **model the `bench` step selected** (the step prints
  `--- final-study model: <id> ---` before it starts; if no bake-off has been run it
  falls back to the pin and says so),
* keeps annotating, topping up from `\final`, until 5 papers are LLM-confirmed as
  research software,
* writes them to `.workingset\full_study_pretest_confirmed` with its own checkpoint —
  the real study's checkpoint and `final_confirmed` folder are untouched.

**Check before going further:** open the checkpoint under `results\checkpoints\` (its
name contains `full_study_pretest`) and verify that `llm_error` is empty, that the
`model` column shows the model you expect, and that the typology columns are filled and
plausible. If the pretest is clean, the real run is just the same command without
`test`:

```cmd
run_pipeline.cmd full <token> 500
```

That confirms 500 research-software papers into `.workingset\final_confirmed`, topping
up from `\pool` as it goes. It is resumable in the same way — re-running continues where
it stopped.

---

## How the two steps are connected

The `bench` step writes the winner; the final study reads it. Nothing else in the
pipeline changes model:

```
bench ──► results\model_selection\model_selection.json ──► full  (annotates with the winner)

           everything else (narrowing loop, goldstandard steps)
           keeps the pinned model in src\preflight.py
```

The pinned model stays pinned on purpose: annotation checkpoints are named after the
model *family*, so repointing the goldstandard steps mid-study would orphan the
annotations already collected. The final study is the one place where the model is still
an open question, so that is the only place the selection applies.

To see what the final study *would* use, without running anything:

```cmd
python src\preflight.py --print_selected_model
```

**To override the selection:** delete (or rename) `model_selection.json` and the pipeline
falls back to the pinned model; or edit the `"winner": {"model": ...}` field in that file
to force a specific id.

---

## If something goes wrong

| symptom | cause / fix |
|---|---|
| `no usable coding_*.csv` | wrong `--shared_folder`, or the goldstandard has not been coded yet |
| `[bench] model catalogue unavailable - candidates NOT verified` | no token, or SAIA unreachable — candidate ids were not checked, the run may fail per model |
| a model shows **DISQUALIFIED (coverage)** | it failed to return parseable JSON too often; look at its `predictions_<model>.csv` `llm_error` column |
| the run stops for minutes at a time | the rate limiter waiting out the 10/min or 200/h SAIA limit — expected |
| `full` prints the pinned model, not the winner | no `model_selection.json` under the current data root (`LNI_DATA_ROOT`); run `bench` first |
| everything is slow / VPN prompts | `bench` needs no VPN; `full` does, because it reads the corpus |
