"""Shared GitHub REST helpers for CI posters (issue comments + review comments)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def request_json(
    method: str, url: str, token: str, payload: dict | None = None
) -> list | dict:
    """HTTP JSON call authenticated with a GitHub token. Raises RuntimeError on HTTP errors."""
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "focus-hud",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {method} {url} failed: {exc.code} {detail}") from exc
