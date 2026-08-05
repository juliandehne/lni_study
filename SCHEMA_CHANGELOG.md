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

## 2026-08-05 — `numerical_mathematical` covers combinatorial search and matching

Trigger: `lni115/78` (Kurbatova, Mančinska & Vīksna, *Protein structure
comparison based on fold evolution*). The artefact's core is a backtracking
search for the largest common subgraph of two 3D graphs — a discrete
combinatorial solver, but the old description enumerated only continuous and
logical cores (Solver, numerische Integratoren, lineare Algebra, Optimierungs-
und Approximationsverfahren, FEM-/Simulationskerne, SAT-/SMT-Solver,
Theorembeweiser). Graph isomorphism and matching kernels therefore had no
obvious home, and the `analysis_pipeline` boundary had to be decided from first
principles.

The description now names combinatorial search and matching (Graph-Isomorphie,
Largest Common Subgraph, Backtracking-Suche) as covered, with the discriminating
clause: the key applies when the computational kernel itself is the
contribution; when the kernel is merely one step in a chain that reads data in
and writes results out, `analysis_pipeline` applies. This shifts a boundary —
some artefacts previously falling to `analysis_pipeline` by default now have a
positive reason to be `numerical_mathematical`, and vice versa.

Rows coded under the earlier wording that carry `numerical_mathematical` (10):

`lni295/paper11_03`, `lni136/189`, `lni220/1821`,
`lni329/23-BIOSIG_2022_paper_4`, `lni48/GI.Band.48-15`, `lni165/286`,
`lni71/GI-Proceedings.71-13`, `lni108/3`, `lni109/75`, `lni110/100`.

Rows on the other side of the boundary, carrying `analysis_pipeline` (7):

`lni329/30-BIOSIG_2022_paper_20`, `lni306/BIOSIG_2020_paper_4_update`,
`lni110/247`, `lni115/78`, `lni314/B1-9`, `lni331/B2-4`, `lni326/trustai_03`.

`lni115/78` was decided under the new wording and stays `analysis_pipeline`: the
LCS kernel is one stage of the chain PDB → SSE prediction → 3D graph
construction → database → matching → alignment and scoring (Fig. 2), and the
deliverable is that run's output.

---

## 2026-08-04 — `software_lifecycle`: the phase a tool SUPPORTS is not its own

Trigger: `lni113/147` (Lohmann & Ziegler, *Partizipationsformen … bei der
verteilten Anforderungserhebung*, SoftWiki). The paper's subject matter *is*
requirements elicitation, and the model duly proposed `anforderungen` — but
justified it with "Erhebung, semantische Anreicherung, SWORE-Ontologie", i.e.
with what the tool is *for*, not with any requirements analysis for the tool
itself. The key survived on other evidence (§2 derives which interface reaches
which stakeholder role, which is an analysis of SoftWiki's own requirements),
but the reasoning that produced it was wrong, and the dimension question did
nothing to prevent it.

The same confusion was already ruled out on 2026-08-04 at *key* level for
`testen_qualitaetssicherung` ("a testing tool's function is not the phase"). It
recurs for every tool whose domain is the software process itself — RE tools,
CASE and modelling tools, test tools, deployment and operations tooling — so it
belongs in the dimension question, where it applies to all six keys at once.

Old wording of the `software_lifecycle` question, in full:

> Welche Phase(n) des Software-Lebenszyklus behandelt das Paper im Bezug auf die
> Forschungssoftware? Mehrfachnennung möglich (die Phasen bauen im Idealfall
> aufeinander auf).

Added after it:

> Kodiert wird ausschließlich der Lebenszyklus der beschriebenen Software SELBST
> — also das, was das Paper über ihre eigene Entwicklung berichtet. Die Phase,
> die das Artefakt inhaltlich UNTERSTÜTZT, ist nicht seine eigene: ein Werkzeug
> für Anforderungserhebung trägt deshalb nicht `anforderungen`, ein Test- oder
> Analysewerkzeug nicht `testen_qualitaetssicherung`, ein Modellierungs- oder
> CASE-Werkzeug nicht `entwurf`, ein Deployment- oder Betriebswerkzeug nicht
> `deployment_betrieb`. Maßgeblich ist allein, ob das Paper die jeweilige Phase
> für die eigene Software berichtet.

This is a **clarification, not a re-scoping**: the old wording already said "im
Bezug auf die Forschungssoftware", and every value coded so far was decided on
that reading (`lni110/100` and `lni110/247` explicitly withheld
`testen_qualitaetssicherung` on exactly this ground). No value is expected to
flip.

Like the `techstack` entry below, this one **cannot enumerate its affected
rows**: a row stores `anforderungen`, not the reason it was assigned, so nothing
in the CSV separates "the paper analysed its own requirements" from "the tool
supports requirements engineering". The upper bound is every substantive
`software_lifecycle` row — alice 80, bob 37, lukka 14, 131 in total — of which
only tools whose domain is the software process itself could be affected at all.

---

## 2026-08-04 — `techstack`: what a tool merely PROCESSES is not its stack

Trigger: `lni110/247` (Staiger, *Statische Analyse von graphischen Oberflächen*).
The paper presents a static analysis that reads **C/C++** source built against
**GTK/Qt** and never once says what the analysis itself is written in. The model
proposed `c_cpp` at certainty **1.0** — reading the analysed language off the
paper as if it were the implementation language.

**The defect.** The dimension question already forbade two ways of guessing
(inferring from the method/domain, and treating algorithm names as technologies),
but it said nothing about the commonest failure in this corpus: a tool whose
*input* is a language. Nothing in the old wording was violated by `c_cpp` here —
C and C++ are literally named, and GTK is an explicitly named library. The
warning "Fehlt jeder solche konkrete Anhaltspunkt, wähle
`insufficient_information` statt zu raten" does not bite, because concrete
evidence *is* present; it just belongs to the analysed system, not to the
artefact.

**Old wording (last sentence of the question):**

> Aus der Methode oder der Fachdomäne auf die vermutlich verwendete Sprache zu
> schließen ist unzulässig — ein Paper, das ausschließlich Verfahren benennt, ist
> `insufficient_information`.

**Added after it:** only the stack the software is itself built with or runs on
is coded; languages, formats and platforms the artefact merely *processes* are
not its stack — naming the target language of an analysis, migration or test
tool, the output language of a generator, the language studied in a study, and
the technology (with libraries) of the analysed foreign systems. A paper that
names only such target languages and is silent on its own implementation is
`insufficient_information`. The converse case is explicitly preserved: a language
the artefact is embedded in, or whose runtime it is built against, does belong to
the stack.

**Rows coded under the old wording — NOT enumerable.** This is the first entry in
this file that cannot list its affected ids, and the reason is structural: a row
records the value `c_cpp`, not the coder's reason for it, so nothing in the data
distinguishes "implemented in C++" from "analyses C++". The upper bound is every
substantive `techstack` row in the gold standard at the time of the edit — alice
52, bob 31, lukka 11 (of 78 / 37 / 13 total; the remainder are already
`insufficient_information`). The realistic subset is much smaller: papers whose
artefact is an analysis, migration, generation or test tool for a named language.
Anyone re-deriving the affected set must do it from the papers, not from the CSV.
Under the standing no-recoding policy nothing is changed retroactively.

---

## 2026-08-04 — `middleware_service`: the artefact must BE the mediating layer

Trigger: `lni110/100` (Dästner/Kausch/Opitz, *An Object Oriented Approach for
Data Fusion*). The paper delivers a C++ fusion kernel plus a GUI development
suite, and states plainly that the middleware is **not** the artefact: "A data
fusion system is always integrated into a middleware specific to the
application… The interfaces are separated from the pure data fusion kernel
through the declaration of an abstract interface class." The model nevertheless
proposed `middleware_service` at certainty 0.95, on the strength of the word
appearing in §2 and Figure 1.

That is a defect of the old wording, not a one-off. It read in full:

> Middleware / dienstorientierte Software: verbindende Schicht zwischen Systemen
> — Web-Services/APIs, Proxy-Server, Workflow-Management-Systeme sowie
> Integrations- und Vermittlungsdienste.

A list of examples with no lower bound. Nothing in it distinguished *being* a
mediating layer from *being embedded in* one or *describing* one, so any paper
whose architecture section mentions integration infrastructure matched. The key
had been queued for this since 2026-08-03 and was assigned five more times on
2026-08-04 before this entry.

The sharpened wording adds three clauses: the artefact must take input from at
least two sides and translate/route/orchestrate between them; embedding into an
externally provided or application-specific middleware, shipping an interface to
such a layer, or merely describing the surrounding infrastructure does not
qualify (code the type the artefact itself has); and the boundary against
`library_package` runs along delivery form — called through an API and built
into someone else's application is `library_package`, running as a standalone
service between systems is `middleware_service`.

Description-only change; no key added, renamed or removed. Per the no-recoding
policy the rows below stay as they are. **Rows coded under the old wording**
(`software_type` containing `middleware_service`):

- alice (20): `lni1/12`, `lni154/cd-1450`, `lni366/Kadi_et_al`,
  `lni51/GI-Proceedings.51-108`, `lni55/GI-Proceedings.55-26`, `lni223/43`,
  `lni103/172`, `lni331/B1-7`, `lni361/BTW2025-50`,
  `lni55/GI-Proceedings.55-17`, `316/DELFI_2021_187-192`, `lni101/191`,
  `lni103/542`, `lni104/103`, `lni106/297`, `lni109/202`,
  `lni17/GI-Proceedings.17-22`, `lni50/GI-Proceedings.50-20`,
  `lni36/GI-Proceedings.36-17`, `lni133/110`
- bob (10): `lni1/12`, `lni154/cd-1450`, `lni51/GI-Proceedings.51-108`,
  `lni55/GI-Proceedings.55-26`, `lni223/43`, `lni293/proceedings-02`,
  `lni103/172`, `lni93/GI-Proceedings-93-4`, `lni331/B1-7`, `lni361/BTW2025-50`
- lukka (6): `lni1/12`, `lni154/cd-1450`, `lni366/Kadi_et_al`, `lni373/B2-1`,
  `lni51/GI-Proceedings.51-108`, `lni55/GI-Proceedings.55-26`

The count is high enough that the reported inter-coder agreement on
`software_type` should be read with this boundary shift in mind: rows before and
after this date were decided under different lower bounds.

---

## 2026-08-04 — `usability_study` requires an evaluation laid out as a collection

Trigger: `lni109/570` (Cermak-Sassenrath, *MR Auto Racing — Mixed Reality Game
for Public Installation*), whose §5 "Experiences" reports that "the players
enjoyed playing the game, and the competition was tough", that not all players
were familiar with joystick control, and that the top-down perspective "seems to
work well with most of them" — but names no method, no sample and no instrument,
and the players are the author's own lab colleagues (Acknowledgments: "Thanks to
everybody at the artecLab for playing the game"). The paper itself defers its
evaluation to future work (§6: "Further development and evaluation will focus on
this relationship").

The model proposed `testing;usability_study` at 0.85. The old description named
only methodical instruments ("Usability-Tests, SUS-/Fragebögen, Think-Aloud") and
never said whether a method-less experience report reaches the key. The gap was
opened by the same-day re-anchoring of `conceptual_evaluation` further down this
file, which moved observed *use* of a running artefact out of that key and toward
`testing`/`empirical_study` — leaving the anecdotal play report with no stated
home.

The description now requires an evaluation laid out as a collection — recognisable
method, named participants, reported result — and states that an anecdotal report
of use ("die Nutzer:innen hatten Spaß", feedback from one's own colleagues,
incidental observations while demonstrating) does not reach the key even when it
contains remarks on operation; such reports code `testing` where the technical
function of the artefact is established, otherwise `insufficient_information`.

Rows coded under the earlier wording that carry `usability_study` (9):

alice `lni373/B2-1`, `312/proceedings-04`; bob `lni332/paper52`,
`lni154/cd-1450`, `lni176/91`, `lni318/swm2021-04`, `312/proceedings-04`;
lukka `lni154/cd-1450`, `lni308/313 DELFI2020_paper_53`.

`lni109/570` is the first row under the new wording: `testing` alone.

---

## 2026-08-04 — `planned`: productive operation is not an announced evaluation

Trigger: `lni109/57` (Dahl & Derigs, *Ein Decision Support System zur
kooperativen Tourenplanung in Verbünden unabhängiger Transportdienstleister*),
whose §4 reports only that the DSS was implemented in 2006 and has been "seit
Anfang 2007 im Produktivbetrieb". No finding, no test, no user feedback, and no
evaluation is announced anywhere in the paper.

Taken literally, the field-deployment clause of `planned` ("ein laufender, aber
noch nicht ausgewerteter Feldeinsatz oder Nutzerbetrieb ohne berichtete Befunde
ist `planned`") would catch this — but that clause was written for a deployment
the paper frames *as* a data collection whose analysis is still outstanding, not
for a plain delivery status. Coding it as an evaluation would also book the same
sentence twice: it already carries `deployment_betrieb` in the lifecycle.

The description now restricts the field-deployment clause to papers that set the
deployment up as a collection or promise an analysis, and states that a mere
productive/regular-operation status without an announced evaluation is
`insufficient_information`.

Rows coded under the earlier wording that carry `planned` (14):

`lni1/12`, `lni366/Kadi_et_al`, `lni51/GI-Proceedings.51-108`, `lni176/91`,
`lni318/swm2021-04`, `lni216/237`, `lni366/Faehndrich_et_al`, `lni338/45`,
`316/DELFI_2021_91-96`, `lni106/337`, `lni211/215`,
`lni287/GIL_2019_Potts_155-160`, `lni225/121`, `lni369/paper-52`.

`lni109/57` is the first row under the new wording: `insufficient_information`.

---

## 2026-08-04 — `xml_xsd` covers XML-serialised exchange and description languages

Trigger: `lni109/202` (Bandara et al., *A Semantic Approach for Description and
Ranked Matching of Services in Pervasive Environments*), whose service and
request descriptions are an OWL ontology edited in Protégé. There is no
ontology/semantic-web key and adding one is barred by the no-recoding policy, so
`xml_xsd` has to carry it — as it already did for WSDL in `lni106/297`. The old
description was the bare list "XML-Technologien (XML, XSD/XML-Schema, GML)",
which never said whether XML-serialised *languages* count or only XML itself.

The description now states that XML-serialised exchange, schema and description
languages — WSDL, SOAP, OWL/RDF-XML, SVG, XSLT/XPath — count when the paper
names the concrete format, and that generic talk of "structured data", "an
exchange format" or a configuration file does not.

Rows coded under the earlier wording that carry `xml_xsd` (12):

`lni1/12`, `lni176/91`, `lni103/172`, `lni55/GI-Proceedings.55-17`,
`lni21/GI-Proceedings.21-2`, `lni101/191`, `lni101/199`, `lni104/103`,
`lni106/297`, `lni225/121`, `lni5/08`, `lni133/110`.

`lni109/202` is the first row under the new wording: `java_jvm;xml_xsd`, with
`xml_xsd` resting on the named OWL ontology alone.

---

## 2026-08-04 — `sql_db`: a named database suffices, generic persistence does not

Trigger: `lni106/337` (Pein, *Qualitätsverbesserung durch gewichtete Teilaspekte
im Image Retrieval*), whose persistence layer is described only as "Der erste
Prototyp basiert auf einer Datenbank" — no DBMS, no SQL, no driver. The old
description was the bare phrase "SQL / Datenbanken.", which left open whether a
generically named database carries the key, and, symmetrically, whether an
unspecified "Persistenzschicht" does.

The description now states the criterion explicitly: an expressly named database
(or a concrete DBMS, SQL, JDBC, ORM) suffices and no product name is required;
generic talk of "Persistenz", "Speicherung", "Datenhaltung", "Repository" or
"Datei" without a database being named does not. This is a clarification of the
practice already followed, not a widening — but it does settle a boundary that
was previously decided per paper.

Rows coded under the earlier wording that carry `sql_db` (10):

`lni214/185`, `lni318/swm2021-04`, `lni216/237`, `lni331/B1-7`, `lni144/257`,
`313/C1-1`, `lni101/191`, `lni103/542`, `lni211/215`,
`lni287/GIL_2019_Potts_155-160`.

`lni106/337` is the first row under the new wording: coded `java_jvm;sql_db` on
the strength of the expressly named database alone.

---

## 2026-08-04 — `testen_qualitaetssicherung`: a testing tool's *function* is not the phase

Trigger: `lni106/297` (Averstegge, *Kontraktbasiertes Black-Box Testen von
Webservices*), where the artefact is a validating proxy web service (VWS) whose
whole purpose is to test *other* web services. The model proposed
`testen_qualitaetssicherung` at certainty 0.98, quoting the system's own purpose
("automatisierte Ableitung, Durchführung und Auswertung von Testfällen") — and
had made the same move one paper earlier on `lni106/101` (a SysML test-case
generator). The old wording demanded "Qualitätssicherung am Artefakt selbst" and
excluded result-quality measurements, but never said that a tool *whose job is
testing* still needs QA reported on itself before the phase applies.

The description now adds: the mere FUNCTION of the software does not carry the
phase — a test tool, a test-case generator or a validating layer codes
`testen_qualitaetssicherung` only when QA on its *own* artefact is reported.

Rows coded under the earlier wording that carry `testen_qualitaetssicherung`
(24; only those whose artefact is itself a testing/QA tool could be affected):

`lni332/paper52`, `lni300/B5-01`, `lni154/cd-1450`, `lni366/Kadi_et_al`,
`lni360/B6-2`, `lni31/GI-Proceedings.31-10`, `lni214/185`, `lni373/B2-1`,
`lni55/GI-Proceedings.55-26`, `lni295/paper11_03`, `lni360/B8-2`, `lni220/1821`,
`lni329/23-BIOSIG_2022_paper_4`, `lni48/GI.Band.48-15`, `lni165/286`,
`lni279/B1-65`, `lni306/BIOSIG_2020_paper_4_update`, `lni366/Faehndrich_et_al`,
`lni331/B1-7`, `lni108/3`, `316/DELFI_2021_187-192`, `lni31/GI-Proceedings.31-8`,
`lni211/215`, `lni326/trustai_03`.

`lni106/297` is the first row under the new wording: coded
`projektdefinition;anforderungen;entwurf;implementierung` *without*
`testen_qualitaetssicherung`.

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
