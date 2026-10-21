# Multi-API Chat Interface v5.0.0 — Handbook for AI Models

> **Purpose:** Orientation for AI models editing the single-file SPA. Read this before touching `index.html`.
>
> **File:** `index.html` (~7,250 lines, ~350 KB). Pure static HTML + embedded CSS + vanilla JS. No build step. CDN deps only.
>
> **Deploy:** GitHub Pages (repo `friendsalot66-cpu/terrywong0606.github.io`, branch `main`). `worker.js` (Cloudflare Worker proxy) is versioned here but deployed separately.

---

## ⚠️ Read this first — environment gotchas

1. **This workspace lives on `\\wsl.localhost\...`.** The DSH `write` / `edit` file tools use an atomic temp-file + hardlink, and 9p returns `ENOTSUP`, so they **cannot write here**. Use `python` (3.13) or `node` (v22) via `pwsh` instead — both are installed and can write normally.
2. **`git` needs `-c safe.directory=*`** on this UNC path, otherwise it aborts with "dubious ownership".
3. **`pwsh`/shell works**, so `node --check`, `python -m http.server 8010`, and Playwright are all available. Playwright is bundled at `%APPDATA%\npm\node_modules\@playwright\cli\node_modules\playwright`; launch the installed Chrome via `executablePath` (no browsers are downloaded in the ms-playwright cache).
4. After every patch: extract the inline `<script>` and run `node --check` on it. `node --check index.html` does **not** work on HTML.

## File Structure

```
index.html
├── <head>   — CSS vars, CDN scripts (showdown, highlight.js, KaTeX, Mermaid, PDF.js, Highcharts, SheetJS)
├── <style>  — ~2,300 lines of CSS (theme tokens, layout, components)
├── <body>   — HTML markup (header, sidebar, tabs, messages, popups, settings)
└── <script> — ~4,700 lines of JS, starts at line 2374 (3 inline blocks; the first is the app)
```

## Class Hierarchy (v5.0.0 — 6 classes, no duplicates)

```
StorageManager            — IndexedDB wrapper (line 2379)
APIProvider (abstract)    — base: getHeaders, getApiUrl, buildRequestBody, buildMessages,
                            parseResponse, parseStreamChunk, fetchModels
├── GenericOpenAIProvider
├── GenericGeminiProvider
└── GenericAnthropicProvider
MultiAPIChat              — the app (constructor at line 2721, ~4,500 lines)
```

> **Removed in v5.0.0:** `PerplexityProvider`, `MoonshotProvider`, `NvidiaNIMProvider`, `OpenRouterProvider`. All providers are now user-defined custom providers.
>
> **Deduplicated in v5.0.0:** the old file defined ~11 `MultiAPIChat` methods twice inside the same class body (later definition silently won). There is now exactly **one** definition of each — `showStatus`, `setModel`, `updateModelOptions`, `setPersona`, `stopGeneration`, `renderChatHistory`, `togglePin`, `renderGenericList`, `exportNamedChats`, `handleBeforeUnload`, `processHighcharts`. Do not resurrect the "patch both copies" workaround; verify with a duplicate scan instead:
>
> ```bash
> node -e "const s=require('fs').readFileSync('index.html','utf8');const m={};s.split(/\r?\n/).forEach((l,i)=>{const x=l.match(/^\s{8,28}(?:(?:async|static|get|set)\s+)?([A-Za-z_\$][\w\$]*)\s*\([^)]*\)\s*\{/);if(!x)return;if(['if','for','while','switch','catch','do','else','return','function','try','finally'].includes(x[1]))return;(m[x[1]]=m[x[1]]||[]).push(i+1)});Object.entries(m).filter(([,v])=>v.length>1).forEach(([k,v])=>console.log(k,v.join(',')))"
> ```
> Cross-class repeats (`constructor`, `getHeaders`, `fetchModels`, `deleteChat`) are expected.

## Key Data Structures

### Session object
```js
{
  id, name,
  messages: [...],        // ACTIVE PATH ONLY — derived from messageTree, never edit directly
  messageTree: {          // v5.0.0 conversation tree (see "Branching" below)
    nodes: { [id]: { id, parentId, childrenIds[], activeChildIndex, role, content, timestamp,
                     citations[], searchResults[], tokenUsage, modelUsed, image, images, finishReason } },
    rootIds: [], activeRootIndex, currentLeafId
  },
  references: {},         // rebuilt from the active path's citations on every recompute
  isLocked, lockedModel, lockedAPI, lockedPersona
}
```

### State on `this`
`this.sessions`, `this.activeSessionId`, **`this.currentChatId`** (persistence key — see pitfalls), `this.messages` (= active path), `this.references`, `this.customProviders`, `this.providerRegistry`, `this.apiKeys`, `this.maxTokens` (4096 default), `this.streamMode` (true default), `this.userMemory`, `this.memoryEnabled`.

### localStorage keys (v5.0.0)
`custom_providers`, `<providerId>_api_key`, `cors_proxy_url`, `currentAPI`, `currentModel`, `currentPersona`, `theme`, `streamMode`, `maxTokens`, `showReferences`, `oneShotMode`, `user_memory` (≤2000 chars), `memory_enabled`, `saved_personas`, `saved_shortcuts`, `saved_chats`, `activeSessionId`.

**Removed keys:** `feedback_loops`, `feedbackMode`, `localTools`, `localLinks`, `nim_settings`, `pplx*`, `moonshot*`, `perplexity_api_key`, `moonshot_api_key`, `openrouter_api_key`, `nvidia_api_key`.

## Core Method Map (v5.0.0, measured)

### Conversation tree / branching (new in v5.0.0)
| Method | Line | Purpose |
|---|---|---|
| `ensureSessionTree(session)` | 4202 | Migrate flat `messages` → tree (idempotent; reuses `m.id`) |
| `recomputeActiveMessages(session)` | 4256 | Walk root → `activeChildIndex` chain, rebuild `session.messages` + `references` |
| `appendMessageNode(session, msgData, parentId?)` | 4297 | Add a node under `currentLeafId` (or explicit parent), activate it |
| `switchBranch(nodeId, delta)` | 4332 | Cycle siblings; **call with the node currently displayed** (UI contract, see 4576) |
| `regenerateResponse(nodeId)` | 4360 | 🔄 on an assistant node → new sibling assistant node |
| `_generateFromUserNode(sessionId, userNodeId)` | 6144 | Edit "Save & Regenerate" / regenerate entry point |
| `scrollToAdjacentUserPrompt(dir)` | 4448 | ⬆⬇ jump between user prompts |

### Messaging
| Method | Line | Purpose |
|---|---|---|
| `sendUserMessage()` | 6217 | Validate, push user node, dispatch |
| `omniRouteAgenticCall(sessionId, parentNodeId?)` | 5786 | Multi-turn agent loop (web_search / web_fetch, max 5 rounds) |
| `streamResponse(msg, pre, sessionId, parentNodeId?)` | 6578 | SSE streaming |
| `callAPI(msg, pre, sessionId)` | 6459 | Non-streaming request |
| `callChatImageAPI(prompt, params, sessionId)` | 6411 | Image generation (passes `_protocol` to `_parseApiResponse`) |
| `buildMessagesForAPI(pre, upToNodeId?)` | 6542 | Build payload; appends `[User Memory]` and slices to the active path |

### Session / persistence
| Method | Line | Purpose |
|---|---|---|
| `createNewSession()` | 4385 | New tab |
| `switchSession(id)` | 4403 | Switch tab (sets `activeSessionId` **and** `currentChatId`) |
| `closeSession(id)` | 4478 | Delete tab |
| `forkConversation()` | 4662 | Duplicate session |
| `loadChat(id)` | 6978 | Restore from IndexedDB (restores `messageTree`) |
| `autoSaveChat()` | 7154 | Save — **keys on `this.currentChatId`**, not `activeSessionId` |
| `saveCurrentChat()` | 7190 | Save with a custom name |
| `persistSessionState()` | 3050 | Persist a non-active session |

### Settings / memory / profile
| Method | Line | Purpose |
|---|---|---|
| `openAddProviderModal(editId?)` | 3314 | Provider form + **Base URL validation/normalisation** |
| `addCustomProvider(cfg)` | 3203 | Persist a new provider |
| `saveMemory()` / `clearMemory()` | 4793 / 4806 | 🧠 global memory (2000-char cap) |
| `updateMemoryToggleIcon()` | 4786 | Active state of the 🧠 button |
| `exportProfile()` | 5357 | Selective JSON export (6 checkbox sections) |
| `handleImportProfileFile(file)` | 5437 | File picker → parse |
| `applyImportedProfile(data)` | 5455 | Restore selected sections |

### API protocol layer
| Method | Line | Purpose |
|---|---|---|
| `_getProviderProtocol()` | 3597 | `openai` / `gemini` / `anthropic` from `cp.apiProtocol` |
| `_buildApiUrl(base, model, protocol, isStream)` | 3603 | Strips `/chat/completions` / `/messages`; appends the right path |
| `_buildHeaders(protocol, key)` | 3619 | `Authorization: Bearer` / `x-goog-api-key` / `x-api-key` |
| `_transformBody(body, msgs, protocol)` | 3638 | Provider payload; **model-family aware for Gemini** |
| `_finishReasonNotice(reason)` | 3748 | finishReason → human-readable warning |
| `_parseApiResponse(data, protocol)` | 3764 | Non-streaming parse |
| `_parseStreamLine(line, protocol, state)` | 3829 | One SSE line → `{content, reasoningContent, finishReason, blockReason, error, ...}` |

### UI
`renderMessages()` 4538 · `renderEnhancedMarkdown(text)` 4830 · `showStatus(msg,type)` 5720 · `updateHeaderStatus()` 5273 · `updateTokenEstimate()` 6867 · `updateMaxTokens(v)` 7093 · `processHighcharts(el)` 6929 (renders ```highcharts``` JSON blocks) · `processTables(el)` 6953.
`window.` helpers: `copyCodeBlock` 7216, `toggleCodeBlock` 7229, `exportTable` 7205.

## Spec A2 — Base URL rules (v5.0.0)

| Protocol | Must end with | Resolved endpoint |
|---|---|---|
| openai | `/v1` | `{base}/chat/completions`, `{base}/models` |
| anthropic | `/v1` | `{base}/messages` |
| gemini | `/v1beta` or `/v1` | `{base}/models/{model}:generateContent` / `:streamGenerateContent?alt=sse` |

`openAddProviderModal()`'s save handler strips trailing slashes, strips `/chat/completions` and `/messages` (with a toast), then validates the suffix and rejects with a `showStatus(...,'warning')` if it fails. The same normalisation runs at startup over `custom_providers` (migration, ~2724) and inside `_buildApiUrl()` / `fetchModels()` so old stored values keep working. Image generation appends `/images/generations` (~6366).

## Spec A3 — Global memory

`buildMessagesForAPI()` prepends to the system message:
```
\n\n[User Memory]\n<this.userMemory.trim()>
```
only when `this.memoryEnabled && this.userMemory.trim()`. Capped at 2000 chars in both the `<textarea maxlength>` and `saveMemory()`.

## Spec A4/B1 — OmniRoute agent loop

`omniRouteAgenticCall()` posts to `{chatUrl}` with `tools: [web_search, web_fetch]`, `tool_choice: 'auto'`, up to **5** rounds. Tool endpoints: `POST {searchBase}/search` `{query, max_results}` → `{results|data|organic:[{url,title,snippet}]}`; `POST {searchBase}/web/fetch` `{url}` → `{content|markdown|text}`. `searchBase` = the provider's `customSearchBaseUrl` when `useCustomSearchEndpoint` is on, else the provider base. Tool steps accumulate into `toolLogMarkdown` and are wrapped in `<details class="tool-collapse">`; citations land on the assistant node (`citations[]` = URLs, `searchResults[]` = `{name,title,url,snippet}`) which feeds the 🔗 References panel.

**Final round:** the loop's last non-streaming round already contains the answer, so it is **reused** — one tool turn costs 2 chat calls, and `streamMode` does not add a request. Only when the 5-round tool budget runs out before any answer exists does the code make **one** extra synthesis request (without `tools`), honouring `streamMode`. Tool HTTP errors (non-2xx) are thrown so the message reaches the model, e.g. “web_search returned HTTP 403: Model \"search\" is not allowed for this API key”.

## Spec B2 — Branching model

- `session.messages` is **derived**; the source of truth is `session.messageTree`.
- Siblings = `parent.childrenIds`; the visible one is `parent.activeChildIndex` (clamped, defaults to last).
- Roots are siblings too (`tree.rootIds` + `activeRootIndex`) — used when the first user turn is edited.
- Editing a user prompt → new sibling **user** node; 🔄 Regenerate → new sibling **assistant** node. Both become active.
- `switchBranch(nodeId, delta)` must receive the node **currently rendered** (that is what the `◀ n/m ▶` buttons pass). Passing a non-active sibling is a no-op when it would clamp to the same index.
- The tree is persisted (`autoSaveChat` includes `messageTree`) and restored by `loadChat`, so branches survive reload.
- Navigator: `.branch-nav` in `.message-header`, rendered only when `siblings.length > 1`.

## Pitfalls (hard-learned)

1. **Never send Gemini 2.5 thinking params to Gemini 3.x.** `thinkingBudget` ↔ `thinkingLevel`. Since Gemini 3.6+, `temperature`/`top_p`/`top_k` are deprecated and ignored (400 on future models). `_transformBody()` splits by model major version: ≥3 → `thinkingConfig.thinkingLevel='low'` with **no** `temperature`; 2.5 → `thinkingBudget:0` + temperature; unknown aliases → no `thinkingConfig` at all.
2. **Gemini `maxOutputTokens` is a hard cutoff that INCLUDES thought tokens.** Truncation arrives as HTTP 200 + `finishReason: "MAX_TOKENS"`. `_parseStreamLine` / `_parseApiResponse` surface `finishReason` / `blockReason` / mid-stream `{error}` frames, and `streamResponse` appends a visible warning. Do not remove that plumbing — silence was the original bug.
3. **`autoSaveChat()` keys on `this.currentChatId`, not `activeSessionId`.** `switchSession()` sets both; a test or feature that only sets `activeSessionId` will silently save the wrong chat.
4. **The empty-stream guard used to eat single-line answers.** The old `content.replace(/^[^\n]*\n?(?:Error: |)/, '')` consumed the entire string when there was no newline, so "Yes." / "42" were replaced by the "no content" diagnostic. Now it is `(content || '').trim()`. Do not reintroduce a first-line-stripping regex here.
5. **Never use bare `effectiveAPI`.** Use `this.effectiveAPI` or a local `effAPI`.
6. **Image rendering must sit outside `if (message.content)`** so image-only replies still render.
7. **KaTeX: watch backslash doubling** in template strings.
8. **Charts:** ```highcharts``` fenced blocks holding Highcharts options JSON are rendered by `processHighcharts()` — a `.highcharts-host` div is injected after the code block (the config stays visible). JSON only; JS functions in the config are not supported.
9. **Agent-loop tool HTTP errors must reach the model.** `/search` and `/web/fetch` used to be parsed without checking `res.ok`, so a 403 looked like an empty result set and the model answered “search found nothing”. They now throw and the reason lands in the tool result. Keep that behaviour.
10. After any patch: extract the inline script → `node --check`, then run the Playwright suites. Static scanning alone will not catch DOM/null regressions.

## Recent Changes (v5.0.0)

- **A1/B3 — Profile backup & restore.** Legacy Storage & Data Rescue (`runStorageDoctor()`, `detectIframe()`, `#runStorageDoctorBtn`, `#reqStorageAccessBtn`, `#forceBreakoutBtn`, `#storageDoctorResult`, `#openInNewTab`) removed. Added the 🛡️ selective JSON export/import in `#settingsPopup` with 6 checkbox sections (meta/memory, providers+keys, CORS, personas, prompt library, chat history).
- **A2 — Standardised Base URL + startup migration.** See the table above.
- **A3 — Global memory (🧠).** Feedback Loop removed (`feedbackMode`, `feedbackLoops`, `#selectionTooltip`, `#revisionPopup`); `#feedbackToggle` → `#memoryToggle` + `#memoryPopup`.
- **A4/B1 — OmniRoute agent loop.** New custom-provider fields `useCustomSearchEndpoint` / `customSearchBaseUrl` (`#_provCustomSearch`, `#_provSearchUrl`).
- **A5/A6/A7 — Provider/tool cleanup.** Tools popup, folder input, workspace file handles, and the four hardcoded providers removed. `#togglePartialMode` / `#partialModeContainer` gone. Safe fallback when no custom provider is configured.
- **B2 — Conversation branching.** `messageTree` + `◀ n/m ▶` navigator, edit/regenerate as siblings.
- **Dedup & fixes.** All duplicate `MultiAPIChat` method definitions removed; `callChatImageAPI()` now passes `_protocol` (was `null`) to `_parseApiResponse()`.
- **Bugfix during acceptance testing:** `_rawContent` empty-stream guard rewritten (pitfall 4).

## Post-acceptance fixes (2026-10-21)

1. **The agent loop no longer pays for the final answer twice.** `needsSynthesisCall` is now `!finalRoundContent`: the loop's last round already contains the answer, so it is reused. One extra request (without `tools`) happens only when the 5-round tool budget ran out before any answer existed, and it respects `streamMode`.
2. **`processHighcharts()` implemented** (was an empty stub since v4.0.4). It parses `code.language-highcharts` / `language-hc` / `language-chart`, injects a `.highcharts-host` div after the code block and calls `Highcharts.chart()`. Invalid JSON is ignored silently; render errors are caught and logged.
3. **Tool HTTP errors are surfaced.** `/search` and `/web/fetch` now throw on non-2xx so the tool result carries `HTTP <status>: <message>`. A permission-blocked key therefore produces a truthful answer instead of “no results”.

### Verification (3 suites, 71 checks, 0 failures, 0 page errors)

| Suite | Covers |
|---|---|
| 1 (42 checks) | boot, removed/new UI, memory, base-URL rules, branch tree + navigator, profile export/import, agent loop (4 scenarios incl. budget-exhausted synthesis), Gemini 3.x regression |
| 2 (12 checks) | tree persistence + restore in IndexedDB, memory without a persona, `/models` + CORS-proxy resolution, full Gemini SSE stream with `MAX_TOKENS` notice |
| 3 (17 checks) | Highcharts real SVG render, **real** OmniRoute non-stream, **real** SSE stream, **real** agent loop with live `tool_calls` **and live citations** (10 results → 10 citations, all http(s) URLs, inline `[n]` markers, `session.references` populated for the 🔗 panel) |

Real-API notes: tested against OmniRoute (`http://127.0.0.1:20128/v1`, model `Commandcode_cheap`). Verified live: chat completions (stream + non-stream, including keepalive frames and `<think>` blocks), OpenAI-style `tool_calls`, `POST /search` (tavily) and `POST /web/fetch`. One agent turn produced 10 search results and a cited answer.

`/search` and `/web/fetch` are **separate model permissions** on the router. Without them the endpoints answer `403 permission_denied`; the tool-error surfacing added above reports that to the model instead of silently handing it an empty result set, so the answer says “the search endpoint returned HTTP 403 …” rather than “no results found”. If citations stop working, check those permissions first.

Gemini has no live endpoint here (OmniRoute is OpenAI-compatible only); the Gemini path is covered by unit + mocked-SSE tests.

## Deployment

- Push `index.html` to `main` → GitHub Pages rebuilds automatically.
- `worker.js` (Cloudflare Worker) is tracked here but must be deployed to Cloudflare separately.
- Never commit `*.bak-*` (ignored) or `index_v5.0.0.html` (source drop, ignored).
