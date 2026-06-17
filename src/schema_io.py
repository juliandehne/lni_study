"""
schema_io.py

Round-trip I/O for prompts/category_schema.yaml — the single SOURCE OF TRUTH for
the RSE typology (gate + dimensions + active/rejected/candidate subcategories).

We use ruamel.yaml in its default round-trip mode so that human comments, blank
lines, key order and block-scalar (`>`) formatting SURVIVE a load->modify->save
cycle. That matters because the file is hand-edited between narrowing rounds: the
`collect` step appends machine-discovered candidates and `review` promotes them,
but neither should destroy the curator's notes.

Public API:
    load_schema(path=SCHEMA_PATH) -> CommentedMap   # behaves like a dict
    save_schema(data, path=SCHEMA_PATH) -> None      # comment-preserving dump

Read-only consumers (categories.py) can treat the result as a plain mapping.
Writers (narrow_categories.py) must mutate the SAME object they loaded and pass it
back to save_schema, so ruamel can re-attach the original comments.
"""

from pathlib import Path

from ruamel.yaml import YAML

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "prompts" / "category_schema.yaml"

# One shared round-trip parser. width is set very high so long German block
# scalars are not hard-wrapped on save (which would churn the diff every round).
_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.width = 4096
# Match the hand-authored style of category_schema.yaml so automated appends do
# not reformat the whole file: nested maps indent 2, list items indent 4 with the
# dash at offset 2 (e.g. `    active:` then `      - key: ...`).
_yaml.indent(mapping=2, sequence=4, offset=2)


def load_schema(path: str | Path = SCHEMA_PATH):
    """Load the schema YAML as a round-trip CommentedMap (dict-like)."""
    path = Path(path)
    if not path.is_file():
        raise SystemExit(
            f"category_schema.yaml not found at {path}. It is the source of truth "
            "for the typology; restore it before running the pipeline.")
    with open(path, "r", encoding="utf-8") as f:
        return _yaml.load(f)


def save_schema(data, path: str | Path = SCHEMA_PATH) -> None:
    """Dump a (round-trip) schema object back to disk, preserving comments."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        _yaml.dump(data, f)


def new_seq():
    """An empty round-trip sequence (block style) for appending list items."""
    from ruamel.yaml.comments import CommentedSeq
    s = CommentedSeq()
    return s


def new_map(**kwargs):
    """A round-trip mapping (block style) seeded with kwargs, preserving order."""
    from ruamel.yaml.comments import CommentedMap
    m = CommentedMap()
    for k, v in kwargs.items():
        m[k] = v
    return m
