r"""
make_pipeline_uml.py - generate the pipeline figure for the EMSE paper.

The process-flow figure in the paper is NOT drawn by hand. It is emitted from the
pipeline's own definitions, so a figure in the paper can never quietly disagree
with the code that produced the data:

  src/pipeline_menu.py   STAGES        -> which steps exist, their grouping, and
                                          which ones spend SAIA tokens
  src/benchmark_models.py PANEL_SIZE   -> how many annotator seats the fork/join
                                          in the diagram has
  src/categories.py      TYPOLOGY      -> the dimensions (and their category
                                          counts) named in the annotation action
  src/preflight.py       DEFAULT_MODEL -> the pinned fallback annotator

What stays here is the LAYOUT (which action follows which, where the loops close),
because that is editorial: a reader-facing diagram is not the same object as the
menu's flat stage list. Every layout entry names a stage key, and an unknown key
is a hard error - so renaming a stage in pipeline_menu.py breaks the figure build
loudly instead of leaving the paper showing a step that no longer exists.

Outputs (both \input by paper/emse_paper.qmd, both regenerated on every render):

  figures/pipeline_uml.tex    the figure environment with the tikzpicture
  figures/pipeline_facts.tex  \newcommand macros so the PROSE uses the same
                              numbers as the figure (\PanelSize, \NumDimensions,
                              \NumCategories, \PinnedModel, \NumStages)

    python paper/figures/make_pipeline_uml.py            # writes next to itself
    python paper/figures/make_pipeline_uml.py --stdout   # print, write nothing

Only tikz + positioning/arrows/shapes/fit/backgrounds are used: all of them are
vendored in the frozen TinyTeX, and the paper sets latex-auto-install: false.
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent.parent               # publications/lni_study
sys.path.insert(0, str(STUDY_ROOT / "src"))

import pipeline_menu                          # noqa: E402  the stage list
import categories as cat                      # noqa: E402  the typology
import preflight                              # noqa: E402  the pinned model

try:                                          # benchmark_models pulls pandas/openai;
    import benchmark_models                    # if that ever fails the figure should
    PANEL_SIZE = benchmark_models.PANEL_SIZE   # still build, just with the default.
except Exception:                              # noqa: BLE001
    PANEL_SIZE = 3

STAGES = {s.key: s for s in pipeline_menu.STAGES}


# --------------------------------------------------------------------------
# LaTeX helpers
# --------------------------------------------------------------------------
_ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}"}


def tex(s: str) -> str:
    return "".join(_ESC.get(c, c) for c in str(s))


def mono(s: str) -> str:
    """A stage key / model id as it appears in the figure."""
    return r"\texttt{" + tex(s) + "}"


def stage(key: str):
    """Look a stage up, loudly. A typo here must not silently drop a step."""
    if key not in STAGES:
        raise SystemExit(
            f"[uml] pipeline_menu.py has no stage '{key}'. The figure layout is out "
            f"of sync with the pipeline - fix the layout in {Path(__file__).name} "
            f"(known keys: {', '.join(sorted(STAGES))}).")
    return STAGES[key]


# --------------------------------------------------------------------------
# The layout: two columns of UML activity nodes.
#   col 0 = corpus preparation + human coding, col 1 = model selection + study.
# Each action names the pipeline stage it stands for; the token badge, and the
# panel fan-out further down, come from the code, not from this table.
# --------------------------------------------------------------------------
COL_X = {0: 0.0, 1: 8.6}
ACTION_W = "3.5cm"

LEFT = [
    # (node id, kind, y, stage key or None, title, subtitle)
    ("start",   "init",     0.0,  None,       "", ""),
    ("corpus",  "object",  -1.15, None,       "LNI corpus",
     r"$\approx$14k papers, PDF"),
    ("draw",    "action",  -2.75, "estimate", "Stratified draw",
     "sample per LNI volume"),
    ("pools",   "action",  -4.55, "pools",    "Build working sets",
     r"narrow / gold / final / pool"),
    ("conf",    "action",  -6.35, "confirm",  "Gate papers",
     "keep research software"),
    ("round",   "action",  -8.35, "round",    "Narrowing round",
     "annotate, mine new categories"),
    ("dcat",    "decision", -10.5, None,      r"new\\categories?", ""),
    ("agold",   "action", -12.65, "a-gold",   "Pre-annotate gold set",
     "machine draft for the coders"),
    ("gold",    "action", -14.45, "gold",     "Two coders code",
     "gate + 5 dimensions, by hand"),
    ("dicr",    "decision", -16.6, None,      r"ICR\\acceptable?", ""),
    ("goldstd", "object", -18.5,  None,       "Goldstandard",
     "human labels, per paper"),
]

RIGHT = [
    ("bench",   "action",  -2.75, "bench",    "Score candidate LLMs",
     "one F score vs.\\ the goldstandard"),
    ("dcov",    "decision", -5.0, None,       r"coverage\\$\geq 90\%$?", ""),
    ("fork",    "bar",     -7.1,  None,       "", ""),
    ("join",    "bar",    -10.4,  None,       "", ""),
    ("vote",    "action", -11.75, None,       "Majority vote",
     "gate, single- and multi-valued keys"),
    ("full",    "action", -13.75, "full",     "Annotate the study corpus",
     "confirm-on-the-fly, resumable"),
    ("dataset", "object", -15.75, None,       "Annotated corpus",
     "merged labels + per-seat votes"),
    ("analyse", "action", -17.4,  None,       "Typology analysis",
     "distributions, dissent, RQs"),
    ("end",     "final",  -19.1,  None,       "", ""),
]

EDGES = [
    # (from, to, options, label, label placement)
    ("start", "corpus", "", "", ""),
    ("corpus", "draw", "", "", ""),
    ("draw", "pools", "", "", ""),
    ("pools", "conf", "", "", ""),
    ("conf", "round", "", "", ""),
    ("round", "dcat", "", "", ""),
    ("dcat", "agold", "", "no", "right"),
    ("agold", "gold", "", "", ""),
    ("gold", "dicr", "", "", ""),
    ("dicr", "goldstd", "", "yes", "right"),
    ("dcov", "fork", "", "yes", "right"),
    ("fork", "join", "", "", ""),          # replaced by the seat branches below
    ("join", "vote", "", "", ""),
    ("vote", "full", "", "", ""),
    ("full", "dataset", "", "", ""),
    ("dataset", "analyse", "", "", ""),
    ("analyse", "end", "", "", ""),
]


def seat_nodes(n: int, x_centre: float, y: float) -> tuple[list[str], list[str]]:
    """The fork/join branches - one per panel seat, straight from PANEL_SIZE."""
    step = 2.75
    body, edges = [], []
    for i in range(n):
        x = x_centre + (i - (n - 1) / 2) * step
        nid = f"seat{i}"
        role = "lead" if i == 0 else f"seat {i + 1}"
        body.append(
            f"  \\node[seat] ({nid}) at ({x:.2f},{y:.2f}) "
            f"{{\\textbf{{LLM {i + 1}}}\\\\[1pt]{{\\tiny {role}}}}};")
        edges.append(f"  \\draw[flow] (fork.south) -- ++(0,-0.25) -| ({nid}.north);")
        edges.append(f"  \\draw[flow] ({nid}.south) |- ++(0,-0.35) -- (join.north);")
    return body, edges


def node_tex(nid, kind, y, key, title, sub, x) -> str:
    """One activity node. The token badge is read off the Stage, not typed here."""
    pos = f"at ({x:.2f},{y:.2f})"
    if kind == "init":
        return f"  \\node[initial node] ({nid}) {pos} {{}};"
    if kind == "final":
        return f"  \\node[final node] ({nid}) {pos} {{}};"
    if kind == "bar":
        return f"  \\node[synchbar] ({nid}) {pos} {{}};"
    if kind == "decision":
        return f"  \\node[decision] ({nid}) {pos} {{\\tiny {title}}};"

    lines = [f"\\textbf{{{title}}}"]
    if sub:
        lines.append(f"{{\\tiny {sub}}}")
    if key is not None:
        s = stage(key)
        badge = mono(s.key) + (r"\,$\bullet$" if s.needs_token else "")
        lines.append(f"{{\\tiny {badge}}}")
    style = "objectnode" if kind == "object" else "action"
    return f"  \\node[{style}] ({nid}) {pos} {{{'\\\\[2pt]'.join(lines)}}};"


def build_figure() -> str:
    dims = [d for d in cat.DIMENSIONS]
    n_cat = sum(len(cat.TYPOLOGY[d].get("examples") or {}) for d in dims)
    token_stages = [s.key for s in pipeline_menu.STAGES if s.needs_token]

    body = []
    for nid, kind, y, key, title, sub in LEFT:
        body.append(node_tex(nid, kind, y, key, title, sub, COL_X[0]))
    for nid, kind, y, key, title, sub in RIGHT:
        body.append(node_tex(nid, kind, y, key, title, sub, COL_X[1]))

    seats, seat_edges = seat_nodes(PANEL_SIZE, COL_X[1], -8.75)
    body += seats

    edges = []
    for a, b, opt, lab, place in EDGES:
        if (a, b) == ("fork", "join"):
            continue                      # the seats carry this flow
        o = f"[flow{',' + opt if opt else ''}]"
        l = f" node[elabel,{place or 'right'}] {{\\tiny {lab}}}" if lab else ""
        edges.append(f"  \\draw{o} ({a}) --{l} ({b});")
    edges += seat_edges

    # the two loops and the hand-off between the columns
    edges.append(
        "  \\draw[flow] (dcat.west) -- node[elabel,above,pos=0.35] {\\tiny yes, "
        "refine schema} ++(-2.3,0) |- (round.west);")
    edges.append(
        "  \\draw[flow] (dicr.east) -- node[elabel,below,pos=0.3] {\\tiny no, "
        "re-code} ++(1.5,0) |- (gold.east);")
    edges.append(
        "  \\draw[flow] (goldstd.east) -- node[elabel,above,pos=0.25] {\\tiny "
        "reference labels} ++(1.4,0) |- (bench.west);")
    edges.append(
        "  \\draw[flow] (dcov.east) -- node[elabel,above] {\\tiny no} ++(1.5,0) "
        "node[right,align=left] {\\tiny disqualified,\\\\[-1pt]\\tiny drop "
        "candidate};")
    edges.append(
        "  \\draw[flow,dashed] (conf.east) -- node[elabel,above,pos=0.55] {\\tiny "
        "study papers} ++(3.0,0) |- (full.west);")

    # partition frames (UML activity partitions), fitted to the nodes they hold
    parts = [
        ("Corpus \\& sampling", ["corpus", "draw", "pools", "conf"]),
        ("Schema narrowing", ["round", "dcat"]),
        ("Human goldstandard", ["agold", "gold", "dicr", "goldstd"]),
        ("LLM selection", ["bench", "dcov"]),
        ("Panel annotation", ["fork"] + [f"seat{i}" for i in range(PANEL_SIZE)]
         + ["join", "vote", "full"]),
        ("Analysis", ["dataset", "analyse"]),
    ]
    back = ["  \\begin{scope}[on background layer]"]
    for i, (label, ids) in enumerate(parts):
        fit = " ".join(f"({n})" for n in ids)
        back.append(f"    \\node[partition,fit={fit}] (p{i}) {{}};")
        # sits ON the dashed border like a UML frame label; the white fill keeps
        # it readable where the box crosses an edge or a synchronisation bar.
        back.append(f"    \\node[partlabel] at ($(p{i}.north west)+(9pt,0)$) "
                    f"{{\\tiny {label}}};")
    back.append("  \\end{scope}")

    dim_list = ", ".join(mono(d) for d in dims)
    caption = (
        "Process flow of the annotation pipeline as a UML activity diagram. "
        f"Rounded boxes are actions, the monospaced key is the pipeline step that "
        f"runs them (\\texttt{{run\\_pipeline.cmd <step>}}); $\\bullet$ marks the "
        f"{len(token_stages)} steps that spend LLM calls. Papers pass the "
        f"research-software gate before they are typed along {len(dims)} dimensions "
        f"({dim_list}) holding {n_cat} categories in total. The fork/join is the "
        f"annotation panel: the {PANEL_SIZE} best-scoring models of the selection "
        f"step classify every paper independently and their answers are merged by "
        f"majority vote, with the highest-scoring model breaking ties. "
        f"Generated from the pipeline sources by "
        f"\\texttt{{paper/figures/make\\_pipeline\\_uml.py}}.")

    return "\n".join([
        "% !! GENERATED FILE - do not edit. See paper/figures/make_pipeline_uml.py",
        r"\begin{figure}[tbp]",
        r"  \centering",
        # max width AND max height: the diagram is taller than it is wide, so
        # scaling to \linewidth alone overflows the page (adjustbox keeps the
        # aspect ratio and picks whichever bound binds first).
        r"  \adjustbox{max width=\linewidth, max totalheight=0.86\textheight}{%",
        r"  \begin{tikzpicture}[",
        r"    font=\footnotesize,",
        f"    action/.style={{rounded corners=3pt, draw, thick, fill=white, "
        f"text width={ACTION_W}, align=center, inner sep=4pt, minimum height=1cm}},",
        f"    objectnode/.style={{draw, thick, fill=white, text width={ACTION_W}, "
        r"align=center, inner sep=4pt, minimum height=0.9cm},",
        r"    decision/.style={diamond, draw, thick, fill=white, aspect=1.9,"
        r" align=center, inner sep=1pt},",
        r"    seat/.style={rounded corners=3pt, draw, thick, fill=white,"
        r" align=center, text width=1.9cm, inner sep=3pt},",
        r"    synchbar/.style={fill=black, minimum width=6.4cm,"
        r" minimum height=2.6pt, inner sep=0pt},",
        r"    initial node/.style={circle, fill=black, minimum size=6pt,"
        r" inner sep=0pt},",
        r"    final node/.style={circle, draw, thick, fill=white, minimum size=9pt,"
        r" inner sep=0pt, path picture={\fill (path picture bounding box.center)"
        r" circle (2.2pt);}},",
        r"    flow/.style={-stealth, thick},",
        r"    elabel/.style={inner sep=1.5pt, fill=white},",
        r"    partition/.style={draw=black!35, dashed, rounded corners=4pt,"
        r" inner sep=7pt},",
        r"    partlabel/.style={anchor=west, text=black!60, fill=white,"
        r" inner sep=1.5pt},",
        r"  ]",
        *body,
        *edges,
        *back,
        r"  \end{tikzpicture}%",
        r"  }",
        f"  \\caption{{{caption}}}",
        r"  \label{fig:pipeline}",
        r"\end{figure}",
        "",
    ])


def build_facts() -> str:
    """Macros so the running text cannot drift from the figure."""
    dims = list(cat.DIMENSIONS)
    n_cat = sum(len(cat.TYPOLOGY[d].get("examples") or {}) for d in dims)
    multi = [d for d in dims if cat.TYPOLOGY[d].get("multi")]
    rows = [
        ("PanelSize", str(PANEL_SIZE)),
        ("NumDimensions", str(len(dims))),
        ("NumMultiDimensions", str(len(multi))),
        ("NumCategories", str(n_cat)),
        ("NumStages", str(len(pipeline_menu.STAGES))),
        ("NumTokenStages", str(sum(1 for s in pipeline_menu.STAGES if s.needs_token))),
        ("PinnedModel", mono(preflight.DEFAULT_MODEL)),
        ("DimensionList", ", ".join(mono(d) for d in dims)),
    ]
    out = ["% !! GENERATED FILE - do not edit. "
           "See paper/figures/make_pipeline_uml.py"]
    out += [f"\\newcommand{{\\{name}}}{{{value}\\xspace}}" for name, value in rows]
    out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stdout", action="store_true",
                    help="print the figure instead of writing the .tex files")
    args = ap.parse_args()

    figure, facts = build_figure(), build_facts()
    if args.stdout:
        print(figure)
        return
    (HERE / "pipeline_uml.tex").write_text(figure, encoding="utf-8")
    (HERE / "pipeline_facts.tex").write_text(facts, encoding="utf-8")
    print(f"[uml] wrote {HERE / 'pipeline_uml.tex'} "
          f"({PANEL_SIZE} panel seats, {len(pipeline_menu.STAGES)} stages known)")
    print(f"[uml] wrote {HERE / 'pipeline_facts.tex'}")


if __name__ == "__main__":
    main()
