"""Post batched inline PR review comments from a FocusHUD JSON payload.

Surface C on GitHub: pin edit-shaped ℹ️ captions to changed lines on the
Files changed tab. Blast radius / downstream stays in the Surface A issue
comment — unchanged files cannot receive review comments.

Uses the same ``pull-requests:write`` scope as the HUD comment poster.
Comments are marked with ``FOCUS_LINE_MARKER`` so re-runs delete + replace
instead of stacking duplicates.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from focus.ci._http import request_json
from focus.hud.render import symbol_sort_key
from focus.models import FocusHUD

FOCUS_LINE_MARKER = "<!-- focus-line -->"
DEFAULT_INLINE_MAX = 8


def build_line_comments(
    hud: FocusHUD,
    *,
    max_comments: int = DEFAULT_INLINE_MAX,
) -> list[dict]:
    """Map FocusHUD captions to GitHub review-comment payloads.

    Returns dicts shaped for ``POST .../pulls/{n}/reviews`` ``comments[]``:
    ``{path, line, side: "RIGHT", body}``. Anchors only on
    ``HunkDetail.line`` / ``LineExplanation.line`` (real changed lines) —
    never on ``ChangedSymbolInfo.line`` (the ``def`` can sit outside the diff).

    Pass-through HUDs yield ``[]``. Cap + order match Surface A ROA
    (danger-zone / public symbols first).
    """
    if hud.mode == "pass_through" or max_comments <= 0:
        return []

    danger_paths = {node.path for node in hud.danger_zones}
    ordered_symbols = sorted(
        hud.changed_symbols,
        key=lambda s: symbol_sort_key(s, danger_paths),
    )

    candidates: list[dict] = []
    for symbol in ordered_symbols:
        for hunk in symbol.hunk_details:
            detail = hunk.detail.strip()
            if not detail or hunk.line <= 0:
                continue
            candidates.append(
                {
                    "path": symbol.path,
                    "line": hunk.line,
                    "side": "RIGHT",
                    "body": _comment_body(detail),
                }
            )

    for orphan in hud.line_explanations:
        detail = orphan.detail.strip()
        if not detail or orphan.line <= 0:
            continue
        candidates.append(
            {
                "path": orphan.path,
                "line": orphan.line,
                "side": "RIGHT",
                "body": _comment_body(detail),
            }
        )

    return candidates[:max_comments]


def post_or_update_pr_review(
    *,
    hud: FocusHUD,
    token: str,
    repository: str,
    pr_number: int,
    commit_id: str,
    api_url: str = "https://api.github.com",
    max_comments: int = DEFAULT_INLINE_MAX,
) -> str:
    """Delete stale Focus line comments, then post a batched COMMENT review.

    Returns ``'posted'`` or ``'skipped'`` (pass-through / no captions).
    """
    comments = build_line_comments(hud, max_comments=max_comments)
    owner, repo = repository.split("/", 1)
    _delete_stale_line_comments(api_url, token, owner, repo, pr_number)
    if not comments:
        return "skipped"

    url = f"{api_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    request_json(
        "POST",
        url,
        token,
        {
            "commit_id": commit_id,
            "event": "COMMENT",
            "comments": comments,
        },
    )
    return "posted"


def post_review_from_env(hud_json_path: Path) -> str:
    """Read FocusHUD JSON and post inline review comments from Actions env."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("FOCUS_PR_NUMBER") or _pr_number_from_event()
    commit_id = os.environ.get("FOCUS_HEAD_SHA") or _head_sha_from_event()
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    max_raw = os.environ.get("FOCUS_INLINE_MAX")
    max_comments = int(max_raw) if max_raw else DEFAULT_INLINE_MAX

    if not token or not repository or not pr_number or not commit_id:
        raise RuntimeError(
            "Need GITHUB_TOKEN, GITHUB_REPOSITORY, FOCUS_PR_NUMBER "
            "(or pull_request event), and head SHA (FOCUS_HEAD_SHA / "
            "pull_request.head.sha / GITHUB_SHA) to post a review."
        )

    hud = FocusHUD.model_validate_json(hud_json_path.read_text(encoding="utf-8"))
    return post_or_update_pr_review(
        hud=hud,
        token=token,
        repository=repository,
        pr_number=int(pr_number),
        commit_id=commit_id,
        api_url=api_url,
        max_comments=max_comments,
    )


def _comment_body(detail: str) -> str:
    return f"{FOCUS_LINE_MARKER}\n{detail}"


def _pr_number_from_event() -> str | None:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path or not Path(path).is_file():
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    pr = payload.get("pull_request") or {}
    number = pr.get("number") or payload.get("number")
    return str(number) if number else None


def _head_sha_from_event() -> str | None:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if path and Path(path).is_file():
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        pr = payload.get("pull_request") or {}
        head = pr.get("head") or {}
        sha = head.get("sha")
        if sha:
            return str(sha)
    return os.environ.get("GITHUB_SHA") or None


def _delete_stale_line_comments(
    api_url: str, token: str, owner: str, repo: str, pr_number: int
) -> None:
    url = f"{api_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments?per_page=100"
    comments = request_json("GET", url, token)
    if not isinstance(comments, list):
        return
    for comment in comments:
        body = comment.get("body") or ""
        if FOCUS_LINE_MARKER not in body:
            continue
        comment_id = comment.get("id")
        if comment_id is None:
            continue
        delete_url = f"{api_url}/repos/{owner}/{repo}/pulls/comments/{int(comment_id)}"
        request_json("DELETE", delete_url, token)
