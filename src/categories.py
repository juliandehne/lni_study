"""
categories.py

Single source of truth for the RSE typology used in the LNI study.

This module defines:
  - RSE_DEFINITION : the working definition of research software (RSE),
                     adapted from the DeLFI / rse-elearning-evaluation prompt
                     (`experiments/experiments/prompt_templates/prompt_template_1.md`).
  - TYPOLOGY       : the typology dimensions ("category of interests") with their
                     seed subcategories ("subcategories as examples", notes step 4).

Both the LLM annotation prompt builder (`annotate_lni.py`) and the interactive
goldstandard scripts import from here so that the categories never drift between
machine annotation and human coding.

The typology mirrors the "Typology interests" section of
`publications/pub_rse_classification/notes.md`:

  1) Position in the research process
  2) Methodology
  3) Type of software
  4) Typical techstacks / programming languages

Subcategories are SEED examples only. The whole point of the bootstrap phase
(notes steps 4-7) is for the models to flag papers that do not fit and to
*suggest new subcategories*, which are then consolidated into the goldstandard.
"""

# ---------------------------------------------------------------------------
# Working definition of research software (RSE gate, notes step 2 / step 6)
# ---------------------------------------------------------------------------
# Reused/adapted from the DeLFI prompt_template_1 definition of
# "Forschungssoftware". The typology is only annotated when this gate == 1.
RSE_DEFINITION = (
    "Forschungssoftware (research software) umfasst Quellcode-Dateien, Algorithmen, "
    "Skripte, rechnergestützte Arbeitsabläufe (Workflows), Bibliotheken und ausführbare "
    "Programme, die zu einem Forschungszweck erstellt, erweitert oder maßgeblich "
    "angepasst wurden. Die bloße Anwendung allgemein verfügbarer Standardsoftware "
    "(z.B. ein kommerzielles Lernmanagementsystem, ein Tabellenkalkulationsprogramm) "
    "ohne eigene Entwicklungsleistung gilt NICHT als Forschungssoftware."
)

# ---------------------------------------------------------------------------
# Typology dimensions ("category of interests")
# ---------------------------------------------------------------------------
# Each dimension has:
#   key        : stable English snake_case identifier (JSON key)
#   label      : human-readable German label
#   question   : the annotation question shown to the coder / model
#   multi      : whether multiple subcategories may apply (techstack: yes)
#   examples   : dict of seed subcategory_key -> German description (with EN gloss)
TYPOLOGY = {
    "research_position": {
        "label": "Position im Forschungsprozess",
        "question": (
            "An welcher Stelle des Forschungsprozesses wird die Forschungssoftware "
            "eingesetzt? Wozu dient sie primär?"
        ),
        "multi": False,
        "examples": {
            "datenerhebung": "Datenerhebung / data acquisition (z.B. Sensorik, Crawler, Logging, Erhebungsinstrumente).",
            "datenanalyse": "Datenanalyse / data analysis (z.B. Statistik, Auswertung, Machine-Learning-Pipelines).",
            "simulation_modellierung": "Simulation oder Modellierung / simulation or modelling (z.B. numerische Modelle, Agentenmodelle).",
            "human_facing_intervention": "Mensch-zugewandte Intervention / human-facing artifact (z.B. ein System, mit dem Versuchspersonen interagieren).",
            "visualisierung_dissemination": "Visualisierung oder Dissemination / visualization or dissemination (z.B. Dashboards, interaktive Abbildungen).",
            "infrastruktur_tooling": "Infrastruktur oder Tooling / infrastructure or tooling (z.B. Frameworks, Build-/Workflow-Werkzeuge für andere Forschende).",
        },
    },
    "methodology": {
        "label": "Methodik der Softwareentwicklung",
        "question": (
            "Welche Methodik liegt der Entwicklung der Forschungssoftware zugrunde?"
        ),
        "multi": False,
        "examples": {
            "design_based": "Design-based / Design-Science: das Artefakt selbst ist der Forschungsbeitrag, iterative Gestaltung und Evaluation.",
            "classical_se": "Klassisches Software Engineering: Anforderungsanalyse, Architektur, Test (plangetrieben).",
            "agile": "Agile/iterative Entwicklung (z.B. Scrum, prototypengetrieben).",
            "data_science_pipeline": "Data-Science-/ML-Pipeline: Daten -> Modell -> Evaluation als zentraler Workflow.",
            "ad_hoc_scripting": "Ad-hoc-Skripting: pragmatische Einzweck-Skripte ohne expliziten Entwicklungsprozess.",
            "formal_methods": "Formale Methoden: Spezifikation, Verifikation, beweisgestützte Entwicklung.",
        },
    },
    "software_type": {
        "label": "Art der Software",
        "question": "Um welche Art von Software handelt es sich technisch?",
        "multi": False,
        "examples": {
            "script": "Skript / script (kleiner, oft einzelner Ausführungsfaden).",
            "library_package": "Bibliothek oder Paket / library or package (zur Wiederverwendung durch andere).",
            "full_stack_application": "Full-Stack-Anwendung / full-stack application (Frontend + Backend, häufig webbasiert).",
            "numerical_mathematical": "Numerisch/mathematisch fokussierte Software (z.B. Solver, Berechnungskerne).",
            "embedded_hardware": "Embedded / hardwarenahe Software (z.B. Mikrocontroller, Robotik).",
            "web_service_api": "Web-Service oder API (serverseitige Schnittstelle ohne eigenes UI).",
            "plugin_extension": "Plugin oder Erweiterung eines bestehenden Systems (z.B. Moodle-Plugin).",
            "notebook": "Notebook-basierte Analyse (z.B. Jupyter, R Markdown).",
        },
    },
    "techstack": {
        "label": "Techstack / Programmiersprachen",
        "question": (
            "Welche Programmiersprachen bzw. Technologien werden verwendet? "
            "Mehrfachnennung möglich."
        ),
        "multi": True,
        "examples": {
            "python": "Python.",
            "java_jvm": "Java oder andere JVM-Sprachen (Kotlin, Scala).",
            "javascript_web": "JavaScript/TypeScript und Web-Frontend (HTML/CSS, React, etc.).",
            "c_cpp": "C oder C++.",
            "csharp_dotnet": "C# / .NET.",
            "r_lang": "R.",
            "matlab": "MATLAB.",
            "sql_db": "SQL / Datenbanken.",
            "other_unspecified": "Andere oder nicht spezifizierte Technologie.",
        },
    },
}

# Convenience: the dimension keys in canonical order.
DIMENSIONS = list(TYPOLOGY.keys())

# ---------------------------------------------------------------------------
# Curated subcategory white/blacklist (notes step 7b — narrowing)
# ---------------------------------------------------------------------------
# Produced by `src/narrow_categories.py` from a 50-paper stratified sample: a
# human accepts (whitelist) or declines (blacklist) each candidate subcategory
# and writes an explanation. The result is consumed in two places:
#   - injected into the annotation prompt as {category_guidance_block}, and
#   - shown to the human coders in build_goldstandard.py.
# Until the narrowing step has been run the file is absent and all helpers below
# degrade to no-ops, so the rest of the pipeline is unchanged.
import json  # noqa: E402
from pathlib import Path  # noqa: E402

WHITELIST_PATH = Path(__file__).resolve().parent.parent / "prompts" / "category_whitelist.json"


def load_category_whitelist() -> dict | None:
    """Load the curated white/blacklist JSON, or None if the narrowing step
    has not produced it yet."""
    if WHITELIST_PATH.exists():
        try:
            return json.loads(WHITELIST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def dimension_guidance(dim: str) -> dict[str, list[dict]]:
    """Return {'whitelist': [...], 'blacklist': [...]} for one dimension.
    Each entry is a {'key', 'explanation'} dict. Empty lists if no curation."""
    data = load_category_whitelist() or {}
    dims = data.get("dimensions", {})
    entry = dims.get(dim, {})
    return {
        "whitelist": entry.get("whitelist", []) or [],
        "blacklist": entry.get("blacklist", []) or [],
    }


def render_category_guidance_block() -> str:
    """Render the curated white/blacklist into a markdown block for injection
    into the annotation prompt (placeholder: {category_guidance_block}).

    Returns "" when no curation file exists, so the prompt is unchanged until
    `narrow_categories.py` has been run."""
    data = load_category_whitelist()
    if not data or not data.get("dimensions"):
        return ""

    lines = [
        "**Kuratierte Subkategorien-Leitlinie (aus einer Stichprobe konsolidiert):**",
        "",
        "Die folgenden Leitlinien wurden von menschlichen Kodierenden festgelegt. "
        "Bevorzuge bestätigte (Whitelist-)Subkategorien. Verwende die abgelehnten "
        "(Blacklist-)Subkategorien NICHT und schlage sie auch nicht als "
        "`new_suggestion` vor; nutze stattdessen die angegebene Alternative.",
        "",
    ]
    for i, (key, dim) in enumerate(TYPOLOGY.items(), start=1):
        g = dimension_guidance(key)
        if not g["whitelist"] and not g["blacklist"]:
            continue
        lines.append(f"*{i}) {dim['label']}* (`{key}`)")
        if g["whitelist"]:
            lines.append("  Bestätigt (Whitelist):")
            for e in g["whitelist"]:
                expl = f" — {e['explanation']}" if e.get("explanation") else ""
                lines.append(f"  - `{e['key']}`{expl}")
        if g["blacklist"]:
            lines.append("  Abgelehnt (Blacklist) — NICHT verwenden:")
            for e in g["blacklist"]:
                expl = f" — {e['explanation']}" if e.get("explanation") else ""
                lines.append(f"  - `{e['key']}`{expl}")
        lines.append("")
    rendered = "\n".join(lines).strip()
    return rendered


def render_categories_block() -> str:
    """
    Render the TYPOLOGY into a markdown block for injection into the prompt
    template (placeholder: {categories_block}).

    Each dimension is rendered with its question and its seed subcategories so
    the model can either pick an existing subcategory or propose a new one.
    """
    lines: list[str] = []
    for i, (key, dim) in enumerate(TYPOLOGY.items(), start=1):
        multi = " (Mehrfachnennung möglich)" if dim["multi"] else ""
        lines.append(f"**{i}) {dim['label']}** (`{key}`){multi}")
        lines.append("")
        lines.append(dim["question"])
        lines.append("")
        lines.append("Beispiel-Subkategorien (Seed):")
        for sub_key, desc in dim["examples"].items():
            lines.append(f"- `{sub_key}`: {desc}")
        lines.append("")
    return "\n".join(lines).strip()


if __name__ == "__main__":
    # Quick manual check: print the rendered block.
    print(render_categories_block())