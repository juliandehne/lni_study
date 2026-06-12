# Method — A Typology of Research Software in LNI Publications

> Scaffold for the paper's method section (notes step 15). Grows as the study
> progresses. Target venue: ICSE 2027.

## 1. Motivation and scope

We study the kinds of research software (RSE) produced in computer-science
research. CS research is a deliberately favourable setting: software artifacts
there are more likely to be tied to software-engineering techniques than software
built incidentally in other sciences. To obtain a legally accessible, concentrated
corpus of CS publications, we restrict the study to the **Lecture Notes in
Informatics (LNI)** series of the Gesellschaft für Informatik (GI).

## 2. Corpus

LNI publication PDFs, organized by volume (`lni37`, `lni52`, `lni132`, `lni169`,
`lni273`, `lni308`, `lni338`, …). Text, title, authors, abstract, and references
are extracted heuristically with the LNI-tuned extractor reused from the DeLFI
study (`pdf_text_extraction.py`). *(TODO: final corpus size, volume/year span,
extraction success rate, exclusion of corrupted PDFs.)*

**Sampling.** Where a sample of the corpus is needed (the bootstrap test runs and
the subcategory-narrowing step), papers are drawn by **stratified sampling with
the LNI volumes as strata** and proportional (largest-remainder) allocation, so
each sample is balanced across volumes of very different sizes rather than
concentrated in the largest. Draws are deterministic (seeded) for
reproducibility (`src/sampling.py`).

## 3. Typology (coding scheme)

Annotation proceeds in two steps. A paper is first gated on whether it contains
**research software** (working definition below); the typology is coded only for
papers that pass the gate.

> **Research software (gate).** Source files, algorithms, scripts, computational
> workflows, libraries, and executable programs created, extended, or substantially
> adapted for a research purpose. Mere use of general-purpose off-the-shelf software
> without own development effort does not count.

The typology has four dimensions (seed subcategories shown; the bootstrap phase
expands these):

1. **Position in the research process** (`research_position`) — data acquisition,
   data analysis, simulation/modelling, human-facing intervention,
   visualization/dissemination, infrastructure/tooling. *(Primary analytical focus
   of the paper, per the notes.)*
2. **Methodology** (`methodology`) — design-based, classical SE, agile, data-science
   pipeline, ad-hoc scripting, formal methods.
3. **Type of software** (`software_type`) — script, library/package, full-stack
   application, numerical/mathematical, embedded, web service/API, plugin/extension,
   notebook.
4. **Techstack / languages** (`techstack`, multi-label) — Python, Java/JVM,
   JavaScript/web, C/C++, C#/.NET, R, MATLAB, SQL/DB, other.

The full, versioned scheme lives in `src/categories.py`.

## 4. Annotation procedure

### 4.1 Machine annotation (bootstrap)
Each paper is annotated by an LLM via the KISSKI SAIA API, prompted (in German,
matching the corpus language) with the gate definition and the four dimensions
including seed subcategories. For every dimension the model returns its chosen
category, a **certainty** value, and—when no seed fits—a **suggested new
subcategory** (`annotate_lni.py`, `prompts/rse_typology_prompt_v1.md`). We collect
new suggestions until ~100 papers have triggered at least one (notes step 7).

### 4.2 Subcategory narrowing
Before the goldstandard coding, the typology is narrowed on a **stratified
50-paper sample** (volumes as strata). For each dimension the candidate
subcategories — the seed categories plus every new subcategory the models
suggested for the sampled papers — are reviewed by a human who **accepts or
rejects each one and records an explanation** (`narrow_categories.py`). The
result is an explicative **white/blacklist** (`prompts/category_whitelist.json`):
confirmed subcategories with usage guidance, and rejected ones with the reason
and the preferred alternative. This curated guidance is then injected into the
annotation prompt and shown to the human coders, so both the model and the
coders work from a consolidated, narrowed set of subcategories.

### 4.3 Goldstandard creation
Two human coders validate the bootstrapped categories interactively
(`build_goldstandard.py`): for each gate-positive paper the coder reviews the PDF
and either accepts the model's category, picks an existing one, or introduces a
new, agreed-upon subcategory. Coders see each other's accepted new categories to
converge on shared names. *(TODO: number of coders, papers coded, consolidation
rules.)*

### 4.4 Intercoder reliability
Reliability between the two coders is computed per dimension with Krippendorff's
alpha (nominal), Cohen's kappa, and raw agreement (`compute_icr.py`).
*(TODO: report values.)*

### 4.5 Full-corpus annotation and aggregation
With the consolidated scheme fixed, the full corpus is annotated by **three LLMs**
with repeated runs; final labels are chosen by **majority voting**, reusing the
aggregation design from the DeLFI study
(`rse-elearning-evaluation/analysis/label_aggregation/`). *(TODO: models, runs,
aggregation rules, disagreement handling.)*

## 5. Analysis

Descriptive statistics of the distribution of RSE categories across the corpus,
with particular attention to the **position in the research process** dimension —
i.e., where in the research lifecycle CS research software is concentrated.
*(TODO: tables/figures from `descriptive_stats.py`.)*

## 6. Threats to validity

*(TODO: PDF extraction errors; LLM annotation bias and per-model liberality—cf. the
DeLFI label-distribution analysis; German/English language mix; LNI corpus
representativeness for CS research at large; gate sensitivity.)*
