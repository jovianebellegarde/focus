# Focus GitHub Action — how to add the HUD to any repo
#
# Drop-in workflow: [examples/focus-action.yml](../examples/focus-action.yml)
# Privacy: [PRIVACY.md](PRIVACY.md)

## Add to your repository

1. Copy [`examples/focus-action.yml`](../examples/focus-action.yml) to `.github/workflows/focus.yml`.
2. Merge to your default branch.
3. Open a PR — Focus posts (and updates in place):
   - **A** — a HUD comment (summary, Mermaid, blast radius)
   - **C** — inline review comments on changed lines (edit-shaped ℹ️ captions)

Install from PyPI ([`PUBLISH.md`](PUBLISH.md)):

```bash
pip install focus-hud
```

CLI entry point remains `focus`.

> **Honesty:** Surface **C** (inline review) needs a `focus-hud` release that includes
> `focus.ci.post_review_from_env` (Phase 5). Until that tag is on PyPI, either omit the
> two JSON/inline steps in the drop-in workflow, install from this repo's `main`, or use
> this monorepo's workflow (which dogfoods the checkout via `uv sync`).

## Permissions

| Permission | Why |
|---|---|
| `contents: read` | Checkout the PR |
| `pull-requests: write` | Post / update the HUD comment **and** batched inline review comments |

No other scopes (no `checks: write`). Focus does not send source to third-party model APIs.

## Surfaces on a PR

| Surface | How | What |
|---|---|---|
| **A — PR comment** | `focus audit` → markdown → `post_from_env` | Full HUD; updates in place via `<!-- focus-hud -->` marker |
| **C — Files changed** | `focus audit --format json` → `post_review_from_env` | Up to 8 edit-shaped ℹ️ captions on changed lines; one batched `COMMENT` review; de-duped via `<!-- focus-line -->` |

Pass-through diffs skip Surface **C** entirely (ROA). Blast radius / downstream stays in **A** — unchanged files cannot receive GitHub review comments.

Optional env: `FOCUS_INLINE_MAX` (default `8`) caps how many inline captions post.

## Forked PRs

Same limitation as today for Surface **A**: the default `GITHUB_TOKEN` on `pull_request` from forks is often read-only, so posting may fail until a maintainer re-runs with write access (or a `pull_request_target` policy you own). Not a Phase 5 regression.

## This monorepo

[`.github/workflows/focus.yml`](../.github/workflows/focus.yml) uses `uv sync --frozen` so PRs dogfood the checkout under test, not only the last PyPI release — including Surface **C**.
