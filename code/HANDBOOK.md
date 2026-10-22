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
`custom_providers`, `<providerId>_api_key`, `cors_proxy_url`, `currentAPI`, `currentModel`, `currentPersona`, `theme`, `streamMode`, `maxTokens`, `showReferences`, `oneShotMode`, `useToolsEnabled`, `maxToolRounds`, `user_memory` (≤2000 chars), `memory_enabled`, `saved_personas`, `saved_shortcuts`, `saved_chats`, `activeSessionId`.

**Removed keys:** `feedback_loops`, `feedbackMode`, `localTools`, `localLinks`, `nim_settings`, `pplx*`, `moonshot*`, `perplexity_api_key`, `moonshot_api_key`, `openrouter_api_key`, `nvidia_api_key`.

## Core Method Map (v5.0.0, measured)

### Conversation tree / branching (new in v5.0.0)
| Method | Line | Purpose |
|---|---|---|
| `ensureSessionTree(session)` | 4250 | Migrate flat `messages` → tree (idempotent; reuses `m.id`) |
| `recomputeActiveMessages(session)` | 4304 | Walk root → `activeChildIndex` chain, rebuild `session.messages` + `references` |
| `appendMessageNode(session, msgData, parentId?)` | 4345 | Add a node under `currentLeafId` (or explicit parent), activate it |
| `switchBranch(nodeId, delta)` | 4380 | Cycle siblings; **call with the node currently displayed** (UI contract, see 4576) |
| `regenerateResponse(nodeId)` | 4408 | 🔄 on an assistant node → new sibling assistant node |
| `_generateFromUserNode(sessionId, userNodeId)` | 6194 | Edit "Save & Regenerate" / regenerate entry point |
| `scrollToAdjacentUserPrompt(dir)` | 4496 | ⬆⬇ jump between user prompts |

### Messaging
| Method | Line | Purpose |
|---|---|---|
| `sendUserMessage()` | 6293 | Validate, push user node, dispatch |
| `omniRouteAgenticCall(sessionId, parentNodeId?)` | 5834 | Multi-turn agent loop (web_search / web_fetch, max 5 rounds) |
| `streamResponse(msg, pre, sessionId, parentNodeId?)` | 6656 | SSE streaming |
| `callAPI(msg, pre, sessionId)` | 6535 | Non-streaming request |
| `callChatImageAPI(prompt, params, sessionId)` | 6487 | Image generation (passes `_protocol` to `_parseApiResponse`) |
| `buildMessagesForAPI(pre, upToNodeId?)` | 6620 | Build payload; appends `[User Memory]` and slices to the active path |

### Session / persistence
| Method | Line | Purpose |
|---|---|---|
| `createNewSession()` | 4433 | New tab |
| `switchSession(id)` | 4451 | Switch tab (sets `activeSessionId` **and** `currentChatId`) |
| `closeSession(id)` | 4526 | Delete tab |
| `forkConversation()` | 4710 | Duplicate session |
| `loadChat(id)` | 7141 | Restore from IndexedDB (restores `messageTree`) |
| `autoSaveChat()` | 7326 | Save — **keys on `this.currentChatId`**, not `activeSessionId` |
| `saveCurrentChat()` | 7362 | Save with a custom name |
| `persistSessionState()` | 3059 | Persist a non-active session |

### Settings / memory / profile
| Method | Line | Purpose |
|---|---|---|
| `openAddProviderModal(editId?)` | 3323 | Provider form + **Base URL validation/normalisation** |
| `addCustomProvider(cfg)` | 3212 | Persist a new provider |
| `saveMemory()` / `clearMemory()` | 4793 / 4806 | 🧠 global memory (2000-char cap) |
| `updateMemoryToggleIcon()` | 4834 | Active state of the 🧠 button |
| `exportProfile()` | 5405 | Selective JSON export (6 checkbox sections) |
| `handleImportProfileFile(file)` | 5485 | File picker → parse |
| `applyImportedProfile(data)` | 5503 | Restore selected sections |

### API protocol layer
| Method | Line | Purpose |
|---|---|---|
| `hasSearchEndpoint(id?)` | 3610 | True only when the provider declares `useCustomSearchEndpoint` + `customSearchBaseUrl` |
| `_fetchRetry429(url, opts, n=2)` | 3619 | Re-send on HTTP 429 honouring `Retry-After` (capped at 20s) |
| `_getProviderProtocol()` | 3633 | `openai` / `gemini` / `anthropic` from `cp.apiProtocol` |
| `_buildApiUrl(base, model, protocol, isStream)` | 3639 | Strips `/chat/completions` / `/messages`; appends the right path |
| `_buildHeaders(protocol, key)` | 3655 | `Authorization: Bearer` / `x-goog-api-key` / `x-api-key` |
| `_transformBody(body, msgs, protocol)` | 3674 | Provider payload; **model-family aware for Gemini** |
| `_finishReasonNotice(reason)` | 3784 | finishReason → human-readable warning |
| `_parseApiResponse(data, protocol)` | 3800 | Non-streaming parse |
| `_parseStreamLine(line, protocol, state)` | 3865 | One SSE line → `{content, reasoningContent, finishReason, blockReason, error, ...}` |

### UI
`renderMessages()` 4586 · `renderEnhancedMarkdown(text)` 4878 · `showStatus(msg,type)` 5768 · `updateHeaderStatus()` 5321 · `updateTokenEstimate()` 6947 · `updateMaxTokens(v)` 7265 · `updateMaxToolRounds(v)` 7250 · `processHighcharts(el)` 7084 (renders ```highcharts/chart/json``` + ```html/js``` containing `Highcharts.chart(...)`) · `processTables(el)` 7116.
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

`omniRouteAgenticCall()` posts to `{chatUrl}` with `tools: [web_search, web_fetch]`, `tool_choice: 'auto'`, up to **`maxToolRounds`** rounds (default **3**, Settings → Max tool rounds).

**Gating (v5 patch):** the agent loop only runs when `hasSearchEndpoint()` is true — i.e. the active custom provider has `useCustomSearchEndpoint` **and** a `customSearchBaseUrl`. Without it the message falls back to a normal streamed answer and a one-time notice appears. The tool endpoints are never guessed from `{baseUrl}`.

**Provider-side tool loops (`use_tools`):** every chat request also carries `use_tools: <tool toggle>`. An endpoint that owns its own agent — e.g. a middleware in front of llama.cpp that ships `web_search` / `run_terminal_command` / playwright tools, forces `stream:false` upstream to read `tool_calls`, then re-streams the result — reads that flag and runs its own loop. For that setup: keep the 🛠 toggle **on**, leave the in-app Custom Search endpoint **empty**, and the app stays on the plain streamed path; the notice reads “tool calls are delegated to your provider”. The app's `maxToolRounds` does not apply there — the middleware has its own round cap. Tool endpoints: `POST {searchBase}/search` `{query, max_results}` → `{results|data|organic:[{url,title,snippet}]}`; `POST {searchBase}/web/fetch` `{url}` → `{content|markdown|text}`. `searchBase` = the provider's `customSearchBaseUrl` when `useCustomSearchEndpoint` is on, else the provider base. Tool steps accumulate into `toolLogMarkdown` and are wrapped in `<details class="tool-collapse">`; citations land on the assistant node (`citations[]` = URLs, `searchResults[]` = `{name,title,url,snippet}`) which feeds the 🔗 References panel.

**Final round:** the loop's last non-streaming round already contains the answer, so it is **reused** — one tool turn costs 2 chat calls, and `streamMode` does not add a request. Only when the `maxToolRounds` budget runs out before any answer exists does the code make **one** extra synthesis request (without `tools`), honouring `streamMode`. Worst case per turn is therefore `maxToolRounds + 1` model requests — keep it at 4 or lower if the model allows only 5 requests/minute. Tool HTTP errors (non-2xx) are thrown so the message reaches the model, e.g. “web_search returned HTTP 403: Model \"search\" is not allowed for this API key”.

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
8. **Tools require a declared search endpoint.** `hasSearchEndpoint()` must be true before `omniRouteAgenticCall()` runs. The old code fell back to `{baseUrl}/search`, which meant **every** OpenAI-compatible provider silently ran a tool loop that could only 404. `useToolsEnabled` now persists in localStorage and **defaults to off**.
   **But** each request also carries `use_tools`, so a provider-side agent (middleware) still receives the flag and runs its own tools on the plain path — do not treat a missing in-app endpoint as “no tools”.
9. **Charts:** models do **not** emit a ```highcharts``` JSON fence — verified against a live router, they return a full ```html``` page containing `Highcharts.chart('container', {...})`. `processHighcharts()` handles both: it extracts the options object, converts the JS literal to JSON (`_jsLiteralToJson`) and calls `Highcharts.chart()` on an injected `.highcharts-host` div. **Model JavaScript is never executed** — anything containing `function`, `=>`, `new`, `document.`, `window.`, `eval`, `import` or `require` is rejected.
10. **Agent-loop tool HTTP errors must reach the model.** `/search` and `/web/fetch` used to be parsed without checking `res.ok`, so a 403 looked like an empty result set and the model answered “search found nothing”. They now throw and the reason lands in the tool result. Keep that behaviour.
11. **A model with a per-minute request cap needs a round budget.** One agent turn costs `maxToolRounds + 1` chat requests. The default of 3 keeps a 5 rpm model usable (4 requests/turn). `_fetchRetry429()` retries 429s using `Retry-After` (max 20s, 2 retries) in the agent loop; `callAPI`/`streamResponse` surface the header instead of retrying.
12. After any patch: extract the inline script → `node --check`, then run the Playwright suites. Static scanning alone will not catch DOM/null regressions.

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

### Verification (4 suites, 83 checks, 0 failures, 0 page errors)

| Suite | Covers |
|---|---|
| 1 (42 checks) | boot, removed/new UI, memory, base-URL rules, branch tree + navigator, profile export/import, agent loop (4 scenarios incl. budget-exhausted synthesis), Gemini 3.x regression |
| 2 (12 checks) | tree persistence + restore in IndexedDB, memory without a persona, `/models` + CORS-proxy resolution, full Gemini SSE stream with `MAX_TOKENS` notice |
| 3 (17 checks) | Highcharts real SVG render, **real** OmniRoute non-stream, **real** SSE stream, **real** agent loop with live `tool_calls` **and live citations** (10 results → 10 citations, all http(s) URLs, inline `[n]` markers, `session.references` populated for the 🔗 panel) |
| 4 (12 checks) | tool gating (no `/search` without a declared endpoint + streamed fallback), `maxToolRounds` honoured, 429 `Retry-After` retry, Highcharts from a real ```html``` answer (SVG + 4 bars) and rejection of model JavaScript |

Real-API notes: tested against OmniRoute (`http://127.0.0.1:20128/v1`, model `Commandcode_cheap`). Verified live: chat completions (stream + non-stream, including keepalive frames and `<think>` blocks), OpenAI-style `tool_calls`, `POST /search` (tavily) and `POST /web/fetch`. One agent turn produced 10 search results and a cited answer.

`/search` and `/web/fetch` are **separate model permissions** on the router. Without them the endpoints answer `403 permission_denied`; the tool-error surfacing added above reports that to the model instead of silently handing it an empty result set, so the answer says “the search endpoint returned HTTP 403 …” rather than “no results found”. If citations stop working, check those permissions first.

Gemini has no live endpoint here (OmniRoute is OpenAI-compatible only); the Gemini path is covered by unit + mocked-SSE tests.

## Patch round 2 (2026-10-21) — tool gating, round budget, 429, Highcharts

Triggered by three reports:

1. **Tools fired for every provider.** `useToolsEnabled` was hard-coded `true`, never persisted, and the dispatch checked only `protocol === 'openai'`, so any custom OpenAI-compatible provider ran the agent loop and POSTed to `{baseUrl}/search` (404 on real APIs). Now: persisted toggle (default **off**), `hasSearchEndpoint()` gate, no `{baseUrl}` fallback, and a streamed fallback + toast when tools are on but unconfigured.
2. **5-requests-per-minute model budget.** Added the **Max tool rounds** slider (1–10, default **3**, `localStorage.maxToolRounds`). A turn costs at most `rounds + 1` model requests. `_fetchRetry429()` retries HTTP 429 using `Retry-After` (capped at 20s, 2 retries) inside the agent loop; `callAPI`/`streamResponse` now include `Retry-After` in the error text and point at the slider.
3. **Highcharts looked broken.** The renderer only accepted a ```highcharts``` JSON fence, but models actually answer with a full ```html``` page calling `Highcharts.chart('container', {...})`. The renderer now extracts the options object from the call, converts the JS literal to JSON (bare keys, single quotes, comments, trailing commas) and renders it — without ever evaluating model JavaScript.

### Verification

83 checks across 4 suites, 0 failures, 0 page errors (see the table above). Live model output for prompt “render a bar chart with Highcharts” was captured and used verbatim as the Highcharts regression fixture.

### Patch round 3 (2026-10-21) — provider-side tools

A llama.cpp setup behind a middleware (middleware :5000 → skill-worker :5001 → llama.cpp :8080) exposed a wording bug: the middleware decides everything from the `use_tools` field the app already sends, and owns its own tool registry (it overwrites any `tools` the client sends). For that architecture the app's in-app search endpoint is unnecessary, so the old “Tools skipped: no Custom Search endpoint configured” toast was wrong and fired on every message.

Now: the notice reads “No in-app search endpoint - tool calls are delegated to your provider” and fires **once per page load**. Behaviour is unchanged — the app still sends `use_tools: <toggle>` on both the streaming and non-streaming paths, so a provider-side agent keeps working with the toggle on and no configured endpoint.

**Verified live** against that setup (middleware `:5000` → skill-worker `:5001` → llama.cpp `:8080`, Qwen3.8-27B):

| App state | Request sent | Result |
|---|---|---|
| 🛠 off | `use_tools:false, stream:true, tools:0` | plain answer in **1.6 s** (middleware fast path) |
| 🛠 on, no in-app endpoint | `use_tools:true, stream:true, tools:0` | middleware ran `run_terminal_command`; a real `date -u` value (1 s from wall clock) reached the app in **3.0 s** |

Only `POST /v1/chat/completions` is ever called — the app never invents a `/search` path for such a provider, and it never sends its own `tools` definitions in that mode (the middleware ships its own registry and overwrites `data["tools"]` anyway). The delegation notice appeared exactly once.

## Deployment

- Push `index.html` to `main` → GitHub Pages rebuilds automatically.
- `worker.js` (Cloudflare Worker) is tracked here but must be deployed to Cloudflare separately.
- Never commit `*.bak-*` (ignored) or `index_v5.0.0.html` (source drop, ignored).
