# Publishing Focus to PyPI

Distribution name on PyPI: **`focus-hud`** (the name `focus` is already taken).  
CLI and import stay **`focus`**.

```bash
pip install focus-hud
focus version   # → 0.5.0
```

## One-time: Trusted Publishing

1. Create the project on [PyPI](https://pypi.org/manage/account/) (or let the first publish create it).
2. Add a Trusted Publisher for GitHub:
   - Owner: `j0viane` / `jovianebellegarde`
   - Repository: `focus`
   - Workflow: `publish.yml`
   - Environment: `pypi`
3. In the GitHub repo, create an Environment named `pypi` (Settings → Environments).

## Release

```bash
git tag v0.5.0
git push origin v0.5.0
```

That runs [`.github/workflows/publish.yml`](../.github/workflows/publish.yml), which does two things on a `v*` tag:

1. **Publishes to PyPI** — `uv build` + `pypa/gh-action-pypi-publish`.
2. **Creates a GitHub Release** — `gh release create <tag> --generate-notes --verify-tag`, so the [Releases page](https://github.com/j0viane/focus/releases) tracks the tag as **Latest**.

> A tag push alone updates PyPI but does **not** create a GitHub Release — that is a separate object. Step 2 (added in #40) ties them together. After a release, confirm both PyPI **and** the Releases page show the new version.

Manual local publish (if you have an API token):

```bash
uv build
uv publish --token "$PYPI_TOKEN"
```

Install the published package: `pip install focus-hud`.
