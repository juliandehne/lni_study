# lni_study — task log

_Last updated: 2026-08-04. This file is the durable, on-disk progress record for
the lni_study pipeline (see the `task-logging` / `recover-work` skills). It has a
**State** snapshot (overwritten each update) and an **append-only Log** (newest
first, never edited)._

## State  (current snapshot — overwrite each update)

- **CURRENT (2026-08-04 — assisted gold coding, 17 papers decided, 11 schema
  sharpenings landed, remote `main` merged; the mid-day session died and was
  reconstructed by `recover-work`, then coding resumed in the same evening
  session):** coding only, **no pipeline and no token spend**.
  `goldstandard/coding_alice.csv` moved
  **65 → 79 accepted / 62 → 65 rejected / 127 → 144 decided** against
  `RS_TARGET = 100`; the frontier is now **paper 84/202** in the frame
  `results/checkpoints/annotations_goldconfirm_mistral_rse_typology_prompt_v1_run_1_checkpoint.csv`
  filtered `label_research_software == 1`. `LNI_DATA_ROOT` is **unset**, so the
  data root is the repo itself.
  **Integrity after the crash: clean.** `gold_peek` reports **0 half-coded
  papers**; every one of the 140 decided papers carries either 6 dimension rows
  (accept) or exactly 1 (gate-0 reject); the last write of the dead session was
  `SCHEMA_CHANGELOG.md` (11:53), i.e. the last round closed normally. Nothing was
  lost and nothing needed repairing — only this file was stale.
  **Decided 2026-08-04 (frame positions 66–78), 10 accept / 3 reject:**
  `lni101/111` gate 0; `lni101/191` (Unternehmensvergleich Milchrind) accept —
  `product_result` / `…;deployment_betrieb` / `full_stack_application;middleware_service`
  / `sql_db;xml_xsd;javascript_web` / `insufficient_information`; `lni101/199`
  (Geodaten) accept — `product_result` / `domain_specific_language` / `xml_xsd` /
  `conceptual_evaluation`; `lni101/47` accept — `product_result` /
  `full_stack_application` / `flash_animation_tools` / `insufficient_information`;
  `lni103/542` accept — `middleware_service` / `java_jvm;sql_db` /
  `performance_evaluation;alternatives_comparison`; `lni104/103` (Ambient
  Learning Spaces) accept — `middleware_service;plugin_extension` / `xml_xsd` /
  `conceptual_evaluation`; `lni105/251` accept — **`formal_verification`** /
  `full_stack_application` / `formal_specification_languages` /
  `insufficient_information`; `lni106/101` gate 0; `lni106/297` (kontraktbasiertes
  Black-Box-Testen) accept — `middleware_service` / `java_jvm;xml_xsd` /
  `conceptual_evaluation`; `lni106/337` (Image Retrieval) accept —
  `full_stack_application` / `java_jvm;sql_db` / `planned`; `lni107/105` gate 0;
  `lni109/202` (Bandara, semantic service matching) accept —
  `proof_of_concept_product` / `middleware_service` / `java_jvm;xml_xsd` /
  `empirical_study`; `lni109/57` (Dahl & Derigs, Tourenplanungs-DSS) accept —
  `product_result` / `…;deployment_betrieb` / `full_stack_application` /
  `csharp_dotnet;sql_db` / `insufficient_information`.
  **Then, after the recovery, position 79:** `lni109/570` (Cermak-Sassenrath, *MR
  Auto Racing*, tabletop MR game, artecLab Bremen) accept — `product_result` /
  `projektdefinition;anforderungen;entwurf;implementierung;testen_qualitaetssicherung`
  / `vr_application` / `insufficient_information` / `testing`. Three calls went
  against the model: no `deployment_betrieb` (the only public deployment is future
  tense — one GI workshop in Sept 2007 — and the lab play sessions are the tests);
  no `full_stack_application` alongside `vr_application` (the full-stack key's own
  precedence clause defers to it); no `usability_study` (see the schema entry
  below). The model proposed `mixed_reality_application`, which is the whitelisted
  synonym of `vr_application` — the `examples:` list did its job.
  **Position 81:** `lni110/100` (Dästner/Kausch/Opitz, *An Object Oriented
  Approach for Data Fusion*, ATLAS ELEKTRONIK + EADS) accept — the
  commercial-product exclusion in the gate needs **all three** of its conditions
  and fails here, because the suite exists to support a research process (rapid
  prototyping, "simulation, test and evaluation of data fusion systems"):
  `product_result` / `projektdefinition;entwurf;implementierung` /
  `library_package;full_stack_application;numerical_mathematical` /
  `c_cpp;xml_xsd` / `insufficient_information`. Six calls went against the model:
  no `testen_qualitaetssicherung` (the 08-04 clause — that the *tool* tests other
  software is not the phase); no `middleware_service` (the paper says the
  middleware is application-specific and external, "the interfaces are separated
  from the pure data fusion kernel" — this is what triggered the sharpening
  below); no `analysis_pipeline` (a processing chain *inside* the artefact does
  not make it one); no `domain_specific_language` for the XML configuration (a
  config language inside a larger system codes the system's type); no `testing`
  or `performance_evaluation` (nothing is measured; "real-time" is an
  architectural claim); no `deployment_betrieb`.
  **Position 82:** `lni110/247` (Staiger, *Statische Analyse von graphischen
  Oberflächen*, Bauhaus-Projekt Uni Stuttgart) accept —
  **`proof_of_concept_product`** /
  `projektdefinition;anforderungen;entwurf;implementierung` / `analysis_pipeline`
  / **`insufficient_information`** / `testing;performance_evaluation`. Four calls
  against the model: `proof_of_concept_product` not `product_result` (the
  contribution is the analysis *algorithm*, the Bauhaus implementation is its
  vehicle — maturity is explicitly a different axis); no
  `testen_qualitaetssicherung` although §4 is titled "Tests und Ergebnisse" (it
  reports recognition rates and runtimes, which the 08-04 clause routes to
  `evaluation`); `techstack = insufficient_information` against the model's
  `c_cpp` at certainty **1.0** (C/C++/GTK/Qt are the *analysed* systems; the
  paper never says what the analysis is written in — this triggered the
  sharpening below); and `analysis_pipeline` alone, `plugin_extension` rejected
  because Bauhaus is the authors' own infrastructure, not a foreign host system.
  **Position 83:** `lni110/58` (Hackelbusch & Winkels, *Stud.IP um ein
  ontologiebasiertes Curriculums-Planungsmodul erweitern*, Uni Oldenburg) accept
  — `product_result` / `projektdefinition;entwurf;implementierung` /
  `plugin_extension;full_stack_application` / `php;java_jvm;xml_xsd` /
  **`planned`**. Two components: a bewusst dünnes PHP-Plugin ("nur noch für die
  Aufbereitung der Webseiten selbst zuständig") plus die Java-Webapplikation
  EUSTEL mit der gesamten Geschäftslogik, JENA/OWL und Diensten "über Servlets
  und Webservices". Four calls against the model (all at certainty 1.0): no
  `middleware_service` — this is the first paper decided by the freshly landed
  lower bound, EUSTEL nimmt zwar Daten aus Stud.IP, HIS-POS und LVP entgegen,
  vermittelt aber nicht zwischen ihnen, sondern rechnet daraus einen Studienplan
  für das eigene Frontend (Webservices sind Auslieferungsform, nicht Zweck);
  `plugin_extension` **und** `full_stack_application` zusammen, weil die
  Vorrangklausel des Full-Stack-Keys nur greift, wenn *ein* Artefakt beschrieben
  wird — EUSTEL ist ausdrücklich auch autonom an andere Systeme anbindbar; no
  `testen_qualitaetssicherung` und kein `testing` (die Verifikation steht im
  Futur, "verifizieren wollen" → `planned`); no `sql_db` (MySQL charakterisiert
  nur Stud.IP) und kein `javascript_web` (vom Modell aus "webbasiert"
  erschlossen, nirgends benannt). `php` wurde erneut über `--new-category` in
  `goldstandard/new_categories_alice.csv` geschrieben — zweiter Beleg für
  Queue-Punkt 2. Queue-Punkt 5 wurde *nicht* strittig: Stud.IP ist unstrittig ein
  fremdes Wirtssystem, was die Lesart stützt, dass dort nur die Eigen-
  Infrastruktur offen ist.
  **Eleven schema sharpenings landed in `prompts/category_schema.yaml`**, each with
  a dated `SCHEMA_CHANGELOG.md` entry naming its trigger paper and listing every
  already-coded row that carries the key under the old wording (no-recoding policy
  holds; all are description-only): `evaluation.planned` (productive operation ≠
  announced evaluation), `techstack.xml_xsd` (XML-serialised exchange/description
  languages count when named), `techstack.sql_db` (a named database suffices,
  generic persistence does not), `software_lifecycle.testen_qualitaetssicherung`
  (a testing tool's *function* is not the phase), `techstack.javascript_web`
  (requires own web-frontend work), the `evaluation` dimension itself (codes only
  what the paper reports), `software_type.domain_specific_language` (covers
  implemented exchange schemas), `evaluation.conceptual_evaluation` (re-anchored
  on the object of evaluation), and `evaluation.usability_study` (requires an
  evaluation laid out as a collection — recognisable method, named participants,
  reported result; an anecdotal experience report of use reaches it NOT and codes
  `testing` or `insufficient_information`; 9 rows listed under the old wording),
  and `software_type.middleware_service` (a lower bound: the artefact must itself
  BE the mediating layer — take input from at least two sides and translate,
  forward or orchestrate between them; middleware as *environment* does not
  count, and the delivery form separates it from `library_package`; 36 rows
  listed under the old wording across alice/bob/lukka), and the **`techstack`
  dimension question** (only the stack the software is itself built with or runs
  on is coded; a language the artefact merely *processes* — the target language
  of an analysis/migration/test tool, a generator's output language, the
  technology of analysed foreign systems — is not its stack, and a paper that
  names only those is `insufficient_information`). That last one is the **first
  changelog entry that cannot enumerate its affected rows**: a row stores
  `c_cpp`, not the reason for it, so nothing in the CSV separates "implemented
  in C++" from "analyses C++"; the entry states the upper bound (alice 52 / bob
  31 / lukka 11 substantive `techstack` rows) instead of a list.
  Verified present in the SSOT and the schema still parses via `schema_io`.
  **Remote `main` was merged** (`3cbafb0`). Both conflicts resolved
  semantically, not textually: `prompts/category_schema.yaml` was an add/add of
  `evaluation.alternatives_comparison` where theirs carried an empty
  `description:` (which `src/` silently drops from the model prompt) — ours kept.
  `goldstandard/coding_alice.csv` resolved **`--ours` in full**, on evidence from
  a 3-way set merge keyed by `(id, coder, dimension)`: base 122 papers / 432
  rows, ours 141 / 521, theirs **98 / 303**; papers in theirs but not in base:
  **0**; in theirs but not in ours: **0**; 24 papers present in base were missing
  from theirs. The only remote commit touching the file (`012f729`, +3/−132) was
  therefore a stale truncated checkout, not new coding, and its three value
  differences were all regressions from an older tool version dropping an unknown
  category token (`lni214/185`, `lni55/GI-Proceedings.55-17` lost
  `hpc_parallel_computing`; `lni71/GI-Proceedings.71-13` had `is_new` flipped).
  **Do not re-litigate this** — nothing was discarded. Noted in passing:
  lukka's own file has two half-coded papers, `lni360/B6-2` (5 rows) and
  `lni94/GI-Proceedings-94-1` (2 rows).
  **SCHEMA QUEUE — 3 of the 6 items queued on 08-03 are still NOT landed**
  (verified against the SSOT on 08-04; items 1 `conceptual_evaluation`, 5
  `sql_db` and the `middleware_service`/`analysis_pipeline` boundary were landed
  today, the rest await a triggering paper):
  1. `research_position.human_facing_intervention` vs `product_result` — decisive
     is whether use with humans is part of a research design reported in the
     paper. Rows coded under the old wording: alice `lni369/paper-52`,
     `lni373/B2-1`; bob `lni176/91`, `lni300/B5-01`.
  2. `techstack` still has **no** container/virtualization key (Docker, K8s,
     Rancher) — proposed `container_virtualization`; and `php` still sits only in
     `goldstandard/new_categories_alice.csv`, not in the SSOT's `active` list.
     This is the one queued item that *adds* keys rather than sharpening prose.
  3. The gate (`label_research_software.definition_de`) still does not state the
     boundary between infrastructure/teaching-service operation and research
     software — the model keeps proposing such papers at high confidence.
  4. (new, 08-04) `software_type.numerical_mathematical` says nothing about
     combining with `library_package` — `lni110/100` carries both and the
     decision rested on judgement, not on the prose.
  5. (new, 08-04) `software_type.plugin_extension` does not say whether the host
     system must be a *foreign* one. `lni110/247` runs only on Bauhaus'
     intermediate representation, yet Bauhaus is the authors' own suite — the
     key was withheld on that reading, which the prose does not carry.
  **Next action: keep coding at paper 84/202** (`lni113/147`, Lohmann & Ziegler,
  *Partizipationsformen und Entwicklung eines gemeinsamen Verständnisses bei der
  verteilten Anforderungserhebung* — SoftWiki; the title reads like a pure
  concept paper, so the gate needs care) — run
  `python ~/.claude/skills/lni-coding/scripts/gold_peek.py --username alice`,
  then read `.workingset/gold_confirmed/lni113/147.pdf` in full before proposing.
  21 more accepts to reach `RS_TARGET = 100`.

- **PRIOR (2026-08-03 — assisted gold coding, 4 papers decided; the procedure is
  now a skill):** the whole day is **coding, no pipeline and no token spend**.
  `goldstandard/coding_alice.csv` moved **63 → 65 accepted / 60 → 62 rejected /
  123 → 127 decided** against `RS_TARGET = 100`; the frontier is now **paper
  66/202** in the frame
  `results/checkpoints/annotations_goldconfirm_mistral_rse_typology_prompt_v1_run_1_checkpoint.csv`
  filtered `label_research_software == 1`. `LNI_DATA_ROOT` is **unset**, so the
  data root is the repo itself.
  **Decided today (all four PDFs read in full first):**
  `316/DELFI_2021_187-192` (EduGame→Kompetenz-Mapping) **accept** —
  `product_result` / `projektdefinition;anforderungen;entwurf;implementierung;testen_qualitaetssicherung`
  / `middleware_service` / `php;csharp_dotnet` / `conceptual_evaluation;testing`;
  `316/DELFI_2021_205-216` (Cook.UP) **gate 0 — the user's call**: a
  teaching/operations service, "not tied to a concrete research process" (the
  paper itself only calls research use "feasible to consider", Kap. 8);
  `316/DELFI_2021_85-90` (360°/VR im Fremdsprachenunterricht) **gate 0** decided
  alone under gate-0 autonomy — a seminar-design practice report over
  off-the-shelf products, no engineering reported;
  `316/DELFI_2021_91-96` (InteractionSuitcase VR, CoTeach/BMBF) **accept** —
  `human_facing_intervention` /
  `projektdefinition;anforderungen;entwurf;implementierung` / `vr_application` /
  `insufficient_information` / `planned` (every evaluation in that paper is
  future tense, RQ2+RQ3 are marked "forthcoming").
  **One new category declared:** `techstack|php` in
  `goldstandard/new_categories_alice.csv` — it was used in the data but stood in
  neither `active` (n=20) nor `rejected` (n=21) of the schema; known gap,
  `SCHEMA_CHANGELOG.md` §E.
  **New skill `lni-coding`** (`~/.claude/skills/lni-coding/`) — see the Log entry
  below for what it contains and why.
  **SCHEMA QUEUE — six items agreed but deliberately NOT yet landed** (the rule is
  to batch them, never edit the SSOT mid-round). All are description-only
  sharpenings plus one new `techstack` key; none renames or removes a key, so
  no-recoding holds:
  1. `evaluation.conceptual_evaluation` — an anecdotal experience report without
     method/sample/data counts belongs here; `planned` stays reserved for papers
     that claim no finding at all.
  2. `research_position.human_facing_intervention` vs `product_result` — decisive
     is whether use with humans is part of a research design reported in the
     paper; a tool paper that merely presents a learning environment is
     `product_result`. Check the 4 rows already coded under the old wording first
     (alice `lni369/paper-52`, `lni373/B2-1`; bob `lni176/91`, `lni300/B5-01`).
  3. `software_type.middleware_service` vs `analysis_pipeline` — decisive is
     mediation between two independent systems vs processing data for insight.
  4. `techstack` has no container/virtualization key (Docker, Kubernetes,
     Rancher, docker-compose) — proposed `container_virtualization`; and `php`
     should move from the sidecar into `active`.
  5. `techstack.sql_db`'s description is only the two words "SQL / Datenbanken" —
     sharpen: it counts when the described software itself operates or fills a
     database even without a named DBMS; the mere mention of a third-party
     system's data storage does not.
  6. The **gate** (`label_research_software`) description should state the
     boundary between infrastructure/teaching-service operation and research
     software — the model proposed Cook.UP at 0.95 confidence and will keep doing
     so otherwise.
  Each item goes into `SCHEMA_CHANGELOG.md` §A with the ids coded under the old
  wording. **Next action: keep coding at paper 66/202** — run
  `python ~/.claude/skills/lni-coding/scripts/gold_peek.py --username alice`.

- **PRIOR (2026-07-31, ~11:10 — external-review schema pass DONE and COMMITTED;
  this entry written by a later `recover-work` pass, the pass itself never got to
  update this file):** the whole 07-31 work is the **external review of the
  category system** (`papers/feedback-category-schema.md`, written by a
  collaborator, added as `f55f2e7`) and the resulting sharpening of
  `prompts/category_schema.yaml` (`7801a43`, +296/−36 on the schema, +128 on
  `SCHEMA_CHANGELOG.md`). **Nothing was left half-written** — the session died
  after committing, not mid-edit; the tracked tree is clean and only `.claude/`,
  `annotation_coverage.md` and `papers/.Rhistory` are untracked.
  **Re-verified on 2026-07-31 by the recovery pass, not merely quoted from the
  changelog:** `src/check_schema_integrity.py` → OK (5 dimensions, no duplicate
  keys); key-set diff of `active`/`rejected`/`candidates` per dimension against
  the pre-pass commit `2d82e75` → **0 differences** (so every coded value still
  resolves — the pass changed wording only); `categories.render_categories_block()`
  (23202 chars) + `render_category_guidance_block()` (6494 chars) both render, and
  neither the new `archetype:` fields nor the `reporting.software_type_archetypes`
  block leak into the prompt; all **11** active `software_type` entries carry an
  `archetype`. Read `SCHEMA_CHANGELOG.md` for the per-category detail — it lists
  which already-coded rows were decided under the older wording.
  **Standing policy set this day: NO RE-CODING before the deadline.** Sharpened
  definitions do not trigger re-coding; the paper states the current definitions
  and the changelog carries the provenance. One review suggestion was
  **deliberately declined** by the user (widening
  `research_infrastructure_support` to ELN / research data management) because it
  would change the extension of an already-coded category.
  **The one real thing still owed to the reviewer:** the feedback asks *"Was ist
  die Abbruchsbedingung von `Wiederhole` bei der Studie?"* — the concrete
  saturation criterion of the narrowing loop as actually run. It is answered
  nowhere in the changelog or here; it is a **method-section item for a human**
  (the loop-until-saturation design is described under "Next (in order)" step 4
  below, but the criterion the study actually stopped on is not recorded).
  **Also uncommitted, one level up:** the superproject
  (`juliandehne.github.io`) still points at the old `publications` submodule
  commit — `M publications` there. `lni_study/main` is **3 ahead of
  `origin/main`**; nothing is pushed (the user pushes).
  **Next action is unchanged: keep gold coding** (alice 62/100, bob 38/100,
  lukka 10/100).

- **PRIOR (2026-07-29, late evening — two `build_goldstandard.py` bugs FIXED +
  progress indicator, uncommitted):** the second bug was **silent data loss**:
  `save_decisions` rewrites the CSV in full but iterated `df` (the 202-row frame
  = model gate 1), so every paper decided *outside* that frame was deleted on the
  next save. It had already wiped **38 of alice's 122 papers (43 rows)** at
  20:41:45 — **fully restored** from `fbd0ca0`. Fixed by carrying over off-frame
  papers (with model columns retained by `load_decisions`); verified lossless by
  round-trip for all three coders. Also added the goal-based progress display
  (`RS_TARGET = 100`, `rs_tally`): **alice 62/100, bob 38/100, lukka 10/100**.
  The ~19:00 broken session lost nothing (0 uncommitted rows). Details in the Log.
  **Coders should `git pull` before their next session.**

- **(2026-07-29, evening — resume-anchor bug FIXED, uncommitted):**
  `src/build_goldstandard.py` patched so a gold session opens on the coder's
  **frontier** (new `next_unseen`) instead of on the first `s`=skip, which pinned
  lukka at paper #8 and bob at #14 across every restart. **No coding data was
  lost** — `coding_lukka.csv` grew monotonically over all 9 commits. Verified by
  recomputing anchors on the live checkpoint (lukka #8 → #13, bob #14 → #52,
  alice #61 unchanged) plus 5 synthetic edge cases; the interactive session was
  **not** run. Full write-up in the Log entry below. Open for the coders: lukka's
  4 half-coded papers and bob's #14 must be settled with `i`, not `s`.

- **(2026-07-29, 16:45 — END OF WORKDAY; alice at 122 coded papers):** a
  full afternoon of gold coding landed as `fbd0ca0` *"Gold coding: 24 papers
  (alice), schema refinements"* — `goldstandard/coding_alice.csv` +135 ll.,
  `prompts/category_schema.yaml` +115 ll. Verified: distinct `id`s in
  `coding_alice.csv` **98 → 122**. `main` is **2 ahead of `origin/main`**
  (`0b24e3b`, `fbd0ca0`) — nothing pushed; the tracked tree is clean. The
  worktree `.claude/worktrees/dsr-related-work` is confirmed **0 commits ahead of
  `main`** (its content merged 2026-07-27 as `3b39428`) — nothing stranded there.
  Untracked and undecided: `annotation_coverage.md` (static AST scan, 6/254
  functions annotated = 2%). **Next action is unchanged: keep gold coding** —
  no top-up is owed. Standing: **62 keeps / 60 rejections, 117 papers todo in
  `gold_confirmed`; the next uncoded paper in manifest order is `lni208/1047`
  "Visualisation of Semantic Enrichment"**. Use
  `C:\Users\julian.dehne\AppData\Local\Programs\Python\Python313\python.exe` for
  the manifest/priors lookups (`C:\Program Files\Python313` does not exist here).
  See `.claude/workday-log.md` at the superproject root for
  the cross-repo picture.

- **(2026-07-29, morning — top-up DONE, `gold_confirmed` = 201; the only work left
  is human coding):** `topup --target 150` ran on the repinned
  `mistral-medium-3.5-128b` (`6857adb`). 166 new papers annotated, **102 rs=1**
  (61% positive rate), confirmed 100 → **202**, staged `gold_confirmed` 99 →
  **201**. It overshot the 170 `confirm_target` because the +20 bump fires as
  confirmations approach the goal — budget ~50% above a naive
  `confirm_target − confirmed` estimate next time.
  **The `_excluded` guard held through a live run:** of the 202 rs=1 rows exactly
  one is unstaged, `lni122/LNI-122-Proceedings-komplett`, which is precisely the
  paper the pre-`5c0e317` code would have copied back into the worklist. Manifest
  = PDFs = positives − lni122, zero drift.
  **No `fill-gold` is owed:** the new positives came back with full typology
  (102/102 on every dimension bar one blank `evaluation`), so alice has model
  priors on all of them. `methodology` is 0/102 on the new rows vs 100/100 on the
  old — the retired dimension is correctly gone from the prompt, but it means the
  two generations differ in SHAPE, not just id. That plus the deliberate mixing of
  `mistral-large-3-675b-instruct-2512` (156 rows) with `mistral-medium-3.5-128b`
  (166 rows) in one checkpoint is a **method-section item**; the per-row `model`
  column keeps them separable.
  **Alice's runway: 141 undecided in set** against 40 keeps / 20 rejections. At her
  67% keep rate that is ~94 more keeps — enough to reach 100 **without another
  top-up**. (bob 38 keeps / 150 undecided; lukka 7 / 193.) Next action is simply
  `gold` coding sessions.
  Two new `pdf_extraction_failed` rows (`lni66/GI-Proceedings.66-49`,
  `lni87/GI-Proceedings-87-35`) join the three known ones — scanned/image PDFs, 2
  in 166 is a normal rate.
  Still open: task #11 (is the coding frame `gold` or `gold_confirmed`?),
  `research_position` single-valued in the schema vs `;` multi-values in the gold
  coding, the two empty schema descriptions (`techstack: go`, `software_type:
  ml_model`), and `narrow_confirmed`'s 208-PDFs-vs-202-rows drift.

- **(2026-07-28, night — `gold_confirmed` purged to 99; the top-up that this
  entry called for has since run, see above):** `fill-gold` ran to completion (absent-only over coded
  papers, full refresh over uncoded ones — it cannot touch `goldstandard/`, cannot
  flip the RSE gate, and writes a `.bak` first). It surfaced **24 "orphans"** in
  `gold_confirmed`: manifest rows with no annotation row in any checkpoint. Cause
  was commit `7f16f61` (2026-07-13), which overwrote the tracked goldconfirm
  checkpoint with a stale copy — 188 records / 124 rs=1 truncated to 156 / 100, the
  survivor being a byte-exact **prefix** of the 2026-06-29 state (`4842dff`). The
  manifest, written from the checkpoint, still described the pre-truncation set.
  **None of the 24 was coded by anyone**, so on the user's call they were purged
  rather than restored from git; 23 are still in `pool/` and a top-up can draw them
  again. Also dropped: the two Komplettbände still sitting in staged worklists
  (`lni122/LNI-122-Proceedings-komplett` 481 pp, `lni221/lni-p-221-komplett` 287 pp)
  — the first non-paper sweep covered `gold`/`final`/`pool` but not `*_confirmed`.
  `gold_confirmed` **124 → 99** (= manifest rows = PDFs on disk = checkpoint rs=1
  rows, zero drift), `narrow_confirmed` **203 → 202**; pre-purge manifests kept as
  `manifest.csv.prepurge-bak`.
  **The exclusion was not sticky** until `5c0e317`:
  `confirm_positives._locate_workingset_pdf` scanned every immediate `.workingset/`
  subfolder for a stageable source, `_excluded/` included, so `lni122` (checkpoint
  row still rs=1) would have been re-staged on the next confirm/topup and the purge
  silently reverted. It now skips underscore-prefixed folders; pinned by
  `tests/test_excluded_folder_is_not_a_restaging_source` (verified to fail without
  the guard).
  **Post-purge coder state:** alice 98 coded / 41 keeps (40 in-set) / 20 in-set
  rejections / 39 in-set undecided; bob 51/38/13/48; lukka 8/7/1/91. Alice keeps
  **67%** of model positives (40 of 60). Default topup math (`--target 100`) gives
  `confirm_target = 100 + 20 = 120` → only ~21 new positives → ~80 keeps, short of
  the goal. **Run `topup` with `--target 150`** (→ `confirm_target = 170`, ~71 new
  positives staged, ≈111 SAIA calls at the observed 64% positive rate) to give her
  enough candidates to walk to 100 confirmed research-software papers; `--target
  120` is the cheaper intermediate step. The target is now settable from the menu
  and as `topup`'s 5th positional arg (`5d946d9`); before that it was hard-wired
  to `GOLD=100`.
  **The model blocker described in the older State entries below is CLOSED.** The
  user queried `/v1/models` with a token on 2026-07-28: the live catalogue has no
  `mistral-large-*` at all, but it does serve **`mistral-medium-3.5-128b`**
  (`status: ready`), which is what the pipeline is already pinned to since the
  repin. Family-named checkpoints mean the new calls append to the same
  `..._mistral_...` goldconfirm checkpoint as the existing annotations — mixing
  the two generations is the user's explicit, informed choice, and the exact id
  per row keeps them separable for the method section. Note `mistral-medium-
  3.5-128b` showed `demand: 9`, the highest in the catalogue, so expect worse
  per-call latency than the logged figures.
  Known drift, NOT caused by this purge: `narrow_confirmed` has 208 PDFs on disk vs
  202 manifest rows.

- **(2026-07-28, late — gold-coding DONE (98/98); no top-up is due):**
  All 98 gold papers coded as `alice`: **41 accept / 57 reject**, integrity clean
  (accepts 6 rows each, rejects 1). Model gate priors backfilled from the mistral
  checkpoint (`1015a17`) — 51 of 52 filled; `lni52/GI.-.Proceedings.52-53` stays blank
  because the checkpoint holds `llm_error: pdf_extraction_failed` there (the model
  never saw it), so it is a retry candidate. Gate agreement over the 97 measurable
  papers: **77 = 79.4%**, and **all 20 disagreements are model=1 / alice=0** — the
  LLM gate over-includes; there is not one case where the human accepted and the
  model rejected.
  **No top-up run is due.** `topup_goldstandard` was charging every human rejection
  to the target, but alice coded the raw estimator set `gold` (98), not
  `gold_confirmed` (124) — so 37 of the 57 rejections are papers the LLM never
  confirmed and rejecting them shrinks nothing. Fixed in `ba65386`: only in-set
  rejections count, giving `100 + 20 = 120` against **124 already confirmed**. The
  real next work is the **64 uncoded papers already in `gold_confirmed`** (and, if
  that set is the intended coding frame, the 38 `gold ∖ gold_confirmed` papers are
  extra coverage rather than part of it — 1 of them is an accept, i.e. an LLM false
  negative the human caught).
  **BLOCKER for any future run:** `mistral-large-3-675b-instruct-2512` — the model
  the whole study is pinned to — is **no longer in the GWDG catalogue**. The base URL
  `https://chat-ai.academiccloud.de/v1` is unchanged (only the docs path moved to
  `/services/ai-services/`). `/v1/models` is 401 without a token, so the replacement
  cannot be verified from here; `python src/preflight.py --list_models` prints the
  live catalogue once a token is set, and `confirm_positives` now fails fast on a
  retired id. Choosing the replacement is the user's call, and it makes any new
  annotations non-comparable with the existing checkpoint — a method-section item.
  **Prompt drift fixed** (`1292a75`): the hard-coded answer skeleton still asked for
  the long-removed `methodology` and omitted `software_lifecycle` + `evaluation`. It
  is now rendered from `cat.DIMENSIONS`. Note this means a top-up would annotate with
  a materially different prompt from the one that produced the checkpoint.
  **Estimator recalibrated** (`fcca927`) against the 98 labels: AUC 0.726 → 0.771,
  P@30 0.70 → 0.77. Added `first_person_artifact` and `code_listing`, halved
  `artifact_vocab`. In-sample, bootstrap CI [-0.005, +0.097]. Corpus finding worth
  reporting and deliberately kept OUT of the filter: **English papers are RSE 56% of
  the time, German ones 15%.**
  Still owed by a human: the two empty schema descriptions (`techstack: go`,
  `software_type: ml_model`, both `source: coder:bob`) — silently excluded from the
  prompt until written. Also open: `research_position` is single-valued in the schema
  but the gold coding used `;` multi-values for it.

- **(2026-07-28, evening — gold-coding at 79/99 + a new "not a single paper"
  filter):** Coded three more papers as `alice`: `lni52/GI.-.Proceedings.52-53`
  (accepted, `ae5b6a5`), `lni220/1005` (**rejected**, gate 0, `70656e8`), and then hit
  `lni300/SE-2020-Komplettband` — the **complete 254-page LNI P-300 volume**, not a
  paper. The user's call: remove it from the gold set AND teach the pipeline to filter
  such files. Done both — and then the same thing happened again one paper later, see
  below. Gold set is now **98 papers, 79 coded**; next uncoded is
  **`Modellierung_2022_WS/paper12(1)`** (manifest pos 68).
  **New filter:** `paper_length.is_non_paper(pdf_path, pages, text, max_pages=60)`
  returns a reason string for (1) more than `MAX_PAPER_PAGES`=60 pages, (2) a
  Komplettband/Tagungsband/Inhaltsverzeichnis/front-matter **filename**, or (3) the LNI
  **series page + editor block** in the first 4000 chars; `select_candidates.py` calls
  it in the `estimate` scan loop before the `--min_score` gate, so a collected volume
  can never enter a set however high it scores. New CLI: `--max_pages N` (0 disables
  the page rule) and `--keep_non_papers` (debug escape hatch). Covered by
  `tests/test_non_paper_filter.py` — **39 checks, all passing**, incl. an end-to-end
  `select_candidates` run over synthesized PDFs. The removed PDF sits in
  `.workingset/_excluded/lni300/` with a README (auditable, outside every `<set>/`
  glob, so `--regen_manifests` cannot resurrect it).
  **A fourth rule followed immediately** (`count_contributions`): the next gold paper,
  `lni352/KB_9th_Workshop_Enterprise_Architecture_Management`, was a 41-page bundle of
  **three** contributions that passed all three earlier rules. Rule 4 counts distinct
  per-paper DOIs stamped behind a CC licence badge; N > 1 means a bundled track.
  **PURGE DONE (user-approved).** `gold` 100 → **98**, `final` 500 → **481**,
  `pool` 1350 → **1314**; 57 PDFs archived in `.workingset/_excluded/` with a README.
  All three sets re-verify at 0 non-papers. No coded row was affected (79 papers coded
  before and after). `gold_confirmed` (124), `narrow` (50), `narrow_confirmed` (203)
  were clean to begin with. **Owed in the paper: the study set is 481, not 500.**
- **PRIOR (2026-07-28, morning — recover-work after TWO crashes — NOTHING WAS LOST):** Two
  Claude sessions died this morning (10:33 and 10:40 local). **No file in `lni_study`
  was written today** — the newest file in the whole tree is this `NEXT_STEPS.md`
  (07-27 16:34). The crashed session was **read-only**: it did `/startworkday`, took
  "continue LNI study", opened `lni361/BTW2025-50` and was dumping the model's
  explanations for the contested dimensions when the process was killed. It had **not
  yet proposed any codes and the user had not decided anything**, so there is no
  half-written row, no drift between comments and code, and no recovery edit was owed.
  Gold state re-verified on disk: `goldstandard/coding_alice.csv` = **243 rows / 73
  distinct ids**, `lni361/BTW2025-50` **not present** → still **73/100**, next paper
  unchanged. No pipeline process is running (the two live `cmd.exe` are an idle shell
  and the known F-Secure browser helper, not ours).
  **Crash cause = memory, not the code.** Machine is 15.6 GB physical / 27.1 GB commit
  limit and was at 15.0 GB committed with only 3.2 GB free (Edge, Outlook, Element,
  Dropbox resident). No node crash dump, no WER entry for node, no `.heapsnapshot` —
  the transcripts simply stop mid-tool-result, the signature of an OS/V8 kill. Crash 2
  came 7 min later inside a recursive `Get-ChildItem` over `.claude` (worktrees
  included) — an unbounded directory walk in an already-tight process. **Mitigation for
  the next session: keep tool output small in this project** (this repo's sessions are
  heavy — one transcript on 07-27 reached **57.5 MB**); avoid `-Recurse` over `.claude`,
  avoid re-reading this whole 1484-line file (Grep or `offset`/`limit` a section), and
  close Edge/Outlook before a long coding run.
  **Still owed before more coding (unchanged from 07-27, human-owed):** the two
  collaborator-added schema keys still have `description: ''` — `ml_model`
  (`software_type`, line ~276) and `go` (`techstack`, line ~451), both `source:
  coder:bob`. `categories.py` EXCLUDES empty-description actives from the prompt, so
  they are inert until filled; do NOT auto-author them (the coder's meaning to give).
  **What the crashed session had already pulled up for `lni361/BTW2025-50`** (from the
  `goldconfirm` mistral checkpoint, so it need not be re-queried): `research_position`
  = **EMPTY** (no model answer, no certainty); `techstack` = `java_jvm` @ 0.7 (inferred
  only from the OpenAPI-Generator mention — weak); `evaluation` =
  `testing;conceptual_evaluation` @ 0.9 (technical demo + API-compatibility check, no
  user study, no benchmarking).
- **PRIOR (2026-07-27, end of workday):** Active work is **gold-coding**, not the
  pipeline. Gold set is at **73/100** papers (73 distinct `id`s in
  `goldstandard/coding_alice.csv`). Next uncoded in manifest order:
  **`lni361/BTW2025-50`** (manifest pos 61, vol lni361, 8 pages) — PDF not yet opened,
  nothing mid-analysis. `main` @ `6edf55a`, in sync with `origin/main` (pushed).
  Also merged the DSR related-work chapter (`papers/related_work.qmd` +
  `papers/references.bib`) from the `worktree-dsr-related-work` worktree into `main`
  (`3b39428`), and pulled a collaborator commit (`5a9db03`) that added two schema keys
  with **empty descriptions** — `ml_model` (`software_type`) and `go` (`techstack`) in
  `prompts/category_schema.yaml`; fill these in before they are used in coding.
  Full detail + the resume loop: `../../.claude/workday-log.md` (topmost marker).
- **RESOLVED (2026-06-26 pass 3 is no longer dangling):** the LLM timing instrumentation
  described below as "NOT committed" **is committed** — `api_s` is present in HEAD for
  both `src/annotate_lni.py` and `src/check_fill_gold_parsing.py`, and `src/` is clean.
  The other two asks from that pass (resume the `confirm`/pool top-up; continue the
  `fill-gold` pass for `software_lifecycle`) are still open and still token-blocked.
- **HISTORICAL (2026-06-26, pass 3 — LLM timing instrumentation, INTERRUPTED by user):** Added per-call SAIA
  round-trip timing so slow LLM queries can be profiled. `src/annotate_lni.py` `_complete_with_retries` now
  wraps each `client.chat.completions.create()` with `perf_counter` (`api_s`) and logs it on the `RESPONSE`
  line: `RESPONSE id=… attempt=N api_s=12.34 finish=… chars=… body=…`. Covers BOTH the annotate and
  confirm-positives paths (both funnel through `classify_paper`→`_complete_with_retries`). The existing
  `%(asctime)s` formatter already timestamps every REQUEST/RESPONSE, and REQUEST already logs `prompt_chars`/
  `max_tokens`, so api_s closes the gap (correlate prompt size + time-of-day with round-trip latency). **Both
  files py_compile clean.** **Backward-compat checked & FIXED this pass:** the new `api_s=` token sits between
  `attempt=` and `finish=`, which broke `src/check_fill_gold_parsing.py`'s `RESPONSE_RE` (it required those
  two adjacent → it would silently stop matching new log lines). Made `api_s` an OPTIONAL group in the regex
  so it parses BOTH old logs and new ones; verified old+new sample lines both match and api_s extracts.
  **NOT committed.** **DANGLING (the user's 3 asks for next time):** (1) ~~re-check the timer lines are
  backward compatible~~ DONE this pass (regex fix above) — but re-confirm against any OTHER log reader if one
  surfaces; (2) **resume the topping up** (the token-blocked `confirm`/pool top-up work, see prior CURRENT
  entries); (3) **continue the gold coding** (resume the interrupted `fill-gold`, was 81/100, + the `gold`
  coding pass for `software_lifecycle`). All three are token-blocked. Everything below is historical; trust
  this paragraph where they conflict.
- **CURRENT (2026-06-26, pass 2):** Fixed the `select_candidates.py` score-cache crash (ragged legacy-6-col
  vs new-7-col CSV → tolerant + self-healing reader) AND made the **full study confirm RS on the fly** (see
  top Log entry). The `full` step (real + test) no longer annotates a fixed sample; it reuses
  `confirm_positives.py` in target mode to annotate-and-extend (topping up from `\pool`/`\final`) until **N
  papers are LLM-confirmed research software**, progress bar tracking confirmed/target, materializing
  `.workingset/final_confirmed` (real) / `full_study_pretest_confirmed` (test). The 3rd arg now means "how
  many CONFIRMED RS papers to collect". `pool_manager` report/`pools`/`refill` gained a **`confirmed`**
  column (count in `<set>_confirmed`, no token). For narrow/gold the confirmed split stays the separate
  `confirm`/`advance` step; only the full study folds it inline (as asked). **Offline-verified (NO token):**
  py_compile of all touched files; synthetic ragged-cache parse+heal+reread; live `pool_manager report` shows
  the confirmed column. **DANGLING (token-blocked):** a live `full … test` SAIA pass to exercise the inline
  confirm-and-extend end-to-end. **NOT committed yet.** Everything below is historical; trust this paragraph
  where they conflict.
- **PRIOR (2026-06-26):** Made the full-study step testable + added corpus-fed pool management (see Log
  entry). NEW `src/pool_manager.py` (no-token utility) + new `pools` menu/cmd step ("show pool-sizes and
  refill pools" — reports all five sets narrow|gold|final|pool|full_study_pretest vs target and tops up short
  sets from `LNI_CORPUS` by re-running the cached estimator). The `full` step now asks (menu) how many papers
  to annotate and whether the run is a "test": a test draws an N-paper stratified subset of `.workingset/final`
  into an isolated `.workingset/full_study_pretest` pool (own folder-derived checkpoint tag) and annotates
  that; a real run tops `final` up via `ensure-final` first. All three asks implemented and **offline-verified
  (NO token):** py_compile, synthetic-workroot report/draw-pretest (balanced 2/2 draw, exact-N rebuild),
  ensure-final exit-2 on unreachable corpus. Everything below is historical context; trust this paragraph where
  they conflict.
- **CURRENT (2026-06-23, recover-work pass 2):** Recovered the in-flight `--absent-only`/`preview` work
  left half-saved by the prior session. The crash site was `src/annotate_lni.py` (10:37): `run_fill_missing`
  had drifted from the session's own logged spec — it read an **undeclared** `args.refresh_uncoded` (always
  `False` → full-refresh was dead code, `fill-gold` always gap-filled and **ignored `--absent-only`**).
  Restored to the documented design: `refresh = (not coded) and not args.absent_only` (default = full-refresh
  uncoded / coded absent-only; `--absent-only` holds everyone to gap-fill), plus matching docstring/comments/
  print. The `preview` step (`--preview-prompt`) and the `--checkpoint`/`--skip-rejected` wiring were already
  correct and untouched. **Verified offline (no token):** both files `py_compile`; `--help` shows
  `--absent-only` and no `--refresh-uncoded`; `--preview-prompt` runs clean. **NOT run live:** no SAIA call;
  the regime fix is correct-by-inspection only. See top Log entry. The earlier-today entry below is now
  historical (it describes the same features as *intended*; this pass made the code match).
- **CURRENT (2026-06-23, recover-work):** NO process is running (the round PID 25852 below is GONE —
  finished/stopped; the only live `cmd.exe` is an unrelated F-Secure browser helper). Since the prior
  notes update (06-22 16:40) exactly TWO things changed on disk, both reconciled this pass (see top Log
  entry): (1) **`fill-gold` WAS RUN LIVE on 06-22 19:54** (the prior notes called it token-blocked/not-run)
  — it populated `software_lifecycle_*` in the gold model checkpoint
  `annotations_goldconfirm_…_run_1_checkpoint.csv` and made a `.bak` of the pre-run version (11:46). It
  reached **81/100** RSE-positive gold papers, then was **INTERRUPTED** (no `--advance` cap on `:fill_gold`;
  all 19 unfilled rows have EMPTY `llm_error` = no API errors, checkpoint intact/loads fine). The 19
  unfilled = **7 human-rejected (rs=0), correctly SKIPPED by design** + **12 owed** (4 uncoded → full
  refresh, 8 coded → absent-only). **DANGLING (token-blocked):** re-run `fill-gold` with a token to finish
  the 12. **CORRECTION (06-23): a plain `fill-gold` resume DOES re-touch most of the 81** — the default
  regime full-refreshes EVERY uncoded paper (re-queries all 5 dims and OVERWRITES existing model answers,
  by design, so new subcategories are reconsidered), so ~95 papers run (~71 min), not just the 12 with a
  blank cell. Coded papers stay absent-only, so the human-baseline / ICR comparison is NOT churned (only
  uncoded model answers are, which has no ICR impact). Two ways to finish: (a) **let the full refresh run**
  — intended after the 06-23 schema edit, every uncoded gold paper gets re-annotated under the current
  schema (picks up `conceptual`, merged `performance_evaluation`, `software_lifecycle` everywhere); or
  (b) **`run_pipeline.cmd fill-gold "" absent-only`** (new flag added 06-23) → fills ONLY the ~12 genuinely
  blank cells for every paper, ~9 min, but uncoded papers keep their old answers for dims that already had
  one. NOTE: the checkpoint is written ONCE at loop end, so Ctrl-C loses the current run's progress — the
  prior 81/100 checkpoint is preserved, so aborting is safe.
  (2) **`prompts/category_schema.yaml` hand-edited 06-23 09:06** — a COMPLETE coder reconciliation, not a
  crash: added `techstack: conceptual` (coder:bob, described) and **merged the duplicate `performance
  evaluation`/`performance_evaluation` evaluation keys** into one canonical `performance_evaluation` whose
  new `examples: [performance evaluation]` alias maps the model's spaced output to the underscore key (the
  `examples:` field is a SUPPORTED schema feature — `categories.py:105`). The SAME 06-23 coder session
  also already MERGED the double key in the live coder files (uncommitted): `new_categories_alice.csv`
  collapsed the two `performance evaluation`/`performance_evaluation` rows into one canonical
  `performance_evaluation`, and `coding_alice.csv` normalized its one coded row (`lni332/paper52` evaluation:
  spaced→underscore, `is_new` True→False). `coding_bob.csv` has no performance-evaluation rows. So schema +
  coding_alice + new_categories_alice all agree on `performance_evaluation`; the spaced form survives only in
  the 06-19 backup. No coding-file merge is owed. Verified: schema loads through
  `categories.py` (5 dims, block now 10337 chars), only the SAME two human-owed empty-desc warnings remain
  (`research_position: testing` / `techstack: formal_specification_languages`). **GIT NOTE CORRECTED:** the
  methodology→software_lifecycle migration + 06-22 schema cleanup are now **COMMITTED** (HEAD
  `33a7613 "added menu and some utilities for better monitoring"`, 06-22 11:54) — the old "uncommitted vs
  ee8ba23" notes below are STALE; only today's 06-23 schema edit is uncommitted. Everything in the verbose
  pre-06-23 snapshot below is historical context; trust this paragraph where they conflict.

- **Now / in flight:** a live `round` IS running — `confirm_positives.py --set narrow --advance 50`
  (PID 25852, started 06-22 09:52:20) with a valid token. It is **glacial but working** (~5 min/SAIA
  call on the 675B model), NOT crashed — see top Log entry (06-22 diagnosis). Do not assume a hang;
  check the narrow checkpoint mtime/row count to confirm progress. **TASKS #8–#11 BUILT AS COPIES
  + OFFLINE-TESTED while this round runs (06-22 ~10:50; see top Log entry); #8 partly SWAPPED LIVE.**
  New standalone modules (real names, inert until wired): `src/preflight.py` (#8/#9 fail-fast SAIA
  reachability+auth + path/mount checks), `src/monitor_run.py` (#10 read-only heartbeat: rows-done +
  avg s/paper + ETA, `--watch`), `src/schema_cow.py` (#11 copy-on-write + **3-way** merge keyed by
  (dim,section,key) — adds/count-bumps AND deletions/promotes, concurrent-writer-safe; tested:
  concurrent add+bump vs delete+promote, idempotent no-op). Wiring lives in `*.fix.py` copies:
  `confirm_positives.fix.py` (#8/#9), `annotate_lni.fix.py` (#8/#9), `narrow_categories.fix.py` +
  `sync_coder_categories.fix.py` (#11). **SWAP STATUS:** only `confirm_positives.py` is swapped in
  live (backup at `confirm_positives.prebak.py`) — SAFE because the running advance already loaded
  its code and the round's auto-spawned `collect`/`review` do NOT import it (only a *future* advance
  re-reads it). **HELD until a supervised `collect`:** `annotate_lni.py` (collect lazy-imports it at
  `narrow_categories.py:95`) and `narrow_categories.py` (collect+review re-read it at the 100%
  boundary) — swapping these mid-round would change THIS round's remaining steps. All `*.fix.py` +
  the 3 new modules pass `py_compile`. **SCHEMA
  CLEANUP 2026-06-22 recovered & reconciled (see top Log entry):** the only file newer than this
  notes' prior update was `prompts/category_schema.yaml` (06-22 09:08) — an unlogged hand-edit that
  (a) removed two bogus `nan` coder categories (techstack + evaluation; the exact artifact the 06-18
  `i`/INSUFFICIENT_INFO sentinel was added to prevent), and (b) added `cmd_tool` + `analysis_pipeline`
  to `software_type` active and `benchmarking` to `evaluation` active. The edit was COMPLETE and the
  schema loads/renders cleanly through `categories.py` (5 dims, prompt block 9893 chars). **One typo
  reconciled this pass:** the new `analysis_pipeline` key was written with a SPACE (`analysis pipeline`)
  — every other key is snake_case AND the model emits `analysis_pipeline` (underscore) throughout the
  mistral checkpoint data, so the space would never exact-match. Renamed to `analysis_pipeline` (safe:
  the space-key appears in NO coding CSV; `analysis_pipeline` already in the data). **Still owed (NOT a
  crash — the documented forcing function):** two active coder categories have empty descriptions and
  are therefore EXCLUDED from the prompt until a human fills them — `research_position: testing`
  (coder:alice) and `techstack: formal_specification_languages` (coder:bob). Do NOT auto-author these
  (intended meaning is the coder's to give). **Git note:** the schema is now git-TRACKED in `lni_study`
  (the old "not committed / untracked" note below is stale); HEAD `ee8ba23 "current alice coding"`
  (06-19 09:49) still carries `methodology`, so the ENTIRE methodology→software_lifecycle migration
  PLUS this cleanup are uncommitted vs HEAD. **TYPOLOGY
  MIGRATION 2026-06-19 (see Log entry):** the `methodology` dimension was replaced by
  `software_lifecycle` (6 classical SW-lifecycle phases, per `software_prozesskategorien.md`) by
  hand-editing `prompts/category_schema.yaml` (old block backed up to
  `category_schema.backup-2026-06-19.yaml`). Code-complete (categories.py derives dims from YAML;
  no `src/*.py` references methodology; `build_goldstandard` tolerates the missing model column).
  **DANGLING (token-blocked):** run the NEW `fill-gold` step (06-22, see top Log entry) so the gold
  papers get `software_lifecycle_*` model annotations under the new schema. **TARGET CORRECTED
  06-22 (see top Log entry):** fill-gold now points at the CONFIRMED gold pool
  (`.workingset\gold_confirmed`, 100 PDFs) and updates the SAME checkpoint the `gold` coding step
  reads — `annotations_goldconfirm_*` (156 rows, `software_lifecycle_category` column ABSENT). The
  earlier wiring targeted the retired raw `gold` set whose live checkpoint no longer exists (only
  `annotations_gold_*.bak1-3`), which is why the run errored "needs an existing gold checkpoint".
  Re-pointed via a new `annotate_lni.py --checkpoint PATH` override (mirrors build_goldstandard
  `--annotations`), since the folder name `gold_confirmed` would NOT derive the `goldconfirm` tag.
  Two regimes (per the
  06-22 refinement): papers NOT yet coded by either coder get a FULL REFRESH (every dimension
  re-queried, so newly-created subcategories are picked up even where a model answer already exists);
  papers already coded by a coder get ABSENT-ONLY (just the missing dims) so their coded baseline /
  ICR comparison is not churned. Either way existing/untouched answers are preserved, unlike
  `a-gold overwrite` which re-does everything. (Plain `a-gold` resume would NOT add software_lifecycle
  to papers already in the checkpoint — it skips done papers entirely — so `fill-gold` is the correct
  tool here.) Then a `gold`
  pass to actually code the new dimension (alice/bob skipped old methodology and have NOT coded
  software_lifecycle). The old gold model checkpoint still carries orphaned `methodology_*` columns
  (harmless). **NEW `--reannotate` flag / `reannotate` step
  added & offline-verified 2026-06-20** (see top Log entry): force-redo path that re-annotates the
  already-confirmed (label==1) narrow papers under the current schema so `collect` mines
  `software_lifecycle` suggestions immediately instead of waiting for `advance` to trickle in fresh
  papers. `confirm_positives.py --reannotate` drops the redo ids from the checkpoint (archives a
  `.bak`, replaces rather than duplicates), pops them from `done`, and re-runs them; `--advance N`
  caps the count (token budget). Wired as `run_pipeline.cmd reannotate <token> "" narrow [N]`.
  Token-blocked work (SAIA) so the live redo is NOT yet run; only `purge_checkpoint_ids` is
  offline-verified (268→265 rows, redo ids gone, no dup ids, columns aligned, `.bak` made).
  Recommended flow: `reannotate` → `collect "" "" "" r1` → `review` (or a full `round`).
  Earlier 06-18 state below is unchanged.
  **NEW short-paper cap added & offline-verified 2026-06-18**
  (see top Log entry): the `pool` reservoir AND the `confirm` top-up drawn from it are now held to
  **<=20% short papers (<6 pages)** via the new `src/paper_length.py` rule — `select_candidates`
  skips over-quota shorts while filling the pool (asserting `fraction_ok` at the end), and
  `confirm_positives` reorders the pool draw with `order_within_cap` so every top-up prefix stays
  capped; `topup_goldstandard` + `run_pipeline.cmd` (`SHORT_PAGES`/`MAX_SHORT_FRAC`) forward it.
  Verified by `tests/test_short_paper_cap.py` (23 checks incl. an end-to-end synthetic-corpus run,
  no token); a live run against the real corpus is NOT yet exercised. Still uncommitted. **NEW
  `i`=insufficient-information coder option added & offline-verified 2026-06-18** (see Log entry): a coder can press `i` at a dimension to
  record the reserved `categories.INSUFFICIENT_INFO` answer ("paper doesn't say enough to code
  this") — a REAL coded row that counts in ICR as a nominal label, distinct from `s`=skip (no
  row, undecided). Never synced as a new category. Offline-verified; the interactive prompt is
  NOT yet exercised in a real terminal. Still uncommitted. **`synccats` step + `gold`
  auto-extension added & offline-verified 2026-06-18** (see Log): coder-coined (is_new) categories are now
  merged into `prompts/category_schema.yaml` `active` as groundtruth (`source: coder:<names>`),
  with a one-line human description captured at coding time into `new_categories_<coder>.csv`;
  `gold` auto-runs `synccats` first so each coder starts from a schema that already holds the
  other coders' new categories (closing the disagreement-by-default gap that would also depress
  ICR). Offline-verified via a synthetic two-coder fixture (collect, dedup, dry-run, real merge,
  idempotency, and the `categories.py` render/exclude forcing function), real schema untouched;
  the interactive description prompt and a live `gold` cycle are NOT yet verified. Still
  uncommitted. **`topup` step added & offline-verified
  2026-06-18** (see Log): after a `gold` pass it separates human-confirmed (rs=1)
  papers from rejected (rs=0) into `goldstandard/gold_human_{confirmed,rejected}_<coder>.csv`,
  then refills `.workingset/gold_confirmed` to `%GOLD% + #rejected` (target bumped +20 when
  confirmations come within 10 of the goal) by re-invoking `confirm`. `build_goldstandard`
  now resumes at the first undecided paper so re-running `gold` lands on the freshly added
  papers. Offline-verified (py_compile + synthetic dry-run + bump-math); a live token refill
  and the interactive resume jump are NOT yet verified. Still uncommitted. — The earlier
  **RSE-human-check feature in `build_goldstandard.py` was RECOVERED & unit-verified 2026-06-18**
  (see 2nd Log entry):
  the gold session now has a human RS-boolean gate (reject cascades to skip dimensions),
  forward/back/goto navigation, and full-rewrite resumable persistence. Compiles + save/load
  round-trip tested offline; the interactive loop and a live end-to-end gold run are NOT yet
  verified. The typology now has **5 dimensions** (added `evaluation`). Still uncommitted in
  the `lni_study` repo. **RESOLVED 2026-06-18** (see top Log entry): `compute_icr` now
  restricts ICR to papers BOTH coders gated rs=1 (a single rs=0 vetoes the paper out of
  every dimension), and reports the research-software gate agreement separately. — Earlier
  state below is unchanged:
  **`a-gold` is COMPLETE** (verified 2026-06-17,
  no crash). All 100 `.workingset\gold` papers annotated with the enriched (whitelist)
  prompt: 100 PDFs / 100 manifest rows / 100 checkpoint rows, all consistent. Labels:
  60 label=1, 39 label=0. **1 straggler**: `lni52/GI.-.Proceedings.52-53.pdf` failed
  with `pdf_extraction_failed` (empty label) — NOT an API/rate-limit error.
  **Gotcha:** a plain `a-gold` re-run will NOT retry it — `annotate_lni.py:611-619`
  builds `done_ids` from the `id` column ignoring error status, so the errored id is
  skipped forever. To re-attempt: delete that one row from the gold checkpoint first,
  OR use the new `a-gold <token> overwrite` (archives the whole checkpoint → fresh run,
  see Log 2026-06-17 `--overwrite`). NOTE: `--overwrite` re-attempts lni52 too, but the
  failure is DETERMINISTIC (no short-paper fallback was added), so it fails the same way.
  DIAGNOSED 2026-06-17 (no token): it is a GENUINE 2-page German paper (paper #53 of
  vol.52; `52-NN` = volume-paper numbering, NOT a whole-volume bundle), score 4.0.
  PDF is fine — `extract_text_from_pdf` yields 4288 clean chars, text is NOT flagged
  corrupted. The failure is entirely in `extract_main_content` (`pdf_text_extraction.py:206`),
  which returns None: this short paper has none of the section anchors it keys on
  (no numbered/standalone Einleitung/Introduction, no `Abstract:`/`Zusammenfassung:`,
  no `Keywords:`), so it falls through all 6 priorities. That flips `extraction_failed`
  (`annotate_lni.py:193`). **DETERMINISTIC** → re-running `a-gold` with a token will
  NOT fix it. Real options: (a) DROP it → gold = 99 clean papers; or (b) add a
  "priority 6" short-paper fallback to `extract_main_content` (return raw body when no
  anchor found but text non-empty & non-corrupt — also helps future short papers in
  narrow/final), then re-annotate just this one paper (delete its checkpoint row first).
  The earlier `Minute limit reached (10/min). Waiting ~3 s...`
  console lines were the **client-side `RateLimiter`** (`annotate_lni.py:90`, 10/min +
  200/h) working as designed — not an error.
  (An interrupted edit to the review CLI — explicit `[f]orward` navigation — was
  recovered & reconciled on 2026-06-16; see the Log. Code consistent, docs updated.)
  The old `estimate` process (PID 20484) has **finished** (no python running; score cache stopped growing at
  15:38, 1800 papers scored). Working sets are filled and **consistent** (manifest
  rows == PDFs on disk): narrow 50 / gold 100 / final 500 / pool 779. The pipeline
  was reworked into a **streaming estimator** that fills the working sets directly,
  plus an optional **LLM-confirm** step replacing the old `a-candidates` + `filter` pair.

- **Done & verified:**
  - `run_pipeline.cmd` is internally consistent — every `goto` resolves, and the
    `estimate` / `confirm` / `full` calls match the current Python arg surfaces
    (verified by grepping goto targets ↔ labels and reading each call site).
  - **`--overwrite` for `a-gold`** (recovered 2026-06-17, see Log): `annotate_lni.py`
    `--overwrite` flag + `run_pipeline.cmd :a_gold` 3rd-arg wiring. py_compile OK,
    `--help` shows the flag, cmd arg/token order verified. NOT run live (needs token).

- **Done, unverified (NOT run end-to-end against the real corpus or SAIA API):**
  - `src/select_candidates.py` — **rewritten** to stream: `enumerate_volumes`
    (cheap per-volume PDF count) → `folder_weighted_order` draw → score-and-fill
    `narrow (50) → gold (100) → final (FULL_N) → pool (rest, up to --cap)` in
    order, with an append-as-you-go score cache `results/rse_scores_<corpus>.csv`
    so an interrupted scan resumes without re-extracting. New args:
    `--min_score --narrow --gold --final --cap --seed --rescore --list_only`.
    **Dropped:** `--name --sample --select --min_pool`.
  - `src/sampling.py` — **added** `folder_weighted_order(groups, seed)`: orders
    all PDFs so a streaming pass is folder-balanced (each PDF equally likely,
    every volume represented from the start), deterministic, stoppable early.
  - `src/confirm_positives.py` — **NEW** `confirm` step: batched annotate (50) +
    keep `label_research_software==1`, topping up from `pool` until `--target`
    confirmed → `.workingset/<set>_confirmed/manifest.csv`. Resumable via
    `results/checkpoints/`. Merges old `a-candidates` + `filter`.
  - `run_pipeline.cmd` — **migrated**: header, dispatch table, all step bodies.
    New step order: `deps | dry | test | estimate | manifests | confirm | advance |
    collect | review | a-gold | gold | icr | full`. Removed `a-candidates`,
    `filter`, `ws-narrow`, `ws-gold` (estimate fills those sets directly).
  - **Category schema is the SOURCE OF TRUTH** (`prompts/category_schema.yaml`):
    `categories.py` → `schema_io.py` (ruamel round-trip) derive the prompt from it;
    `category_whitelist.json` + the JSON review CLI are RETIRED. Per dimension:
    `active` / `rejected` / pre-seeded empty `candidates: []`. The narrowing LOOP
    (grounded-theory theoretical sampling): `advance` (confirm next 50, **token**) →
    `collect --to_schema` (mine + append candidates, no token) → `review`/hand-edit
    the YAML (no token) → repeat until **saturation** (~0 new candidates for ~2
    rounds) → lock → `a-gold`/`gold`. All machinery verified OFFLINE only — see the
    2026-06-17 Log entry "category schema is now the SOURCE OF TRUTH" for exactly
    what was/wasn't run.

- **Next (in order):**
  1. **Smoke-test the streaming rewrite** (no token, no slow mount): tiny fake
     corpus of a few volume folders; assert `estimate` fills
     narrow→gold→final→pool in order, respects `--cap`, and the score cache makes
     a re-run skip extraction. Confirm `folder_weighted_order` is reproducible and
     spans folders. **The streaming rewrite has NO tests yet.**
  2. **Run `estimate` on the real corpus** (`Z:\Publikationen\LNI\Proceedings`):
     `run_pipeline.cmd estimate` — the one-time heavy pass over the slow mount;
     stops early once sets + pool are full; scores cache for re-runs.
  3. **Tune `--min_score`** (default 2.0): open `results/rse_scores_<corpus>.csv`,
     eyeball high/low scorers (DE *and* EN), adjust the gate and/or weights in
     `rse_estimator.py`. Re-run `estimate` (cached / instant unless `--rescore`).
     Watch per-set `SHORT` warnings (gate too high or `--cap` too low).
  4. **Run the narrowing LOOP until saturation** (theoretical sampling): one command
     per round — `run_pipeline.cmd round <token> "" "" rN` chains `advance` (token;
     confirm next 50) → `collect --to_schema` (no token; mine + append candidates to
     the YAML) → `review` / hand-edit (no token; fill descriptions, resolve
     `pending_restructuring`, promote candidates). The three stages are also exposed
     individually (`advance`/`collect`/`review`) for re-runs. Stop when a round adds
     ~0 new candidates (~2 dry rounds). FIRST live use of the loop — all machinery is
     so far OFFLINE-verified only. Also work the `pending_restructuring`
     backlog: add `middleware_service`, rename `perl_web`→`perl` and
     `hdl_hardware_description`→`hardware_description_languages`, and fill the 10
     empty `source:added` descriptions (categories.py warns about these on load).
  5. **Lock the typology**, then **`confirm --set gold --target 100`** (token) →
     **`a-gold` → `gold` → `icr`**.
  6. **`full`** per model (`run_1`, then `run_2`/`run_3` with other models) for the
     majority vote. `.workingset/final` is reused across models (no re-selection).

- **Blocked / open questions:**
  - **`min_score = 2.0`** is the new default (was 1.0) — decide the real threshold
    after step 3 by reading the score distribution.
  - **`cap = 2000`** — is `narrow+gold+final + pool` large enough that `confirm`
    never runs the pool dry? If `confirm` warns it ran out before `--target`,
    raise `--cap` or lower `--min_score` and re-run `estimate` (cached, fast).
  - ~~**`collect` annotation reuse:** verify `narrow_categories.py --mode collect`
    reads `confirm`'s checkpoint.~~ **RESOLVED 2026-06-16:** it does. `collect`
    globs `annotations_*_checkpoint.csv` (matches confirm's
    `annotations_narrowconfirm_..._checkpoint.csv`) and keys on `paper_id` =
    corpus-relative path (matches the manifest id `select_candidates` writes). The
    "Phase A checkpoints" wording in collect's output is stale labelling only.
    **Required order: `confirm --set narrow` BEFORE `collect`** — collect makes no
    LLM calls itself; it only reuses confirm's annotations.
  - **Estimator weights/patterns** in `rse_estimator.py` are still a first cut.
  - **Optional:** wire `mupdf_warning_summary()` into `annotate_lni.py`'s end-of-run log.
  - **Superseded / now unused:** `src/filter_positives.py` and
    `prepare_workingset.py --restrict` are no longer wired in (their job moved to
    `select_candidates` + `confirm_positives`). Decide whether to delete.
  - **Retired, not deleted:** `prompts/category_whitelist.json` is no longer the
    system of record (the YAML schema is). Confirm with the user before deleting it,
    and grep for any lingering reader first.
  - **Not committed:** `publications` is a submodule with local changes — decide
    when to commit.

## Log  (APPEND-ONLY — newest entry at the top, never edit past entries)

### 2026-08-04 (evening, 3) — `lni110/58` coded; the `middleware_service` lower bound decides its first case

**Paper 83/202, `lni110/58`** (Hackelbusch & Winkels, Uni Oldenburg,
*Erweiterung des Open-Source-Lernmanagementsystems Stud.IP um ein
ontologiebasiertes Curriculums-Planungsmodul*, 5 pp) — **accepted**. Two
components: ein bewusst dünnes **Stud.IP-Plugin in PHP** ("Dieses ist nur noch
für die Aufbereitung der Webseiten selbst zuständig") und die separate
**JAVA-Webapplikation EUSTEL**, die die gesamte Geschäftslogik trägt, ihre
Dienste "über Servlets und Webservices" anbietet und die Prüfungsordnungen als
OWL-Ontologie (CMO) mit JENA auswertet; Daten kommen aus HIS-POS und LVP
(Abb. 1). Stand: "Phase der Fertigstellung".

Coded `product_result` / `projektdefinition;entwurf;implementierung` /
`plugin_extension;full_stack_application` / `php;java_jvm;xml_xsd` / `planned`.

Four calls against the model, das alle fünf Dimensionen mit certainty 1.0
vorschlug:

- **kein `middleware_service`.** Das ist der erste Fall, den die am selben Abend
  gelandete Untergrenze entscheidet: verlangt wird, dass das Artefakt selbst die
  vermittelnde Schicht IST. EUSTEL nimmt zwar Daten von mehreren Seiten
  entgegen, vermittelt aber nicht zwischen ihnen — es rechnet daraus einen
  Studienplan und liefert ihn an das eigene Frontend. Servlets/Webservices sind
  Auslieferungsform, nicht Zweck. Die Klausel hat genau den Fall gefangen, für
  den sie geschrieben wurde.
- **`plugin_extension` und `full_stack_application` gemeinsam.** Die
  Vorrangklausel des Full-Stack-Keys ("sofern sie nicht besser durch …
  `plugin_extension` … beschrieben sind") entscheidet, wenn *ein* Artefakt
  beschrieben wird. Hier werden zwei Komponenten getrennt ausgeliefert und
  EUSTEL ist ausdrücklich auch ohne Stud.IP verwendbar ("kann EUSTEL leicht auch
  alternativ als autonome Anwendung angebunden an andere Systeme eingesetzt
  werden") — das Plugin allein bildet das Artefakt nicht ab.
- **kein `testen_qualitaetssicherung`, kein `testing`.** Die Verifikation steht
  vollständig im Futur ("Zu Testzwecken modellieren wir zunächst ausgesuchte
  Prüfungsordnungen … welches wir zunächst in ein Stud.IP-Testsystem
  integrieren, verifizieren wollen"). Maßgeblich ist laut `planned`, ob im Paper
  Ergebnisse berichtet werden — es werden keine berichtet. Gleiche Linie wie bei
  `lni109/570`.
- **kein `sql_db`, kein `javascript_web`.** MySQL wird nur genannt, um Stud.IP zu
  charakterisieren; dass die Erweiterung selbst darauf zugreift, steht nirgends.
  `javascript_web` hat das Modell aus "webbasiert" erschlossen — nicht benannt,
  also nicht kodiert. `php` bleibt dagegen drin: das Plugin *ist* PHP-Code in
  Stud.IPs Laufzeit, was die 08-04-Klausel zum `techstack` ausdrücklich
  einschließt ("eine Sprache, in der das Artefakt eingebettet ausgeführt wird …
  gehört sehr wohl zum Stack").

**Schema: keine Änderung gelandet.** `php` wurde erneut über `--new-category` in
`goldstandard/new_categories_alice.csv` geschrieben (der Sidecar dedupliziert
über `(dimension, key)`); die Aufnahme in die `active`-Liste der SSOT bleibt
Queue-Punkt 2, weil Keys nicht nebenbei angelegt werden — das ist jetzt der
zweite Beleg nach `316/DELFI_2021_187-192`. Queue-Punkt 5 (`plugin_extension` —
muss das Wirtssystem fremd sein?) wurde **nicht** strittig, Stud.IP ist
unstrittig fremd; das stützt die Lesart, dass dort nur die Eigen-Infrastruktur
offen ist.

Stand danach: **79 accepted / 65 rejected / 144 decided**, Frontier **84/202**
(`lni113/147`, Lohmann & Ziegler, SoftWiki). 21 Accepts bis `RS_TARGET = 100`.

### 2026-08-04 (evening, 2) — `lni110/247` coded; `techstack` told that a tool's input language is not its stack

**Paper 82/202, `lni110/247`** (Staiger, *Statische Analyse von graphischen
Oberflächen*, Institut für Softwaretechnologie Stuttgart, 7 pp) — **accepted**. A
new static analysis that extracts widget hierarchies, GUI events and their
handlers from C/C++ source, built on the Bauhaus suite's pointer analyses, global
control-flow analysis and interprocedural SSA form; tested against 11
open-source programs from `codebreaker` to `gimp`. Coded
`proof_of_concept_product` /
`projektdefinition;anforderungen;entwurf;implementierung` / `analysis_pipeline` /
`insufficient_information` / `testing;performance_evaluation`.

Four calls went against the model:

- **`proof_of_concept_product`, not `product_result`** (model 0.95). The
  decision rule turns on the *unit of the contribution*, and here that is a
  single new algorithm — §3 explains "den Algorithmus hinter unserer statischen
  Analyse", Figure 1 is its pseudocode, §4 shows feasibility ("Testresultate
  untermauern die Tragfähigkeit unseres Ansatzes"). That the analysis ships
  inside a real tool suite is maturity, which the definition says is a different
  axis and is expressly not coded.
- **No `testen_qualitaetssicherung`** (model 1.0). §4 is titled "Tests und
  Ergebnisse" but reports recognition rates (~85 % of widget expressions bound,
  few false positives) and runtimes — exactly what the clause landed earlier the
  same day routes to `evaluation` instead, "auch dann nicht, wenn das Paper sie
  als 'Test' bezeichnet". No quality assurance on the artefact itself is
  reported.
- **`techstack = insufficient_information`, not `c_cpp`** (model 1.0) — see
  below.
- **`analysis_pipeline` alone.** `plugin_extension` is a near miss: the analysis
  runs only on Bauhaus' intermediate representation. It was withheld because
  Bauhaus is the authors' own research infrastructure and the paper presents the
  work as a new analysis, not as an extension of a host system. That reading is
  not carried by the prose, so it went into the schema queue as item 5.
  `library_package` fails on delivery form (nobody links it into their own
  software), `numerical_mathematical` because graph algorithms are not a
  computation kernel.

**Schema: the `techstack` dimension question got a lower bound.** The model read
the *analysed* language off the paper as if it were the implementation language,
at certainty 1.0 — and nothing in the old wording forbade it. Its two guardrails
covered inferring from method/domain and mistaking algorithm names for
technologies; both assume the evidence is *absent*. Here the evidence is present
and concrete (C, C++, GTK, Qt are all named outright) — it just belongs to the
systems under analysis. Added: only the stack the software is itself built with
or runs on counts; a language, format or platform the artefact merely
**processes** is not its stack (a tool's target language, a generator's output
language, the language studied in a study, the technology and libraries of
analysed foreign systems), and a paper naming only those is
`insufficient_information`. The converse is preserved explicitly, so that
embedding languages and runtimes an artefact is built against keep counting.

This is the **first `SCHEMA_CHANGELOG.md` entry that cannot list its affected
rows**, and the reason is structural rather than lazy: a row stores the value
`c_cpp`, not the coder's reason for it, so nothing in the CSV separates
"implemented in C++" from "analyses C++". The entry therefore states the upper
bound — substantive `techstack` rows at the time of the edit: alice 52, bob 31,
lukka 11 (of 78 / 37 / 13 total, the remainder already
`insufficient_information`) — and says the realistic subset is far smaller and
recoverable only from the papers. No re-coding, per the standing policy.

Tally after the round: **78 accepted / 65 rejected / 143 decided**, frontier
**83/202** (`lni110/58`, a Stud.IP module — which will exercise queue item 5
immediately). 22 accepts short of `RS_TARGET = 100`.

### 2026-08-04 (evening) — remote `main` merged (both conflicts resolved semantically), `lni110/100` coded, `middleware_service` given a lower bound

**The merge.** `git pull` left two conflicts. Neither was resolved textually.

*`prompts/category_schema.yaml`* — an add/add of `evaluation.alternatives_comparison`.
Theirs carried `description: ''`, ours the filled 556-character wording. An
active entry with an empty description is silently dropped from the model prompt
by `src/`, so the model could never propose the key. Ours kept. That add/add was
the remote's *entire* schema diff against the merge base — three lines.

*`goldstandard/coding_alice.csv`* — resolved **`--ours` in full**. The file is a
*set* of rows, not a line-ordered document (`build_goldstandard.save_decisions`
groups accepts before rejects), so a textual merge of it means nothing. Instead a
3-way set merge keyed by `(id, coder, dimension)` was run over base/ours/theirs
(`$CLAUDE_JOB_DIR/tmp/merge3.py`):

| side | papers | rows |
|---|---|---|
| merge base | 122 | 432 |
| ours (HEAD) | 141 | 521 |
| theirs (`origin/main`) | **98** | **303** |

Papers in theirs but not in base: **0**. In theirs but not in ours: **0**. Papers
present in base but *missing* from theirs: 24. Only three cells differed at all,
each a regression from an older tool version dropping a category token it did not
know: `lni214/185` and `lni55/GI-Proceedings.55-17` lost `hpc_parallel_computing`
from `techstack` (with `is_new` True→False), and `lni71/GI-Proceedings.71-13` had
`is_new` flipped True→False. The single remote commit touching the file
(`012f729`, +3/−132) was therefore a **stale truncated checkout, not coding
work** — which also answers the question of whether coder `lukka` had written
into alice's file: no new paper of lukka's exists there to move out. Taking ours
discarded nothing. Merge committed as `3cbafb0`.

Post-merge verification: 0 conflict markers, the schema parses via
`schema_io.load_schema`, no active `evaluation` key has an empty description, and
all 141 of alice's papers carry either 6 rows or exactly 1. Lukka's own file has
two half-coded papers — `lni360/B6-2` (5 rows), `lni94/GI-Proceedings-94-1`
(2 rows) — flagged for them, not touched here.

**Paper 81/202, `lni110/100`** (Dästner/Kausch/Opitz, *An Object Oriented
Approach for Data Fusion*, ATLAS ELEKTRONIK + EADS, 5 pp) — **accepted**. The
industrial affiliation is not by itself disqualifying: the gate's
commercial-product exclusion requires *all three* of its conditions, and this
fails them, because the class-library suite exists to support a research process
("simulation, test and evaluation of data fusion systems", rapid prototyping of
fusion algorithms). Coded `product_result` /
`projektdefinition;entwurf;implementierung` /
`library_package;full_stack_application;numerical_mathematical` /
`c_cpp;xml_xsd` / `insufficient_information`. Six calls went against the model,
each resting on a clause of the current wording: no `testen_qualitaetssicherung`
(that the *tool* tests other software is not the lifecycle phase — the clause
added earlier the same day); no `analysis_pipeline` (a processing chain inside
the artefact does not make the artefact one); no `domain_specific_language` for
the XML configuration (a config language inside a larger system codes the
system's type); no `testing` and no `performance_evaluation` (nothing is
measured — "real-time" is an architectural claim); no `deployment_betrieb`.

**Schema: `software_type.middleware_service` got a lower bound** — the overdue
queue item 2 from 08-03, landed because this paper triggered it for the sixth
time in a day. The old wording was a bare list of examples with no lower bound,
so the key was being assigned whenever a paper merely *mentioned* middleware; the
model proposed it here at 0.95 although the paper states the middleware is
application-specific and external and that "the interfaces are separated from the
pure data fusion kernel". Three clauses added: the artefact must itself BE the
mediating layer (take input from at least two sides and translate, forward or
orchestrate between them); middleware as *environment* (embedded in it, offering
an interface to it, or merely describing it) does not count, nor do adapter
classes; and the boundary to `library_package` runs along the delivery form —
called through an API and built into foreign code is `library_package`, running
as a standalone service between systems is `middleware_service`.
Description-only, so the no-recoding policy holds; `SCHEMA_CHANGELOG.md` carries
the dated entry with the old wording quoted in full and all **36** rows coded
under it listed (alice 20, bob 10, lukka 6). Inter-coder agreement on
`software_type` must be read with this boundary shift in mind.

Tally after the round: **77 accepted / 65 rejected / 142 decided**, frontier
**82/202** (`lni110/247`). 23 accepts short of `RS_TARGET = 100`.

### 2026-08-04 — 13 papers coded, 8 schema sharpenings landed; session crashed, `recover-work` found nothing broken

**The crash.** The coding session of 2026-08-04 died without updating this file.
The last three writes on disk were `goldstandard/coding_alice.csv` (11:52),
`prompts/category_schema.yaml` (11:52) and `SCHEMA_CHANGELOG.md` (11:53) — all
newer than the previous `NEXT_STEPS.md` update (08-03 14:40), which is what
identified them as the in-flight work.

**Reconstruction, from the files** (the `recover-work` procedure prescribes mtimes
+ docstrings + notes over a diff, so that is what was used):

| check | result |
|---|---|
| half-coded papers (`gold_peek`) | **0** |
| rows per paper across all 140 decided | 6 (accept) or 1 (gate-0 reject) — no odd counts |
| tally vs. the 08-03 snapshot | 65→75 accepted, 62→65 rejected = +10/+3 = the 13 frame positions 66–78 |
| trigger rows named in the changelog (`lni109/57`, `lni109/202`, `lni106/337`, …) | all present in the CSV with the values the changelog claims |
| `evaluation.planned` wording in the SSOT | matches the changelog entry verbatim |
| write order | changelog last ⇒ the final round closed normally |

So the crash cost **no data and no consistency** — the classic recovery target (a
header/docstring describing a new design over a body still implementing the old
one) did not occur here. The only casualty was the record, and only this file was
rewritten. **Nothing in `src/`, the CSV or the SSOT was touched by the recovery.**

**Ordering caveat for future recoveries:** `coding_alice.csv` is **not** in
chronological order — `build_goldstandard.save_decisions` groups accepts before
rejects, so "the last rows in the file" are *not* the last papers coded. Recover
the day's papers from the frame order instead (positions in the
`…goldconfirm…_run_1_checkpoint.csv` filtered `label_research_software == 1`)
diffed against the ids already in the CSV, which is how the 13 above were found.

**git caveat (correction):** an earlier draft of this entry claimed the repo held
no commit for the day's work. That is false — the crashed session committed after
every round (`7e5ffcb` … `e2b246c`, eight commits on 08-04, ending with
`Gold coding: lni109/57 + planned/deployment boundary`). The file-based
reconstruction above was done independently and its 13 papers match those commits
exactly, so the findings stand; but the *cheap* check next time is `git log`
first, and the file evidence second as confirmation. Nothing was lost because the
crash landed after the last commit — the working tree was clean.

**Substance of the day** (see the State snapshot for the full per-paper values):
10 accepts / 3 gate-0 rejects, and eight description-only sharpenings of the SSOT
— `planned`, `xml_xsd`, `sql_db`, `testen_qualitaetssicherung`, `javascript_web`,
the `evaluation` dimension, `domain_specific_language`, `conceptual_evaluation` —
each landed with a dated changelog entry that names the trigger paper and lists
the already-coded rows decided under the old wording, per the no-recoding policy.
Two of the six items queued on 08-03 (`conceptual_evaluation`, `sql_db`) were
among them; the other four remain queued and are listed in the State snapshot.

**Not verified:** no pipeline run, no model call, no ICR recomputation was made
during the recovery (per the standing "no token work unprompted" rule). The
agreement statistics and anything downstream of the goldstandard are therefore as
stale as they were before the crash.

**Coding then resumed in the same session** and took position 79, `lni109/570`
(*MR Auto Racing*) — accepted, and the ninth schema sharpening of the day
(`usability_study` now requires an evaluation laid out as a collection) came out
of it. The interesting part is that the sharpening was *caused* by an earlier one:
re-anchoring `conceptual_evaluation` on the object of evaluation had pushed
observed use of a running artefact out of that key, which left an anecdotal
"the players enjoyed it" report with no stated home until `usability_study` was
given its lower bound. Worth watching for more such knock-on gaps as the
description edits accumulate.

### 2026-08-03 — assisted coding turned into a skill (`lni-coding`), 4 papers decided, 6 schema items queued

**Why a skill.** The assisted-coding round has a fixed shape, and recalling it
from memory kept dropping an aspect — twice in one session: once the PDF was not
opened at all and the proposal was argued from the model's checkpoint rationale
(the user's correction: *"you did not open the pdf"*), and once the schema half
was skipped (*"pdf öffnen und auch vorschläge an dem schema SSOT machen,
speichere das Ganze Prozedere als lni-coding skill, because recalling this always
dropps an aspect"*). The procedure is now written down instead of remembered.

**What was created** (in `~/.claude/skills/lni-coding/`, i.e. **outside this
repo** — it is a user-level skill, not committed here):

| file | role |
|---|---|
| `SKILL.md` | the 7-step round + a paths table + standing constraints |
| `scripts/gold_peek.py` | **read-only** frontier probe: data root, tally, frontier index, half-coded papers, the model's proposals + rationales. `--username --n --index` |
| `scripts/apply_coding.py` | headless writer for ONE decision: `--username --id --rs {0,1} --<dim> … [--new-category "dim\|key\|desc"] [--dry-run]` |

The 7 steps: locate the frontier → **read the whole PDF** → load the *current*
definitions from the SSOT (never quote remembered wording) → propose as a table
with arguments for the close calls only → propose the schema improvements the
paper exposed → one `AskUserQuestion` to confirm → write.

`apply_coding.py` exists because the interactive TUI (`run_pipeline.cmd:576`)
takes the terminal, and because writing the CSV by hand is how 38 papers were
lost on 2026-07-29. It goes through `build_goldstandard.load_decisions` /
`save_decisions`, so out-of-frame papers are preserved; it computes `is_new` via
`bg.is_new_category`; and it **aborts on an unknown category token** unless the
token is declared with `--new-category`, which also writes the shared sidecar
non-interactively (the twin of `record_new_category`, which prompts on stdin).
That abort is what surfaced the missing `techstack: php` key today rather than
letting a typo through.

**Two working notes for the next session.** (1) Reading schema descriptions via
an inline `python -c` fails: an f-string with an embedded conditional makes
PowerShell's parser throw `Unerwartetes Token "if" in Ausdruck oder Anweisung`.
Write the snippet to a file under the job tmp dir and run the file. (2) A 12-page
PDF cannot be Read in one call ("too many to read at once") — page it,
`pages: "1-6"` then `"7-12"`.

**Codings.** Four papers, detail in the State block above. The two rejections are
the interesting ones: both are *built* software with real users, and both fail the
gate for the same reason — the artefact serves teaching or data-centre
**operations**, not a concrete research process. That boundary is queued as
schema item 6 precisely because the model cannot see it (it proposed Cook.UP at
0.95).

**Not done:** nothing was run against SAIA, no schema file was edited, nothing
was pushed.

### 2026-07-31 — `recover-work` after the schema session died: NOTHING was in flight, only the task log was missing

**What the recovery found.** Files newer than the previous notes update
(07-29 21:02) were exactly four: `papers/feedback-category-schema.md` (09:55),
`papers/.Rhistory` (10:36, an unrelated R session), `SCHEMA_CHANGELOG.md`
(10:59:01) and `prompts/category_schema.yaml` (10:59:13). Both of the latter two
are **committed** — `7801a43 "Sharpen category definitions after the external
review pass"` (11:02) and `f55f2e7 "Add the external review of the category
system"` (11:08). So the session reached a clean stopping point and then
stopped; there is **no comment-vs-code mismatch to reconcile**, which is the
usual recovery target. The only casualty was this file: the pass never wrote its
State entry, so the durable record still described 07-29.

**The changelog's claims were re-checked rather than trusted.** Running the same
three checks the changelog asserts:

| check | result |
|---|---|
| `src/check_schema_integrity.py` | OK — 5 dimensions, no duplicate keys, `software_lifecycle` within canonical phases |
| key-set diff `active`/`rejected`/`candidates` per dimension vs `2d82e75` (pre-pass) | **0 differences** |
| prompt render | `render_categories_block()` 23202 chars, `render_category_guidance_block()` 6494 chars, both succeed |
| `archetype:` / `reporting:` leakage into the prompt | none — absent from both blocks |
| `archetype` present on every active `software_type` | 11/11 |

The zero key-set diff is the load-bearing one: the pass rewrote **descriptions**
and added non-computational metadata, and renamed/added/removed **no key**, so
every value in `goldstandard/coding_*.csv` and in the model checkpoints still
resolves.

**Reviewer questions: one is unanswered.** The feedback file has a
*"Verständnis / Frage LLM-Methodik"* half that the changelog's trigger list does
not mention. Of it, the per-category justification suggestion is struck through
by the reviewer themself ("Ok steht in den rationales"), and the
`### software_lifecycle` section is literally "/" (no feedback). What remains
open is **"Was ist die Abbruchsbedingung von `Wiederhole` bei der Studie?"** —
the saturation criterion the narrowing loop actually stopped on. Not invented
here; it is a human/method-section answer.

**Not done by this pass:** nothing was run against SAIA or the corpus, no
coding row was touched, and the superproject's `publications` submodule pointer
was left uncommitted (the recovery only wrote this file).

### 2026-07-29 (late evening) — DATA LOSS FOUND AND REVERSED: `save_decisions` deleted every paper outside the coding frame (38 of alice's 122)

**Trigger.** While checking whether an interactive session that broke up around
19:00 had lost work, `git status` showed `goldstandard/coding_alice.csv`
*shrinking*: **432 rows / 122 ids → 389 rows / 84 ids**, written at **20:41:45**.

**Root cause — `save_decisions` iterated the frame, not the state.** The function
rewrites the CSV *in full* from in-memory state after every decision (that is
what makes back-navigation and editing possible). Its loop was
`for _, row in df.iterrows():` — and `df` is the **current coding frame**, i.e.
the checkpoint filtered in `main()` to model `label_research_software == 1`, 202
rows. Any paper a coder had decided that is **not** in that frame therefore never
got written, and the full rewrite deleted it. The papers outside the frame are
exactly the ones the coder **rejected that the model also scored 0** — invisible
to the frame, but real human decisions and needed for the model-vs-human
comparison.

**Measured damage (alice, the only coder with off-frame history):** 38 papers /
43 rows deleted, **0 rows added** — the writing session made no decisions at all,
it only truncated. Human verdicts on the 43 lost rows: **37 rejections and 1
accepted paper with a full 6-row typology coding** (a genuine human-vs-model
disagreement — the model gate said 0, the human said 1). 37 of the 38 sat in the
checkpoint with gate `0`, one with `NaN`.

**Nothing was lost permanently.** Restored with
`git checkout fbd0ca0 -- goldstandard/coding_alice.csv` → back to 432 rows / 122
ids, tracked tree clean. The truncated copy is kept at
`%TEMP%\coding_alice.truncated-20-41.csv`. No Python process was live, so nothing
could re-truncate mid-repair.

**The ~19:00 session that broke up lost nothing.** Row-set diff of working copy
vs `fbd0ca0`: *rows present in the working copy but not committed = **0***. The
loss came entirely from the separate 20:41:45 write.

**Fix.** `save_decisions` rewritten around an `emit(pid, st, model_of)` helper
plus a second loop that carries over every decided paper **absent from `df`**, in
original file order. Their `model_category` / `model_certainty` can no longer be
read from `df`, so `load_decisions` now retains what the *file* said in
`st["model"][dim]` and `save_decisions` replays it verbatim. The docstring states
the invariant and the incident so the loop is not "simplified" back.

**Verified (`scratchpad/roundtrip.py`, `fullcmp2.py`).** `load_decisions` →
`save_decisions` against the live 202-row frame, all three coders:

| coder | rows | ids | lost | added | off-frame preserved |
|---|---|---|---|---|---|
| alice | 432 → 432 | 122 → 122 | 0 | 0 | 38 papers / 43 rows |
| lukka | 57 → 57 | 12 → 12 | 0 | 0 | — |
| bob | 236 → 236 | 51 → 51 | 0 | 0 | — |

Outer-merge on `(id, dimension)`: **0 left_only, 0 right_only**;
`final_category` and `is_new` **0 differing** for all three. Pre-existing,
unchanged behaviour worth knowing: `model_category` differs on **79 in-frame rows
for alice and 9 for bob**, because in-frame model columns are (and always were)
re-read from the *current* checkpoint, which has been re-run since that coding —
off-frame model columns differ on **0** rows.

**Progress indicator added** (the position counter `61/202` understated the work,
since every rejection advances `i`). New `RS_TARGET = 100` and
`rs_tally(state) -> (accepted, rejected, decided)`, counted from `state` so
off-frame papers still count. Session start now prints a 20-cell bar
(`[############........] 62/100 papers confirmed as containing research
software (62%)` + `122 papers decided so far (62 accepted, 60 rejected) out of
202 in this frame`), and the per-paper header carries a live
`| RS confirmed: 62/100`. Current standing: **alice 62/100, bob 38/100,
lukka 10/100**.

Note for interpretation: alice's *frontier* is #61/202 while she has decided 122
papers — 38 of those are off-frame and ~24 in-frame ones sit past #61, so the
position counter is a weak progress signal (frame order has changed since her
early coding; see the `gold` vs `gold_confirmed` frame task). The tally is the
number to trust.

**Not done:** the interactive session was not run end-to-end; the fix is verified
by round-trip on real data, not by a live coding pass. Non-ASCII em-dashes in
`print()` calls render as `?` under the coders' cmd.exe codepage — pre-existing
throughout the file, cosmetic, not touched.

### 2026-07-29 (evening) — FIXED: gold session re-opened on the first `s`=skip for ever (lukka + bob pinned)

**Trigger.** Lukka reported that `menu.cmd` "fängt immer an der gleichen Stelle
an, nämlich da wo ich heute früh war" — every run re-opens where he was that
morning — and that his pushes produced no visible progress online. He suspected
git, or the pipeline's import/export.

**Not git, and no data was lost.** `coding_lukka.csv` grows monotonically across
all 9 of its commits (2 rows → 57 rows / 12 papers; 07-27 had 8 papers, today 12)
and `lni_study` is clean and fully pushed. The diff between today's two commits
(`2203c07` 14:49 → `3f66a33` 17:09 — his "I redid two of them and pushed again")
is **2 lines, both on `lni360/B6-2`**: he re-coded that ONE paper twice. So
"online sieht man keine Änderung" was almost literally true, and the cause was
the cursor, not the transport.

**Root cause (`build_goldstandard.py`).** `run_session` anchored at
`next_incomplete(df, state, 0)` — the first paper *not fully coded*. But
`s`=skip writes **no row**, so `dims_missing` counts that dimension as missing
for ever (its own docstring called this "by design", to re-offer interrupted
papers). A single deliberate skip therefore pinned every future session on that
paper. Verified against the real data: lukka's anchor was **#8/202
`lni360/B6-2`** (missing `techstack`) though his frontier was #13 — he has four
such papers (#8, #10, #11 missing `techstack`; #12 missing `software_type` +
`evaluation`). **bob was pinned too**, at #14 (RS-accepted, all 5 dimensions
missing — a mid-paper quit) with his frontier at #52. alice has zero skips, which
is why the pipeline looked healthy.

**Fix.** New `next_unseen(df, state, start)`; the session now anchors on the
**frontier** (first paper with no human RS answer). Half-coded papers keep being
*listed* up front with their `#` (reachable with `g`) but no longer move the
cursor. If every paper has been seen, it falls back to `next_incomplete` for a
finishing pass, then to #1 for review. The in-session advance after finishing a
paper still uses `next_incomplete` (it only moves forward, so it cannot pin).
The session-start banner now also states that `s` leaves a dimension open and
that `i`=insufficient info is what settles a dimension the paper does not state
— this is the misuse that trapped lukka. Docstrings corrected (module header,
`dims_missing`, `run_session`).

`run_icr_session` does **not** share the flaw: it persists an explicit
`records[pid]["checked"]` visit flag in its own progress file, so a skip there
cannot pin the cursor. Its `q` handling saves correctly (`:801-802`).

**Verified:** anchors recomputed against the live `goldconfirm` checkpoint —
lukka #8 → **#13**, bob #14 → **#52**, alice **#61 unchanged**; and 5 synthetic
edge cases (first-ever session, clean forward pass, skip-trap, all-seen-with-
partial, all-complete) all anchor correctly. **NOT verified:** the interactive
session was not actually run (no live coding pass, no PDF opened); no CSV was
written by the patched code.

**Follow-ups for the coders (not code).** lukka's 4 half-coded papers and bob's
#14 are still open — they must be finished with `i` (or a real category), not
`s`, or they will stay on the list for ever. Tell lukka: nothing he coded was
lost; use `g` + the printed `#` to clear the four listed papers.

### 2026-07-28 (night) — 24 orphans + 2 Komplettbände purged from `gold_confirmed`; `_excluded` made sticky

**Trigger.** The user ran `fill-gold` and asked, first, whether it could destroy
human coding, and then why `gold_confirmed` showed "orphans".

**The safety answer (no code change).** Nothing human-coded is at risk.
`annotate_lni.py` has no write path into `goldstandard/`. A **coded** paper gets
the absent-only regime (`:830 refresh = (not coded) and not args.absent_only`),
so only blank cells are filled and the ICR baseline is preserved. The RSE gate
`label_research_software` lives under `gate:` in `category_schema.yaml`, not
under `typology:`, so it is never in `cat.DIMENSIONS` and a **full refresh cannot
flip it 1 → 0**; `classify_paper_dims` only ever returns
`{dim}_category/_certainty/_new_suggestion/_explanation` keys, and the merge loop
at `:849-852` writes exactly those. A `.bak` is archived at `:796` before any
rewrite.

**The orphan diagnosis.** 24 papers had a `gold_confirmed` manifest row but no
annotation row in any checkpoint or `.bak`. Bisecting git found commit `7f16f61`
(2026-07-13, "current state of lukkas coding of RSE papers"): it overwrote the
tracked goldconfirm checkpoint with a stale copy, truncating **188 records / 124
rs=1 → 156 / 100**. The survivor is a **byte-exact prefix** of the 2026-06-29
state (`4842dff`) — same 38 columns, same model id — i.e. a clean truncation, not
a re-run. Since the manifest is written *from* the checkpoint, it still described
the pre-truncation set.

**The decision.** I proposed restoring the truncated rows from `4842dff`. The
user overrode that: *"if no human coding was involved it doesnt matter, you can
just keep them removed so long as it is for everyone, you can also be aggressive
about leaving the whole volume pdf out"*. An audit of all 124 staged PDFs
confirmed the precondition — **0 of the 24 orphans is coded by alice, bob or
lukka** — so they were purged. 23 of the 24 remain in `pool/` and a top-up draws
them again normally.

**Also purged: the staged Komplettbände.** The first `is_non_paper` sweep covered
`gold`, `final` and `pool` but **not** the `*_confirmed` staged worklists, which
hold their own PDF copies. `lni122/LNI-122-Proceedings-komplett` (481 pp, in both
confirmed sets) and `lni221/lni-p-221-komplett` (287 pp, also an orphan) were
still in a coder's queue. Their `_excluded/` originals from the first pass are
untouched; only the staged duplicates were deleted.

| set | before | after |
|---|---|---|
| `gold_confirmed` | 124 | **99** |
| `narrow_confirmed` | 203 | **202** |

Verified afterwards: 99 manifest rows = 99 PDFs on disk = 99 checkpoint rs=1 rows
(minus `lni122`), zero rows without a PDF, zero PDFs not in the checkpoint. 17
now-empty volume dirs removed. Pre-purge manifests kept as
`manifest.csv.prepurge-bak`.

**The bug that would have undone all of it** (`5c0e317`).
`confirm_positives._locate_workingset_pdf` — the reconciliation fallback that
re-stages a confirmed paper whose PDF vanished — scanned **every** immediate
subfolder of `.workingset/`, `_excluded/` included. `lni122`'s checkpoint row
still says rs=1 (the purge deliberately leaves `results/` alone), so the very
next `confirm` / `topup` would have copied the 481-page volume straight back out
of `_excluded` into `gold_confirmed`. The scan now skips underscore-prefixed
folders (`_excluded`, `_stage_*`), which is what `_excluded/README.md` always
claimed. Pinned by `test_excluded_folder_is_not_a_restaging_source`, which I
verified **fails** when the guard is removed (not a vacuous test). All 3 tests in
`tests/test_materialize_confirmed.py` pass. Note there is no `pytest` in the
miniconda env — the file is pytest-style, run it with a two-line `tempfile` driver.

**Coder state after the purge, and the top-up arithmetic handed to the user:**

| coder | coded | keeps | keeps in set | rejections in set | undecided in set |
|---|---|---|---|---|---|
| alice | 98 | 41 | 40 | 20 | 39 |
| bob | 51 | 38 | — | 13 | 48 |
| lukka | 8 | 7 | — | 1 | 91 |

Alice keeps **67%** of model positives (40 of 60). The default `--target 100`
gives `confirm_target = 100 + 20 (in-set rejections) = 120` against 99 confirmed
→ only ~21 new positives → ~80 keeps, short of the 100 goal. Recommended
**`--target 150`** → `confirm_target = 170` → ~71 new positives staged, ≈111 SAIA
calls at the observed 64% positive rate (100 positives per 156 annotated).
`--target 120` is the cheaper intermediate step. **Not run** — token steps are the
user's to launch, and the `mistral-large-3-675b-instruct-2512` availability
blocker still applies (`python src/preflight.py --list_models` first).

**Left alone deliberately:** `results/` checkpoints keep their rows for every
excluded id (they are simply no longer joined by any manifest), and
`narrow_confirmed`'s pre-existing 208-PDFs-vs-202-rows drift.

### 2026-07-28 (latest) — SAIA model repinned; checkpoints renamed by model FAMILY
- **Trigger.** GWDG retired `mistral-large-3-675b-instruct-2512`. The user pulled the
  live `/v1/models` catalogue (16 models, no mistral-large). New pin:
  **`mistral-medium-3.5-128b`** — nearest same-family successor that emits plain
  text. The larger `qwen3.5-*` options list a `"thought"` channel in their `output`
  array, which the strict-JSON parser does not handle. It is a much smaller model
  than the 675B pin.
- **One constant, not a grep.** `preflight.DEFAULT_MODEL` is now the single source of
  truth; every `--model` argparse default reads from it (`annotate_lni`,
  `confirm_positives`, `topup_goldstandard`, `narrow_categories`, `pipeline_menu`).
  `run_pipeline.cmd`'s `%MODEL%` is the .cmd mirror.
- **The trap this exposed.** `run_pipeline.cmd` interpolates the model id into
  checkpoint FILENAMES. Moving the pin silently repointed the `gold` coding step at
  `annotations_goldconfirm_mistral-medium-3.5-128b_..._checkpoint.csv` — a file that
  does not exist. Coding would have opened an EMPTY checkpoint and lost all 156
  stored annotation rows. Caught before any run.
- **Fix (the durable one).** Checkpoints are named after the model **family**, not the
  exact id: `annotations_goldconfirm_mistral_rse_typology_prompt_v1_run_1_checkpoint.csv`.
  A version bump within a family keeps writing to the same file. The exact id of every
  call was ALREADY recorded per row in the checkpoint's `model` column — that is where
  a later validity check reads it from, and it is strictly better than a filename
  because one file can now honestly span two versions, row by row.
  `preflight.model_family()` derives the slug (first hyphen-segment, version digits
  stripped: `mistral-medium-3.5-128b` → `mistral`, `qwen3.5-397b-a17b` → `qwen`).
- **Migration.** `src/migrate_checkpoint_names.py` (dry-run by default, `--apply` to
  act) renamed **28 files** under `results/` — checkpoints, `new_category_suggestions_*`
  and every `.bak`/`.legacy` sidecar. It substitutes only ids that actually appear in
  the checkpoints' own `model` column, deliberately NOT a filename regex: sidecars like
  `..._run_1.legacy-2026-06-15.bak` contain hyphen-plus-digit runs that a regex reads as
  a versioned model id and renames the DATE away (observed in the first draft).
  Idempotent — a second run reports "already family-named".
- **Estimator recalibration** (same day, commit `fcca927`): AUC 0.726 → 0.771,
  P@30 0.70 → 0.77 against the 98 gold labels. Two new groups
  (`first_person_artifact` 3.0/cap 2, `code_listing` 2.0/cap 1), `artifact_vocab`
  weight 1.0 → 0.5. In-sample; bootstrap dAUC +0.044, 95% CI [-0.005, +0.097].
  Language was deliberately NOT made a feature although German papers accept at
  14.7% vs English 56.3% — that is a corpus property, not a research-software signal.
  23 checks in `tests/test_rse_estimator.py` lock it in.
- **Top-up target bug** (commit `ba65386`): `confirm_target` counted every human
  rejection as attrition, including rejections of papers that were never in the
  confirmed set. Corrected to count only in-set rejections: 100 + 20 = 120 against 124
  available → **no top-up is due**. The real next work is the 64 uncoded papers already
  sitting in `gold_confirmed`, which cost no API calls.
- **Still open.** The `gold` vs `gold_confirmed` frame question (see State block).
- **Verified:** 98 checks across the four test files; all module imports; migration
  idempotence; `deprecate_research_position.CKPT` resolves post-rename (60 coded RSE
  rows). **NOT verified:** anything requiring a live SAIA call — no token run was made.

### 2026-07-28 (later) — 4th rule (bundled tracks), 57 non-papers purged, study set 500 → 481
- **Trigger.** The very next gold paper, `lni352/KB_9th_Workshop_Enterprise_Architecture_Management`,
  was **not a paper either**: 41 pages holding the whole 9th EAM workshop track of
  INFORMATIK 2024 — three contributions, three DOIs (`inf2024_134/135/136`). It passes
  all three earlier rules (under 60 pages, no Komplettband keyword in the name, opens
  straight into a paper rather than a series page). The model had gated it 0 at
  certainty 1.0, but only because it read the first contribution — no evidence at all
  about the other two. User: remove it and add the rule.
- **New rule 4: `count_contributions(text)`.** Counts DISTINCT per-paper DOIs stamped
  behind a CC licence badge (`cba doi:10.18420/…`); `is_non_paper` reports
  "N contributions in one PDF" for N > 1. A bibliography citation prints a bare `doi:`
  with no badge, so a paper citing another LNI paper is not counted
  (`lni352/Neuroth_et_al_…`, verified). **Known limitation:** volumes older than the
  per-paper DOI carry no stamp, so a bundle there is invisible to this rule — the page
  and filename rules still apply.
- **A false-positive design that was caught before it did damage.** The first version
  counted the `<editors> (Hrsg.): … Lecture Notes in Informatics` footer instead.
  Several volumes repeat that footer on EVERY page, so ordinary single papers scored
  2–6 "contributions": `lni220/736` (6), `lni327/PVM2022_8` (6), `lni197/83`,
  `lni197/47`, `lni285/3032414_GI_P_285_23`, `lni285/3032414_GI_P_285_04`,
  `lni314/K1-2` — **7 real papers** that the purge would have deleted from `final` and
  `pool`. Found by inspecting every short bundle hit before applying anything. The
  footer detector is gone; the false positive is pinned as a regression test.
- **Purge of the existing sets (user-approved).** The audit was re-run properly: the
  manifests' `pages` column is **empty for nearly every row**, so my first audit — which
  trusted it — saw only the filename rule fire and reported 3 non-papers in `final`.
  Opening and measuring every PDF gives **19**. Corrected number put to the user before
  applying; approved.

  | set | before | after | removed |
  |---|---|---|---|
  | `gold` | 100 | **98** | 2 (the Komplettband + the KB_9th bundle) |
  | `final` | 500 | **481** | 19 (17 complete volumes 140–2113 pp, 1 table of contents, 1 bundle) |
  | `pool` | 1350 | **1314** | 36 (all volume-length or pure front matter) |

  All 57 PDFs moved to `.workingset/_excluded/<volume>/`; `_excluded/README.md` records
  the sweep, the per-set counts and the footer-rule post-mortem. Re-running the filter
  over all three sets afterwards reports **0 non-papers** in each. **No coded row was
  touched** — `coding_alice.csv` is 79 papers before and after. `results/` checkpoints
  still hold rows for removed ids; they are simply no longer joined by any manifest.
- **Verified.** `tests/test_non_paper_filter.py` grew to **52 checks, all passing** —
  rule 4 positive/negative, the bibliography-DOI case, the per-page-footer regression,
  and the end-to-end run now includes a synthesized 3-DOI bundle that must not be
  placed.
- **Method-section note owed.** The study set is **481**, not 500. Worth one sentence:
  the sample was drawn at 500 and 19 entries turned out to be complete proceedings
  volumes rather than contributions.
- **Resume point.** Gold-coding at **79/98**; next paper is now
  `Modellierung_2022_WS/paper12(1)` (manifest pos 68 after the removal).

### 2026-07-28 — collected volumes are no longer candidates (`is_non_paper`); gold set 100 → 99
- **Why this pass.** Gold-coding reached manifest pos 68, `lni300/SE-2020-Komplettband`
  — and it is not a paper: the **whole 254-page LNI P-300 volume** (*Software
  Engineering 2020*, Innsbruck), front matter plus every contribution of the conference,
  its tracks and five satellite events. Nothing about it is codeable (no single research
  position, software type or evaluation) and coding it would double-count papers already
  sampled individually (`lni300/B5-01`, `lni300/B5-03`). User: "remove this from the
  goldset and add to the estimation step in the pipeline that it should check for
  Tagungsband / pagesize and filter pdfs that are clearly not single papers."
- **Removed from the gold set.** Row deleted from `.workingset/gold/manifest.csv`
  (100 → **99 rows**); the PDF **moved** (not deleted) to
  `.workingset/_excluded/lni300/SE-2020-Komplettband.pdf` with a `README.md` recording
  what was excluded, from which set and why. `_excluded/` sits outside every `<set>/`
  directory, so `annotate_lni`'s per-volume glob, `pool_manager`'s PDF count and
  `select_candidates --regen_manifests` cannot pick it up again. `.workingset/` is
  git-ignored, so this is a working-set change only — nothing to commit there.
- **New in `src/paper_length.py`.** `MAX_PAPER_PAGES = 60`, `NON_PAPER_NAME_PATTERNS`
  and `is_non_paper(pdf_path=None, pages=None, text=None, max_pages=MAX_PAPER_PAGES)
  -> str | None` — returns a short **reason** if the PDF is clearly not a single
  contribution, else None. Three independent, conservative tests, any one sufficient:
  1. **pages > max_pages** (60). Generous on purpose: normal LNI papers are 4-14 pages,
     doctoral-symposium/survey contributions reach ~40, collected volumes start ~150 —
     the gap is wide, so a high threshold costs no recall. An unknown/unparsable page
     count never triggers it (same convention as `is_short`).
  2. the **file name** contains a collected-volume word (`komplettband`, `tagungsband`,
     `gesamtband`, `inhaltsverzeichnis`, `front matter`, `titelei`,
     `complete proceedings`, `book of abstracts`, …).
  3. the **first 4000 chars** carry the LNI series line AND an editor/board block
     (`Volume Editors` / `Series Editorial Board`). Head-only + both-required, so a
     paper that merely *cites* an LNI volume in its bibliography is not caught. An
     earlier draft also matched `ISBN 97…`; dropped before testing because individual
     papers carry the volume ISBN in their headers/footers (false positives).
- **Wired into the `estimate` step** (`src/select_candidates.py`): the check runs in the
  scan loop right after scoring and **before** the `--min_score` gate, so a collected
  volume is never placed however high it scores. Counter `n_skipped_non_paper`, a
  per-file `tqdm.write` naming the reason, a banner line reporting the filter state and
  a `"; N collected volume(s)/front matter skipped"` clause in the run summary. New CLI:
  `--max_pages N` (0 disables **only** the page rule; name + front-matter stay on) and
  `--keep_non_papers` (turn the whole filter off, debugging).
  **Bug caught while wiring:** `text` was only assigned on the fresh-extraction path, so
  a **score-cache hit** would have carried the *previous* iteration's text into the
  front-matter test. Fixed by setting `text = None` in the cached branch.
- **Verified.** New `tests/test_non_paper_filter.py` (styled after
  `test_short_paper_cap.py`, PDFs synthesized with PyMuPDF, no SAIA token, no corpus):
  **39 checks, all passing.** Covers the 60-page boundary (60 → paper, 61 → non-paper),
  unknown/empty/non-numeric lengths, 8 positive and 6 negative filenames (incl.
  `band_structure_simulation.pdf` and `GI.-.Proceedings.52-53.pdf`, which must NOT
  match), each front-matter fingerprint alone (→ paper) vs. together (→ non-paper), a
  paper citing an LNI volume in its references, `is_non_paper()` with no arguments, and
  an **end-to-end** `select_candidates.py` run over 10 ordinary + 3 non-paper PDFs
  asserting only the 10 reach the manifest, none is copied to disk, the summary reports
  the skips, and `--keep_non_papers` restores all 13.
- **Audit of the existing manifests (OPEN — user decision owed).** Applying the filter
  retroactively: `final` (500 rows) contains **3** non-papers —
  `lni353/PVM-Tagungsband2024-komplett` (score 27.0), `lni374/Tagungsband_komplett`
  (27.0), `lni352/KB_Inhaltsverzeichnis` (12.0), all empty `pages`, all caught by the
  filename rule; `pool` (1350 rows) contains **33**, all volume-length (e.g.
  `lni313/lni_p313_complete` 354 pp, `lni316/DELFI_2021-Proceedings` 392 pp,
  `lni156/lni-p-156-komplett` 381 pp). `gold` (99), `gold_confirmed` (124), `narrow`
  (50) and `narrow_confirmed` (203) are clean. **Not purged** — dropping the 3 would
  take the study set from 500 to 497, which is the user's call.
- **Gold coding this pass.** `lni52/GI.-.Proceedings.52-53` — Nowaczyk, *Explorationen*
  / Automatix: gate **1**, `product_result`, `entwurf;implementierung`,
  `full_stack_application`, `java_jvm`, evaluation `insufficient_information` (none
  reported and none announced, so not `planned`); commit `ae5b6a5`.
  `lni220/1005` — Pillmann, history of *Umweltinformatik*: gate **0**, against the
  model's 1. The model's `full_stack_application;middleware_service;simulation_framework`
  + `xml_xsd` came with the lowest certainties in the set and an empty
  `research_position` — a vocabulary-driven read of a retrospective essay that develops
  no software; commit `70656e8`. Gold now **79/99**.
- **Resume point.** Gold-coding at **79/99**; next paper
  `lni352/KB_9th_Workshop_Enterprise_Architecture_Management` (manifest pos 68).
  Per-paper loop unchanged, plus the user's 07-28 rule: **open the PDF and present the
  proposal in the SAME message** so the paper on screen always matches the question.

### 2026-07-28 — recover-work after two crashes: NOTHING to recover, cause was RAM
- **Why this pass.** User: "you crashed twice, check the reason, also run /recover-work".
- **The two crashes.** Session `d82c7927` (0.9 MB transcript) died ~10:33 local; its last
  recorded event is a tool_result at 07:31 UTC from a Python read of
  `results/checkpoints/annotations_goldconfirm_mistral-large-3-675b-instruct-2512_rse_typology_prompt_v1_run_1_checkpoint.csv`
  printing the model's category/certainty/explanation for `lni361/BTW2025-50`. Session
  `92c65323` died ~10:40, only 25 lines in, mid `Get-ChildItem -Recurse` over `.claude`.
  Neither transcript contains an error record — they just stop, which is what a killed
  process looks like (an API or tool failure would have been logged).
- **Cause: memory pressure, not a code fault.** 15.6 GB physical with 3.2 GB free;
  commit charge 15.0 / 27.1 GB; Edge (2 procs, 1.4 GB), Outlook, Element, Dropbox
  resident. No node entry in Windows Error Reporting (the WER hits are LiveKernelEvent /
  StoreAgentInstallFailure noise), no heap snapshot, no node report file. Aggravating
  factor: sessions in this repo carry very heavy tool output — the 07-27 transcript is
  **57.5 MB**. Crash 2's recursive `.claude` walk (which includes the git worktrees) is
  a plausible direct trigger for that one.
- **Recovery target: NONE — verified, not assumed.** Ordered every file under
  `lni_study` by mtime: the newest is `NEXT_STEPS.md` (07-27 16:34); the only other
  post-07-27-noon files are `prompts/category_schema.yaml` (16:31),
  `goldstandard/coding_lukka.csv` (16:31), `papers/related_work.qmd` + `references.bib`
  (16:30), `goldstandard/coding_alice.csv` (16:27) — all from yesterday's committed
  session. **Zero files newer than the notes**, i.e. the crashed session wrote nothing.
  Confirmed by content too: `coding_alice.csv` = 243 rows / 73 distinct ids with
  `lni361/BTW2025-50` absent, so no truncated or duplicate row was left behind. And the
  transcript shows no assistant text after the user's "continue LNI study" — only tool
  calls — so no coding proposal had been made and no user decision was pending capture.
- **Salvaged from the dead session (so the model answers need not be re-read).** For
  `lni361/BTW2025-50`: `research_position` empty (no model answer at all),
  `techstack` = `java_jvm` @ 0.7 (justification is only "OpenAPI-Generator is typically
  JVM" — weak, the paper never states a stack), `evaluation` =
  `testing;conceptual_evaluation` @ 0.9 (functional demo + API-compatibility
  verification + demo-UI discussion; explicitly no user study and no benchmarking).
- **Verified (offline, NO token).** mtime sweep of the whole `lni_study` tree; row/id
  count of `coding_alice.csv`; both new schema keys still `description: ''`
  (`ml_model` @276, `go` @451) hence still excluded from the prompt; no python/pipeline
  process running. **NOT done:** no PDF re-opened, no SAIA call, no coding row written,
  no commit — recovery only, per the ask.
- **Resume point (unchanged).** Gold-coding at **73/100**, next paper
  `lni361/BTW2025-50` (manifest pos 61, vol lni361, 8 pages). Fill the two empty
  schema descriptions first if they are wanted in the prompt for it.

### 2026-06-26 (pass 3) — LLM per-call timing instrumentation + backward-compat fix [offline-verified, INTERRUPTED]
- **Why.** User asked to add timestamps to the LLM hits so one can profile why some SAIA queries take longer
  than others. Then interrupted and asked to record three follow-ups here: re-check the new timer lines are
  backward compatible, resume the topping up, and continue the gold coding.
- **What changed.** `src/annotate_lni.py` `_complete_with_retries` (the shared SAIA call core that BOTH the
  annotate loop and `confirm_positives.py` reach via `classify_paper`): timed each
  `client.chat.completions.create()` with `perf_counter` into `api_s` and added it to the `RESPONSE` log line
  (`RESPONSE id=… attempt=N api_s=12.34 finish=… chars=… body=…`). This isolates the pure API round-trip from
  retry/backoff and JSON-parse overhead (the loop-level `t_api` at `annotate_lni.py:~1341` already includes
  those). The log formatter already stamps `%(asctime)s` and the REQUEST line already logs `prompt_chars`/
  `max_tokens`, so api_s is the missing piece for profiling. api_s is scoped to successful calls (the
  timeout/retry error paths return before the RESPONSE line and log their own outcome).
- **Backward-compat — caught & fixed.** The new `api_s=` token was inserted BETWEEN `attempt=` and `finish=`,
  which broke `src/check_fill_gold_parsing.py`'s `RESPONSE_RE` (it matched `attempt=\d+ finish=\S+` adjacent,
  so it would silently find "No RESPONSE records" on new logs). Made `api_s` an OPTIONAL named group
  (`(?:api_s=(?P<api_s>\S+) )?`) so the replay tool parses BOTH legacy logs and new ones.
- **Verified (offline, NO token).** `py_compile` of `annotate_lni.py` + `check_fill_gold_parsing.py`; a regex
  smoke test confirms old and new sample RESPONSE lines both match and `api_s` extracts (12.34). NOT run live
  against SAIA (no token) — the instrumentation is correct-by-inspection + unit-checked only. Uncommitted.
- **Owed next (token-blocked):** (1) resume the topping up (the `confirm`/pool top-up); (2) continue the gold
  coding — resume the interrupted `fill-gold` (81/100) + the `gold` pass for `software_lifecycle`.

### 2026-06-26 (pass 2) — score-cache crash fix + full-study confirms-on-the-fly + pool confirmed reporting [offline-verified]
- **Why this pass.** Two user asks: (1) **BUG** — `select_candidates.py` crashed in `load_score_cache`
  with `pandas.errors.ParserError: Expected 6 fields … saw 7`. (2) **FEATURE** — "split the pools into
  confirmed and not confirmed (confirm = LLM annotated it as RS). In all steps but the full study this is a
  separate step; in the full study the run should check on the fly if RS is coded as yes and dynamically
  extend the queried number, and show this in the progress bar." Clarified via three questions: applies to
  **Full study (real + test)**; target = **N confirmed RS papers** (keep drawing until N are LLM-confirmed);
  split materialized as a **separate `<set>_confirmed` folder** (reuse the existing confirm-step convention).
- **Bug root cause + fix (`src/select_candidates.py`).** The score cache `results/rse_scores_<corpus>.csv`
  gained a `pages` column (`SCORE_COLUMNS` → 7), but the header is only written for a brand-new file, so a
  legacy 6-col header followed by appended 7-col rows made the file ragged → pandas' C parser choked.
  Replaced the `pd.read_csv` loads (`load_score_cache`, `load_cache_rows`) with a tolerant `_read_cache_rows`
  that parses by field count (handles 7-col new rows, 6-col `_LEGACY_SCORE_COLUMNS` rows → blank `pages`,
  skips the header + malformed lines via `csv.reader`, which also quotes the JSON `signals` field), plus a
  **self-healing `_rewrite_cache`** that normalizes the file to the canonical 7 columns on load whenever a
  ragged/legacy/bad row was seen — so the crash cannot recur. The cache is regenerable, so any skipped
  malformed line is just re-scored. **Verified:** py_compile + a synthetic ragged cache (legacy + new +
  blank-pages rows) parsed correctly, healed in place, then re-read by pandas; `signals` JSON preserved.
- **Full study now confirms on the fly (real + test).** The `full` step no longer annotates a fixed
  `--sample N` of `.workingset/final` (which yields however many RS papers happen to fall in the draw).
  It now reuses `confirm_positives.py` in target mode: annotate (full typology via `classify_paper`) and
  keep drawing — topping up from `\pool` (real) / `\final` (test) — until **N papers are LLM-confirmed
  research software** (`label_research_software==1`), with the **progress bar tracking confirmed/target**
  (`confirm_positives`' existing target-mode bar). Confirmed PDFs are materialized into
  `.workingset/final_confirmed` (real) / `.workingset/full_study_pretest_confirmed` (test); the per-model
  checkpoint tag becomes `finalconfirm_<model>_<prompt>_run_1` (resp. `full_study_pretestconfirm_…`),
  consistent with the rest of the pipeline (`goldconfirm`, `narrowconfirm`). No new aggregation reader
  exists yet, so the tag change breaks nothing downstream. The **3rd arg now means "how many CONFIRMED RS
  papers to collect"** (blank → `FINAL_N`); `ensure-final`/`draw-pretest` still top up `final` first so
  there is a candidate buffer to confirm from. For narrow/gold the confirmed split stays the separate
  `confirm`/`advance` step (unchanged) — only the full study folds it inline, exactly as asked.
- **`pool_manager` reports confirmed-vs-unconfirmed (no token).** `report` (and thus `pools`/`refill`)
  gained a **`confirmed`** column = count in `<set>_confirmed` (manifest rows, else PDFs on disk) via the
  new `count_confirmed`. It is reported plainly (not as `on_disk − confirmed`) because the confirmed pool
  tops up from `\pool` and so can exceed its named set (e.g. `narrow_confirmed` accumulates across rounds);
  `-` means the set was never confirmed. **Verified:** live `report` over the real `.workingset` shows
  narrow 203 / gold 100 confirmed, final/pool `-`.
- **Files touched:** `src/select_candidates.py` (cache reader, self-heal), `run_pipeline.cmd` (`:full_real`
  + `:full_test` now call `confirm_positives.py --set … --target …`; header/usage comments), `src/pipeline_menu.py`
  (`_ask_full_n`/`_ask_full_test` prompts + `full` Stage description now say "confirmed RS papers"),
  `src/pool_manager.py` (`count_confirmed` + `confirmed` report column). All py_compile clean.
- **DANGLING (token-blocked):** a live `full … test` SAIA pass to exercise the inline confirm-and-extend
  end-to-end (bar fills to confirmed/target, `full_study_pretest_confirmed` materializes). Offline-verified
  only: the reused `confirm_positives` target path is already battle-tested by the `confirm`/`gold` flow.

### 2026-06-26 — new `pools` step + reworked `full` (test/sample decision, corpus-fed pool refill) [offline-verified]
- **Why this pass.** User asked to make the full-study step testable: (a) the `full` menu must let you pick
  how many papers to annotate AND whether the run is a "test" — a test annotates a subset into a separate
  `full_study_pretest` pool; (b) pool management — top up the working-set PDF pools from the corpus
  (`LNI_CORPUS`), and before any full-study run (real OR test) check `final` has enough papers and draw more
  if short; (c) a new menu item "show pool-sizes and refill pools". Design locked earlier via three
  questions: test source = **subset of `.workingset/final`**; pretest pool = **isolate only** (own
  folder-derived checkpoint tag, no exclusion logic vs the real study); refill scope = **all sets**.
- **New module `src/pool_manager.py` (no token).** Modes: `report` (read-only `set/on_disk/manifest/
  target/status` table over narrow|gold|final|pool|full_study_pretest), `refill` (report → re-run the
  estimator → report), `ensure-final` (exit 0 if `final >= --need`, else refill from corpus; exit 2 if still
  short), `draw-pretest` (ensure `final >= --pretest_n`, stratified-sample N of final by volume, **rmtree+
  rebuild** `.workingset/full_study_pretest` to EXACTLY N, copy preserving rel_path, enrich rows from
  final's manifest, write pretest manifest.csv). Refill = subprocess the deterministic, score-cached
  `select_candidates.py` (single tested corpus-streaming path; no reimplementation). Targets: narrow=--narrow,
  gold=--gold, final=--final, pool=max(cap-(narrow+gold+final),0), pretest=--pretest_n. `dst` stored relative
  to `LNI_DATA_ROOT`. If corpus missing/unreachable: warn + report-only, never silently succeed.
- **`run_pipeline.cmd`.** Added `FINAL_N=500` knob (canonical final target; NOT clobbered by the global arg3
  `FULL_N` assignment). New `pools` step → `pool_manager --mode refill`. Reworked `:full` with sequential
  goto labels (NO paren block — avoids the delayed-expansion pitfall): reads `IS_TEST` (4th arg `test`) and
  `FULL_SAMPLE` (3rd arg). `:full_real` → `ensure-final --need <FULL_SAMPLE|FINAL_N>` then `annotate_lni
  --lni_folder .workingset\final --no_stage --model %MODEL% --run run_1 [--sample N] [token]`. `:full_test`
  → `draw-pretest --pretest_n <FULL_SAMPLE|5>` then annotate `.workingset\full_study_pretest` (folder name
  derives an isolated checkpoint tag automatically — no extra plumbing). Added `:full_no_final` /
  `:full_no_pretest` error labels; updated header step-list + `:usage`.
- **`src/pipeline_menu.py`.** Added `_ask_full_n()` (blank = ALL for real, →5 for test) and `_ask_full_test()`
  (returns "test"/""). `full` Stage now `extras=[(3,_ask_full_n),(4,_ask_full_test)]`. New
  `Stage("pools", "Estimator (non-LLM)", "show pool-sizes and refill pools", uses_corpus=True)`.
- **Verified (offline, NO token).** `py_compile` of pool_manager.py + pipeline_menu.py; `--help` OK. On a
  synthetic workroot: `report` lists all five sets with size-vs-target/status; `draw-pretest 4` did a balanced
  stratified draw (lni10 2/5, lni20 2/5), wrote a 4-row pretest manifest with enriched score/pages, rebuilt
  the folder to exactly 4 PDFs; re-draw with N=2 cleanly wiped the prior 4 (rmtree rebuild); `ensure-final
  --need 999` with no corpus warned and exited 2 (no silent success). **NOT run live:** no SAIA full-study
  `test` pass — exercising the `full … test` path end-to-end against the API is the dangling next step once a
  token is supplied.

### 2026-06-23 (later) — recover-work: code had drifted from the `--absent-only` spec; restored it
- **Why this pass.** `/recover-work` after the prior session was interrupted. Anchored on mtimes vs the
  prior notes update (10:14). Newest files were `src/annotate_lni.py` (10:37 = crash site),
  `src/pipeline_menu.py` (10:25), `prompts/rse_typology_prompt_v1.md` (10:23), `run_pipeline.cmd` (10:13)
  — all newer than the notes, i.e. the in-flight work the notes didn't yet reflect. No process running.
- **The mismatch (recovery target).** Three self-consistent layers — the argparse `--absent-only` help, the
  `run_pipeline.cmd :fill-gold` driver, AND the prior 10:14 State + the Log entry below — all describe ONE
  design: **default = full-refresh uncoded papers; `--absent-only` = gap-fill EVERY paper.** But the body of
  `run_fill_missing` had drifted to a DIFFERENT, non-functional design: `refresh = (not coded) and
  getattr(args, "refresh_uncoded", False)`. `--refresh-uncoded` was **never declared in argparse**, so the
  getattr was permanently `False` → the full-refresh branch was DEAD CODE (every paper always gap-filled)
  and the declared `--absent-only` flag was **never consumed**. So `fill-gold` ignored its flag entirely.
- **Decisive evidence it was a botch, not a redesign.** The 06-23 Log entry directly below literally
  specifies the intended line — *"Implemented via `refresh = (not coded) and not args.absent_only`"* — and
  says the `mode` label / counter / intro print "all key off `refresh` now". The on-disk body had silently
  diverged from the session's own written spec. The docstring + inline comments had been rewritten to the
  inverted (gap-fill-by-default) story too, so body and its own comments agreed with each other but
  contradicted the spec, the argparse, and the driver.
- **Fix (smallest reconciling change, matches the logged spec).** In `run_fill_missing`: line ~671
  `refresh = (not coded) and not getattr(args, "absent_only", False)`; rewrote the intro `print` block
  (line ~626) and the per-paper comment + the function docstring back to the documented semantics
  (default refresh-uncoded / coded absent-only / `--absent-only` holds everyone to gap-fill). No change to
  argparse, the driver, the menu, or `run_preview_prompt` — those were already correct.
- **Verified (NO token).** `py_compile` OK (annotate_lni.py + pipeline_menu.py); `--help` lists
  `--absent-only` and no longer any `--refresh-uncoded`; `grep` confirms `refresh_uncoded` is gone and
  `absent_only` is now consumed at the `refresh=` line + intro print (not just declared); `annotate_lni.py
  --preview-prompt` ran clean (exit 0, rewrote `results/prompt_preview.txt`). **NOT verified:** no live
  SAIA `fill-gold` run was made — the regime fix is correct by inspection + matches the prior session's
  spec, but has not been exercised against the API. The prompt's `vier`→`fünf` literal fix (flagged "NOT
  done / user's call" in the entry below) IS now present in `rse_typology_prompt_v1.md` (applied after that
  entry was written); harmless and correct (there are 5 dims).
- **Still owed (unchanged, token-blocked).** Finish the interrupted `fill-gold` (was 81/100): either let
  the default full refresh run, or `run_pipeline.cmd fill-gold "<token>" absent-only` for the ~12 blank
  cells only — the flag now actually works.

### 2026-06-23 — prompt-preview step + `--absent-only` fill regime (annotate_lni.py / run_pipeline.cmd)
- **Why.** While running `fill-gold` the user saw the bar say `refresh-all research_position,…,evaluation`
  over 100/100 papers (~71 min ETA) and was confused — they expected only the ~12 papers with a blank cell.
  Diagnosed: that IS the documented full-refresh-for-uncoded regime (`run_fill_missing`, the `dims =
  list(cat.DIMENSIONS) if refresh else _missing_dims(row)` branch). `refresh-all` = all 5 dims re-queried
  AND overwritten for that (uncoded, non-rejected) paper — by design, not a bug. Coded papers stay
  absent-only. Two follow-up asks from the user: a way to finish only the genuine gaps, and a prompt
  preview to inspect/shrink the prompts for performance.
- **`--absent-only` flag (annotate_lni.py).** New `--absent-only` (dest `absent_only`) forces the
  absent-only regime for EVERY paper, incl. uncoded ones. Implemented via `refresh = (not coded) and not
  args.absent_only`; `dims`, the `n_refresh` counter, the bar `mode` label and the intro print all key off
  `refresh` now (was `not coded`). Wired into `run_pipeline.cmd fill-gold "" absent-only` (3rd arg, like
  `a-gold overwrite`). Lets a resume fill just the ~12 blank cells (~9 min) instead of full-refreshing ~95.
- **`--preview-prompt` step (annotate_lni.py + cmd `preview`).** New corpus-free, token-free `run_preview_
  prompt(args)`: loads the template, splices bracketed placeholders for the paper body, and prints the
  SYSTEM prompt, the FULL annotation user prompt and the TARGETED fill prompt with char/token sizes + a
  size breakdown, also writing `results/prompt_preview.txt`. Dispatched EARLY in `main()` (before any
  scan/stage), so `--lni_folder` is now optional (required only for the other modes; validated explicitly).
  cmd step: `run_pipeline.cmd preview`.
- **Verified (no token).** `py_compile` OK; `--help` lists both flags; `src/annotate_lni.py --preview-prompt`
  ran and produced the breakdown. **Two findings the preview surfaced** (candidates for the user's
  "reduce/alter" goal): (1) the full annotation prompt is **17.3k chars / ~4.3k tokens** of static
  scaffolding, dominated by the **10.3k-char category catalogue block** + a **3.6k-char curated guidance
  block** — the body text adds up to 40k chars on top. (2) the prompt's Schritt-2 intro still hardcodes
  **"die folgenden vier Dimensionen"** though there are now **5** (research_position, software_lifecycle,
  software_type, techstack, evaluation) — a stale literal in `prompts/rse_typology_prompt_v1.md` worth
  fixing. The two empty-description active subcategories (`research_position: testing`,
  `techstack: formal_specification_languages`) are still EXCLUDED from the prompt (human-owed, unchanged).
- **NOT done.** No SAIA call made; prompt template text not edited (the "vier"→"fünf" fix and any
  shrinking are the user's editorial call). The interrupted `fill-gold` (81/100) was NOT resumed.

### 2026-06-23 — recover-work: reconciled the live `fill-gold` run (81/100, interrupted) + the 06-23 schema edit
- **Why this pass.** `/recover-work` after an interrupted session. Anchored on mtimes vs the prior notes
  update (06-22 16:40). No python/cmd/biber/quarto process was running (the round PID 25852 from the prior
  State is gone; the only live `cmd.exe` is an F-Secure browser helper). Exactly TWO files were newer than
  the notes: `prompts/category_schema.yaml` (06-23 09:06, the newest = crash site) and the gold model
  checkpoint `annotations_goldconfirm_…_run_1_checkpoint.csv` (06-22 19:54).
- **Finding 1 — `fill-gold` actually ran (the prior notes still called it token-blocked/not-run).** The
  goldconfirm checkpoint now CARRIES `software_lifecycle_*` columns (previously ABSENT — the exact gap
  fill-gold closes), grew 327k→339k, and a `.bak` of the pre-run state was written at 11:46. So a live,
  token-spending `fill-gold` happened ~19:54 on 06-22. **Completeness (pandas, offline):** of 100
  RSE-positive gold papers, **81 have software_lifecycle filled, 19 do not.** The 19 = **7 human-rejected
  (rs=0)** → fill-gold's default skip-rejected SKIPPED these correctly + **12 owed** (4 not-coded → full
  refresh regime, 8 coded → absent-only regime). All 19 unfilled rows have EMPTY `llm_error` (no API
  failures), and `:fill_gold` carries no `--advance` cap (run_pipeline.cmd:450) ⇒ the run was
  **INTERRUPTED ~12 papers short**, not capped and not errored. Checkpoint is intact (loads, 156 rows).
- **Finding 2 — the 06-23 09:06 schema edit is COMPLETE, not a half-migrated crash.** `git diff HEAD`
  (HEAD moved to `33a7613`, see below) shows two changes: (a) added `techstack: conceptual` (coder:bob,
  described: "No code has been written but it describes a concept"); (b) merged the two duplicate
  evaluation keys `performance evaluation` (spaced) + `performance_evaluation` into one canonical
  `performance_evaluation`, deleting the spaced key and adding `examples: [performance evaluation]` +
  a corrected, merged German description (fixed typos berzieht→bezieht, Performanzmatriken→Performanzmetriken).
  The `examples:` field is a SUPPORTED active-entry feature (`categories.py:105` reads it), so this is the
  intended fix for the space-vs-underscore alias problem the 06-22 notes flagged — handled via examples
  rather than a rename.
- **Verified (offline, NO token).** Schema loads through `categories.py`/`schema_io.py`: 5 dims
  (`research_position, software_lifecycle, software_type, techstack, evaluation`), `render_categories_block`
  builds (10337 chars, up from 9893), zero space-keys, only the SAME two human-owed empty-desc warnings
  (`research_position: testing` [alice], `techstack: formal_specification_languages` [bob] — still owed,
  left for the coder, NOT auto-authored). Goldconfirm checkpoint loads via pandas (156 rows). NOT run: any
  token/live step.
- **Git note corrected.** Contrary to the prior State's "uncommitted vs HEAD ee8ba23", the
  methodology→software_lifecycle migration + the 06-22 schema cleanup + menu/utilities + coding files are
  **COMMITTED** at HEAD `33a7613` ("added menu and some utilities for better monitoring", 06-22 11:54).
  Only today's 06-23 schema edit (conceptual + performance_evaluation merge) is uncommitted.
- **Resume / dangling (token-blocked).** Re-run `fill-gold` with a SAIA token to finish the 12 owed gold
  papers' `software_lifecycle` (resumable; absent-only for coded papers won't churn the 81 already done).
  Then the `gold` coding pass for the new dimension (per the 06-19 migration). Commit the 06-23 schema edit
  on request.

### 2026-06-22 — `fill-gold` TARGET FIXED: points at the confirmed gold pool / `goldconfirm` checkpoint
- **Symptom.** Running `fill-gold` errored: *"--fill-missing needs an existing gold checkpoint to
  update, but none was found at …\annotations_gold_…_checkpoint.csv. Run the gold annotation first."*
  User asked: "was the last goldcheckpoint moved to the backup or what happened?"
- **Diagnosis (nothing was moved by this run).** fill-gold failed at the existence check, BEFORE any
  archive step; `_archive` only ever *copies* (shutil.copy2), never moves. The live
  `annotations_gold_*_checkpoint.csv` (raw "gold" tag) is genuinely gone — only `.bak` (06-16),
  `.bak2` (06-17), `.bak3` (06-18 10:53) remain. The workflow MIGRATED off the raw `gold` set on
  06-18 when `confirm` produced the CONFIRMED pool: `.workingset\gold_confirmed\` (100 PDFs) +
  `annotations_goldconfirm_…_checkpoint.csv` (06-18 11:46, 156 rows). That `goldconfirm` checkpoint
  — NOT `gold` — is what the `gold` coding step (`build_goldstandard --annotations`) actually reads.
  fill-gold (and a-gold) were still pointed at the dead `.workingset\gold` (tag "gold").
- **Fix.** New `annotate_lni.py --checkpoint PATH` override (mirrors build_goldstandard
  `--annotations`): PDFs still come from `--lni_folder`, but the checkpoint read/updated is the named
  one — needed because the folder name `gold_confirmed` derives tag "gold_confirmed", not the live
  "goldconfirm". Re-derives the paired `new_category_suggestions_*` path from the checkpoint's own tag.
  `run_pipeline.cmd :fill_gold` now uses `--lni_folder .workingset\gold_confirmed --checkpoint
  …annotations_goldconfirm_…_checkpoint.csv`.
- **Verified (offline, no token).** `py_compile` clean; `--help` lists `--checkpoint`; gold_confirmed
  has 100 PDFs; goldconfirm checkpoint loads (156 rows, `software_lifecycle_category` column ABSENT —
  exactly the gap fill-gold closes; `run_fill_missing` adds every canonical column as blank before the
  gap scan, so the absent column is filled, not a KeyError). run_pipeline.cmd stays CRLF (539/539).
  NOT run live (token must not be spent unasked).
- **Note.** a-gold still points at the retired raw `.workingset\gold`; left as-is (it's the pre-confirm
  path and the user only runs fill-gold). Revisit if a-gold is ever re-exercised.

### 2026-06-22 — `fill-gold` now SKIPS human-rejected (rs=0) papers by default (offline-verified)
- **Why.** User asked whether running `topup` early would shrink the fill set by dropping human-rejected
  no-RS papers. It would not: `topup` *copies* coded papers into `gold_human_{confirmed,rejected}_*.csv`
  and *adds* new pool papers to refill the confirmed set to target — it never prunes the annotation
  checkpoint `fill-gold` iterates, so it would only grow the work. The real waste is that `fill-gold`
  keyed RS off the MODEL label only, so a paper the model called rs=1 but a human rejected (rs=0) still
  got its absent dims filled even though it can never enter the goldstandard. Fix: skip human-rejected
  ids in `fill-gold` directly — works regardless of how many of the 100 are coded.
- **What changed (all offline; NO SAIA call):**
  - `src/annotate_lni.py`: added `_rejected_paper_ids(goldstandard_dir)` — unions ids from
    `coding_*.csv` rows where `dimension == label_research_software` and `final_category` is 0/false,
    plus any `gold_human_rejected_*.csv`. `run_fill_missing` computes `rejected_ids` (when
    `args.skip_rejected`, default True) and skips those pids before the RS/dims checks, tracking
    `n_skip_rejected` in the progress bar + final summary. New CLI flag
    `--skip-rejected / --no-skip-rejected` (BooleanOptionalAction, default skip). Section header
    comment + `run_fill_missing` docstring updated.
  - `run_pipeline.cmd`: `fill-gold` REM doc + `:fill_gold` label comment note the rs=0 skip default.
  - `src/pipeline_menu.py`: `fill-gold` Stage description mentions "skip human-rejected (rs=0)".
- **Verified:** `py_compile` of annotate_lni passes; `argparse.BooleanOptionalAction` present on
  Python313; smoke test against the real `goldstandard/` resolved 30 coded ids and 7 rejected ids.
  **NOT run live against SAIA** (token-blocked). Uncommitted.

### 2026-06-22 — `fill-gold` refinement: full refresh for UNCODED papers, absent-only for CODED (offline-verified)
- **Why this pass.** The first `fill-gold` (entry below) only ever queried ABSENT dimensions, so a
  newly-created subcategory in a dimension that already has an answer would never be reconsidered. User
  refined: "I want this also for the subcategories that already have an answer but only for the papers
  that were not coded yet (by either coder)." So the model baselines of papers a human has already
  coded must stay stable (don't churn the ICR comparison), but uncoded gold papers should be fully
  re-annotated to pick up the new subcategories.
- **Design (two regimes, decided per paper):**
  - paper id NOT in any `goldstandard/coding_*.csv` → **full refresh**: `dims = list(cat.DIMENSIONS)`
    (re-query every dimension; the targeted prompt then renders all subcategories incl. new ones).
  - paper id present in some `coding_*.csv` → **absent-only**: `dims = _missing_dims(row)` (unchanged
    original behaviour).
  - Skip only when the chosen `dims` is empty (coded + already complete), non-RSE, or not-in-checkpoint.
- **What changed (all offline; NO SAIA call):**
  - `src/annotate_lni.py`: added `_coded_paper_ids(goldstandard_dir)` (unions the `id` column across
    `coding_*.csv`, tolerant of empty/badly-shaped files). `run_fill_missing` now computes
    `coded_ids = _coded_paper_ids(DATA_ROOT / "goldstandard")` once, picks `dims` per the two regimes,
    and reports full-refresh vs absent-only counts (`n_refresh`) in the progress bar + final summary.
    Section header comment + docstring updated.
  - `run_pipeline.cmd`: `fill-gold` REM doc + `:fill_gold` label comment + usage line updated to
    describe the two regimes. Dispatch/command unchanged.
  - `src/pipeline_menu.py`: `fill-gold` Stage description updated.
- **Verified:** `py_compile` of annotate_lni / categories / pipeline_menu all pass. **NOT run live
  against SAIA** (token-blocked by policy). Uncommitted.

### 2026-06-22 — new `fill-gold` step: incrementally fill ONLY the MISSING gold typology dimensions (offline-verified)
- **Why this pass.** After the methodology→software_lifecycle migration the gold model checkpoint has
  no `software_lifecycle_*` cells. The existing path was `a-gold overwrite`, which re-annotates EVERY
  dimension of EVERY gold paper — needlessly redoing (and possibly changing) answers that are already
  correct. User asked for a step that, for the selected papers, only the missing categories are
  suggested "without rewriting the whole thing".
- **Design (locked with the user via two questions):** (1) **Query mode = targeted per-dimension
  prompt** — the model is asked ONLY about the missing dimension(s), not the full typology; (2) **Gap
  rule = only ABSENT dimensions** — a dimension is a gap iff its `<dim>_category` cell is absent /
  NaN / blank. Stale or retired present values are left as-is (not refreshed).
- **What changed (all offline; NO SAIA call — token must not be spent unasked):**
  - `src/categories.py`: `render_categories_block()` / `render_category_guidance_block()` gained a
    `dims: list[str] | None` filter (default None = all dims, fully backward-compatible) so the
    targeted prompt renders only the missing dimensions' subcategories + rejected-key guidance.
  - `src/annotate_lni.py`: extracted the shared SAIA call+retry+parse core into
    `_complete_with_retries(...)` (classify_paper now calls it — behaviour unchanged). Added
    `build_fill_user_prompt`/`_fill_json_skeleton` (focused German prompt: "bereits als RSE
    klassifiziert" + "annotiere AUSSCHLIESSLICH die folgende(n) Dimension(en)"),
    `classify_paper_dims` (returns only the requested dims' flat cells),
    `_is_blank`/`_missing_dims`/`_is_rse`/`_archive` helpers, and `run_fill_missing` (reads the
    one-row-per-paper checkpoint as strings with `keep_default_na=False`, ensures new-dim columns
    exist, per paper fills only the absent dims via `df.at`, logs new suggestions, then backs the
    checkpoint up to `.bak` and rewrites it). New `--fill-missing` flag (mutually exclusive with
    `--overwrite`); `main()` branches to `run_fill_missing` after client creation and returns.
  - `run_pipeline.cmd`: new `fill-gold` step (dispatch + REM doc + usage line) running
    `annotate_lni.py --lni_folder %DATA%\.workingset\gold --no_stage --model %MODEL% --fill-missing`
    (full final-grade model, NOT the loop model).
  - `src/pipeline_menu.py`: new `fill-gold` Goldstandard stage (needs_token, full model — correctly
    NOT in `LOOP_MODEL_STAGES`).
- **Verified:** `py_compile` of annotate_lni / categories / pipeline_menu all pass; smoke-tested
  `_is_blank`, `_fill_json_skeleton` (single + multi dims), and `build_fill_user_prompt` render
  offline. **NOT yet run live against SAIA** (token-blocked by policy) — a real `fill-gold` pass is
  the dangling next step once a token is supplied. Uncommitted.

### 2026-06-22 — slowdown diagnosis + tweaks #2 (max_tokens cap) & #4 (faster loop model); interactive menu front door
- **Why this pass.** User asked to diagnose the ~400s/paper annotation slowdown ("prompt growth vs. SAIA
  being slow?") and then to apply two low-complexity tweaks: **#2** cap `max_tokens`, **#4** use a
  faster model for the candidate-mining loop steps. Plus earlier this pass: build the interactive
  launcher (`src/pipeline_menu.py`) + repo-root `menu.cmd`, and honor `LNI_CORPUS` in run_pipeline.cmd.
- **Diagnosis (data, not guess).** Per-paper time swings 225→662s *within a single round where the
  prompt is FIXED* (schema only changes between rounds, at review) → variance is **API/model-side**
  (prefill + queue on the 675B), NOT prompt growth. ~30% of papers hit the 300s client timeout.
  Prompt is minor: 55 active categories + ~3.6k-char template vs paper text capped at 40000 chars
  (which dominates input). Conclusion: predominantly SAIA latency-bound.
- **#2 max_tokens cap (DONE, offline-verified).** `annotate_lni.py`: new `DEFAULT_MAX_TOKENS=2048`
  constant; `classify_paper(..., max_tokens=DEFAULT_MAX_TOKENS)` passes it to the API and adds a
  **finish_reason=="length" guard** that returns `{"llm_error": "truncated ...", "llm_raw_response": ...}`
  instead of silently parsing a half-filled JSON. New `--max_tokens` CLI flag (0 = uncapped) on BOTH
  `annotate_lni.py` and `confirm_positives.py`; call sites use `(args.max_tokens or None)`;
  `confirm_positives.py` imports `DEFAULT_MAX_TOKENS`. Measured a complete output is ~885 tok median /
  ~1354 max, so 2048 ≈ 50% headroom — well-formed answers NEVER truncate; the guard only fires on
  genuinely over-long/malformed output. **HONEST CAVEAT:** outputs don't ramble to a cap, so #2 bounds
  the worst case + adds predictability but does NOT materially cut the ~400s avg. The real win is #4.
- **#4 faster loop model (DONE, offline-verified).** New `ADVANCE_MODEL` knob in `run_pipeline.cmd`
  (defaults to `%MODEL%` → **zero behavior change until opted in**; overridable inline or via
  `LNI_ADVANCE_MODEL` env). Used by ONLY the candidate-mining token steps: `advance`, the advance
  sub-step of `round`, and `reannotate` (they merely mine `new_suggestion` subcategories). The
  final-grade steps `a-gold`/`full`/`confirm`/`topup` STILL use the full `%MODEL%` (675B). Config
  banner prints a `loop model` line only when it differs from `%MODEL%`. `pipeline_menu.py` affirms the
  loop model for those 3 stages (`LOOP_MODEL_STAGES`) and exports `LNI_ADVANCE_MODEL`.
  **OPEN — the model id is the user's call:** no faster SAIA model id was hard-coded (must not spend the
  token to list models without being asked). To get the speedup, set `LNI_ADVANCE_MODEL` (or edit the
  `ADVANCE_MODEL` line) to a faster model your SAIA account offers; TASKS.md names llama/gemma as the
  majority-vote alternates. Until then the loop runs on the 675B exactly as before.
- **Interactive front door (DONE).** `src/pipeline_menu.py`: numbered stage menu (mirrors the project's
  other `input()` UIs), token prompted (getpass, hidden) ONLY if the stage needs one and none is in
  `SAIA_TOKEN`/`SAIA_API_KEY`, affirms working dir (`LNI_DATA_ROOT`) + corpus (`LNI_CORPUS`), per-stage
  extras fill run_pipeline.cmd slots 2–5, opt-in SAIA reachability check, then dispatches. Token passes
  via the child ENV (not on the launcher's command line). `menu.cmd` at repo root launches it.
  `run_pipeline.cmd` now honors `LNI_CORPUS` (overrides the CORPUS placeholder).
- **Verified:** all edited files `py_compile` clean (`MENU_OK`); `--max_tokens` shows in both `--help`
  outputs. **NOT verified:** no live SAIA run this pass (token not to be spent unasked) — #2's guard and
  #4's faster model are UNTESTED against the real API. Nothing committed.

### 2026-06-22 — built #8–#11 as copies while the round runs; swapped in the one swap-safe fix (#8 confirm_positives)
- **Why this pass.** User: "check the round.log regularly … create your fixes in copies, once you are
  finished and the round.log has not reached 100%, it should be safe to copy the new versions, right?"
  So: build the four deferred fixes (#8–#11) WITHOUT touching live files, then hot-swap only the ones
  that can't affect the in-flight round. Round was at 10→18% (9/50, ~400s/paper) throughout this pass.
- **Swap-safety analysis (the crux of "is it safe to swap while <100%?").** YES for the running
  process — it loaded its modules at import; replacing a `.py` on disk does not change PID 25852's
  behavior. The CAVEAT: a `round` is ONE cmd process running advance→collect→review back-to-back, and
  the instant advance hits 100% it auto-spawns `collect` (a FRESH Python that re-reads code from disk).
  The files that fresh `collect`/`review` re-read: `narrow_categories.py` (+ its top imports
  `categories.py`, `schema_io.py`, `sampling.py`) and `annotate_lni.py` (lazy import at
  `narrow_categories.py:95`). `confirm_positives.py` is NOT re-read by collect/review — only by a
  *future* advance. ⇒ swapping `confirm_positives.py` now is safe; swapping `annotate_lni.py` or
  `narrow_categories.py` now would change this round's remaining steps. `schema_io.py` left untouched.
- **What was built (all as new files; live files untouched except the one swap below).**
  - `src/preflight.py` (#8/#9): `check_saia(base_url, token)` fail-fast reachability+auth via a
    short-timeout `models.list()` (AuthError→fail token rejected; conn/timeout→fail unreachable;
    other HTTP status→soft-pass "reachable, auth not verified" so a `/models`-less endpoint can't
    false-fail); `check_path`/`check_paths`/`check_data_root` (LNI_DATA_ROOT + results + .workingset);
    `require(...)` prints each check and `SystemExit`s on failure. CLI for manual pre-run use.
  - `src/monitor_run.py` (#10): read-only heartbeat — parses round.log's tqdm line (UTF-16 aware) and
    cross-checks the newest checkpoint CSV (rows/confirmed/errors/mtime), prints sec/paper + ETA;
    `--watch`. Tested live against the running round.
  - `src/schema_cow.py` (#11): copy-on-write + **3-way** merge. `work_copy()` writes a numbered work
    copy AND a pristine base snapshot; `merge_back()` RE-READS the canonical fresh and 3-way-merges
    work-vs-base-vs-canonical keyed by (dim,section,key): changed-in-work-only→take work (covers adds
    AND collect's count bumps), changed-in-canonical-only→keep (concurrent writer preserved),
    deleted-in-work+untouched-canonical→delete (covers review's promote/decline), both-changed→flag
    conflict + keep canonical. Atomic write (temp + os.replace). `discard()` for no-op exits.
    **Note:** upgraded from the originally-planned purely-additive 2-way merge — additive-only would
    have LOST collect's count bumps (key already in canonical) and left review's promoted candidates
    stranded in `candidates`. The base snapshot makes updates+deletions representable.
  - `*.fix.py` wiring copies: `confirm_positives.fix.py` + `annotate_lni.fix.py` call `preflight`
    (confirm: SAIA+paths before the slow candidate load; annotate: paths up front, SAIA deferred to
    the annotation step so report-only/estimate modes don't need a token). `narrow_categories.fix.py`
    routes collect (load/save) and review (per-decision save + merge at end/on quit) through
    `schema_cow`; `sync_coder_categories.fix.py` routes its merge through `schema_cow` (discards the
    work copy on dry-run/no-op).
- **Verified (offline, NO token spent, real canonical untouched).** `py_compile` of all 3 new modules
  + all 4 `*.fix.py` + the now-live `confirm_positives.py`. schema_cow tested on TEMP copies: writer A
  (collect-style: bump c1 count 1→5, add c3) and writer B (review-style: promote c2 candidates→active)
  both made from the SAME base, merged A-then-B → final had c1=5, c3 added, c2 removed from candidates
  and present in active, no clobber; a third no-op merge changed nothing (idempotent). `.schema_work`
  left empty; real `prompts/category_schema.yaml` mtime unchanged (09:27).
- **SWAPPED LIVE (the only swap-safe one):** `confirm_positives.py` ← `confirm_positives.fix.py`
  (original backed up to `src/confirm_positives.prebak.py`). Diff is minimal: one `import preflight`
  + one `preflight.require([...])` block before the candidate load; all referenced symbols
  (`DEFAULT_SAIA_ENDPOINT`, `--saia_endpoint/--saia_token`) confirmed present. Compiles. Affects only
  the NEXT advance, not this round.
- **HELD (do NOT swap until a `collect` can be supervised):** `annotate_lni.py` and
  `narrow_categories.py` — both on this round's remaining collect/review path. Swap them only when no
  round is mid-flight (or right before deliberately starting a fresh round), then run a supervised
  `collect` once to confirm the schema_cow merge + preflight behave on real data.
- **NOT verified (honest):** no live/token run of any swapped or held fix; preflight's SAIA branch
  against the real endpoint with a real token; the interactive `review` merge-on-quit in a real TTY;
  a real two-writer concurrent schema race (only the deterministic temp-copy simulation was run).
- **Resume.** When ready to adopt #9/#11: swap `annotate_lni.py`←`.fix.py` and
  `narrow_categories.py`←`.fix.py` (back up first), `py_compile`, then a supervised `collect`/`round`.
  Optionally also `sync_coder_categories.py`←`.fix.py`. Run `python src/monitor_run.py --watch` any
  time to watch the current round. Commit only on request (per standing constraint).

### 2026-06-22 — diagnosed a `round` that "took long to start then crashed" / "isn't reacting": SAIA per-call latency, NOT the schema
- **Symptom (user).** Ran `round` to narrow the new categories (esp. `software_lifecycle`); it
  hung at startup then appeared to crash; on a retry it again "isn't reacting really."
- **Verdict: not a crash and not schema-related.** Confirmed by catching the live process in the
  act: `confirm_positives.py --set narrow --advance 50 --saia_token …` (PID 25852, started
  09:52:20) was alive 10+ min using only **1.9s CPU** (blocked on the network socket, not
  computing), and it **wrote a real, clean annotation** to the narrow checkpoint at 09:57:29
  (`id=lni195/47`, `label_research_software=0`, `llm_error=nan`). So token, schema, parsing,
  and checkpoint append all work — it is simply **glacial**: ~5 minutes per paper. At that rate
  `--advance 50` is a ~4-hour job that emits one CSV line every few minutes, which reads as frozen.
- **Ruled out, with evidence.**
  - *Schema:* startup printed only the expected "active subcategories with no description are
    EXCLUDED" warning (the two empty-desc coder cats) and nothing else; the 06-20 narrow
    checkpoint header already carries `software_lifecycle_*` (no `methodology`), so appends stay
    column-aligned. The `analysis_pipeline` rename is in place.
  - *Slow local startup:* a token-free repro (`--advance 1`, no `SAIA_API_KEY`) loaded all
    **829 candidates incl. page-counting 779 pool PDFs in ~4.2s** and stopped cleanly at the token
    guard. The local `.workingset/pool` copies (779 PDFs present) make page-counting fast, so the
    short-paper cap is NOT the bottleneck.
  - *Network/endpoint down:* `GET /v1/models` returned 401 (auth-required, as expected w/o token)
    in ~4s incl. TLS — endpoint healthy. The token was accepted (no fast 401 → no AuthError).
  - *Rate limiter:* `RateLimiter` is an in-memory deque (fresh per run), not persisted — not it.
- **Root cause.** Per-call latency of `mistral-large-3-675b-instruct-2512` on SAIA right now
  (~5 min/call, within the 300s client timeout). The earlier "crash" was most likely the same
  slowness without a token resolved: long page-count load, then `SystemExit("Missing SAIA token…")`
  at the guard (no `.env` exists; token comes from arg2 / `SAIA_TOKEN`).
- **Guidance given (no code changed; live round left running).** Safe to Ctrl-C — every paper is
  checkpointed on return and `confirm_positives` resumes from the checkpoint (the checkpoint IS the
  cursor), losing at most the in-flight paper. For a faster narrowing loop, re-run with a small
  `--advance` (5–10) — you only need a trickle of new `new_suggestion` candidates. Leave the 300s
  timeout alone (calls are succeeding, just slow; lowering it would discard slow successes).
- **Follow-up features requested (tasks #8–#10, DEFERRED until the live round finishes so we don't
  disturb PID 25852):** (8) SAIA connectivity preflight (reachable + auth ok, fail-fast) before the
  long loop; (9) mount/folder availability check (corpus Z:\ / `\\DC01` + `LNI_DATA_ROOT` dirs)
  fail-fast; (10) a passive background progress/heartbeat monitor that tails the checkpoint and
  reports rows-done + avg sec/paper + ETA so "glacial but working" is visible.

### 2026-06-22 — recover-work: reconciled the unlogged 06-22 `category_schema.yaml` hand-edit
- **Why this pass.** `/recover-work` after an interrupted session. Anchored on mtimes (notes last
  updated 06-20 12:36): the **only** file newer was `prompts/category_schema.yaml` (06-22 09:08) —
  the crash site / in-flight work. Everything else in `src/`, `tests/`, `goldstandard/` was ≤06-20
  and matched the prior State. No python/cmd/quarto process was running (nothing to interrupt).
- **What the 06-22 edit did (reconstructed via `git diff HEAD` minus the logged 06-19 migration).**
  Discovered the schema is now git-TRACKED (HEAD `ee8ba23`, 06-19 09:49, still has `methodology`),
  so `git diff HEAD` bundles the whole methodology→software_lifecycle migration with today's edit.
  Subtracting the already-logged migration, today's hand-edit = a schema cleanup: removed two bogus
  `nan` coder categories (`techstack`, `evaluation`; `key: nan, source: coder:bob, description: ''`
  — the artifact the 06-18 INSUFFICIENT_INFO sentinel was meant to replace), and added `cmd_tool`
  + `analysis_pipeline` (`software_type` active) and `benchmarking` (`evaluation` active), all with
  descriptions. The edit was COMPLETE — not a half-migrated crash.
- **The one mismatch found & fixed (the recovery target).** The newly-added software_type key was
  written `analysis pipeline` **with a space** — the only key in the whole schema not snake_case,
  and the mistral checkpoint data emits `analysis_pipeline` (underscore) everywhere, so the spaced
  key would never exact-match the model's output (it'd register as a separate category in
  `collect`/ICR). Renamed the key to **`analysis_pipeline`**. Safe: grep confirmed the spaced form
  is in NO coding CSV (coders coded under the old schema), and `analysis_pipeline` already exists in
  the checkpoint data — so the rename aligns the schema with the data, it doesn't orphan anything.
- **Verified (offline, no token, no corpus).** Schema loads through `categories.py`/`schema_io.py`:
  5 dims (`research_position, software_lifecycle, software_type, techstack, evaluation`; `methodology`
  gone), `render_categories_block()` builds (9893 chars), zero keys with spaces remain. Confirmed no
  lingering `nan` category in `coding_alice.csv`/`coding_bob.csv` (so the schema removal isn't
  silently undone by a coder file a future `synccats` would re-read). **NOT run:** any token/live
  step, the interactive coding loop.
- **Surfaced, deliberately NOT changed.** Two active coder categories still have empty descriptions
  and are therefore EXCLUDED-from-prompt + warned by `categories.py`: `research_position: testing`
  (coder:alice), `techstack: formal_specification_languages` (coder:bob). These need a HUMAN one-line
  description (the coder's intended meaning) — auto-authoring them would fabricate the typology, so
  they're left for Julian. Until filled they simply don't appear in the model prompt.
- **Carried-over dangling (unchanged, token-blocked).** The 06-19 migration's data-level work is
  still owed: `a-gold` (token) to give the gold papers `software_lifecycle_*` model annotations, then
  a `gold` coding pass for the brand-new dimension. See the 06-20 migration Log entry + State → Next.
- **Not committed.** All of the above plus the migration remain uncommitted in `lni_study` vs HEAD
  `ee8ba23`. Commit only on request.

### 2026-06-20 — added `--reannotate` force-redo flag (jump-start `software_lifecycle` mining)
- **Why.** After the 06-19 `methodology`→`software_lifecycle` migration, `collect` only sees
  the new dimension on papers annotated under the new schema. Normally those trickle in via
  `advance` (50 new papers at a time). User asked for a flag that "forces a new set of annotated
  papers to quicker start that process" — i.e. re-annotate the papers ALREADY confirmed so the
  whole narrow_confirmed set carries `software_lifecycle_new_suggestion` at once.
- **What changed.**
  - `src/confirm_positives.py`: new `--reannotate` arg + a worklist branch that selects the
    already-confirmed (label==1) candidates of `--set` (cap with `--advance N`), and a new
    `purge_checkpoint_ids()` helper that drops those ids from the checkpoint up front (archiving a
    timestamp-free `.bak`, mirroring `annotate_lni --overwrite`) and `done.pop`s them, so the
    re-run REPLACES rather than appends duplicate rows. SAIA token check runs BEFORE the purge, so
    `--reannotate` without a token exits non-destructively.
  - `run_pipeline.cmd`: new `reannotate` dispatch + `:reannotate` body + header/usage doc.
    Usage: `run_pipeline.cmd reannotate <token> "" narrow` (redo all confirmed) or
    `... narrow 20` (cap at 20). Hint points to `collect "" "" "" r1` next.
- **Why it's correct end-to-end.** Confirmed `annotate_lni.CHECKPOINT_COLUMNS` is built
  dynamically from `cat.DIMENSIONS` (`flatten_annotation({}).keys()`), so re-annotated rows AND
  the reindexed kept rows align to the CURRENT schema (`software_lifecycle_*`), and the stale
  `methodology_*` cells drop out. So `collect` (mines `_new_suggestion` from label==1 rows) sees
  the new dimension right after a `reannotate` round.
- **Verified (offline only).** `py_compile` passes. `purge_checkpoint_ids` tested on a COPY of the
  real narrow checkpoint: 268→265 rows after dropping 3 ids, redo ids absent, no duplicate ids,
  columns aligned to `CHECKPOINT_COLUMNS`, `.bak` created. **NOT verified:** the live re-annotation
  loop (needs a SAIA token) and the full `reannotate → collect → review` cycle against real data.
- **Next.** When a token is available: `reannotate narrow` (or capped) → `collect "" "" "" r1`
  → `review`; separately still owe `a-gold` + a `gold` pass for `software_lifecycle` (see State).
- **Caveat to remember.** A capped `--advance N` reannotate leaves confirmed papers beyond N with
  NaN `software_lifecycle_*` until a later round redoes them — by design (token budget), not a bug.

### 2026-06-20 — recover-work: logged the unlogged 06-19 `methodology`→`software_lifecycle` migration; no run to interrupt
- **Why this pass.** User asked to "save the current state for continuation and safely
  interrupt the run." The 2026-06-19 work was entirely UNLOGGED (this file's State said
  "Last updated 2026-06-18 / nothing running"), so recovered intent from mtimes + the new
  `software_prozesskategorien.md` note + schema backups rather than git.
- **What happened on 06-19 (reconstructed).** The `methodology` typology dimension was
  **replaced by `software_lifecycle`** — the six classical SW-lifecycle phases
  (projektdefinition_hintergrund, anforderungen, entwurf, implementierung,
  testen_qualitaetssicherung, deployment_betrieb) seeded from `software_prozesskategorien.md`
  ("Dies statt der Methodologiefrage"). Done by **hand-editing `prompts/category_schema.yaml`**
  (13:42 backup → `category_schema.backup-2026-06-19.yaml`; final edit 14:57). The old
  `methodology` block is preserved in that backup + a removal comment in the YAML.
  Also added `pipeline_workflow.qmd`/`.html` (mermaid diagram of `run_pipeline.cmd`).
- **Coders ran a gold session** (`goldstandard/coding_{alice,bob}.csv`, 15:32; pre-edit copies
  in `*.backup-2026-06-19.csv`). Both coded the gate + `research_position`, `software_type`,
  `techstack`, `evaluation` and **deliberately skipped the old `methodology` dimension** — which
  is what motivated the replacement. (alice 20 gate rows; bob 16.)
- **Consistency check after the migration (read + grep, NOT run live):**
  - `categories.py` derives `DIMENSIONS`/`TYPOLOGY` from the YAML, so the rename needed **no
    Python change**. Confirmed **no `src/*.py` references `methodology`** (grep) — the only
    `methodology` hits left are docs, the YAML backups, the old gold model-annotation checkpoint,
    and stale candidate CSVs.
  - `build_goldstandard.py` walks `cat.DIMENSIONS` dynamically and reads model columns via
    `row.get(f"{dim}_category")`, so the now-absent `software_lifecycle_category` column just
    yields `None` (no model suggestion shown) instead of crashing. **Migration is code-complete.**
- **DANGLING / data-level (the real recovery target — needs token, NOT done here):**
  1. The gold model-annotation checkpoint
     `results/checkpoints/annotations_goldconfirm_..._run_1_checkpoint.csv` still has
     `methodology_*` columns and **no `software_lifecycle_*` columns** (annotated under the old
     schema). So in the coding UI the new dimension has **no model suggestion**. Re-run **`a-gold`**
     (🔑 token) over `.workingset/gold` to annotate `software_lifecycle` under the new prompt.
     Beware the known straggler-skip gotcha (use `a-gold <token> overwrite` if a clean re-annotate
     is wanted).
  2. `software_lifecycle` is a **brand-new, never-coded** dimension — alice/bob's existing rows do
     not cover it; a follow-up `gold` coding pass is needed (resumes at first undecided paper).
  3. The old `methodology_*` data in the gold checkpoint is now orphaned (harmless; ignored by the
     new dims' `row.get`).
  4. `ideas.md` (separate, NOT started): a utility to sync coder working files (papers +
     checkpoints) to `P:\24-0012_KTS_RSE-Master\05_Research\lni_study_working_files` so the 2nd
     coder can proceed after the top-up; keep backups + git-pull in sync.
- **"Interrupt the run":** at recovery time **no python/cmd/quarto/biber process was running**
  (checked `Get-CimInstance Win32_Process` + `Get-Process`) — nothing to kill. Any interactive
  `build_goldstandard.py` session lives in a coder's own terminal and is **resumable**
  (full-rewrite persistence after every decision), so Ctrl-C there loses nothing.
- **Verified:** code-consistency by reading + grep only. **NOT** run: `py_compile`, any live/token
  step, or the interactive coding loop.

### 2026-06-18 — short-paper cap: pool + top-up draw held to <=20% short (<6 pages)
- **What & why.** Short papers (<6 pages: abstracts, posters, front-matter — e.g. the 2-page
  `lni52/GI.-.Proceedings.52-53.pdf` straggler) lack the section anchors the extractor and the
  human coders rely on, so a goldstandard dominated by them is hard to code. New constraint: at
  most **20% of the `pool` reservoir AND of the `confirm` top-up drawn from it** may be short.
- **New module `src/paper_length.py`** — the single source of the rule. Constants
  `SHORT_PAGE_THRESHOLD = 6`, `MAX_SHORT_FRACTION = 0.20`; `page_count()` (wraps
  `pdf_text_extraction.get_page_count`, None on a broken PDF); `is_short()` (None/unknown =>
  NOT short — an unmeasurable paper is not charged against the quota; 6 pages is NOT short);
  `short_allowed(n_short, n_total)` = `(n_short+1) <= frac*(n_total+1)` — a RUNNING invariant
  that keeps `short/total <= frac` after every accepted paper, so the cap holds at ANY final set
  size (even a corpus exhausted before target); `fraction_ok()`, `short_fraction()`,
  `order_within_cap()` (stable two-queue interleave; emits a short only when `short_allowed`,
  drops nothing).
- **`select_candidates.py` (pooling).** Added a `pages` column to the score cache + every
  manifest (page count computed once at extract time, cached, recovered lazily for old caches).
  The streaming gate now SKIPS an over-quota short positive for a capped set and keeps scanning
  (leaving the set possibly short of target rather than over-quota short). New flags
  `--short_pages` / `--max_short_frac` / `--short_cap_sets` (default `pool`). Final per-set
  `assert fraction_ok(...)` guards the invariant; the run reports skipped shorts + per-set short%.
- **`confirm_positives.py` (topping off).** The pool overflow is reordered with
  `order_within_cap` before the draw, so whatever prefix the top-up stops at stays <=20% short
  (the named `--set` itself is left untouched — the cap is scoped to the pool it draws from).
  New `--short_pages` / `--max_short_frac`; `topup_goldstandard.py` forwards both to `confirm`.
- **`run_pipeline.cmd`.** New `SHORT_PAGES=6` / `MAX_SHORT_FRAC=0.20` config vars wired into the
  `estimate`, `manifests`, `confirm`, and `topup` steps.
- **Verified (offline, NO token):** `tests/test_short_paper_cap.py` — 23 checks, all pass.
  Pure invariants; 300 randomized `order_within_cap` trials on <=20%-short input (every prefix
  capped, length-preserving) + over-cap degenerate inputs (nothing dropped); PyMuPDF
  `page_count` on synthesized PDFs; and an END-TO-END `select_candidates` run on a synthetic
  40-short/40-long corpus -> pool = 49 papers, **9 short (18%)**, 31 over-quota shorts skipped,
  assertion held with the corpus exhausted before target. NOT yet exercised: a live run against
  the real corpus/`confirm` (no token spent). Still uncommitted.
- **Scope note.** The cap is on `pool` only (the request: "the pool"). narrow/gold/final are
  uncapped; pass `--short_cap_sets pool,gold` (or wire it in the .cmd) to extend it to `gold`.

### 2026-06-18 — `i`=insufficient-information coder option (reserved sentinel, NOT skip)
- **What & why.** A coder needs to record "the paper does not contain enough information to
  code this dimension" as a real ANSWER — distinct from skipping the dimension. New reserved
  category `categories.INSUFFICIENT_INFO = "insufficient_information"` (a CSV-safe descriptive
  string, deliberately NOT the literal "NaN", which pandas would coerce to a missing value). In
  the goldstandard coding flow the coder presses **`i`** at a dimension to assign it.
- **Semantics.** `i`=insufficient writes a row and counts in ICR as a nominal label (two coders
  both marking it AGREE; one marks it / the other codes a real category = disagreement). This is
  intentionally different from `s`=skip, which returns nav 'skip' and writes NO row (the
  dimension stays undecided and is excluded from ICR as pairwise-incomplete). Because the
  sentinel is reserved, `is_new` is always False, so it is never recorded to the
  `new_categories_<coder>.csv` sidecar nor synced into the schema as a coder-coined category.
- **How.**
  - `categories.py`: new `INSUFFICIENT_INFO` constant + `is_reserved_category(value)` helper
    (single source of truth).
  - `build_goldstandard.py`: `prompt_decision` gains an `'i'` branch returning
    `(cat.INSUFFICIENT_INFO, False, None)`; menu text + module/function docstrings updated;
    `is_new_category` now counts the sentinel among `known` (never new).
  - `sync_coder_categories.py`: `collect_coder_categories` defensively skips any
    `is_reserved_category` token, so even a sentinel row wrongly flagged `is_new` can never be
    lifted into the schema.
  - `compute_icr.py`: unchanged — it already treats `final_category` as a nominal label, so the
    sentinel participates correctly.
- **Verified OFFLINE (no token, no TTY, no corpus):** `py_compile` of the 4 touched/related
  modules; a synthetic test asserted: `prompt_decision('i')` returns the sentinel with
  `is_new=False`/`nav=None` and is not treated as `new`; `save_decisions`→`load_decisions`
  round-trips the sentinel as a STRING (not NaN-coerced) with `is_new=False`; `sync` skips a
  sentinel row even when marked `is_new=True` while still collecting a genuinely-new category;
  and `compute_dimension_icr` scores both-insufficient as raw_agreement 1.0 and
  one-insufficient-vs-real as 0.0. **NOT verified:** the interactive prompt in a real terminal.
- **Not committed:** still uncommitted in the `lni_study` repo (commit only on request).

### 2026-06-18 — coder-coined categories merged into the schema as groundtruth (`synccats`; `gold` auto-extends)
- **What & why.** When one coder advances further during coding and INVENTS a new
  subcategory (a name the seed list and the other coder did not offer), the other coder is
  extremely unlikely to independently guess the same category AND the same name — so it would
  otherwise register as a pure disagreement in `compute_icr` and the typology would never
  accumulate the coders' findings. New step **`synccats`** lifts every coder-created (is_new)
  category out of the coding files and merges it into the SINGLE SOURCE OF TRUTH
  (`prompts/category_schema.yaml`) as **active groundtruth**, so the next coder (and the model)
  sees it as a first-class category.
- **How.**
  - `src/sync_coder_categories.py` (NEW): `collect_coder_categories(shared)` reads every
    `coding_<coder>.csv`, keeps `is_new==True` rows (RS-gate rows are is_new=False so they
    never leak), splits multi-value (techstack) `final_category` on ';', and returns
    `{dim: {key: {coders, count}}}`. `load_sidecar_descriptions(shared)` reads the optional
    `new_categories_<coder>.csv` sidecars for human one-line definitions.
    `merge_coder_categories_into_schema(shared, bucket="active", dry_run, schema_path)` appends
    each genuinely-new key to `dimensions.<dim>.active` as
    `{key, source: "coder:<names>", description: <sidecar or "">}`, deduped against the
    dimension's active/rejected/candidate keys AND the alias (`examples`) names — mirrors
    `narrow_categories.merge_candidates_into_schema`. `--bucket candidates` routes them through
    the normal `review` inbox instead of trusting them directly; `--dry_run` reports without
    writing. Default target is `active` ("as groundtruth", the intent).
  - `src/build_goldstandard.py`: when a coder applies a new category, `record_new_category(...)`
    now prompts once for a one-line description and persists it to a per-coder
    `new_categories_<coder>.csv` sidecar (cols `dimension,key,description,coder`). This supplies
    the human DEFINITION so the merged category is immediately usable — an active entry with an
    EMPTY description is excluded from the model prompt (the existing `categories.py` forcing
    function) until one is written.
  - `run_pipeline.cmd`: new `synccats` dispatch + step body; **`gold` now auto-runs `synccats`
    first** (the "gold step needs an extension that includes the other coders' input into the
    knowledge base" ask) so each session starts from a schema that already contains the other
    coders' new categories. Header REM + usage updated.
- **Provenance, not silent trust.** Merged entries carry `source: "coder:<names>"` so a curator
  can see exactly which coder(s) coined each one and reconcile in the YAML.
- **Verified OFFLINE (no token, no TTY, no corpus):** `py_compile` of both changed scripts; a
  synthetic two-coder fixture (alice+bob both coin `NEW_A` with a sidecar description; bob alone
  coins `NEW_B` with NO description; alice also "uses" an existing seed key that must be ignored)
  asserted: collect returns exactly `{NEW_A, NEW_B}` with the right coder sets, the existing seed
  does NOT leak in, `--dry_run` writes nothing, the real merge adds `NEW_A` (described,
  `source: coder:alice,bob`) and `NEW_B` (empty desc, `source: coder:bob`) to `active` without
  duplicating the seed, a second merge is idempotent (adds nothing), and `categories.py` loading
  the merged temp schema RENDERS `NEW_A` while EXCLUDING+warning on the undescribed `NEW_B`. All
  GREEN; the real `prompts/category_schema.yaml` was untouched (test merged against a temp copy
  via the `schema_path` param). **NOT verified:** the interactive description-capture prompt in a
  real terminal, and a live `gold`→`synccats`→`gold` cycle with real coder CSVs.
- **Not committed:** still uncommitted in the `lni_study` repo (commit only on request).

### 2026-06-18 — `compute_icr` restricted to the human-confirmed goldstandard (RS veto)
- **What & why.** ICR must describe only papers that actually contain research software.
  `src/compute_icr.py` now includes a paper in the dimension reliability **only when BOTH
  coders set the research-software gate to rs=1**; a single rs=0 from either coder is a
  **veto** that removes the paper from every dimension. This resolves the prior open design
  call ("`compute_icr` does NOT yet score the human RS gate").
- **How.** New helpers `confirmed_rs_ids(state_a, state_b)` (returns `confirmed` = both rs=1,
  `vetoed` = one rs=1/other rs=0) and `gate_agreement(...)` (raw agreement over papers both
  coders decided). `main()` loads each coder's `coding_<name>.csv` via
  `build_goldstandard.load_decisions`, computes `confirmed`/`vetoed`, filters both coder
  dataframes to `confirmed` ids **before** the dimension loop, and exits early if no paper is
  both-confirmed. The gate is reported separately (console + a line in `icr_goldstandard.md`),
  NOT as a typology dimension. RS_DIM rows never enter the dimension loop (not in
  `cat.DIMENSIONS`).
- **Verified (offline).** `py_compile` + a synthetic two-coder fixture: P1/P2 both rs=1
  (kept), P3 rs=1 vs rs=0 (vetoed, excluded), P4 both rs=0 (gate-only). Asserted
  `confirmed={P1,P2}`, `vetoed={P3}`, gate agreement 0.75 over 4 jointly-decided papers, and
  end-to-end `n_shared==2` on every dimension (P3 absent), eval raw_agreement 0.5,
  research_position 1.0, plus the gate line in the `.md`. NOT yet run on real coder data
  (only one coder file exists so far). Still uncommitted in the `lni_study` repo.

### 2026-06-18 — new `topup` step: separate human-confirmed from rejected + refill the gold set
- **What & why.** After a `gold` coding pass the human rejects some LLM-confirmed papers
  (rs=0), which shrinks the usable goldstandard below the target. New step **`topup`**
  (`src/topup_goldstandard.py` + `run_pipeline.cmd :topup`, dispatch + header + usage)
  runs AFTER `gold` and:
  1. reads `goldstandard/coding_<coder>.csv` via `build_goldstandard.load_decisions`,
     **partitions** confirmed (rs=1) / rejected (rs=0) / uncoded, and writes two shareable
     CSVs: `gold_human_confirmed_<coder>.csv` (one row per confirmed paper WITH its full
     per-dimension typology coding — the actual goldstandard slice) and
     `gold_human_rejected_<coder>.csv`.
  2. computes `effective_target = bump(target=%GOLD%)` — grown by **+20** each time the
     human-confirmed count comes within **10** of it (so as confirmations approach e.g.
     90/100 the goal becomes 120, making it likely enough real-RSE papers are found), then
     `confirm_target = effective_target + #rejected`.
  3. tops `.workingset/gold_confirmed` up to `confirm_target` by invoking
     `confirm_positives.py --set gold --target <confirm_target>` — which is cumulative +
     cached, so it only annotates NEW `pool` papers and appends them to the SAME
     `goldconfirm` checkpoint the `gold` step reads.
- **Resume-aware (the "continue where the coder came" ask).** `build_goldstandard.run_session`
  now **starts at the first undecided paper** (rs is None) instead of paper 1, so after a
  top-up appends fresh papers to the end of the worklist, re-running `gold` lands the coder
  directly on the new ones (earlier papers still reachable via p/g).
- **Token discipline.** The top-up only spends SAIA quota when a token is resolved AND
  `--dry_run` is not set; otherwise it just writes the separation CSVs and PRINTS the exact
  `confirm` command (token value redacted as `<TOKEN>`). The `:topup` cmd step passes the
  token only when one is resolved, same as the other token steps.
- **Verified OFFLINE (no token, no live API):** py_compile of both changed scripts; a dry-run
  over synthetic fixtures (90 confirmed / 30 rejected / 120 LLM-confirmed) produced the right
  partition counts, the +20 bump (→120), `confirm_target=150`, `need=30`, and the redacted
  command; the prompt-template default resolves to `rse_typology_prompt_v1.md` (so the refill
  appends to the same checkpoint `gold` reads); the no-bump and already-enough (need≤0) branches
  and 6 bump-math edge cases all pass. **NOT verified:** a live token refill end-to-end, and the
  interactive resume jump in a real terminal.
- **Still open (unchanged):** `compute_icr.py` does not score the human RS gate. Still
  uncommitted in the `lni_study` repo (commit only on request).

### 2026-06-18 — `recover-work` pass: recovered the RSE-human-check rewrite of `build_goldstandard.py`
- **Anchor this time was git, not just mtimes.** `lni_study` turned out to be its OWN
  git repo (a gitlink inside `publications`, hence the parent's `AM lni_study`). HEAD =
  `c120823 "current changes to pipeline -pre RSE human check"`, committed 2026-06-18 13:34.
  That checkpoint captured the whole 06-18 13:12–13:15 file cluster (run_pipeline.cmd,
  select_candidates, annotate_lni, confirm_positives, narrow_categories, compute_icr) AND
  the earlier `evaluation` dimension (`da38f4f`). The ONLY uncommitted change vs HEAD was
  `src/build_goldstandard.py` (+205/−66) — which is also the newest file on disk (13:41,
  7 min AFTER the checkpoint commit). So: session committed a "pre-feature" checkpoint,
  started the RSE-human-check feature, crashed before committing or documenting it.
  NEXT_STEPS.md (last touched 06-17 19:18) described NONE of the 06-18 work.
- **The in-flight feature (now recovered, was already complete on disk):** a human
  RS-boolean gate in the goldstandard session. `prompt_decision` now returns a 3-tuple
  `(final, is_new, nav)` with nav ∈ {None, skip, back, quit} and takes `current=` to KEEP
  a prior decision. New `load_decisions`/`save_decisions` keep the whole decisions file as
  in-memory state and REWRITE it on every decision (resumable AND editable, not append-only).
  New `run_session` driver: per paper the coder re-validates `label_research_software` by
  hand; rejecting (rs=0) CASCADES — dimensions skipped, only the RS row written. Navigation
  p/x/g/q + b/s. `main()` rewired to `load_decisions` → `run_session`. Decisions CSV now
  carries one `label_research_software` row per coded paper plus one row per dimension.
- **NOT a half-migrated crash** — every `prompt_decision` return is the new 3-tuple, its
  sole caller (run_session, l.355) unpacks 3, the old append loop in `main()` is fully
  removed, nothing else imports the module. Both halves consistent.
- **Verified (no token, no TTY, no corpus):** `py_compile` OK; `categories` surface intact
  (`DIMENSIONS` now = research_position/methodology/software_type/techstack/**evaluation**;
  `dimension_guidance`, `TYPOLOGY` present) and run_session/save_decisions iterate
  `cat.DIMENSIONS` so they pick up `evaluation` automatically. **Unit-tested the riskiest new
  logic offline:** a save→load round-trip on a fake 2-paper frame confirmed rs=1 with two dim
  rows round-trips, rs=0 writes ONLY the RS row (cascade holds), and `is_new`/`_to_bool`
  survive the CSV. **NOT verified:** the interactive `run_session` loop (needs a TTY) and a
  real end-to-end gold run (needs PDFs + a Phase-A annotation CSV).
- **Reconciled the one straggler doc:** the module docstring at the top of
  `build_goldstandard.py` still described the OLD append-only flow — rewrote it to describe
  the RS gate + cascade, forward/back/goto navigation, and full-rewrite persistence.
- **Open design call (surfaced, NOT silently changed):** `compute_icr.py` loops the 5 real
  `cat.DIMENSIONS`, so it silently IGNORES the new `label_research_software` rows — ICR is
  NOT computed on the human RS gate. No crash (rows just don't match), but if you want
  intercoder agreement on the RS boolean too, `compute_icr` needs a row added for it. Decide
  before the gold/icr run.
- **Not committed:** `build_goldstandard.py` (feature + docstring) is still uncommitted in
  the `lni_study` repo; `lni_study` itself is an uncommitted gitlink in `publications`. Commit
  only on request.
- Resume: from State → Next. The gold session is ready to RUN (`run_pipeline.cmd gold`) once a
  Phase-A annotation CSV for `.workingset/gold` exists; first live use is still unverified.

### 2026-06-17 — `recover-work` pass: recovered & verified the `a-gold --overwrite` feature
- Crash-site signal: two files newer than this notes file (18:12) — `src/annotate_lni.py`
  (18:24) and `run_pipeline.cmd` (18:28, newest). Everything else in `src/` was ≤18:12
  and matched the notes. The 18:24/18:28 edits were undocumented in-flight work.
- The in-flight change (motivated by the 18:12 prompt rewrite — re-annotate gold with the
  new enriched/no-speculation prompt, which plain `a-gold` skips because it resumes):
  - `annotate_lni.py`: new `--overwrite` arg + a block (right before `done_ids` is built)
    that renames the existing checkpoint AND new-suggestions CSV to `.bak` (`.bak2`, `.bak3`
    on collision). Originals gone → empty `done_ids` → fresh header, no skips, no dup rows.
  - `run_pipeline.cmd :a_gold`: 3rd arg `overwrite` (or `force`) sets `OVERWRITE_ARG=--overwrite`,
    passed before `%TOKEN_ARG%`. REM header + step comment updated.
- **NOT a half-migrated crash** — both halves were already complete and consistent. Verified
  (no token, no corpus): `checkpoint_path`/`suggestions_path` defined (l.599-600) before the
  new block; cmd token is `%~2` so `overwrite` lands in `%~3` as the code expects; `py_compile`
  passes; `--help` lists `--overwrite`. Only the docs were missing — now reconciled (State + this).
- **Honest caveat:** `--overwrite` re-attempts the lni52 straggler too, but its failure is
  DETERMINISTIC (`extract_main_content` → None; the short-paper fallback, option b, was NOT
  added — `pdf_text_extraction.py` untouched since 06-15), so `a-gold <token> overwrite` still
  lands 99/100 with lni52 failing. Not run live (needs token).
- Resume: unchanged — State → Next. To refresh gold with the new prompt: `run_pipeline.cmd a-gold <token> overwrite`.

### 2026-06-17 — merged subcategories become `examples` (synonym whitelist), not rejections
- **New schema shape:** an `active` entry may carry an optional `examples:` list of
  alternate subcategory NAMES that were merged into it. They render in the prompt
  after the description as a synonym hint — e.g.
  `` - `middleware_service`: … (auch: `middleware_service_integration`, `middleware_integration_tool`) ``.
- **Removed the 16 auto "merged into X (same subcategory, different wording)."
  rejections** (15 in software_type, 1 in techstack) and re-attached each removed
  key as an `examples` alias under its former `move_to` target. The human-reasoned
  `move_to` rejections (e.g. web_service_api, integration_extension) were KEPT as
  rejections — only the boilerplate merge entries moved.
- **categories.py:** `_build` collects each active entry's `examples` into
  `TYPOLOGY[dim]["aliases"]`; `render_categories_block` appends them as `(auch: …)`.
  `TYPOLOGY[dim]["examples"]` (the `{key:desc}` map other code relies on) is
  unchanged in shape.
- **narrow_categories.py:** the `[m]erge` review action now appends the candidate
  to the chosen active entry's `examples` list (was: a `rejected`+`move_to` entry),
  so future rounds don't recreate the merge boilerplate. `merge_candidates_into_schema`
  dedup now also skips any name already in an active `examples` list, so a merged
  alias is never re-offered as a fresh candidate.
- **Verified:** 0 leftover "merged into" rejections; all 10 alias groups render as
  `(auch: …)`; `schema_io` round-trips; a temp-copy test confirmed a re-suggested
  alias (`testing_framework`) is skipped by collect while a genuinely new key is
  added. Real schema untouched by the test; UTF-8 intact.

### 2026-06-17 — post-round cleanup of category_schema.yaml + no-speculation prompt rule
- **Backup first.** Copied the live schema to
  `prompts/category_schema.backup-2026-06-17.yaml` BEFORE editing (the working
  copy is `prompts/category_schema.yaml`; both untracked in git, so the .bak is
  the only restore point).
- **Cleaned the working copy** (reflecting the first loop round's accept/merge
  decisions):
  - Filled every empty `source:added` description — the WARNING that excluded
    them from the prompt is gone (`schema_io` round-trip confirms 0 empty active
    descriptions). For the heavily-merged categories the description is the
    *common denominator* of what was merged in: `middleware_service` (absorbed
    web_service_api / proxy_server_application / workflow_management_system /
    middleware_integration + 2 more), `test_automation_framework` (testing_framework,
    test_code_generator), `data_exchange_standard` (schema_definition_tool).
  - Applied the two `pending_restructuring` renames: techstack `perl_web -> perl`,
    `hdl_hardware_description -> hardware_description_languages` (dropped the
    now-satisfied `rename_to` notes).
  - Replaced two verbose model-rationale "descriptions" (flash_animation_tools,
    visual_basic) with concise category definitions.
  - Trimmed `pending_restructuring` to just the still-open Math-RSE grouping
    question; removed the resolved add_category/rename/fill_descriptions items
    and the stale "target group does not exist yet" note on `web_service_api`.
  - **Judgment-call descriptions I authored** (standard SE/RSE concepts, derived
    from key name since no human definition existed yet — review & adjust if the
    intended meaning differs): methodology commercial_software_adaptation /
    standardization_driven / model_driven_optimization; software_type
    domain_specific_language / deep_learning_model. Kept the rejected keys intact
    (the loop dedups new candidates against them).
- **Prompt template** (`prompts/rse_typology_prompt_v1.md`, Schritt 2): added a
  "WICHTIG — keine Spekulation" paragraph. A subcategory / new_suggestion may
  only be assigned when the publication's text EXPLICITLY supports it; the model
  must not infer from context what is "typischerweise/üblicherweise/vermutlich"
  used, and must justify each category with the concrete textual evidence. This
  matches the `Spekulation`/`fehlende explizite Nennung` rejection reasons the
  human gave in techstack.
- **Verified:** `categories.render_categories_block()` renders all keys with no
  exclusions; `schema_io.load_schema()` round-trips with 0 empty descriptions and
  the renamed keys present; UTF-8 intact (console mojibake only). NOT re-run
  against SAIA/the corpus — re-annotation with the new prompt is the next step.

### 2026-06-17 — one-command `round`; review CLI gains `[m]erge` + rationale fallback
- **`run_pipeline.cmd round`** — single command that runs the loop iteration
  `advance -> collect -> review` back-to-back (aborts the round if advance or
  collect fails, so review never runs on a half-finished batch; only advance
  spends token). 5th arg = round label (advance fixed at the default %NARROW%
  batch). The three stages stay exposed individually. REM header + usage updated.
  Usage path re-run to confirm the batch still parses.
- **`narrow_categories.py` review CLI, two additions** (py_compile OK; surfaced 32
  real pending candidates live, then stopped before any decision so the schema is
  untouched):
  - `[m]erge->existing`: lists the dimension's `active` subcategories with numbered
    quick-keys; picking one records the candidate under `rejected` + `move_to:<key>`
    (renders as "use X instead"). `[b]`/blank backs out and re-prompts the SAME
    candidate — the per-candidate decision was restructured into one `while action
    is None` loop so a sub-menu/invalid input no longer skips the candidate.
  - Accept with an empty description now FALLS BACK to the candidate's model
    `rationale` as the description (only stays pending if neither exists).
  - **Both write paths verified END-TO-END** (not just compile): a throwaway-copy
    harness drove accept-empty (→ rationale written to `active`, source:added) and
    merge (→ `rejected` + `move_to:<picked key>`), confirming consumed candidates
    are removed and the YAML round-trips with comments + UTF-8 umlauts intact. Real
    schema untouched. Caveat: rationale-as-description is verbose (model hedging) —
    tighten accepted ones in the YAML.
- **Heads-up:** `prompts/category_schema.yaml` already holds 32 pending candidates
  from a pre-compaction `collect` — `review` (or `round`) has material to work now.
- Submodule still uncommitted. No token spent this pass.

### 2026-06-17 — category schema is now the SOURCE OF TRUTH; narrowing LOOP wired
- **Architecture flip.** `prompts/category_schema.yaml` is now the single source of
  truth for the typology. `src/categories.py` derives RSE_DEFINITION / TYPOLOGY /
  prompt guidance from it (via the new `src/schema_io.py` ruamel round-trip layer),
  so every consumer reads the YAML through `categories.py`'s public surface — no
  call-site changes were needed to flip the pipeline. **Retired:**
  `prompts/category_whitelist.json` + the JSON review CLI are no longer the system
  of record (file not deleted yet — see State → open questions).
- **Per-dimension shape** in the YAML: `active` (offered to the model; an active
  entry with an empty `description:` is EXCLUDED + warned), `rejected` (human ruled
  out, with reason/move_to → "do not use" guidance), `candidates` (merge-not-clobber
  inbox the loop appends to). Each dimension was pre-seeded with an empty
  `candidates: []` bucket (NO end-of-line comment) right after its `rejected:` list —
  this is a CONVENTION, not optional: it forces ruamel to land appended candidates in
  place instead of after the trailing `pending_restructuring` banner.
- **The narrowing LOOP (grounded-theory theoretical sampling), now a real cmd flow:**
  `advance` (confirm the next 50 papers, **token**) → `collect --to_schema` (mine each
  paper's `new_suggestion` and append to the YAML `candidates`, **no token**) →
  `review` or hand-edit the YAML (promote candidates to active/rejected, fill
  descriptions, **no token**) → repeat until **saturation** (collect adds ~0 new
  candidates for ~2 rounds) → lock → `a-gold`/`gold`. Stopping rule documented in
  the cmd header.
- **Code touched:** `schema_io.py` (NEW; indent matched to hand-authored style so
  appends don't reflow the file). `narrow_categories.py::merge_candidates_into_schema`
  (positional-insert fallback for a missing bucket; dedup + freq bump in place).
  `confirm_positives.py` (new `--advance N` mode: confirm next N without a `--target`
  top-up; summary handles `target=None`). `run_pipeline.cmd` (header + dispatch +
  `:advance`/`:collect`/`:review` step bodies + usage). `requirements.txt`
  (`ruamel.yaml>=0.18.0`).
- **Verified OFFLINE only (no token, no SAIA, no corpus scan):** real schema loads
  through `categories.py` (DIMENSIONS = research_position/methodology/software_type/
  techstack; rse_def len 362; block style preserved); `merge` lands candidates in the
  right bucket and round-trips comments; `review` reports "No pending candidates" on
  empty `[]` buckets; `confirm --advance` argparse; `collect --from_set narrow` mines
  48 suggestions (dry). **NOT yet run live** — no `advance`/`collect` against SAIA has
  happened (consistent with "don't spend token without being asked").
- **Bugs fixed this pass:** schema_io `offset=0` churned every dash → `offset=2`;
  techstack candidates landed after the `pending_restructuring` banner (ruamel binds
  that comment to the last `rejected` item) → pre-seeded empty buckets; an eol comment
  on `candidates:` re-broke placement → removed (header documents the bucket instead);
  a `collect` dispatch test accidentally appended 15 candidates to the untracked schema
  → restored via Write.
- **Submodule still uncommitted** (`publications`) — not to be committed without an
  explicit request.
- Resume: from State → Next. The loop machinery is ready; first live use is
  `advance` (token) on the narrow set, then `collect --to_schema`, then `review`.

### 2026-06-17 — `recover-work` pass: no crash; `a-gold` already complete (99/100)
- The State said `a-gold` was "in flight". Disk says otherwise: no python running,
  nothing newer than NEXT_STEPS.md, and the gold annotation finished 2026-06-16 19:24.
  The "in flight" line was stale — corrected in State above.
- Verified from disk (no token, no corpus scan): gold = 100 PDFs / 100 manifest rows /
  100 checkpoint rows (consistent). Annotations 99/100 clean (60 label=1, 39 label=0).
- One straggler: `lni52/GI.-.Proceedings.52-53.pdf` → `pdf_extraction_failed`, empty
  label. Resume won't retry it (id is in `done_ids` regardless of error,
  `annotate_lni.py:611-619`).
- Diagnosed it fully (no token): genuine 2-page German paper, PDF + raw text fine
  (4288 chars, not corrupted). Failure is `extract_main_content` returning None — the
  paper lacks every section anchor it keys on (Einleitung/Abstract:/Keywords:), so it
  falls through all 6 priorities (`pdf_text_extraction.py:206`). DETERMINISTIC: a token
  re-run won't fix it. Documented the two real options in State (drop → gold=99, or add
  a short-paper fallback then re-annotate just this id).
- Resume: from State → Next. Decide the lni52 row (drop vs short-paper fallback), then
  proceed to `gold` (build goldstandard) → `icr`.

### 2026-06-16 — recovered an in-flight edit: review CLI gained explicit `[f]orward`
- `recover-work` pass. Crash-site signal: `src/narrow_categories.py` (18:34) was
  newer than `NEXT_STEPS.md` (18:32) — an edit made AFTER the notes were written.
  Sequence on disk: review run saved `category_whitelist.json` (18:31) → candidates
  regenerated + notes updated (18:32) → `narrow_categories.py` edited (18:34).
- The in-flight change (already on disk, complete): `run_review`'s prompt is now
  `[a]ccept / [d]ecline / [b]ack / [f]orward / [s]kip / [q]uit`. `[f]orward` was
  added as an explicit synonym of `[s]kip` (both advance the cursor without
  changing a decision), symmetric to `[b]ack`. Input validation, the branch, and
  the explanatory comment all agree — nothing half-done in the code.
- Reconciled the stale docs the notes/code drift left behind: `TASKS.md` 7b-ii and
  `narrow_categories.py`'s module docstring both still listed only the old
  `[a]/[d]/[s]/[q]` prompt; updated both to include `[b]ack`/`[f]orward`.
- Verified: `py_compile` passes; every prompt-string ↔ validation-tuple ↔ branch
  triplet matches. **Not** run interactively (review needs a TTY). No token spent,
  no corpus scanned.
- Resume: unchanged from below — `run_pipeline.cmd review` to keep narrowing
  (software_type + techstack still untouched; revisit the missed methodology
  category via `[b]ack`).

### 2026-06-16 — fixed bogus `''`/`nan` candidate in `collect` (review showed empty key)
- Bug: review displayed a candidate with key `''` and a `nan || nan || ...` rationale,
  one per dimension (freq 50/44/36/37). Root cause in `collect_candidates`: pandas
  reads a blank `<dim>_new_suggestion` as float NaN, and `str(NaN) == "nan"` is a
  truthy non-empty string, so the old guard `if sugg is not None and str(sugg).strip()`
  let every empty suggestion through as a literal `"nan"` key (same for explanations).
  `to_csv` wrote `"nan"`; `read_csv` parsed it back to NaN; review's `.fillna("")`
  rendered it as `''`.
- Fix: new `clean_cell(v)` helper (None for NaN/blank/`"nan"`/`"none"`), used for the
  chosen category, the suggestion key, AND the explanations. Also a defensive skip in
  `run_review` so a stale CSV can't resurface the blank key.
- Cleaned artifacts: removed the 2 bogus `''` decisions the user had recorded in the
  whitelist (research_position + methodology blacklists). Regenerated
  `results/category_candidates_narrow.csv` from cached annotations (no token): **66 → 62
  rows**, 0 bogus, 29 seed + 33 genuine suggestions. Real prior decisions preserved
  (all on seed keys that still exist): research_position 5 acc/1 dec, methodology 3 acc/5 dec.
- Verified: `py_compile` passes; `collect` re-run live (cache-only, no token) and the
  CSV confirmed clean. Review not re-run interactively (needs a TTY).
- Resume: `run_pipeline.cmd review` to continue narrowing (software_type + techstack
  still untouched; revisit the missed methodology category via `[b]ack`).

### 2026-06-16 — review CLI: added [b]ack navigation + re-decide
- `narrow_categories.py --mode review` now flattens all candidates (across the 4
  dimensions) into one navigable list with a movable cursor and a `[b]ack` option,
  so you can step to the previous candidate and CHANGE an earlier decision. Old
  code skipped any already-decided key, so a missed/wrong call could not be fixed
  without hand-editing the JSON.
- New helpers: `current_decision(entry,key)` (accepted/declined/None) and
  `set_decision(...)` (drops any prior entry in either list, then appends — so
  re-deciding overwrites cleanly, no dupes). Replaced `decided_keys`.
- Resume: opens at the FIRST still-undecided candidate; already-decided ones show
  `(currently accepted/declined — re-decide to change)` and can be revisited via
  `[b]`. Each candidate shows `[i/total]`. Saves after every decision (still fully
  resumable). Prompt is now `[a]ccept / [d]ecline / [s]kip / [b]ack / [q]uit`.
- Current on-disk progress (from the cancelled run): research_position 5 acc/2 dec,
  methodology 3 acc/6 dec; software_type + techstack not started. Candidates CSV:
  results/category_candidates_narrow.csv (66 rows). Re-run `review` to continue.
- Verified: `py_compile` passes. **Not** run interactively (needs a TTY).

### 2026-06-16 — confirm tqdm bar now starts at set size, grows only on top-up
- The bar starts sized to the named set (`total=len(primary)`, e.g. /50) so it
  matches "confirm the set first". It grows to the full candidate count
  (set + pool) ONLY when the set is exhausted before `--target` and top-up begins,
  printing `'<set>' exhausted at X/target confirmed -> topping up from 'pool'`.
  Removes the confusion of the bar reading /829 up front.
- Confirmed PDF source: `confirm` reads the LOCAL `.workingset` copies (manifest
  `dst`, fast disc); the `\\DC01` network `src` is only a fallback if a local copy
  is missing. "Slow startup" = the first LLM round-trip (bar sits at 0 until the
  first paper's model call returns); RateLimiter caps at 10 calls/min thereafter.
- NOTE on intent: `--target N` means "N LLM-confirmed (label==1) papers". With
  `--set narrow --target 50`, if any of the 50 narrow papers are label==0 it WILL
  top up from the pool to reach 50 confirmed. If the goal is just "annotate the 50
  narrow and see which are RSE" (no top-up), use `collect` (annotates exactly the
  set) or set a smaller `--target`.

### 2026-06-16 — added per-paper tqdm progress bar to `confirm`
- `confirm_positives.py` now shows a paper-level `tqdm` bar (`desc="Confirming
  <set>"`, `unit="paper"`) with live postfix `confirmed=X/target, annotated,
  reused, errors`. The per-batch summary still prints, via `tqdm.write` so it
  doesn't tear the bar. Matches the bar style already in `annotate_lni.py`.
- Clarified a user misunderstanding (no code implied it, just doc): `--batch` is
  ONLY a target-check + summary cadence — papers are annotated one at a time
  regardless. Top-up from the pool is driven by `--target` (walk narrow-set then
  pool until target label==1 reached), NOT by `--batch`.
- Verified: `py_compile` passes. **Not** run live (needs token).

### 2026-06-16 — recovered stale pool manifest after PID 20484 finished
- `recover-work` pass. No python running anymore → PID 20484 (old in-memory code)
  finished, score cache last written 15:38 (1800 rows). Crash-site signal: the
  score cache (15:38) was newer than NEXT_STEPS.md (15:31).
- Inconsistency found: `.workingset/pool` had **779 PDFs on disk but only 267
  manifest rows**. Cause: the 15:08 `--regen_manifests` snapshotted pool at 267
  while it was mid-growth; the old process then copied PDFs up to 779 but (running
  the OLD code that writes manifests only at the very end, or stopped before that
  write) never refreshed pool/manifest.csv. narrow/gold/final were already stable.
- Fix: ran `select_candidates.py --regen_manifests` (no corpus scan, no token) →
  pool manifest rebuilt to 779 rows (763 with cached score, 16 on disk but absent
  from the 1800-row cache — harmless, they're still pool members). narrow/gold/
  final regenerated identically (50/100/500).
- Verified: manifest rows == PDFs on disk for all four sets. **Not** run live
  (no confirm/collect/annotate executed; no token spent).
- Resume: sets are stable and consistent — proceed to State → Next step 3 (tune
  `--min_score` by reading `results/rse_scores_Proceedings.csv`) then step 4
  (`confirm --set narrow` <token> → `collect` → `review`). `confirm` now sees all
  779 pool papers when topping up.

### 2026-06-16 — "no manifest" from confirm: estimate was STILL RUNNING + durability fix
- Symptom: `confirm` failed with `No manifest at ...\gold\manifest.csv` though sets
  existed (narrow 50, gold 100, final 500, pool growing). Root cause: the OLD
  `select_candidates.py` wrote ALL manifests only at the very END of the scan, and
  the `estimate` process (PID 20484, started 15:02) was **still running**, slowly
  filling the large `pool` target (cap 2000 - 650 = 1350) — so manifests didn't
  exist yet. Not a crash, not an old/new compat issue.
- Durability fix in `select_candidates.py`: `write_manifest()` is now called the
  moment each set fills (not just at the end), so an interrupted/long pool scan no
  longer loses narrow/gold/final manifests.
- Recovery tool added: `select_candidates.py --regen_manifests` (cmd step
  `manifests`) rebuilds every `.workingset/<set>/manifest.csv` from the copied PDFs
  + score cache, NO corpus scan. Ran it: narrow 50 / gold 100 / final 500 / pool
  267 manifests written (pool was mid-growth). Verified row counts match PDF counts
  for the stable sets.
- NOTE: the code fixes apply to FUTURE runs only — PID 20484 holds the old code in
  memory and will still write its manifests at the end (harmless overwrite).
- Resume: gold/narrow/final are stable — `confirm`/`collect`/`gold` can run now.
  For pool: either let PID 20484 finish, or stop it and re-run `manifests`.

### 2026-06-16 — made `collect` self-contained (no separate confirm needed)
- `run_pipeline.cmd :collect` now exports `SAIA_API_KEY` from the resolved token
  and passes `--annotate_missing`, so `collect <token>` annotates the narrow set
  itself and then mines candidates in one command. Without a token it behaves as
  before (reuses existing checkpoints only).
- `narrow_categories.py::annotate_missing` now **persists** its annotations to
  `results/checkpoints/annotations_narrowcollect_checkpoint.csv` (merged + deduped
  by id). Previously it only returned an in-memory frame, so every `collect` re-ran
  the SAIA calls; now a re-run reuses the cache and spends no new token.
- Verified: `py_compile` passes. **Not** run live (needs token + corpus).
- Resume command: `run_pipeline.cmd collect <token>` (annotates exactly the 50
  narrow papers — does NOT top up from pool, unlike `confirm`).

### 2026-06-16 — verified confirm→collect wiring (collect returned 0 candidates)
- User ran `collect` straight after `estimate` and got `0/50 in checkpoints`,
  `29 seed + 0 model-suggested` — confusing because no LLM calls fired.
- Diagnosis: not a bug. `collect` makes no LLM calls; it reuses annotation
  checkpoints. The narrow set was never annotated, so there was nothing to mine.
- Verified (code read, not run) that `confirm --set narrow` → `collect` is wired
  correctly: matching checkpoint glob + matching `paper_id` keys. Resolved the
  long-standing "collect annotation reuse" open question.
- Resume command: `run_pipeline.cmd confirm <token> "" narrow 50` then
  `run_pipeline.cmd collect`.

### 2026-06-16 — converted this file to State+Log task-log shape
- Restructured `NEXT_STEPS.md` into the `task-logging` skill's two-part shape
  (overwritable **State** snapshot + append-only **Log**). No content lost — the
  prior "Where we are / Next steps / Open questions" sections folded into State.
- Verified: file edit only; nothing run.

### 2026-06-16 — recovered the streaming-refactor crash; finished run_pipeline.cmd
- Recovered an OOM-interrupted refactor (per the `recover-work` skill, no git).
  mtimes showed `select_candidates.py` / `sampling.py` / `confirm_positives.py`
  (Jun 16) already migrated to the streaming + confirm architecture, but
  `run_pipeline.cmd` was half-migrated: header rewritten while the dispatch
  table + step bodies still ran the OLD flow, and `:estimate` passed removed args
  (`--name/--sample`) → the pipeline was broken.
- Fixed `run_pipeline.cmd`: new dispatch (`deps|dry|test|estimate|confirm|collect|
  review|a-gold|gold|icr|full`), `:estimate` uses the real arg surface, added
  `:confirm` (set/target via 4th/5th args), rewrote `:full` to just annotate the
  pre-drawn `.workingset\final`, dropped dead `a-candidates/filter/ws-narrow/
  ws-gold` steps.
- Verified: internal consistency only (goto↔label, call signatures). **Not** run
  end-to-end; the streaming rewrite still has no tests (see State → Next step 1).
