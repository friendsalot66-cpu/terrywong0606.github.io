# Multi-API Chat Interface v4.0.4 — Handbook for AI Models

> **Purpose:** This handbook summarizes the single-file SPA at `index.html` (~7,000 lines, 354 KB) so other AI models can make targeted edits without scanning the full file.
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
└── <script> — ~3,900 lines of JS (classes + IIFE bootstrap)
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

MultiAPIChat            — Main app class (~3,900 lines, lines 3104–7016)
  └── (DUPLICATE CLASS at ~line 5500 — same methods, slightly different line numbers)
```

> ⚠️ **Critical:** The `MultiAPIChat` class is **duplicated** in the file (lines ~3104–~5500 and ~5500–7016). Both copies are functionally identical. When patching methods that exist in both, use `replace_all=True` or patch each location separately.

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
- Managed by `StorageManager` class (lines ~2390–2641)

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
| `constructor()` | ~3105 | Init, load state, bind events |
| `createNewSession()` | ~4696 | Create tab with empty messages |
| `switchSession(id)` | ~4704 | Switch active tab |
| `forkConversation()` | ~4884 | Duplicate session with all messages |
| `closeSession(id)` | ~4752 | Delete session |
| `renderTabs()` | ~4762 | Render tab bar |

### Messaging
| Method | Line | Purpose |
|--------|------|---------|
| `sendUserMessage()` | ~5773 | Handle send: validate, render, call API |
| `callAPI()` | ~5890 | Non-streaming API call with retries |
| `streamResponse()` | ~6137 | SSE streaming response |
| `buildMessagesForAPI()` | ~6000 | Build message array with persona, context |
| `moonshotWebSearchCall()` | ~6032 | Multi-turn Moonshot web search (tool calls) |
| `stopGeneration()` | ~5552 | Abort current request |

### Model & Provider
| Method | Line | Purpose |
|--------|------|---------|
| `setModel(m, a)` | ~5507 | Set model + provider (updates global + locked) |
| `effectiveModel` (getter) | ~5252 | Returns lockedModel if locked, else currentModel |
| `effectiveAPI` (getter) | ~5264 | Returns lockedAPI if locked, else currentAPI |
| `updateModelOptions()` | ~5520 | Highlight active model in popup |
| `setPersona(idx)` | ~5544 | Change system persona |
| `getActiveProvider()` | ~3613 | Get provider instance for current API |
| `buildProviderRegistry()` | ~3589 | Build provider map |

### Lock Features (model + persona per tab)
| Method | Line | Purpose |
|--------|------|---------|
| `toggleLock()` | ~5770 | Toggle lock on/off for current tab — locks model, API, AND persona |
| `updateLockButton()` | ~5757 | Update 🔒/🔓 button state + tooltip |
| `effectiveModel` (getter) | ~5703 | Returns lockedModel if locked, else currentModel |
| `effectiveAPI` (getter) | ~5719 | Returns lockedAPI if locked, else currentAPI |
| `effectivePersona` (getter) | ~5706 | Returns lockedPersona if locked, else currentPersona (NEW) |
| `effectivePersonaPrompt` (getter) | ~5711 | Returns persona system prompt for effective persona (NEW) |
| `setPersona(p)` | ~6019 | If locked: blocks change + shows warning; caller skipped (NEW) |

### Copy / Export / Navigation / Code Preview Features (NEW v4.0.3)
| Method | Line | Purpose |
|--------|------|---------|
| `_filterVisibleContent(text)` | ~5303 | Strip `<think>...</think>` blocks for copy/export |
| `downloadMD(text)` | ~(export popup) | Export message as `.md` file via Blob/URL |
| `scrollToAdjacentUserPrompt(dir)` | ~5450 | Navigate ⬆⬇ to prev/next user prompt using viewport |
| `toggleCodeBlock(btn, codeId)` | ~7775 | Expand/collapse truncated code block (>10 lines) |

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
| `autoSaveChat()` | ~6848 | Save current session to IndexedDB |
| `loadChat(id)` | ~6558 | Load session from IndexedDB |
| `saveCurrentChat()` | ~6882 | Save with custom name |

### UI Rendering
| Method | Line | Purpose |
|--------|------|---------|
| `renderMessages()` | ~4800 | Render message list with markdown, code blocks, images |
| `updateHeaderStatus()` | ~5273 | Update header model/persona display |
| `showStatus(msg, type)` | ~5503 | Toast notification |
| `togglePopup(type)` | ~5316 | Show/hide settings popups |

### API Protocol Helpers
| Method | Line | Purpose |
|--------|------|---------|
| `_getProviderProtocol()` | ~4014 | Detect openai/gemini/anthropic protocol |
| `_buildApiUrl()` | ~4022 | Construct endpoint URL |
| `_buildHeaders()` | ~4036 | Build auth + content headers |
| `_transformBody()` | ~4056 | Transform messages to provider-specific format |
| `_parseApiResponse()` | ~4159 | Parse response for all protocols |
| `_parseStreamLine()` | ~4194 | Parse SSE stream chunks |

## Common Editing Patterns

### When patching methods that exist twice (both class copies)
Use `replace_all=True` or patch both locations. Affected methods:
- `setModel()`, `updateModelOptions()`, `updatePersonaOptions()`, `showStatus()`, `stopGeneration()`, `renderToolsList()`, `renderChatHistory()`, `togglePin()`, `exportNamedChats()`, `handleBeforeUnload()`

### Finding methods
Use line numbers above. The file is ~7,016 lines.

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

### Files Changed
- `index.html` — `renderEnhancedMarkdown()` at line ~5310 (HTML escaping logic)
- `index.html` — `_transformBody()` at line ~4271-4281 (Gemini generationConfig params)

### Verification
- 5/5 Playwright E2E tests passed (headless Chromium, port 8081)
- Tests covered: user input HTML escape, assistant response HTML escape, renderEnhancedMarkdown direct call, Gemini _transformBody params, fenced code block safety

## Deployment

- **Target:** GitHub Pages (user: friendsalot66, repo: terrywong0606.github.io)
- **Type:** Single-file static HTML — just push `index.html`
- **Dependencies:** All CDN-loaded (showdown, highlight.js, KaTeX, Mermaid, PDF.js, Highcharts, SheetJS)
- **No build step required**
