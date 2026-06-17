"""
categories.py

Single source of truth for the RSE typology used in the LNI study — now BACKED BY
``prompts/category_schema.yaml`` (see schema_io.py). The hardcoded TYPOLOGY dict +
``category_whitelist.json`` it used to carry are gone; this module now *derives* the
same public surface from the hand-edited YAML so the schema lives in one place and
the narrowing loop can edit it between rounds.

Public surface (unchanged, so annotate_lni.py / build_goldstandard.py /
compute_icr.py / narrow_categories.py keep importing it as before):
  - RSE_DEFINITION            : the gate definition (gate.definition_de)
  - TYPOLOGY                  : {dim: {label, question, multi, examples{key:desc}}}
                                where `examples` are the dimension's ACTIVE
                                subcategories that have a non-empty description
  - DIMENSIONS                : the dimension keys in canonical (file) order
  - dimension_guidance(dim)   : {'whitelist': [...active...], 'blacklist': [...rejected...]}
  - render_categories_block() : the {categories_block} prompt injection
  - render_category_guidance_block() : the {category_guidance_block} prompt injection

Mapping from the YAML:
  * gate.definition_de                        -> RSE_DEFINITION
  * dimensions.<dim>.{label,question,multi}   -> TYPOLOGY[dim].{label,question,multi}
  * dimensions.<dim>.active[]  (key,desc)     -> TYPOLOGY[dim].examples  (the prompt
                                                 categories) + whitelist guidance. An
                                                 active entry's optional `examples:`
                                                 list (merged-in alternate names) ->
                                                 TYPOLOGY[dim].aliases, rendered as a
                                                 "(auch: ...)" synonym hint.
  * dimensions.<dim>.rejected[] (key,reason,
        move_to)                              -> blacklist guidance ("don't use X,
                                                 use move_to instead")
  * dimensions.<dim>.candidates[]             -> IGNORED here (the merge-not-clobber
                                                 bucket the loop appends to; promoted
                                                 to active/rejected by `review`)

IMPORTANT: an ``active`` entry with an EMPTY ``description`` is dropped from the
prompt and a warning is printed. The model cannot apply a category it has no
definition for, so this turns the schema's `fill_descriptions` TODO into a hard
forcing function — fill the description before the category takes effect.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema_io  # noqa: E402

# Kept for backward-compat references; the schema YAML is the real source now.
SCHEMA_PATH = schema_io.SCHEMA_PATH
WHITELIST_PATH = Path(__file__).resolve().parent.parent / "prompts" / "category_whitelist.json"


def _as_str(v) -> str:
    return "" if v is None else str(v).strip()


def _build():
    """Load the schema once and derive RSE_DEFINITION / TYPOLOGY / guidance.

    Returns (rse_definition, typology, guidance, undescribed) where:
      typology    : {dim: {label, question, multi, examples{key:desc}}}
      guidance    : {dim: {'whitelist': [{key,explanation}], 'blacklist': [...]}}
      undescribed : {dim: [keys]} active keys skipped for want of a description
    """
    schema = schema_io.load_schema()

    rse_definition = _as_str(schema.get("gate", {}).get("definition_de"))

    typology: dict[str, dict] = {}
    guidance: dict[str, dict] = {}
    undescribed: dict[str, list] = {}

    for dim, spec in (schema.get("dimensions") or {}).items():
        spec = spec or {}
        active = spec.get("active") or []
        rejected = spec.get("rejected") or []

        examples: dict[str, str] = {}
        aliases: dict[str, list] = {}
        whitelist: list[dict] = []
        skipped: list[str] = []
        for e in active:
            key = _as_str(e.get("key"))
            if not key:
                continue
            desc = _as_str(e.get("description"))
            whitelist.append({"key": key, "explanation": desc})
            if desc:
                examples[key] = desc
                al = [_as_str(x) for x in (e.get("examples") or [])]
                al = [x for x in al if x]
                if al:
                    aliases[key] = al
            else:
                skipped.append(key)

        blacklist: list[dict] = []
        for e in rejected:
            key = _as_str(e.get("key"))
            if not key:
                continue
            reason = _as_str(e.get("reason"))
            move_to = _as_str(e.get("move_to"))
            if move_to:
                reason = (f"{reason} (stattdessen `{move_to}` verwenden)"
                          if reason else f"stattdessen `{move_to}` verwenden")
            blacklist.append({"key": key, "explanation": reason})

        typology[dim] = {
            "label": _as_str(spec.get("label")) or dim,
            "question": _as_str(spec.get("question")),
            "multi": bool(spec.get("multi", False)),
            "examples": examples,
            "aliases": aliases,
        }
        guidance[dim] = {"whitelist": whitelist, "blacklist": blacklist}
        if skipped:
            undescribed[dim] = skipped

    return rse_definition, typology, guidance, undescribed


# Eager load at import: the schema YAML is required (it is the source of truth).
RSE_DEFINITION, TYPOLOGY, _GUIDANCE, _UNDESCRIBED = _build()
DIMENSIONS = list(TYPOLOGY.keys())

if _UNDESCRIBED:
    msg = "; ".join(f"{dim}: {', '.join(keys)}" for dim, keys in _UNDESCRIBED.items())
    print(f"[categories] WARNING: active subcategories with no description are "
          f"EXCLUDED from the prompt until defined -> {msg}", file=sys.stderr)


def load_category_whitelist() -> dict | None:
    """Back-compat shim: the curated guidance now lives in the schema YAML, not
    category_whitelist.json. Returns the derived white/blacklist in the old shape."""
    return {"version": 2, "dimensions": _GUIDANCE, "source": SCHEMA_PATH.name}


def dimension_guidance(dim: str) -> dict[str, list[dict]]:
    """Return {'whitelist': [...], 'blacklist': [...]} for one dimension.
    Each entry is a {'key', 'explanation'} dict. whitelist = active subcategories,
    blacklist = rejected ones (with the reason / regrouping target)."""
    g = _GUIDANCE.get(dim, {})
    return {"whitelist": g.get("whitelist", []) or [], "blacklist": g.get("blacklist", []) or []}


def render_categories_block() -> str:
    """Render the ACTIVE typology into the {categories_block} prompt injection.

    Lists, per dimension, the curated active subcategories with their (human)
    definitions. Undescribed active keys are omitted (see module docstring). The
    model may still propose a `new_suggestion` outside this list.
    """
    lines: list[str] = []
    for i, (key, dim) in enumerate(TYPOLOGY.items(), start=1):
        multi = " (Mehrfachnennung möglich)" if dim["multi"] else ""
        lines.append(f"**{i}) {dim['label']}** (`{key}`){multi}")
        lines.append("")
        if dim["question"]:
            lines.append(dim["question"])
            lines.append("")
        lines.append("Subkategorien:")
        aliases = dim.get("aliases", {})
        for sub_key, desc in dim["examples"].items():
            al = aliases.get(sub_key)
            suffix = (" (auch: " + ", ".join(f"`{a}`" for a in al) + ")") if al else ""
            lines.append(f"- `{sub_key}`: {desc}{suffix}")
        lines.append("")
    return "\n".join(lines).strip()


def render_category_guidance_block() -> str:
    """Render the {category_guidance_block} prompt injection.

    With the YAML schema the active categories are already the definitive list
    (rendered in {categories_block}), so this block focuses on the REJECTED
    subcategories: keys the human has ruled out, which the model must not use or
    propose as a `new_suggestion` — with the replacement category where given.
    Returns "" if nothing has been rejected yet.
    """
    blocks = []
    for i, (key, dim) in enumerate(TYPOLOGY.items(), start=1):
        bl = _GUIDANCE.get(key, {}).get("blacklist", [])
        if not bl:
            continue
        block = [f"*{i}) {dim['label']}* (`{key}`) — NICHT verwenden:"]
        for e in bl:
            expl = f" — {e['explanation']}" if e.get("explanation") else ""
            block.append(f"  - `{e['key']}`{expl}")
        blocks.append("\n".join(block))
    if not blocks:
        return ""
    header = (
        "**Abgelehnte Subkategorien (von menschlichen Kodierenden ausgeschlossen):**\n\n"
        "Verwende die folgenden Subkategorien NICHT und schlage sie auch nicht als "
        "`new_suggestion` vor; nutze stattdessen die angegebene Alternative bzw. eine "
        "der oben gelisteten aktiven Subkategorien.\n"
    )
    return (header + "\n" + "\n\n".join(blocks)).strip()


if __name__ == "__main__":
    print(render_categories_block())
    print("\n\n--- guidance ---\n")
    print(render_category_guidance_block())
