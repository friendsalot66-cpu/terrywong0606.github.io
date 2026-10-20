# Multi-API Chat Interface v4.0.5 — Handbook for AI Models

> **Purpose:** This handbook summarizes the single-file SPA at `index.html` (~7,955 lines, 412 KB / 412,490 bytes) so other AI models can make targeted edits without scanning the full file.
>
> **File:** `/home/erry/.hermes/projects/terrywong0606/index.html`
>
> **Architecture:** Pure static HTML + embedded CSS + vanilla JS. No build step. CDN deps only. Deploy target: GitHub Pages.

---

## File Structure

```
index.html
├── <head> — CSS vars, CDN scripts (showdown, highlight.js, KaTeX, Mermaid, PDF.js, Highcharts, SheetJS)
├── <style> — ~2,700 lines of CSS (theme tokens, layout, components)
├── <body> — HTML markup (header, sidebar, tabs, messages, popups, settings)
└── <script> — ~5,400 lines of JS starting at line 2554 (classes + IIFE bootstrap)
```

## Class Hierarchy

```
StorageManager          — IndexedDB wrapper (saveChat, getChat, deleteChat, listChats)
APIProvider (abstract)  — Base class: getHeaders, fetchModels, buildMessages, parseResponse
├── PerplexityProvider
├── MoonshotProvider
├── NvidiaNIMProvider
├── GenericOpenAIProvider
├── GenericGeminiProvider
├── GenericAnthropicProvider
└── OpenRouterProvider

MultiAPIChat            — Main app class (line 3273 → end of file, ~4,680 lines)
```

> ⚠️ **Critical — it is a duplicated METHOD BLOCK, not a duplicated class.**
> There is exactly **one** `class MultiAPIChat` (line 3273). But ~11 of its methods are
> **defined twice** inside that single class body. In a JS class body the **later
> definition wins**, so copy 1 is dead code:
>
> | Method | Copy 1 (DEAD) | Copy 2 / last (LIVE) |
> |---|---|---|
> | `renderChatHistory()` | 6013 | 6235 |
> | `togglePin()` | 6073 | 6295 |
> | `renderGenericList()` | 6086 | 6308 |
> | `showStatus()` | 6093 | 6315 |
> | `setModel()` | 6097 | 6319 |
> | `updateModelOptions()` | 6110 | 6332 |
> | `setPersona()` | 6137 | 6359 |
> | `stopGeneration()` | 6152 | 6374 |
> | `handleBeforeUnload()` | 5940, 6162 | **7845** |
> | `exportNamedChats()` | 5955, 6177 | **7858** |
>
> **Rule:** patch the LIVE copy (or both). `node --check` will NOT catch a fix that landed
> only in a dead copy — the app simply behaves as if nothing changed.

## Key Data Structures

### Session Object (per tab/chat)
```js
{
  id: string,           // timestamp-based unique ID
  name: string,         // display name ("Topic 1", custom, etc.)
  messages: Array,      // [{role, content, timestamp, image?, isStreaming?, searchResults?, modelUsed?}]
  references: Object,   // {url, title, ...}
  isLocked: boolean,    // Per-Tab Model + Persona Lock
  lockedModel: string,  // Locked model name
  lockedAPI: string,    // Locked API provider
  lockedPersona: string, // Locked persona ID (NEW v4.0.3)
}
```

### Provider Registry
Built dynamically via `buildProviderRegistry()`. Maps provider ID → provider instance. Each provider has:
- `baseUrl` — API endpoint
- `fetchModels(apiKey, proxyUrl)` — fetch model list
- `getHeaders(apiKey)` — auth headers
- `buildRequestBody(messages, model, ...)` — transform to provider format
- `parseResponse(data)` — extract content from response

### State Variables (on `this`)
| Variable | Purpose | Default |
|----------|---------|---------|
| `this.sessions` | Map of all sessions (keyed by id) | `{}` |
| `this.activeSessionId` | Currently visible session | first session |
| `this.currentModel` | Global model selector | `'sonar'` |
| `this.currentAPI` | Global API provider | `'perplexity'` |
| `this.messages` | Messages array for active session | `[]` |
| `this.references` | References for active session | `{}` |
| `this.currentPersona` | Active persona index | `0` |
| `this.personas` | Persona definitions | loaded from localStorage |
| `this.apiKeys` | Map of provider → API key | `{}` |
| `this.customProviders` | User-defined custom providers | `[]` |
| `this.maxTokens` | Token limit slider | `4096` |
| `this.streamMode` | Streaming toggle | `true` |
| `this.useToolsEnabled` | Tool use toggle | `false` |
| `this.savedChats` | Metadata cache for chat history | `{}` |

## localStorage Keys

| Key | Type | Purpose |
|-----|------|---------|
| `currentModel` | string | Last selected model |
| `currentAPI` | string | Last selected provider |
| `currentPersona` | number | Last selected persona index |
| `streamMode` | bool | Streaming toggle |
| `maxTokens` | number | Token limit |
| `theme` | string | `light` or `dark` |
| `perplexity_api_key` | string | Perplexity API key |
| `moonshot_api_key` | string | Moonshot API key |
| `openrouter_api_key` | string | OpenRouter API key |
| `nvidia_api_key` | string | NVIDIA NIM API key |
| `pplxSearchEnabled` | bool | Perplexity search toggle |
| `pplxRecency` | string | Recency filter (`month`/`week`/`day`/`custom`/null) |
| `pplxStartDate` / `pplxEndDate` | string | Custom date range |
| `moonshotSearchEnabled` | bool | Moonshot web search toggle |
| `moonshotReasoningEnabled` | bool | Moonshot thinking toggle |
| `feedback_loops` | array | User corrections |
| `saved_personas` | array | Custom personas |
| `saved_chats` | array | Chat metadata |
| `localTools` | array | Custom tools |
| `localLinks` | array | Bookmark links |
| `custom_providers` | array | Custom provider configs |
| `cors_proxy_url` | string | CORS proxy URL |
| `nim_settings` | object | NVIDIA NIM settings |
| `showReferences` | bool | Reference panel visibility |
| `oneShotMode` | bool | One-shot mode |
| `feedbackMode` | bool | Feedback mode |
| `activeSessionId` | string | Last active session |

## IndexedDB

- **Store name:** `savedChats`
- **Key path:** `chat.id`
- **Structure:** `{ id, name, messages, references, timestamp, isLocked, lockedModel, lockedAPI, lockedPersona }`
- Managed by `StorageManager` class (lines 2559–2810)

## Provider Endpoints (apiEndpoints)

| Provider | Endpoint Pattern | Protocol |
|----------|-----------------|----------|
| perplexity | `https://api.perplexity.ai/chat/completions` | openai |
| moonshot | `https://api.moonshot.cn/v1/chat/completions` | openai |
| openrouter | `https://openrouter.ai/api/v1/chat/completions` | openai |
| nvidia | `https://integrate.api.nvidia.com/v1/chat/completions` | openai (CORS proxy needed) |
| custom_* | User-defined | configurable (openai/gemini/anthropic) |

## Core Method Map (MultiAPIChat)

### Session Management
| Method | Line | Purpose |
|--------|------|---------|
| `constructor()` | 3274 | Init, load state, bind events |
| `createNewSession()` | 5048 | Create tab with empty messages |
| `switchSession(id)` | 5056 | Switch active tab |
| `forkConversation()` | 5263 | Duplicate session with all messages |
| `closeSession(id)` | 5124 | Delete session |
| `renderTabs()` | 5134 | Render tab bar |

### Messaging
| Method | Line | Purpose |
|--------|------|---------|
| `sendUserMessage()` | 6383 | Handle send: validate, render, call API |
| `callAPI()` | 6727 | Non-streaming API call with retries |
| `streamResponse()` | 7006 | SSE streaming response |
| `buildMessagesForAPI()` | 6869 | Build message array with persona, context |
| `moonshotWebSearchCall()` | 6917 | Multi-turn Moonshot web search (tool calls) |
| `callChatImageAPI()` | 6658 | Image generation (protocol-aware pipeline) |
| `stopGeneration()` | 6374 (dead copy at 6152) | Abort current request |

### Model & Provider
| Method | Line | Purpose |
|--------|------|---------|
| `setModel(m, a)` | 6319 (dead copy at 6097) | Set model + provider (updates global + locked) |
| `effectiveModel` (getter) | 5818 | Returns lockedModel if locked, else currentModel |
| `effectiveAPI` (getter) | 5850 | Returns lockedAPI if locked, else currentAPI |
| `updateModelOptions()` | 6332 (dead copy at 6110) | Highlight active model in popup |
| `setPersona(idx)` | 6359 (dead copy at 6137) | Change system persona |
| `getActiveProvider()` | 3792 | Get provider instance for current API |
| `buildProviderRegistry()` | 3768 | Build provider map |

### Lock Features (model + persona per tab)
| Method | Line | Purpose |
|--------|------|---------|
| `toggleLock()` | 5885 | Toggle lock on/off for current tab — locks model, API, AND persona |
| `updateLockButton()` | 5872 | Update 🔒/🔓 button state + tooltip |
| `effectiveModel` (getter) | 5818 | Returns lockedModel if locked, else currentModel |
| `effectiveAPI` (getter) | 5850 | Returns lockedAPI if locked, else currentAPI |
| `effectivePersona` (getter) | 5830 | Returns lockedPersona if locked, else currentPersona |
| `effectivePersonaPrompt` (getter) | 5841 | Returns persona system prompt for effective persona |
| `setPersona(p)` | 6359 | If locked: blocks change + shows warning; caller skipped |

### Copy / Export / Navigation / Code Preview Features (NEW v4.0.3)
| Method | Line | Purpose |
|--------|------|---------|
| `_filterVisibleContent(text)` | 7810 | Strip `<think>...</think>` blocks for copy/export |
| `downloadMD(text)` | 5339 | Export message as `.md` file via Blob/URL |
| `scrollToAdjacentUserPrompt(dir)` | 5094 | Navigate ⬆⬇ to prev/next user prompt using viewport |
| `toggleCodeBlock(btn, codeId)` | 7934 (`window.`) | Expand/collapse truncated code block (>10 lines) |
| `copyCodeBlock(id, btn)` | 7921 (`window.`) | Copy a code block to clipboard |

### HTML Structure (NEW v4.0.3)
| Element | Purpose |
|---------|---------|
| `.chat-nav-area` | Center-bottom container for ⬆⬇ nav buttons (parallel to delete FAB) |
| `.chat-nav-btn` | 32px circle nav button, opacity 0.5, hover highlight |
| `.code-show-more-btn` | "Show more (N more lines) ▾" — click to expand truncated code |
| `.code-block-truncated` | CSS class: `max-height: 18em`, gradient fade overlay |

### Persistence
| Method | Line | Purpose |
|--------|------|---------|
| `autoSaveChat()` | 7766 | Save current session to IndexedDB |
| `loadChat(id)` | 7475 | Load session from IndexedDB |
| `saveCurrentChat()` | 7801 | Save with custom name |
| `persistSessionState()` | 3648 | Persist a non-active session without re-rendering |

### UI Rendering
| Method | Line | Purpose |
|--------|------|---------|
| `renderMessages()` | 5172 | Render message list with markdown, code blocks, images |
| `renderEnhancedMarkdown(text)` | 5388 | Markdown → HTML (escaping, code collapse, math, think blocks) |
| `updateHeaderStatus()` | 5858 | Update header model/persona display |
| `showStatus(msg, type)` | 6315 (dead copy at 6093) | Toast notification |
| `togglePopup(type)` | 5906 | Show/hide settings popups |
| `updateTokenEstimate()` | 7377 | Recompute token estimate |
| `updateMaxTokens(v)` | 7671 | Set token slider value + persist to localStorage |

### API Protocol Helpers
| Method | Line | Purpose |
|--------|------|---------|
| `_getProviderProtocol()` | 4193 | Detect openai/gemini/anthropic protocol |
| `_buildApiUrl()` | 4201 | Construct endpoint URL (`:streamGenerateContent?alt=sse` for gemini) |
| `_buildHeaders()` | 4215 | Build auth + content headers (`x-goog-api-key` for gemini) |
| `_transformBody()` | 4235 | Transform messages to provider-specific format (**model-family aware for gemini — see v4.0.5**) |
| `_finishReasonNotice(reason)` | 4369 | finishReason → human-readable warning (NEW v4.0.5) |
| `_parseApiResponse()` | 4385 | Parse response for all protocols |
| `_parseStreamLine()` | 4457 | Parse SSE stream chunks |

## Common Editing Patterns

### When patching methods that exist twice (both class copies)
Use the LIVE copy from the duplication table at the top (last definition wins), or patch both.
Verified duplicated: `renderChatHistory()`, `togglePin()`, `renderGenericList()`, `showStatus()`, `setModel()`, `updateModelOptions()`, `setPersona()`, `stopGeneration()`, `handleBeforeUnload()`, `exportNamedChats()`

### Finding methods
Use line numbers above. The file is ~7,955 lines. Re-derive them with a quick
`grep`/Node scan after any large patch — every edit above line 4369 shifts the rest.

### Adding CSS
CSS is in `<style>` tag (~lines 58–~2700). Use CSS variables (`--color-*`) for theming.

### Adding localStorage items
Follow the convention: snake_case keys, serialize with `JSON.stringify()`.

> **Bug fixes (2026-07-02):**
> - `switchSession` missing `toggleImageModeUI()` — switching back to a tab locked with an image model didn't re-show the image parameter panel. Root cause: `toggleImageModeUI()` was called in constructor + model change, but never in `switchSession()`. Fixed by adding `this.toggleImageModeUI()` after `updateLockButton()` in `switchSession()`.
> - Export button (`message-export-btn`) missing from `createMessageElement()` — only fork button was rendered. Added `📤` export button adjacent to fork button, wired to `exportMessageToWindow()`.

### Prompt Library Sidebar Button (REWRITTEN 2026-07-02)
> - Sidebar `📋` icon (`promptLibraryToggle`) now opens **new dedicated modal popup** (`promptLibraryPopup`) instead of old floating shortcut menu
> - Full CRUD management: Add, Edit, Delete, Delete All
> - **Search**: real-time filter by alias or prompt content (`promptLibrarySearch`)
> - **Import**: `.md`, `.txt`, `.json` — auto-detects format; JSON arrays or markdown `## /alias` blocks
> - **Export**: downloads `prompt-library-YYYY-MM-DD.md` with markdown format (`## /alias\ncontent\n---`)
> - Backward-compat: `showShortcutMenu()` delegates to `showPromptLibrary()` 
> - Functions: `showPromptLibrary()`, `_getShortcuts()`, `_saveShortcuts()`, `_renderPromptLibrary(filter)`, `_bindPromptLibraryEvents()`, `_showPromptForm(mode, idx)`, `_hidePromptForm()`, `_savePromptForm()`, `_promptLibraryExport()`, `_promptLibraryImport(file)`
> - All UI bindings registered in constructor via safe `document.getElementById()` null-checks
> - Modal uses standard `togglePopup('promptLibrary')` pattern (added to popups array)

## Recent Changes (v4.0.5 — Gemini 3.x Streaming Truncation Fix)

Fixed 2026-10-20.

### Symptom
Gemini-compatible custom provider (Base URL = Cloudflare Worker in front of
`generativelanguage.googleapis.com`, e.g. `gemini-3.8-flash`). With **streaming on**,
the answer stopped abruptly part-way — "only the first batch" — with no error, no toast,
and **no "Show more" button** (so it was real truncation, not the `code-block-truncated` collapse).
Non-streaming looked fine.

### Root cause (confirmed against Google's docs)
`_transformBody()` sent a Gemini 2.5 payload to Gemini 3.x models:

```js
generationConfig: {
    maxOutputTokens: body.max_tokens || 4096,
    temperature: body.temperature ?? 0.2,
    responseMimeType: "text/plain",
    thinkingConfig: { thinkingBudget: 0 }   // <-- 2.5-only parameter
}
```

Three official facts break this on Gemini 3.6+:

1. **`thinking_budget` was replaced by `thinking_level`** (`low`/`medium`/`high`).
   Sending `thinkingBudget` on 3.x is ignored or rejected, so thinking kept running at
   the model default (`medium` for 3.6/3.8 Flash, `high` for 3 Flash / 3 Pro).
2. **`max_output_tokens` is a hard cutoff that INCLUDES thought tokens.** Google:
   *"If the model hits this limit while reasoning, it stops generating with status
   `incomplete` and returns truncated or empty output."* With a 4096 cap and `medium`
   thinking, the visible answer got whatever was left — hence mid-sentence truncation.
3. **`temperature` / `top_p` / `top_k` are deprecated and ignored** on Gemini 3.6+,
   and future models return HTTP 400. They must not be sent.

Because the response is still HTTP 200, and the parser never read `finishReason`
(`MAX_TOKENS`), nothing in the UI could explain the missing text.

### Fix

| # | Location | Change |
|---|----------|--------|
| R1 | `_transformBody()` 4235 | Model-family split: `gemini[N.]X` with X≥3 → `thinkingConfig: { thinkingLevel: 'low' }` and **no `temperature`**; 2.5 → `{ thinkingBudget: 0 }` + temperature; older/unknown aliases → **no** thinkingConfig at all. `maxOutputTokens` fallback 4096 → 8192. |
| R2 | `_parseStreamLine()` 4457 | Reads `candidates[0].finishReason`, `promptFeedback.blockReason`, mid-stream `{"error":…}` frames; splits `parts[].thought` into `reasoningContent`; accepts `data:{` without the space (some relays). |
| R3 | `_parseApiResponse()` 4385 | Same fields for the non-streaming path. |
| R4 | `_finishReasonNotice()` 4369 | NEW helper mapping finishReason → human text. |
| R5 | `streamResponse()` ~7150 | Wires finishReason / blockReason / streamError onto the assistant message. |
| R6 | `streamResponse()` finally ~7250 | Appends a visible warning when finishReason ≠ `STOP` (e.g. `MAX_TOKENS` says "raise Max Tokens or lower the thinking level"). |
| R7/R8 | `streamResponse()` 7096, 7115 | Fixed a swallowed error: the old `try { throw new Error(msg) } catch (e) { throw new Error(rawBody) }` always rethrew the raw JSON. Also: on HTTP 400 whose body mentions "thinking", strip `generationConfig.thinkingConfig` and retry once (guards gemini-compatible endpoints that reject the param). |
| R9 | `callAPI()` ~6855 | Same truncation notice for non-streaming. |
| R10 | `worker.js` | `respHeaders.delete('content-length')` — a stale length on a re-streamed body makes the browser cut the SSE short. |

### Model detection
`/gemini[-_ ]?(\d+)(?:\.(\d+))?/` on the lowercased model id. `gemini-3.8-flash`,
`gemini-3.6-flash`, `gemini-3-pro-preview`, `models/gemini-3.8-flash`, `GEMINI-3.8-FLASH`
and `gemini-4-argon` all resolve to major≥3. `gemini-flash-latest` matches nothing → no
thinkingConfig is sent (safe default: never guess a param the endpoint may not know).

### Verification
- `node --check` on the extracted inline script (314,872 chars) — exit 0
- `node --check` on `worker.js` — exit 0
- 20/20 unit tests on the real `_parseStreamLine` (MAX_TOKENS, error frame, thought split,
  `data:` without space, `[DONE]`, OpenAI branch regression)
- 26/26 unit tests on the real `_transformBody` (3.8/3.6/3-pro/4-argon → thinkingLevel low
  and no temperature; 2.5 → thinkingBudget 0; 2.0/1.5/unknown → no thinkingConfig)
- `python -m http.server 8010` smoke test — HTTP 200

### Files changed
- `index.html` — 403,869 → 412,008 chars (+8,139), 10 patches
- `worker.js` — 3,503 → 3,719 chars, 1 patch (now tracked in git)
- `code/HANDBOOK.md` — this update

### Pitfalls learned
1. **Do not send Gemini 2.5 thinking params to 3.x.** `thinkingBudget` ↔ `thinkingLevel`.
2. **`maxOutputTokens` includes thought tokens.** Truncation is a budget problem, not a network problem.
3. **Gemini truncation is HTTP 200.** Always read `finishReason`; otherwise the failure is invisible.
4. **`write`/`edit` file tools cannot write into this workspace.** The workspace lives on
   `\\wsl.localhost\...` (WSL 9p). The tools use atomic temp-file + hardlink, and 9p returns
   `ENOTSUP`, so writes fail. Use `python`/`node` (available on this machine) to write files.
   `git` also needs `-c safe.directory=*` because of the UNC path ownership check.

## Recent Changes (v4.0.4 — 5 Features: Filter, Export, Nav, Code Preview, Persona Lock)

Added 2026-07-15:

### Feature 1 — Copy/Export Filter (`_filterVisibleContent`)
Strips `<think>...</think>` blocks from copy and export content. Applied in `createMessageElement()` copy + export button handlers. Uses regex `/<\/think>[\s\S]*?<\/think>/gi`.

### Feature 2 — Export as .md (`downloadMD`)
Export popup now has "📝 Download as Markdown (.md)" button alongside existing .txt. Uses `Blob([mdContent], {type:'text/markdown'})` + `URL.createObjectURL` + `<a>` click for auto-download.

### Feature 3 — Chat Navigation Buttons (⬆⬇)
Two 32px circle buttons centered at chat bottom (`.chat-nav-area`, `left:50%`), parallel to delete FAB. `scrollToAdjacentUserPrompt('up'/'down')` uses `getBoundingClientRect()` to find nearest user prompt above/below viewport midpoint, then scrolls `.chat-container`.

### Feature 4 — Code Block 10-Line Preview
Code blocks >10 lines get `.code-block-truncated` class: `max-height:18em` + gradient fade overlay. "Show more (N more lines) ▾" button calls `toggleCodeBlock(btn, codeId)` to expand/collapse.

### Feature 5 — Per-Tab Persona Lock (extends model lock)
Session gains `lockedPersona` field. New getters: `effectivePersona` (lockedPersona || currentPersona), `effectivePersonaPrompt` (persona system prompt for effective persona). `toggleLock()` now locks model + API + persona atomically. `setPersona()` blocked with warning toast when active tab is locked. Each locked tab independently locks its own persona — Tab 1 Excel / Tab 3 Auditor, switching resumes correctly. `buildMessagesForAPI()` uses `effectivePersonaPrompt`. Persisted to IndexedDB + localStorage via `autoSaveChat()`/`loadChat()`.

### CSS / HTML Changes
- `.chat-nav-area` + `.chat-nav-btn` (NEW, replaces old `.fab-nav-btn`)
- `.code-block-truncated` + `pre::after` gradient + `.code-show-more-btn` (NEW)
- `.fab-nav-btn` REMOVED — nav buttons moved to independent `.chat-nav-area`

### Files Changed
- `index.html` — +165 lines, ~5 patches
- Fix thinking block ordering: moved think block extraction before HTML escaping (line 5329)

## Recent Changes (Per-Tab Model Lock)

Added in this session:
1. Session data: `isLocked`, `lockedModel`, `lockedAPI` fields
2. Getters: `effectiveModel`, `effectiveAPI` — route to locked values when active tab is locked
3. `toggleLock()` and `updateLockButton()` — UI toggle for lock state
4. All API call paths (`callAPI`, `streamResponse`, `moonshotWebSearchCall`, `buildMessagesForAPI`) now use `effectiveModel`/`effectiveAPI`
5. `autoSaveChat()` persists lock state to IndexedDB
6. `loadChat()` restores lock state from IndexedDB
7. `forkConversation()` starts with `isLocked: false`

> **Bug fixes:**
> - Event listener: `toggleModelLock()` → `toggleLock()` (lock button was dead)
> - `switchSession` missing `updateHeaderStatus()` call (header showed global model instead of locked model when switching back to locked tab)
> - `callAPI` / `streamResponse`: bare `effectiveAPI` used in `this.apiEndpoints[effectiveAPI]` — should be `effAPI` (const defined at top of each method). Caused "effectiveAPI is not defined" error on every API call.

## Recent Changes (v4.0.3 — reasoning_content Fallback for Non-Streaming)

Added 2026-07-04:

### Problem
Some providers (FreeTheAI, others) send model output in `reasoning_content` field instead of `content`. In streaming mode, `_parseStreamLine` already handles this by collecting `reasoningContent` and wrapping it in `think` tags. However, non-streaming `callAPI()` → `_parseApiResponse()` only looked at `message.content` — when it was empty string, v4.0.2's empty response detection fired a false error even though valid `reasoning_content` was present.

### Solution
In `_parseApiResponse()` OpenAI default path (~line 4298): added a 3-line fallback:
```js
if (!content && message.reasoning_content) {
    content = message.reasoning_content;
}
```
This runs before the array-content check, so `reasoning_content` strings are picked up transparently. Tested with `glm/glm-5.2` non-streaming: content=`""`, reasoning=`"..."` → fallback_content=`"..."` ✅.

### Files Changed
- `index.html` — `_parseApiResponse()` at line ~4298 (3 lines added)

## Recent Changes (v4.0.2 — Silent Empty Response Detection)

Added 2026-07-04:

### Problem
Some providers return HTTP 200 with empty/missing content — no error in console, no toast, just a blank bubble. User can't tell if it's a model-side or client-side issue.

### Solution — three detection points:
1. **`callAPI()` (~6568-6598)**: After `_parseApiResponse()`, check if `content` is empty. If so, construct a diagnostic error with: model name, provider ID, endpoint URL, `finish_reason`, `hasChoices` flag, and troubleshooting tips. Throw as Error so it's caught by `sendMessage()` catch block.
2. **`streamResponse()` (~6942-6960)**: In the `finally` block after stream ends, check if `assistantMessage.content` is effectively empty (no raw content, no images). If empty, inject a diagnostic message directly into `assistantMessage.content` and log to console with `[Empty Stream]` prefix.
3. **`sendMessage()` catch (~6220-6235)**: Enhanced to include `modelUsed` in the error bubble, log `[API Error]` to console, and show first line of error as toast.

### Error Message Format
```
⚠️ Model returned empty response (HTTP 200 OK)

Provider: vova/claude-opus-4-8 (custom_xxx)
Endpoint: https://api.freetheai.xyz/v1/chat/completions
Finish reason: "stop"
Has choices: true

👉 This is usually a model-side issue. Try:
• Switch to a different model
• Simplify your prompt
• Check provider status
```

### For Streaming
```
⚠️ Stream completed with no content (HTTP 200 OK)
...
👉 This is usually a model-side issue. The server accepted the request but produced zero tokens.
```

## Recent Changes (v4.0.3 — HTML Escaping + Gemini Output Fix)

Added 2026-09-07:

### Problem 1: Raw HTML Rendering
User input and model responses containing HTML code were rendered as DOM elements instead of visible text. This allowed potential XSS via `<script>` tags and unintended layout breaks from raw `<div>`/`<style>` blocks.

### Problem 2: Gemini "Only Thinking, No Output"
Gemini models (especially Self-gemini combo models via OpenRouter or Google AI Studio) consumed all output budget on thinking tokens, returning zero text content.

### Solution 1 — HTML Escaping in `renderEnhancedMarkdown()` (~5310):
1. Extract fenced code blocks (` ```...``` `) → replace with `FENCEDBLOCK{n}` placeholders
2. Extract inline code (` `...` `) → replace with `INLINEBLOCK{n}` placeholders
3. HTML-entity-escape remaining text: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`
4. Restore placeholders → code blocks keep original content (Showdown handles escaping inside `<pre><code>`)
5. Result: raw HTML outside code blocks renders as visible text, never as DOM elements

### Solution 2 — Gemini Request Parameters in `_transformBody()` (~4271-4281):
Added to `generationConfig` for Gemini protocol requests:
- `responseMimeType: "text/plain"` — prevents Gemini from returning HTML/Markdown that browsers might parse
- `thinkingConfig: { thinkingBudget: 0 }` — disables thinking token budget so all output capacity goes to content

> ⚠️ **SUPERSEDED in v4.0.5.** `thinkingBudget` is a **Gemini 2.5-only** parameter.
> On Gemini 3.x it is ignored (or rejected), thinking stays on at the default level,
> and the reasoning tokens eat `maxOutputTokens` — which truncated answers mid-sentence.
> `temperature` is also deprecated on Gemini 3.x. See the v4.0.5 section below.

### Files Changed
- `index.html` — `renderEnhancedMarkdown()` at line ~5310 (HTML escaping logic)
- `index.html` — `_transformBody()` at line ~4271-4281 (Gemini generationConfig params)

### Verification
- 5/5 Playwright E2E tests passed (headless Chromium, port 8081)
- Tests covered: user input HTML escape, assistant response HTML escape, renderEnhancedMarkdown direct call, Gemini _transformBody params, fenced code block safety

## Deployment

- **Target:** GitHub Pages (user: friendsalot66-cpu, repo: terrywong0606.github.io, branch `main`)
- **Type:** Single-file static HTML — just push `index.html`
- **Also versioned:** `worker.js` (Cloudflare Worker proxy for gemini/CORS). It is **not**
  served by Pages for the app; it must be deployed separately to Cloudflare Workers.
- **Never commit** the `*.bak-*` patch backups.
- **Dependencies:** All CDN-loaded (showdown, highlight.js, KaTeX, Mermaid, PDF.js, Highcharts, SheetJS)
- **No build step required**
