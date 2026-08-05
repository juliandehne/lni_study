# README_FABIAN — the LLM selection and the final-study test

Two steps, run in this order:

| # | step | what it decides | token cost |
|---|------|-----------------|-----------|
| 1 | **LLM selection** (`bench`) | *which three* LLMs annotate the study | ~1 call per paper per candidate model |
| 2 | **final-study test** (`full … test`) | whether the study run itself works, on a tiny isolated subset | ~1 call per pretest paper **per panel model** |
| 3 | final study (`full`) | the actual data | hundreds of calls per panel model, hours |

The study is annotated by the **three best-scoring models together**: each paper goes to
all three and their answers are merged by **majority vote**. That is what step 1 decides
— not a single winner, a panel of three.

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

### What it does, in one paragraph

Our humans coded ~150 papers by hand into `goldstandard\coding_<coder>.csv`. This step
lets **every candidate model re-annotate exactly those papers** and scores it against the
humans — the gate (`label_research_software`) as macro-F1, the five typology dimensions
by exact match / micro-F1, combined into one `overall`. **One F score over the whole
goldstandard, nothing trained, nothing held out.** The **three best** above the coverage
floor become the **annotation panel**; the best of them is the *lead* and breaks ties.
The final study then annotates every paper with all three and merges their answers by
majority vote.

> **The full reference — every metric, the exact voting rules, the output tables, how to
> change the candidate slate or the panel size — is in
> [`README.md` → LLM selection](README.md#llm-selection--picking-the-annotation-panel-bench).**
> What follows here is just how to run it.

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

### What to look at afterwards

Everything lands in `results\model_selection\`. Read **`model_selection.md`** first; the
line that matters is the panel:

```
Panel: qwen3.5-122b-a10b (0.741), mistral-medium-3.5-128b (0.698), llama-3.3-70b (0.681)
       ; last panel seat +0.012 over gemma-3-27b (0.669) - NARROW, that seat is
       effectively a coin flip
```

`*` marks the lead in the overall table, `+` the other two seats. A **NARROW** last seat
is worth a look but not a problem — the panel votes, so a near-tie between seat 3 and
seat 4 changes the outcome much less than a near-tie used to when one model decided
alone. The same folder has `category_scores.csv` (per category: precision/recall/F1 and
human vs model support) and `paper_comparison.csv` (per paper: agree / partial /
disagree, which keys were missed or added); `notebooks\model_selection.ipynb` is a stub
that loads them. `run_pipeline.cmd bench "" "" score` regenerates all tables for free.

Two things worth knowing:

* Only coded papers whose PDF sits in `.workingset\gold_confirmed` are re-annotated, and
  that cache leans toward *accepted* papers — the step prints a `[config] NOTE` telling
  you how skewed the gate measurement is. Typology scores are unaffected.
* `goldstandard\` holds several coding files; left alone the step takes the one with the
  most decided papers and says which. `run_pipeline.cmd bench <token> "" "" bob` scores
  against `coding_bob.csv` instead.

Details for both, plus how to change the candidate slate (`DEFAULT_CANDIDATES` in
`src\benchmark_models.py`) or the panel size, are in
[`README.md`](README.md#llm-selection--picking-the-annotation-panel-bench).

---

## 2. The final-study test — `run_pipeline.cmd full <token> <n> test`

Before the multi-hour real run, do a **pretest**: the same code path, on a handful of
papers, in an isolated folder that can never touch the real study's data.

```cmd
run_pipeline.cmd full <token> 5 test
```

* draws 5 papers from `.workingset\final` into `.workingset\full_study_pretest`,
* annotates them with the **panel the `bench` step selected** (the step prints
  `--- final-study panel: <a>,<b>,<c> ---` before it starts; if no bake-off has been run
  it falls back to the single pinned model and says so),
* asks each panel model separately and merges the three answers by majority vote — so
  5 pretest papers cost **15 calls**, not 5,
* keeps annotating, topping up from `\final`, until 5 papers are LLM-confirmed as
  research software,
* writes them to `.workingset\full_study_pretest_confirmed` with its own checkpoint —
  the real study's checkpoint and `final_confirmed` folder are untouched.

**Check before going further:** open the checkpoint under `results\checkpoints\` (its
name contains `full_study_pretest` and `panel3`) and verify that `llm_error` is empty,
that the `model` column lists the models you expect (`a+b+c`), and that the typology
columns are filled and plausible. Then glance at the two panel columns:
`panel_gate_votes` shows the individual gate answers (`1|1|0`, `-` = that model errored)
and `panel_dissent` names the fields the models disagreed on — a couple of split rows is
normal, *every* row splitting means one seat is misreading the prompt. The per-model
answers are in the `..._votes.csv` next to the checkpoint. The run also prints a summary
like `Panel (a + b + c): 2/5 paper(s) with any disagreement, 0 of them on the gate
itself.` If the pretest is clean, the real run is just the same command without `test`:

```cmd
run_pipeline.cmd full <token> 500
```

That confirms 500 research-software papers into `.workingset\final_confirmed`, topping
up from `\pool` as it goes — with a panel of three that is ~1500 calls, so budget the
time accordingly. It is resumable in the same way: re-running continues where it
stopped.

---

## How the two steps are connected

The `bench` step writes the panel; the final study reads it. Nothing else in the
pipeline changes model:

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
python src\preflight.py --print_selected_panel
```

**To override the selection:** delete (or rename) `model_selection.json` and the pipeline
falls back to the single pinned model; or edit the `"panel"` list in that file to force
specific ids (keep `"winner"` equal to the first entry — that is the lead).

---

## If something goes wrong

| symptom | cause / fix |
|---|---|
| `no usable coding_*.csv` | wrong `--shared_folder`, or the goldstandard has not been coded yet |
| `[bench] model catalogue unavailable - candidates NOT verified` | no token, or SAIA unreachable — candidate ids were not checked, the run may fail per model |
| a model shows **DISQUALIFIED (coverage)** | it failed to return parseable JSON too often; look at its `predictions_<model>.csv` `llm_error` column |
| the run stops for minutes at a time | the rate limiter waiting out the 10/min or 200/h SAIA limit — expected |
| `full` prints one pinned model, not a panel | no `model_selection.json` under the current data root (`LNI_DATA_ROOT`); run `bench` first |
| a panel of **two**, not three | fewer than three candidates cleared the 90 % coverage floor; an even panel needs unanimity and the lead decides every tie — widen `DEFAULT_CANDIDATES` and re-run `bench` |
| `panel_dissent` says `all_failed` | every panel model errored on that paper (usually PDF text extraction or a timeout); look at the `..._votes.csv` |
| everything is slow / VPN prompts | `bench` needs no VPN; `full` does, because it reads the corpus |
