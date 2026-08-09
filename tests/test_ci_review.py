"""Inline PR review helpers — no network; mapping + ROA + HTTP sequence."""

from __future__ import annotations

from focus.ci.github_review import (
    FOCUS_LINE_MARKER,
    build_line_comments,
    post_or_update_pr_review,
)
from focus.models import (
    ChangedSymbolInfo,
    FocusHUD,
    HunkDetail,
    ImpactNode,
    LineExplanation,
)


def _hud(
    *,
    mode: str = "full",
    symbols: list[ChangedSymbolInfo] | None = None,
    orphans: list[LineExplanation] | None = None,
    danger_zones: list[ImpactNode] | None = None,
) -> FocusHUD:
    return FocusHUD(
        mode=mode,  # type: ignore[arg-type]
        seed="auth_utils.py",
        summary="Test HUD.",
        risk_tier="HIGH",
        changed_symbols=symbols or [],
        line_explanations=orphans or [],
        danger_zones=danger_zones or [],
    )


def test_build_line_comments_maps_hunk_and_orphan_details():
    hud = _hud(
        symbols=[
            ChangedSymbolInfo(
                path="auth_utils.py",
                name="validate_token",
                kind="function",
                line=10,  # def line — must NOT be used as anchor
                changed_lines=[14, 15],
                hunk_details=[
                    HunkDetail(line=14, changed_lines=[14, 15], detail="Returns False on expiry."),
                ],
            )
        ],
        orphans=[
            LineExplanation(
                path="auth_utils.py",
                line=3,
                changed_lines=[3],
                detail="Adds import for clock skew helper.",
            )
        ],
    )
    comments = build_line_comments(hud)
    assert len(comments) == 2
    assert all(c["side"] == "RIGHT" for c in comments)
    assert all(FOCUS_LINE_MARKER in c["body"] for c in comments)
    lines = {c["line"] for c in comments}
    assert lines == {14, 3}
    assert 10 not in lines  # never anchor on ChangedSymbolInfo.line
    by_line = {c["line"]: c for c in comments}
    assert "Returns False on expiry." in by_line[14]["body"]
    assert "Adds import for clock skew helper." in by_line[3]["body"]


def test_build_line_comments_skips_pass_through():
    hud = _hud(mode="pass_through", symbols=[
        ChangedSymbolInfo(
            path="docs/README.md",
            name="n/a",
            kind="function",
            line=1,
            hunk_details=[HunkDetail(line=1, changed_lines=[1], detail="Docs only.")],
        )
    ])
    assert build_line_comments(hud) == []


def test_build_line_comments_caps_and_orders_danger_public_first():
    danger = [ImpactNode(path="billing.py", hops=1, reason="API route")]
    symbols = [
        ChangedSymbolInfo(
            path="helpers.py",
            name="_private_helper",
            kind="function",
            line=1,
            hunk_details=[HunkDetail(line=2, changed_lines=[2], detail="Private helper edit.")],
        ),
        ChangedSymbolInfo(
            path="billing.py",
            name="charge_user",
            kind="function",
            line=1,
            hunk_details=[HunkDetail(line=20, changed_lines=[20], detail="Public billing edit.")],
        ),
        ChangedSymbolInfo(
            path="util.py",
            name="format_cents",
            kind="function",
            line=1,
            hunk_details=[
                HunkDetail(line=i, changed_lines=[i], detail=f"Util edit {i}.")
                for i in range(30, 40)
            ],
        ),
    ]
    orphans = [
        LineExplanation(path="z.py", line=100 + i, changed_lines=[100 + i], detail=f"Orphan {i}.")
        for i in range(5)
    ]
    comments = build_line_comments(_hud(symbols=symbols, orphans=orphans, danger_zones=danger))
    assert len(comments) == 8
    # Danger-zone public symbol first
    assert comments[0]["path"] == "billing.py"
    assert comments[0]["line"] == 20
    assert "Public billing edit." in comments[0]["body"]
    # Private helper should sort after public non-danger (util) — with cap 8,
    # private + orphans may be dropped; ensure no private before public billing.
    assert all(
        not (c["path"] == "helpers.py" and idx == 0) for idx, c in enumerate(comments)
    )


def test_build_line_comments_skips_empty_detail_and_bad_line():
    hud = _hud(
        symbols=[
            ChangedSymbolInfo(
                path="a.py",
                name="foo",
                kind="function",
                line=1,
                hunk_details=[
                    HunkDetail(line=5, changed_lines=[5], detail=""),
                    HunkDetail(line=0, changed_lines=[], detail="Bad line."),
                    HunkDetail(line=6, changed_lines=[6], detail="Keep me."),
                ],
            )
        ]
    )
    comments = build_line_comments(hud)
    assert len(comments) == 1
    assert comments[0]["line"] == 6


def test_post_or_update_pr_review_deletes_stale_then_posts(monkeypatch):
    calls: list[tuple[str, str, dict | None]] = []

    def fake_request(method: str, url: str, token: str, payload: dict | None = None):
        calls.append((method, url, payload))
        if method == "GET":
            return [
                {"id": 11, "body": f"{FOCUS_LINE_MARKER}\nold"},
                {"id": 12, "body": "human review reply"},
                {"id": 13, "body": f"{FOCUS_LINE_MARKER}\nalso old"},
            ]
        return {}

    monkeypatch.setattr("focus.ci.github_review.request_json", fake_request)

    hud = _hud(
        symbols=[
            ChangedSymbolInfo(
                path="auth_utils.py",
                name="validate_token",
                kind="function",
                line=10,
                hunk_details=[
                    HunkDetail(line=14, changed_lines=[14], detail="Returns False on expiry."),
                ],
            )
        ]
    )
    result = post_or_update_pr_review(
        hud=hud,
        token="t",
        repository="jovianebellegarde/focus",
        pr_number=42,
        commit_id="abc123",
        api_url="https://api.github.com",
    )
    assert result == "posted"
    assert calls[0][0] == "GET"
    assert "/pulls/42/comments" in calls[0][1]
    deletes = [c for c in calls if c[0] == "DELETE"]
    assert len(deletes) == 2
    assert any("/pulls/comments/11" in c[1] for c in deletes)
    assert any("/pulls/comments/13" in c[1] for c in deletes)
    assert not any("/pulls/comments/12" in c[1] for c in deletes)
    posts = [c for c in calls if c[0] == "POST"]
    assert len(posts) == 1
    assert "/pulls/42/reviews" in posts[0][1]
    payload = posts[0][2]
    assert payload is not None
    assert payload["event"] == "COMMENT"
    assert payload["commit_id"] == "abc123"
    assert len(payload["comments"]) == 1
    assert payload["comments"][0]["line"] == 14
    assert payload["comments"][0]["side"] == "RIGHT"


def test_post_or_update_pr_review_skips_pass_through_after_cleanup(monkeypatch):
    calls: list[tuple[str, str, dict | None]] = []

    def fake_request(method: str, url: str, token: str, payload: dict | None = None):
        calls.append((method, url, payload))
        if method == "GET":
            return [{"id": 99, "body": f"{FOCUS_LINE_MARKER}\nstale"}]
        return {}

    monkeypatch.setattr("focus.ci.github_review.request_json", fake_request)

    result = post_or_update_pr_review(
        hud=_hud(mode="pass_through"),
        token="t",
        repository="jovianebellegarde/focus",
        pr_number=7,
        commit_id="deadbeef",
    )
    assert result == "skipped"
    assert any(c[0] == "GET" for c in calls)
    assert any(c[0] == "DELETE" for c in calls)
    assert not any(c[0] == "POST" for c in calls)
