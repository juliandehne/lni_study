# SCHEMA_CHANGELOG

Provenance log for `prompts/category_schema.yaml` — the single source of truth of
the RSE typology.

**This file is documentation only.** Nothing in it is read by `src/`; it enters
neither the model prompt, nor the gold standard, nor any agreement statistic. It
exists so that the paper can state *when* a definition was sharpened and *which
already-coded rows were decided under the earlier wording*.

## Standing policy (as of 2026-07-31)

> **No re-coding.** The deadline is close. When a definition is sharpened, the
> already-coded values stay as they are. The residual validity cost of a handful
> of rows decided under a slightly looser wording is accepted, because it is
> small against the cost of mislabelling a much larger number of cases in the
> final, definition-driven study step.

Consequence for the write-up: definitions in the paper are the *current* ones;
the rows listed below were coded under the *previous* wording. Where the count is
small the affected ids are listed in full, so the claim is checkable.

---

## 2026-08-04 — `javascript_web` requires own web-frontend work

Trigger: `lni104/103` (Bick et al., *Standards for Ambient Learning
Environments*). The paper builds an XML content chain — IMS LD package, TeachML
assets, ISO Topic Map — whose output is "published using xHTML, or WML", and
imports it into the third-party LMS Open-sTeam. No JavaScript, no own frontend.
The old wording ("JavaScript/TypeScript + Web-Frontend (HTML/CSS, React, ...)")
did not say whether *generated* delivery markup, or a web-based host system that
somebody else wrote, is enough to carry the key.

The description now demands own web-frontend or JavaScript development and names
three cases that do **not** count: generated delivery markup out of an XML chain
(→ `xml_xsd`), a third-party web-based host system (LMS, CMS, portal), and web
services used merely as an interface.

This narrows the key. Rows coded under the earlier wording — all of them decided
on genuine frontend work as far as the coding notes show, but listed here so the
claim is checkable:

- `lni216/237`
- `312/proceedings-04`
- `313/C1-1`
- `lni101/191`
- `lni287/GIL_2019_Potts_155-160`
- `lni297/DELFI2019_320_Dungeons___DFAs`

`lni104/103` itself is the first row decided under the new wording: `xml_xsd`
alone.

---

## 2026-08-04 — `evaluation` codes only what the paper itself reports

Trigger: two consecutive gold-coding rounds hit the same constellation.
`lni101/199` cites a cost-benefit assessment as `[MSK06]`; `lni101/47` cites a
full evaluation of the very system it describes — "Evaluation des E-Learning-
Systems … Methoden und Ergebnisse" `[DWGSH06]`, by the same authors — and quotes
its conclusion in one sentence. The dimension had no rule for an evaluation that
demonstrably exists but lives in a companion publication. A new key for the case
is barred by the no-recoding policy, so the rule goes into the dimension-level
`question`, next to the existing `insufficient_information` sentinel.

**Sharpening (boundary shift).** The `evaluation` `question` now states that only
what is reported *in the paper* is coded: an evaluation published elsewhere and
merely cited — even an author's own companion paper on the same software —
does not count as long as neither method nor result appears in the paper; that
case is `insufficient_information`. Once the paper reproduces the procedure or
the finding, the corresponding method is coded.

Rows at risk under the previous wording are those carrying an outcome-bearing
method: `performance_evaluation` 18, `empirical_study` 9, `benchmarking` 11,
`testing` 12, `usability_study` 2, `alternatives_comparison` 1 (68 evaluation
rows total). They are **not** listed individually and not re-coded: whether a
given row was decided on a cited external evaluation is not recoverable from the
coded data — the CSV records the value, not the sentence that carried it.

`src/check_schema_integrity.py` → OK. No `key` was added, renamed, removed or
re-scoped; only the dimension-level `question` changed.

---

## 2026-08-04 — `domain_specific_language` covers implemented exchange schemas

Trigger: gold-coding round on `lni101/199` (Verarbeitung von Geodaten in
agroXML). The artefact is an XML exchange schema — a GML application schema that
was implemented and then replaced by an embedded GML3.1.1 geometry profile. That
sits exactly in the gap between the gate, which excludes "Metamodelle … oder
Spezifikationen eines Systems", and `software_type: domain_specific_language`,
which declares "Grammatik oder Metamodell" to be *the artefact* of a language.
Deciding the gate cost real time, which is the signal that a discriminating
clause was missing.

**Sharpening (boundary shift).** `domain_specific_language` now states that
serialisation and data-exchange languages (XML exchange language, XSD/GML
application schema, ontology or vocabulary schema) fall under the key **when the
schema itself was implemented in the described work** — the schema is then the
grammar of the language and hence the artefact. It also states what the gate
exclusion targets: unimplemented conceptual descriptions, not a delivered schema.
The clause was deliberately put in the category, **not** in the gate: the gate
definition has been kept byte-stable because all 202 frame rows hang on it.

Rows carrying `domain_specific_language` under the previous wording (5, listed in
full): `lni48/GI.Band.48-15`, `lni55/GI-Proceedings.55-17`, `lni144/257`,
`lni5/08`, `lni36/GI-Proceedings.36-17`. Per the standing no-re-coding policy
these values stay as they are. Not checkable from the coded data are gate
rejections that might have gone the other way under the new clause — the gate row
does not record *why* a paper was rejected.

**Synonym whitelist filled (boundary shift, no key touched).**
`domain_specific_language` had `examples: []`, i.e. an empty synonym whitelist
despite five coded uses. Added: `data_exchange_language`, `application_schema`,
`xml_exchange_format`.

`src/check_schema_integrity.py` → OK. No `key` was added, renamed, removed or
re-scoped.

---

## 2026-08-04 — `conceptual_evaluation` re-anchored on the object of evaluation

Trigger: gold-coding round on `lni101/191` (Unternehmensvergleich Milchrind).
The model proposed `conceptual_evaluation` at certainty 0.8 for a paper that
reports no assessment at all — only a reachable implementation. The old wording
("die Vorstellung des Gesamtkonzeptes bei Nutzer:innen oder Expert:innen und die
Software wird basierend auf dem Konzept alleine bewertet") named a *form* of
evaluation, which left every feasibility demo looking like a near-match.

**Sharpening (boundary shift).** `evaluation: conceptual_evaluation` now names
its deciding criterion explicitly: what is being judged is **not the software but
the concept behind it** — process or data model, architecture/procedure design,
plausibility and viability of the approach. Measuring or observing the running
artefact belongs to `testing` / `performance_evaluation` / `benchmarking` /
`empirical_study`; judging the concept is `conceptual_evaluation`. A bare
demonstration of a working implementation without a reported assessment is
explicitly excluded and falls to `insufficient_information` — which restates, at
the level of the key, the rule the dimension-level `question` already carried.

Rows coded under the previous wording (10, listed in full):
`lni154/cd-1450`, `lni94/GI-Proceedings-94-1`, `lni318/swm2021-04`,
`lni223/43`, `lni366/Faehndrich_et_al`, `lni177/168`, `lni361/BTW2025-50`,
`lni21/GI-Proceedings.21-2`, `313/C1-1`, `316/DELFI_2021_187-192`
(the last two carry it in combination: `conceptual_evaluation;testing` and
`conceptual_evaluation;planned`). Per the standing no-re-coding policy these
values stay as they are.

**Synonym moved (boundary shift, no key touched).**
`middleware_data_processing_system` sat in the `examples:` of
`software_type: full_stack_application`. Since `examples:` acts as the synonym
whitelist, that entry pulled middleware systems towards the wrong key while
`middleware_service` exists as its own category. It now sits in the `examples:`
of `middleware_service`. Rows coded while the synonym was mis-filed:
20 with `full_stack_application`, 16 with `middleware_service` — the overlap
(`lni1/12`, `lni154/cd-1450`, `lni101/191`, `lni36/GI-Proceedings.36-17`) carries
both and is unaffected either way.

**Data fix, not a schema change.** `lni101/191` had been written with an empty
`evaluation` cell, against the dimension-level rule that "no evaluation reported"
is coded as `insufficient_information` (8 rows already followed it). Corrected in
`goldstandard/coding_alice.csv`; no empty `evaluation` cells remain.

`src/check_schema_integrity.py` → OK (5 dimensions, no duplicate keys). No `key`
was added, renamed, removed or re-scoped.

---

## 2026-07-31 — external review pass on the category system

Trigger: written review of the category system (1:1 exportability as an SSOT;
`research_position` naming; heterogeneity of `datenerhebung`; missing enumeration
for `formal_verification`; the `research_infrastructure_support` /
`research_infrastructure_management` apparent contradiction; `product_result` vs
`proof_of_concept_product` as a possible TRL axis; `software_type` mixing
delivery form with architecture archetypes; DSL as meta-tool).

**Structural invariant of the whole pass — verified mechanically against
`HEAD`:** no `key` was renamed, added, removed or re-scoped; the dimension keys
are byte-identical; the gate definition is unchanged. Every coded value therefore
still resolves. Checks run after the pass:

- `src/check_schema_integrity.py` → OK (5 dimensions, no duplicate keys)
- key-set diff of `active`/`rejected`/`candidates` per dimension vs.
  `git show HEAD:prompts/category_schema.yaml` → 0 differences
- prompt render (`categories.render_categories_block()` /
  `render_category_guidance_block()`) → succeeds; the new `archetype:` and
  `reporting:` metadata do **not** appear in the prompt

### A. Sharpenings that may partially invalidate existing codings

These shift a boundary, not just the wording. Rows below were coded before the
sharpening and are **not** re-coded.

| Category | Sharpening | Coded rows decided under the old wording |
|---|---|---|
| `research_position: formal_verification` | Was a bare one-liner. Now names the instrument classes (Theorembeweiser, Beweisassistenten, Model Checker, SMT-/SAT-Solver, Spezifikations- und Verifikationswerkzeuge, Programmanalyse-Software) and draws the boundary against `testen_qualitaetssicherung` (dynamic testing) and the `evaluation` dimension. | 5: `lni279/B1-65` (alice), `lni360/B8-2` (alice, bob), `lni48/GI.Band.48-15` (alice), `lni5/08` (alice) |
| `research_position: research_infrastructure_support` | Now explicit: **building** infrastructure software counts; **operating** existing infrastructure does not (that case fails the gate). | 2: `lni225/97` (bob), `lni318/swm2021-04` (bob) |
| `research_position: product_result` / `proof_of_concept_product` | The deciding criterion is now stated as the **unit of contribution**, explicitly **not** maturity/TRL: an unfinished lab-only system build is `product_result` if the system is the contribution; a system in production stays `proof_of_concept_product` if the contribution is a single new algorithm. Maturity is declared a different axis that is *not* coded. `proof_of_concept_product` now precedes `product_result` and both are de-nested (the nested definition was the "smell" the review flagged). | 36 + 51 = 87 rows (the two largest `research_position` values) |
| `software_type: domain_specific_language` | Now applies when the **language and its infrastructure are the artifact** (grammar/metamodel, parser, compiler/generator, editor and tooling — language workbench). A DSL used merely as an interface *inside* a larger system is coded as that system's type. | 7: `lni144/257` (alice), `lni176/91` (bob), `lni36/GI-Proceedings.36-17` (alice), `lni48/GI.Band.48-15` (alice, bob), `lni5/08` (alice), `lni55/GI-Proceedings.55-17` (alice) |
| `evaluation: testing` | The description ended mid-sentence and was completed; `performance_evaluation` and `benchmarking` are now declared the more specific cases to prefer. | 18 |
| `evaluation: alternatives_comparison` | **Defect fix.** The entry was `active` with an empty `description:` and was therefore *silently dropped from the model prompt* — the model could never propose it, although it already occurred in the coded data. Description filled from its single coded use. | 1: `lni71/GI-Proceedings.71-13` (alice). Affects the model side much more than the human side: no model run before 2026-07-31 could emit this category. |

### B. Clarifications without a boundary shift

No coding decided under the old wording changes meaning; listed for completeness.

- `research_position` — key **frozen** (it is the literal `dimension` value in
  every coding row and in the model checkpoints). Only `label` and `question`
  were reframed to *Zweck im Forschungsprozess (research purpose)*, with the
  explicit note that the **purpose** is asked, not the position in time: a data
  analysis can sit exploratively at the start or evaluatively at the end of a
  study and is `datenanalyse` in both cases.
- `datenerhebung` — enumerated (sensor systems, crawlers/scrapers, logging,
  survey/measurement instruments) with the note that this set is *deliberately*
  technically heterogeneous, because the dimension asks for the purpose; the
  build form is captured in `software_type`.
- `simulation_modellierung` (typo `Phäonoment` → `Phänomen`, discrete-event
  simulation added), `human_facing_intervention`, `visualisierung_dissemination`
  — definitional rewrites with exemplars.
- `software_type`: `numerical_mathematical`, `embedded_hardware`,
  `plugin_extension`, `vr_application` — bare one-liners replaced by definitions
  with exemplars.
- `techstack`: `linden_scripting_language`, `scratch_programming_environment`,
  `alloy_language` — pasted model rationales replaced by clean definitions
  (`alloy_language` notes its overlap with `formal_specification_languages`).
  None of the three occurs as a `final_category` in the coded data.
- rejected `research_infrastructure_management` — the rejection reason now states
  why this is *not* a contradiction with the active
  `research_infrastructure_support`: management = operating existing
  infrastructure (fails the gate); support = infrastructure software actually
  built.

### C. Additions that are non-computational by construction

Read by nothing in `src/`; they cannot invalidate a coding.

- `archetype:` on every active `software_type` entry
  (`transformation` | `embedded` | `interactive` | `delivery_form`).
- Top-level `reporting.software_type_archetypes` block: the three architecture
  archetypes (Datentransformationspipeline / Eingebettetes System / Interaktives
  System), the rule for deriving an archetype for the delivery-form keys
  (`library_package`, `plugin_extension`) from the paper's `research_position`,
  and a legacy mapping for `conceptual` / `test_automation_framework`.

  Rationale: the review is right that `software_type` mixes two axes. Splitting
  the dimension would mean re-coding, which the policy forbids. The archetype is
  therefore a **derived** reporting quantity, not a coded one — the derivation
  rule is stated in the paper and the `unresolved` share is reported rather than
  silently assigned. Of 146 `software_type` codings, 37 carry
  `archetype: delivery_form` (`library_package` 23, `plugin_extension` 14) and
  thus need the derivation — which is why the residual has to be reported
  openly instead of being folded into one of the three archetypes.

### D. Deliberately *not* done

- **Widening `research_infrastructure_support` to cover ELN / research data
  management.** The review raised it; the user decided against it on
  2026-07-31 — even though it is cheap — because it would change the extension
  of a category that is already coded, and no re-coding happens before the
  deadline.

### E. Known pre-existing gaps (not caused by this pass, not fixed here)

- Coded values that are legacy/post-rejection: `research_position: testing` (1),
  `software_type: conceptual` (3), `software_type: test_automation_framework`
  (1), `techstack: conceptual` (3). They resolve against the `rejected` list, so
  nothing breaks; they simply are not offered any more.
- `techstack: php` (1 row) occurs in the coded data but is in neither the active
  nor the rejected list.
- Open, undecided: whether `alloy_language` should be deprecated in favour of
  `formal_specification_languages`.
