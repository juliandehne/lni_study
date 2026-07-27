from pathlib import Path
import yaml


def clean_text(value):
    """Convert multiline YAML text into a clean single-line string."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def build_rse_definition(schema):
    """Extract the research-software definition."""
    definition = schema["gate"].get("definition_de")

    if not definition:
        raise ValueError("No 'gate.definition_de' was found.")

    return clean_text(definition)


def build_categories_block(schema):
    """
    Generate the selectable dimensions and active categories.
    Active categories with an empty description are excluded.
    """

    lines = []
    for dimension_key, dimension in schema["dimensions"].items():
        label = dimension.get("label", dimension_key)
        question = clean_text(dimension.get("question"))
        is_multi = bool(dimension.get("multi", False))

        lines.append(f"### {label}")
        lines.append(f"JSON-Feld: `{dimension_key}`")
        lines.append(
            "Mehrfachauswahl: ja"
            if is_multi
            else "Mehrfachauswahl: nein"
        )

        if question:
            lines.append(f"Fragestellung: {question}")

        lines.append("Erlaubte Subkategorien:")

        active_categories = dimension.get("active", [])
        included_categories = 0

        for category in active_categories:
            key = category.get("key")
            description = clean_text(category.get("description"))

            # According to the schema comments, an active category with
            # no description should not be offered to the model.
            if not key or not description:
                continue

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
            lines.append("- Keine verwendbare aktive Subkategorie vorhanden.")

        lines.append("")

    return "\n".join(lines).strip()


def build_category_guidance_block(schema):
    """
    Generate general selection rules and rejected-category guidance.
    """
    lines = [
        "### Allgemeine Kategorieregeln",
        "- Verwende ausschließlich Subkategorien aus `active`.",
        "- Verwende keine Einträge aus `rejected` oder `candidates`.",
        "- Aktive Kategorien mit leerer Beschreibung dürfen nicht verwendet werden.",
        "- Bei `multi: false` muss genau ein Wert im Feld `category` stehen.",
        "- Bei `multi: true` müssen alle belegten Werte im Feld `categories` "
        "als JSON-Liste stehen.",
        "- Kategorien dürfen nur aufgrund expliziter Belege in der Publikation "
        "vergeben werden.",
        ""
    ]

    for dimension_key, dimension in schema["dimensions"].items():
        rejected_categories = dimension.get("rejected", [])

        if not rejected_categories:
            continue

        label = dimension.get("label", dimension_key)

        lines.append(f"### Nicht verwenden: {label}")

        for category in rejected_categories:
            key = category.get("key")
            reason = clean_text(category.get("reason"))
            move_to = category.get("move_to")

            rule = f"- `{key}` darf nicht verwendet werden."

            if reason:
                rule += f" Grund: {reason}"

            if move_to:
                rule += f" Stattdessen gegebenenfalls `{move_to}` verwenden."

            lines.append(rule)

        lines.append("")

    return "\n".join(lines).strip()


def build_prompt_blocks(ground_truth_path):
    """Build all three template values from one ground-truth file."""

    with Path(ground_truth_path).open("r", encoding="utf-8") as file:
        schema = yaml.safe_load(file)

    return build_rse_definition(schema), build_categories_block(schema), build_category_guidance_block(schema)
