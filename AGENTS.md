# AGENTS.md — Multi-API Chat Interface

> **Purpose:** This file tells any AI model *how to work on this project safely*. It's the operational playbook. For code structure, see `code/HANDBOOK.md`.

## Project Identity

| Field | Value |
|-------|-------|
| **App** | Multi-API Chat Interface v4.0.1 |
| **File** | `index.html` (~7,000 lines, 354 KB) |
| **Type** | Single-file SPA (HTML + embedded CSS + vanilla JS) |
| **Deploy** | GitHub Pages (`friendsalot66/terrywong0606.github.io`) |
| **Deps** | CDN only (showdown, highlight.js, KaTeX, Mermaid, PDF.js, Highcharts, SheetJS) |
| **Build** | None — pure static, push to deploy |
| **Owner** | Terry Wong (Hong Kong, Cantonese speaker) — replies in 繁體中文 |

---

## ⚠️ CRITICAL: Before You Do ANYTHING

1. **Load `code/HANDBOOK.md`** — read it first. Every single time. It tells you the code structure, class hierarchy, method locations, duplicate class warnings, and known pitfalls.
2. **Load the `multi-api-web-app` skill** — `skill_view(name='multi-api-web-app')`. It has the latest pitfalls, method maps, and per-feature reference docs.

---

## Workflow: How to Handle Every Task

### Phase 1 — Understand
1. Load `code/HANDBOOK.md`
2. Load `multi-api-web-app` skill
3. Ask the user **clarifying questions (max 7)** before writing any code
4. Do your own research if needed — propose a plan, wait for user approval

### Phase 2 — Plan
5. Design a concrete plan with:
   - What files/lines will change
   - What tests will verify the changes
   - Whether this is **simple** (direct edit) or **complex** (orchestrator + kanban)
6. **Complex task threshold (AI self-judges):** If the task involves 3+ methods across different sections, cross-cutting concerns, new API integrations, or significant UI restructuring → spin up an orchestrator with kanban tasks for specialists.

### Phase 3 — Execute
7. Make targeted edits using `patch` tool
8. After every patch, run `node --check index.html` to catch syntax errors immediately
9. Start a local server on **port 8010**:
   ```bash
   cd /home/erry/.hermes/projects/terrywong0606 && python3 -m http.server 8010 &
   ```
10. Run automated browser tests on `http://localhost:8010` — only test the **changed features**, keep it under 5 minutes
11. If tests fail: patch → `node --check` → retest. Loop until pass.
12. If stuck (3+ failed attempts): **stop and ask the user for help.** Don't keep patching blindly.

### Phase 4 — Validate
13. When tests pass → **notify the user** with a summary of what changed and test results
14. **Wait for user confirmation** before proceeding

### Phase 5 — Document
15. After user confirms → **auto-update `code/HANDBOOK.md`** to reflect the changes:
    - Update line numbers if code shifted
    - Add new methods to the method map
    - Update data structures if modified
    - Add to "Recent Changes" if significant
    - Add new pitfalls if you hit any

### Phase 6 — Done
16. Remind the user they handle deployment themselves (push to GitHub Pages)

---

## Decision Rules

| Situation | Action |
|-----------|--------|
| **Uncertain how to implement** | Research first → propose plan → wait for approval. Do NOT guess. |
| **Multiple valid approaches** | Propose options with trade-offs → let user pick |
| **Stuck after 3 patch attempts** | Stop. Ask the user. Do not keep patching. |
| **Simple bug fix (1 method, 1 area)** | Direct edit. No orchestrator needed. |
| **Complex feature (3+ methods, new UI, new API)** | Orchestrator + kanban with specialists |
| **Line numbers shift after edit** | Update HANDBOOK.md line numbers after confirmation |
| **Method exists in BOTH class copies** | Use `replace_all=True` in patch, or patch both locations |

---

## Testing Convention

- **Server:** `python3 -m http.server 8010` from project root
- **URL:** `http://localhost:8010`
- **Scope:** Only test features touched by the change
- **Duration:** Under 5 minutes
- **Tool:** Browser automation (Playwright via `browser_navigate` / `browser_click` / `browser_snapshot` / `browser_console`)
- **Checks:**
  - No console errors (`browser_console`)
  - UI elements render correctly
  - Changed functionality works as expected
  - No regression on adjacent features

---

## Communication Rules

- **Always reply in 繁體中文** (Traditional Chinese)
- **Casual but technical tone** — like a dev who's been vibe-coding for 1-2 years
- **Be concise** — Terry prefers direct answers over walls of text
- **Propose, don't assume** — when uncertain, present options

---

## Key Pitfalls (from `multi-api-web-app` skill)

These are the hard-learned lessons. Read the skill for full details:
1. Duplicate `MultiAPIChat` class — always `replace_all=True`
2. Event listener method names must match HTML bindings exactly
3. `switchSession()` must call `updateHeaderStatus()`
4. Never use bare `effectiveAPI` — always `this.effectiveAPI` or local `effAPI`
5. Brace mismatches from patching — always `node --check` after every patch
6. "Parse but forget to wire" — multiple message construction sites
7. Image rendering must be outside `if (message.content)` block for image-only responses
8. KaTeX backslash double-escaping danger
9. Image API methods MUST use protocol-aware pipeline
10. Chat image body MUST include `modalities: ['image']`

---

## File Map

```
/home/erry/.hermes/projects/terrywong0606/
├── index.html              ← THE app (edit this)
├── code/
│   └── HANDBOOK.md         ← Code structure reference (READ FIRST, UPDATE AFTER)
├── index_chunk_0           ← Split chunks for large-file handling
└── index_chunk_1
```
