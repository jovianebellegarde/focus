# Focus — Phase 0 Decisions

Resolved open questions from ethics, privacy, and planning reviews.

**Last updated:** July 2026

---

## Decisions log

| Question | Decision | Rationale |
|---|---|---|
| Default HUD caveat for partial static analysis | Use frozen text in [`HUD.md`](HUD.md) Block 4; append detected blindspots | Honest without alarming on every PR |
| LLM caption labeler (evidence pack) | **Qwen via Ollama for audit (Phase 4c+)** | Labels **all** ℹ️ on CLI audit / Audit Local; never invents topology; fail-closed validate. Overlay excluded. See [`PRIVACY.md`](PRIVACY.md) |
| LLM pack payload vs engineering rule 11 | **Capped edit lines + measured slots** (never full files / never full graph) | Aligns product with PRIVACY; topology stays deterministic |
| Grounded caption validate before enable | **Fail-closed `validate_label`** | Reject hops, wrong risk, ungrounded identifiers/scope claims; keep deterministic on reject |
| Caption model | **`qwen2.5-coder:3b` via Ollama** (optional `qwen2.5-coder:7b`) | Local only; no OpenAI/Anthropic path |
| Cloud caption providers | **Removed** | Product is Qwen-only; fail-closed when Ollama is down |
| Captions user off-switch | **Removed** | Always try Qwen on audit; overlay/autosave stay hardcoded LLM-off |
| How Ollama gets on the machine | **Helper, not bundled** — macOS may offer Homebrew install; Windows/Linux get printed instructions | Avoid shipping a large binary; user keeps Ollama updated |
| Caption prompt revision | **`320-ground-v3`** (fingerprinted in cache) | Tighter what/why prompts + `grounding` pack keys; fail-closed on chatty preamble, >2 sentences, ungrounded scope |
| Portable caption facts (target repo) | **Thin slice shipped (Phase 4d)** — more shapes deferred | Generic ledger from *target* AST/diff/graph (module assign + readers + importers); never Focus-product lore. See [`ROADMAP.md`](ROADMAP.md) Phase 4d |
| Fixture repo license | MIT for `tests/fixtures/` (same as Focus) | Clear redistribution for open-source / portfolio adoption |
| Project license | **MIT** (briefly tried GPL-3.0 for copyleft, reverted for adoption) | Credit via copyright notice; maximize try/fork friction-free use |
| Stack: CLI framework | **Typer** | Locked in [`STACK.md`](STACK.md) |
| Stack: graph library | **NetworkX** | Locked in [`STACK.md`](STACK.md) |
| HUD schema source of truth | **`docs/HUD.md`** | `focus.mdc` references it; tests assert against it |
| Phase 0 exit | **Complete** — Phase 1 may start | All exit criteria met 2026-07-06 |

---

## Related documents

- [`ETHICS.md`](ETHICS.md)
- [`PRIVACY.md`](PRIVACY.md)
- [`ROADMAP.md`](ROADMAP.md)
