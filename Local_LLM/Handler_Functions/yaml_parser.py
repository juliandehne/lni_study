import json
from pathlib import Path

import yaml


REQUIRED_ROW_FIELDS = ("title", "abstract", "text", "references")


def clean_text(value):
    """Convert multiline YAML text into a clean single-line string."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def load_schema(ground_truth_path):
    """Load and minimally validate a category-schema YAML file."""
    with Path(ground_truth_path).open("r", encoding="utf-8") as file:
        schema = yaml.safe_load(file)

    if not isinstance(schema, dict):
        raise ValueError("The ground-truth file must contain a YAML mapping.")
    if not isinstance(schema.get("gate"), dict):
        raise ValueError("No valid top-level 'gate' mapping was found.")
    if not isinstance(schema.get("dimensions"), dict) or not schema["dimensions"]:
        raise ValueError("No non-empty top-level 'dimensions' mapping was found.")

    return schema


def iter_selectable_categories(dimension):
    """Yield active, described, non-deprecated categories."""
    for category in dimension.get("active", []):
        key = category.get("key")
        description = clean_text(category.get("description"))

        if not key or not description or category.get("deprecated", False):
            continue

        yield category, key, description


def build_rse_definition(schema):
    """Extract the research-software definition."""
    definition = schema["gate"].get("definition_de")

    if not definition:
        raise ValueError("No 'gate.definition_de' was found.")

    return clean_text(definition)


def build_categories_block(schema):
    """Generate all selectable dimensions and categories."""
    lines = []

    for dimension_key, dimension in schema["dimensions"].items():
        label = dimension.get("label", dimension_key)
        question = clean_text(dimension.get("question"))
        is_multi = bool(dimension.get("multi", False))

        lines.append(f"### {label}")
        lines.append(f"JSON-Feld: `{dimension_key}`")
        lines.append("Mehrfachauswahl: ja" if is_multi else "Mehrfachauswahl: nein")

        if question:
            lines.append(f"Fragestellung: {question}")

        lines.append("Erlaubte Subkategorien:")
        included_categories = 0

        for category, key, description in iter_selectable_categories(dimension):
            category_line = f"- `{key}`: {description}"
            examples = category.get("examples", [])

            if examples:
                formatted_examples = ", ".join(
                    f"`{example}`" for example in examples
                )
                category_line += f" Auch: {formatted_examples}."

            lines.append(category_line)
            included_categories += 1

        if included_categories == 0:
            raise ValueError(
                f"Dimension '{dimension_key}' has no selectable active category."
            )

        lines.append("")

    return "\n".join(lines).strip()


def build_category_guidance_block(schema):
    """Generate general rules and rejected-category guidance."""
    lines = [
        "### Allgemeine Kategorieregeln",
        "- Verwende ausschließlich aktive, nicht als `deprecated` markierte "
        "Subkategorien.",
        "- Verwende keine Einträge aus `rejected` oder `candidates`.",
        "- Aktive Kategorien mit leerer Beschreibung dürfen nicht verwendet "
        "werden.",
        "- Bei `multi: false` muss genau ein Wert im Feld `category` stehen.",
        "- Bei `multi: true` müssen alle belegten Werte im Feld `categories` "
        "als JSON-Liste stehen.",
        "- `insufficient_information` darf nicht mit einer inhaltlichen "
        "Subkategorie kombiniert werden.",
        "- Kategorien dürfen aufgrund ausdrücklicher Belege oder aufgrund einer "
        "in ihrer Definition ausdrücklich zugelassenen eindeutigen Ableitung "
        "vergeben werden.",
        ""
    ]
    dimension_keys = set(schema["dimensions"])

    for dimension_key, dimension in schema["dimensions"].items():
        rejected_categories = dimension.get("rejected", [])

        if not rejected_categories:
            continue

        label = dimension.get("label", dimension_key)
        lines.append(f"### Nicht verwenden: {label}")

        for category in rejected_categories:
            key = category.get("key")
            if not key:
                continue

            reason = clean_text(category.get("reason"))
            move_to = category.get("move_to")
            rule = f"- `{key}` darf nicht verwendet werden."

            if reason:
                rule += f" Grund: {reason}"

            if move_to in dimension_keys:
                rule += f" Stattdessen in der Dimension `{move_to}` kodieren."
            elif move_to:
                rule += (
                    f" Stattdessen gegebenenfalls die Subkategorie `{move_to}` "
                    "verwenden."
                )

            lines.append(rule)

        lines.append("")

    return "\n".join(lines).strip()


def build_answer_json_block(schema):
    """Build a valid, dimension-dynamic JSON response example."""
    typology = {}

    for dimension_key, dimension in schema["dimensions"].items():
        selectable_keys = [
            key
            for _, key, _ in iter_selectable_categories(dimension)
        ]
        if not selectable_keys:
            raise ValueError(
                f"Dimension '{dimension_key}' has no selectable active category."
            )

        selection_placeholder = "<aktiver-subkategorie-key>"
        entry = {
            "categories" if dimension.get("multi", False) else "category": (
                [selection_placeholder]
                if dimension.get("multi", False)
                else selection_placeholder
            ),
            "certainty": 0.0,
            "new_suggestion": "",
            "explanation": "kurze Erklärung"
        }
        typology[dimension_key] = entry

    example = {
        "label_research_software": 1,
        "label_research_software_certainty": 0.0,
        "label_research_software_explanation": "kurze Erklärung",
        "typology": typology
    }

    return json.dumps(example, ensure_ascii=False, indent=2)


def build_prompt_context(ground_truth_path):
    """Build every named placeholder required by the priming template."""
    schema = load_schema(ground_truth_path)
    return {
        "rse_definition": build_rse_definition(schema),
        "categories_block": build_categories_block(schema),
        "category_guidance_block": build_category_guidance_block(schema),
        "answer_json_block": build_answer_json_block(schema)
    }


def build_prompt_blocks(ground_truth_path):
    """Return the four prompt blocks in template order."""
    context = build_prompt_context(ground_truth_path)
    return (
        context["rse_definition"],
        context["categories_block"],
        context["category_guidance_block"],
        context["answer_json_block"]
    )


def validate_row(row):
    """Validate and normalize the publication fields used by the template."""
    if not isinstance(row, dict):
        raise TypeError("row must be a dictionary.")

    missing = [field for field in REQUIRED_ROW_FIELDS if field not in row]
    if missing:
        raise KeyError(f"row is missing required fields: {', '.join(missing)}")

    return {
        field: "" if row[field] is None else str(row[field])
        for field in REQUIRED_ROW_FIELDS
    }


def render_prompt(priming_path, ground_truth_path, row):
    """Render the supplied priming template end to end."""
    template = Path(priming_path).read_text(encoding="utf-8")
    context = build_prompt_context(ground_truth_path)
    normalized_row = validate_row(row)

    try:
        return template.format(row=normalized_row, **context)
    except KeyError as error:
        raise KeyError(
            f"Unknown placeholder in priming template: {error.args[0]}"
        ) from error
