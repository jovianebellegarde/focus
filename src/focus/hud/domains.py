"""Owner-declared domain labels for Phase 6 summary framing.

Business meaning comes from ``.focus.toml`` ``[domains]`` (human-owned) or
a small set of path conventions (labeled heuristic). Focus never invents
domain labels from an LLM in v1.
"""

from __future__ import annotations

import fnmatch

from focus.hud.classify import is_danger_path


def match_domain(path: str, domains: dict[str, str]) -> str | None:
    """Return the first domain label whose glob matches ``path``.

    Patterns are tried in document order (dict insertion order). Matching is
    case-sensitive against POSIX-style relative paths.
    """
    if not domains or not path:
        return None
    normalized = path.replace("\\", "/")
    for pattern, label in domains.items():
        text = (label or "").strip()
        if not text:
            continue
        if _glob_match(normalized, pattern.replace("\\", "/")):
            return text
    return None


def domain_for_seeds(
    seeds: list[str],
    domains: dict[str, str],
    *,
    danger_paths: set[str] | None = None,
) -> str | None:
    """Pick one domain label for the executive summary (ROA: at most one).

    Order: seed paths first (document order of seeds), then Danger Zone paths
    not already tried. Owner map wins; convention fallback only when the map
    is empty or has no hit.
    """
    seen: set[str] = set()
    candidates: list[str] = []
    for seed in seeds:
        if seed and seed not in seen:
            seen.add(seed)
            candidates.append(seed)
    for path in sorted(danger_paths or ()):
        if path not in seen:
            seen.add(path)
            candidates.append(path)

    if domains:
        for path in candidates:
            hit = match_domain(path, domains)
            if hit:
                return hit
        return None

    # No owner map — quiet convention fallback (labeled heuristic).
    dangerish = set(danger_paths or ())
    for path in candidates:
        hint = convention_domain_label(
            path,
            treat_as_danger=path in dangerish or is_danger_path(path),
        )
        if hint:
            return hint
    return None


def convention_domain_label(
    path: str,
    *,
    treat_as_danger: bool = False,
) -> str | None:
    """Heuristic domain phrase from path conventions — not owner business map.

    Only fires for strong, portable shapes (billing/auth) when the path is a
    Danger Zone (path heuristic **or** fan-out hub). Silence over filler.
    """
    if not path:
        return None
    if not (treat_as_danger or is_danger_path(path)):
        return None
    padded = f"/{path.replace(chr(92), '/')}/"
    if "/billing/" in padded:
        return "Billing / payment path"
    if "auth" in padded:
        return "Auth boundary"
    return None


def _glob_match(path: str, pattern: str) -> bool:
    """Path-aware glob: ``*`` does not cross ``/``; ``**`` matches a tree."""
    if pattern == path:
        return True
    # ``billing/**`` → match anything under billing/ (including the dir itself)
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    # Segment-wise ``*`` so ``jobs/*`` matches ``jobs/worker.py`` but not nested.
    path_parts = path.split("/")
    pat_parts = pattern.split("/")
    if len(path_parts) != len(pat_parts):
        return False
    return all(
        fnmatch.fnmatch(part, pat) for part, pat in zip(path_parts, pat_parts, strict=True)
    )
