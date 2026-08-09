"""Mermaid flowchart from a computed import graph subgraph.

Nodes are files. Arrows show *impact direction* (seed → dependents),
which is the reverse of the import edge A→B ("A imports B"). Every
emitted arrow is checked against the graph so the diagram cannot invent
topology.

Role colors (``classDef``) are presentation only — they do not add nodes
or edges. Legend for product + agent chat:

- **seed** — changed file(s) you edited
- **danger** — Danger Zone (shared hub / API / schema / config)
- **downstream** — in blast radius, not seed/danger
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath

import networkx as nx

MAX_NODES = 15

# Modest fills that stay readable on GitHub light/dark Mermaid themes.
_CLASS_DEFS = (
    "  classDef seed fill:#1f6feb,stroke:#58a6ff,color:#fff",
    "  classDef danger fill:#9e6a03,stroke:#d29922,color:#fff",
    "  classDef downstream fill:#21262d,stroke:#8b949e,color:#c9d1d9",
)


def render_mermaid(
    graph: nx.DiGraph,
    seed: str | list[str],
    rings: list[tuple[int, list[str]]],
    *,
    danger_paths: set[str] | None = None,
) -> str:
    """Build a Mermaid flowchart for seed(s) and blast radius.

    ``danger_paths`` colors Danger Zone nodes (warm). Seeds take priority
    over danger when a path is both (changed file stays blue).
    """
    seeds = [seed] if isinstance(seed, str) else list(seed)
    seed_set = set(seeds)
    danger_set = set(danger_paths or ())
    nodes = _select_nodes(seeds, rings)
    impact_edges = _impact_edges(graph, nodes)
    lines = [
        "flowchart LR",
        "  %% Nodes = files. Arrow = change flows to (is used by).",
        "  %% Colors = role only (seed / danger / downstream) — not new topology.",
    ]
    lines.extend(_subgraph_blocks(nodes, seed_set))
    for src, dst in impact_edges:
        lines.append(f"  {_node_id(src)} --> {_node_id(dst)}")
    lines.extend(_CLASS_DEFS)
    lines.extend(_class_assignments(nodes, seed_set, danger_set))
    return "\n".join(lines)


def validate_mermaid_edges(graph: nx.DiGraph, mermaid: str) -> list[str]:
    """Return invalid edge descriptions; empty list means all edges are real.

    Mermaid shows impact direction (B --> A when A imports B). Validation
    checks that the reverse import edge exists in the graph.
    """
    invalid: list[str] = []
    id_to_path = {_node_id(n): n for n in graph.nodes()}
    for line in mermaid.splitlines():
        stripped = line.strip()
        if "-->" not in stripped or stripped.startswith("%%"):
            continue
        # Skip classDef / class lines (no edges).
        if stripped.startswith("classDef") or stripped.startswith("class "):
            continue
        left, right = [part.strip() for part in stripped.split("-->", 1)]
        src_path = id_to_path.get(left)
        dst_path = id_to_path.get(right)
        if src_path is None or dst_path is None:
            invalid.append(f"unknown node in edge {left} --> {right}")
            continue
        # Impact src --> dst means dst imports src in the graph.
        if not graph.has_edge(dst_path, src_path):
            invalid.append(f"no import edge for impact {src_path} --> {dst_path}")
    return invalid


def _select_nodes(seeds: list[str], rings: list[tuple[int, list[str]]]) -> list[str]:
    ordered = list(seeds)
    for _, paths in rings:
        for path in paths:
            if path not in ordered:
                ordered.append(path)
    if len(ordered) <= MAX_NODES:
        return ordered
    kept = list(seeds)
    for _, paths in rings:
        for path in paths:
            if len(kept) >= MAX_NODES:
                return kept
            if path not in kept:
                kept.append(path)
    return kept


def _impact_edges(graph: nx.DiGraph, nodes: list[str]) -> list[tuple[str, str]]:
    allowed = set(nodes)
    edges: list[tuple[str, str]] = []
    for importer, imported in graph.edges():
        if importer in allowed and imported in allowed:
            # Import: importer → imported. Impact: imported → importer.
            edges.append((imported, importer))
    return sorted(edges)


def _subgraph_blocks(nodes: list[str], seeds: set[str]) -> list[str]:
    groups: dict[str, list[str]] = defaultdict(list)
    for path in nodes:
        groups[_layer(path)].append(path)

    lines: list[str] = []
    for layer, paths in sorted(groups.items()):
        sid = _safe_id(layer)
        lines.append(f"  subgraph {sid} [{_label(layer)}]")
        for path in sorted(paths):
            marker = " ⭐" if path in seeds else ""
            lines.append(f'    {_node_id(path)}["{path}{marker}"]')
        lines.append("  end")
    return lines


def _class_assignments(
    nodes: list[str],
    seeds: set[str],
    danger_paths: set[str],
) -> list[str]:
    """Assign Mermaid classes: seed > danger > downstream."""
    by_role: dict[str, list[str]] = {
        "seed": [],
        "danger": [],
        "downstream": [],
    }
    for path in nodes:
        nid = _node_id(path)
        if path in seeds:
            by_role["seed"].append(nid)
        elif path in danger_paths:
            by_role["danger"].append(nid)
        else:
            by_role["downstream"].append(nid)

    lines: list[str] = []
    for role, ids in by_role.items():
        if not ids:
            continue
        lines.append(f"  class {','.join(ids)} {role}")
    return lines


def _layer(path: str) -> str:
    parts = PurePosixPath(path).parts
    if len(parts) == 1:
        return "root"
    if parts[0] == "src" and len(parts) > 1:
        return parts[1]
    return parts[0]


def _node_id(path: str) -> str:
    return "n_" + _safe_id(path)


def _safe_id(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text)


def _label(layer: str) -> str:
    return layer.replace("_", " ").title() if layer != "root" else "Root"
