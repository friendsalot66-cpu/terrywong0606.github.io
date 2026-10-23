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

### DSH task runner in the middleware (2026-10-22)

The llama.cpp middleware (`C:\Users\Terry\Desktop\AI_projects\LLM\middleware`) now exposes
two extra tools, verified end-to-end through the web app:

| Tool | Behaviour |
|---|---|
| `run_dsh_task(task, cwd?)` | spawns `dsh --profile headless --json "<task>"` detached and returns a job id immediately |
| `check_dsh_task(job_id, cancel?)` | status + elapsed + final answer + stderr tail; `cancel=true` kills the process group |

State lives in `$DSH_JOB_DIR` (default `/tmp/dsh_jobs`) as `<id>.json`, `.events.jsonl`, `.err.log`
and `.exit`. gunicorn runs 4 workers, so disk state is what lets a poll handled by a different
worker see the job. **The child writes its exit code to `<id>.exit`, and that file is the only
liveness signal** — the first implementation used `os.kill(pid, 0)`, which succeeds on a zombie,
so a job that finished in 6 s reported "running" forever. The spawner also reaps the child in a
daemon thread, and the whole run is wrapped in `timeout -k 5 N`.

Env knobs: `DSH_ENABLED`, `DSH_NODE`, `DSH_BIN`, `DSH_PROFILE`, `DSH_JOB_DIR`, `DSH_MAX_SECONDS`
(900), `DSH_MAX_CONCURRENT` (2), `DSH_MAX_TASK_CHARS` (8000), `DSH_ALLOWED_ROOTS`
(`/home/erry:/tmp:/mnt/c/Users/Terry`), `DSH_DEFAULT_CWD`, and `DSH_DEPTH` (recursion guard — the
runner refuses to start when it is already 1). `DSH_NODE` **must be node >= 20**: gunicorn's PATH
resolves `node` to v18, so the runner probes `/home/erry/.local/bin/node` and friends by version
instead of trusting PATH.

The headless profile is pointed at a local OpenAI-compatible endpoint by
`~/.dsh/profiles/headless/cordis.patch.yml` (pi-ai provider `local-openai`), configured through
`DSH_LOCAL_BASEURL` / `DSH_LOCAL_API_KEY` / `DSH_LOCAL_MODEL`. llama.cpp ignores the credential but
the provider still requires one, so the runner injects a harmless placeholder when the env var is
absent.

**Sandbox is the real boundary.** DSH's own config sets `sandbox-policy.workspaceRoot =
process.cwd()` (the job's cwd) and approval policy `ask` unless `DSH_PERMISSION_MODE` is
`danger-full-access`. Verified live: a task told to write `/etc/dsh_escape_test.txt` was denied with
`Permission denied`, the escalation failed closed for lack of an approval channel, and the file was
absent afterwards. Keep `DSH_PERMISSION_MODE` at `workspace-write`; never give a headless runner
full access.

Infra note: `middleware.service` now binds `127.0.0.1:5000` (was `0.0.0.0`). WSL runs in
*mirrored* networking, so the Windows browser and the cloudflared tunnel (`originService=http://localhost:5000`)
still reach it, while LAN hosts no longer can. The tunnel itself still publishes the service —
that surface needs Cloudflare Access or a disabled tunnel, not a bind change.

### Terminal sandbox + OmniRoute default route (2026-10-22, round 2)

`run_terminal_command` used to hand model-authored shell to the skill worker, which runs
`subprocess.run(command, shell=True)` as `erry` - an account with **passwordless sudo**. Reachable
through the public tunnel, one prompt injection was full host compromise. It is now wrapped in
`bubblewrap` before it leaves the middleware:

```
bwrap --ro-bind / / --dev /dev --proc /proc
      --bind /tmp /tmp --tmpfs /dev/shm
      --bind <each TERMINAL_SANDBOX_ROOTS + TERMINAL_SANDBOX_RW>
      --ro-bind /tmp/.X11-unix /tmp/.X11-unix
      --tmpfs <each TERMINAL_SANDBOX_MASK>
      --unshare-user --unshare-pid --die-with-parent --new-session
      --chdir <middleware cwd> -- /bin/bash -c "<command>"
```

* defaults - ROOTS `/tmp:/mnt/c/Users/Terry/Desktop/AI_projects:/home/erry/.hermes/projects`,
  RW `/home/erry/.cache/ms-playwright`,
  MASK `/home/erry/.ssh:/home/erry/.omniroute:/home/erry/.dsh:/home/erry/.aws:/home/erry/.config`
* `TERMINAL_SANDBOX=none` disables it; `bwrap` (default) enables it.

Two things that bite:

1. **`--tmpfs` cannot be mounted over a symlink.** `/home/erry/.aws` is a symlink to
   `/mnt/c/Users/Terry/.aws`, so `bwrap: Can't mount tmpfs on /newroot/home/erry/.aws` killed every
   command. The mask list now runs through `os.path.realpath()`.
2. **The sandbox self-tests at startup** (`bwrap ... -- /bin/true`). If that fails the module caches
   a `["!FAILED"]` sentinel and `_execute_terminal_command` **refuses** the command instead of
   running it unsandboxed. Failing closed is the point; `TERMINAL_SANDBOX=none` is the deliberate
   override.

Verified live through the real model: `id -u` -> `1000`; `echo PWN > /etc/sbx2` -> `Read-only file
system` and the file does not exist; `sudo -n id -u` -> fails (`/etc/sudo.conf` owned by 65534, no
privilege escalation); `systemctl --user ...` -> `Failed to connect to bus` (no dbus in the private
namespaces); `/tmp` and the project mount stay writable, so playwright still drives Chromium
(`DISPLAY=:99` via the bind-mounted X socket, `~/.cache/ms-playwright` writable for the daemon).

**DSH route order is now OmniRoute first, llama.cpp second.** `_dsh_spawn(task, workdir, model=,
baseurl=, api_key=, is_fallback=)` centralises spawning, so `check_dsh_task` can start a retry:
when a job ends in `error` with **no** answer text, is not already a fallback, and did not run on
`DSH_FALLBACK_MODEL`, the task is respawned once on `http://127.0.0.1:8080/v1`. The tool result
returns the *new* job id. `DSH_LOCAL_BASEURL` (20128) / `DSH_LOCAL_MODEL` (`Commandcode_cheap`) /
`DSH_FALLBACK_*` live in `middleware.service`; the OmniRoute key lives in
`~/.config/middleware-secrets.env` (0600, pulled in via `EnvironmentFile=`), never in the unit or
the repo.

Measured: the same timestamp task took **18.7 s** on `Commandcode_cheap` vs **45.8 s** on the local
27B - OmniRoute is also the cheaper route because llama.cpp runs `-np 1` and the outer model shares
that single slot. Forced-failure test (bogus primary base URL): primary `error` in 16 s -> automatic
respawn on `Qwen3.8-27B-MTP-Q4_K_M` -> `done` in 15.1 s with `FALLBACK_OK`.

### Auth guard, llama.cpp API key, tunnel posture (2026-10-22, round 3)

**llama.cpp had no authentication at all.** `llama-server.service` never passed `--api-key`, even
though the middleware was sending `Authorization: Bearer <LLAMA_CPP_API_KEY>` to it; llama.cpp accepts any
request when no key is configured, so every probe returned 200 (wrong key, no key). It also listens
on `0.0.0.0:8080`. `--api-key <same value as LLAMA_CPP_API_KEY>` is now in the unit, and
`no key`/`wrong key` both return 401. The key value itself is unchanged - rotating it is
independent of adding the flag, and rotating only matters if a value actually leaked.

**`/tools` used to be anonymous.** It is a complete map of what the host can be made to do, and it
was readable by anyone who found the tunnel URL. It now goes through the same guard as
`/v1/chat/completions`; `/health` stays public but exposes only status, not secrets.

**Auth guard** (`AUTH_RATE_ENABLED`, default on):

| Knob | Default | Meaning |
|---|---|---|
| `AUTH_FAIL_MAX` | 10 | failed credentials per window before lockout |
| `AUTH_FAIL_WINDOW` | 300 s | failure-counting window |
| `AUTH_LOCKOUT_BASE` | 300 s | first lockout; doubles per strike |
| `AUTH_LOCKOUT_MAX` | 86400 s | cap |
| `AUTH_STRIKE_DECAY` | 86400 s | how long a strike is remembered |
| `AUTH_RPM_LIMIT` | 120 | authenticated requests/min/IP (0 = off) |
| `TRUST_PROXY_HEADERS` | 1 | read `CF-Connecting-IP` (needed behind the tunnel) |

Sequence: lockout check -> token check -> rpm counter. A locked IP gets 429 + `Retry-After` even
with the **correct** key. A valid token clears the failure window but **not** an active lockout,
otherwise one lucky guess would wipe the penalty.

**Three bugs this went through, all the same shape as the DSH zombie-pid bug - in-memory state
under a multi-process server:**

1. `_auth_fail`/`_auth_locked` as module dicts. gunicorn runs **4 workers**, so 40 bad attempts
   spread over 4 processes only ever looked like ~10 each and the threshold was never reached.
   Moved to `/tmp/middleware-auth/state.json` (`AUTH_STATE_DIR`).
2. Same for the rpm counter - 130 parallel authenticated requests all returned 200 because each
   worker counted its own share. Fixed with `fcntl.flock` on a sidecar `.lock` file around a
   read-modify-write context manager (`_auth_state_txn`). Verified: exactly **120 x 200, 10 x 429**.
3. `AUTH_STRIKE_DECAY`: pruning deleted the strike counter when the lockout expired, so an attacker
   who waited out 300 s was back to a 300 s penalty forever. Strikes now live in their own map and
   survive expiry. Verified escalation: **300 -> 600 -> 1200 -> 2400 s**.

Also caught in review: an early version of `_auth_record_failure` returned from inside the
`with _auth_state_txn()` block *before* mutating the state, so failures were never persisted and
lockout silently never fired. The transaction commits on normal exit - never `return` out of it
before applying the change.

**Tunnel posture.** `cloudflared-middleware.service` still publishes :5000 and the token is static,
so the guards above cap brute force but do not authenticate a *human* at the edge. IP lockout is
per-`CF-Connecting-IP`, so a botnet rotating IPs still gets `AUTH_FAIL_MAX` guesses each - the only
real fix for that is Cloudflare Access in front of the hostname (dashboard-side; the local
cloudflared is token-based and no API token exists on this machine to script it).

### State persistence + public-surface trimming (2026-10-22, round 4)

**Auth state moved off `/tmp`.** `/tmp` is wiped on reboot, which silently reset every strike
counter and re-armed brute force at the base delay. `AUTH_STATE_DIR` now points at
`/mnt/c/Users/Terry/Desktop/AI_projects/LLM/middleware/.state` (same place as the rest of the
project state, survives reboots). `fcntl.flock` works on the drvfs mount - verified - so the
cross-process transaction is unaffected. Note the directory lands mode 777 because drvfs does not
honour chmod; the file only ever contains SHA-free IP strings and timestamps, no credentials.
Verified: lockout written, `systemctl --user restart middleware`, same IP still got 429.

**Public surface, measured from the internet** (`https://docker-llm.friendsalot66.ccwu.cc`):

| Endpoint | Anonymous | Note |
|---|---|---|
| `/health` | 200 | was leaking masked paths + tool inventory |
| `/tools` | 401 | authenticated since round 3 |
| `/v1/chat/completions` | 401 | authenticated |

`/health` now branches: anonymous callers get `{status, timestamp}` only; an authenticated caller
gets the full inventory. The uptime checker still works; an attacker learns nothing about the host.

**Answers for the record:**

* Doing nothing on Cloudflare is survivable **because of the layers underneath it** - llama.cpp
  rejects anonymous calls (401), `/tools` is closed, `/v1/chat/completions` needs the bearer token,
  wrong guesses lock the IP out exponentially, and shell commands run inside bubblewrap. What
  remains open is: anyone can reach `/health`, anyone can attempt up to `AUTH_FAIL_MAX` guesses per
  IP (`AUTH_RPM_LIMIT` per minute), and a botnet rotating IPs gets a fresh allowance each time.
  Access would close that; it is a dashboard step, not a code step.
* The tunnel hostname is `docker-llm.friendsalot66.ccwu.cc` (from
  `cloudflared`'s ingress config in the journal), origin `http://localhost:5000`.

### DSH turn ended with "[Called tools: check_dsh_task]" (2026-10-23)

Symptom: the web app showed `[Called tools: check_dsh_task]` as the entire answer and stopped,
while the DSH job kept running. Three separate defects stacked up:

1. **`check_dsh_task` returned instantly** (`status: running`), so the model polled it in a tight
   loop, two seconds apart.
2. **The repeat-call breaker treated that poll as a stuck loop.** It hashes tool name + arguments,
   and every poll had identical arguments, so after 2 consecutive rounds it fired
   `forced_fallback` and broke out.
3. **The fallback synthesis produced the empty answer.** It strips `tool_calls` messages and
   replaced them with the synthetic line `[Called tools: ...]`; the model had written no prose in
   those turns, so that line *was* the reply.

Fixes:

* `check_dsh_task` now **blocks until the job settles** (`DSH_POLL_WAIT`, default 240 s;
  `DSH_POLL_INTERVAL` 2 s; per-call `wait_seconds` override, `0` = check immediately). One tool
  call replaces N polls - cheaper too, since every poll re-sends the whole transcript. The tool
  description now says "call it ONCE ... do not poll".
* The repeat signature for `check_dsh_task` is built from **the job's state** (`status`/`exit_code`)
  rather than its arguments, and a round that is waiting on a live job no longer increments the
  duplicate counter at all. Boundedness comes from the iteration budget and `DSH_MAX_SECONDS`.
  A genuine repeat (finished job, same state) is still caught.
* The fallback keeps whatever prose the model wrote next to the tool call instead of emitting only
  the `[Called tools: ...]` marker.

**A fourth defect surfaced underneath it:** the job had `turn_end reason: max-tokens` after
`outputTokens: 8192`. The DSH profile pinned `maxTokens: 8192` for *every* model, but
`Commandcode_cheap` reports `max_output_tokens: 131072` and `context_length: 200000`. The headless
profile now sets 131072 (OmniRoute) and 16384 (local Qwen, which shares llama.cpp's 131072 context
with the prompt). Before this, long tasks silently ran out of output mid-thought and exited 1.

Verified: a two-file task through `dsh --profile headless` completed in **17.4 s** with both files
really created; the full middleware turn returned a normal `finish_reason: stop` in **24.3 s** and
`/tmp/e2e/hello.txt` contained `BANANA`.

### DSH state off /tmp, context length from llama.cpp (2026-10-23, round 2)

**Job records moved out of `/tmp`.** `DSH_JOB_DIR` now defaults to
`$MIDDLEWARE_STATE_DIR/dsh_jobs` = `LLM/middleware/.state/dsh_jobs`, next to the auth state, so a
reboot no longer wipes the history of jobs the user may still be waiting on. Existing records were
copied over; the old `/tmp/dsh_jobs` is ignored from now on.

Moving them exposed a stale-state bug that could never happen while the directory was ephemeral:

* A record says `status: running` long after its process died, and **pids are recycled**, so
  `os.kill(pid, 0)` on a stale pid can succeed against an unrelated process and the job reports
  "running" forever.
* Records now store `boot_id` (`/proc/sys/kernel/random/boot_id`). `_dsh_job_process_alive()`
  requires the **same boot id and a live pid**; a mismatch resolves the record to `error` with
  "the machine or service restarted before it finished" instead of hanging.
* Verified by forging a record with a dead pid and a foreign boot id: it resolved to `error`
  immediately rather than waiting out the 900 s deadline.

**Local context length is read, not guessed.** The profile used to hard-code `16384` for the local
Qwen. `_llama_context_length()` asks llama.cpp for `n_ctx` (`/props` ->
`default_generation_settings.n_ctx`, falling back to `/slots[0].n_ctx`; 5 min cache, then
`DSH_CTX_FALLBACK`). The spawn passes `DSH_LOCAL_CTX` and `DSH_LOCAL_MAXTOK` to the profile, which
interpolates them with `!!js parseInt(...)`.

`DSH_CTX_OUTPUT_FRACTION` (default 0.25) is the important part: llama.cpp runs `-np 1`, so prompt
and generation **share one 131072 window**. Advertising the whole window as `maxTokens` invites a
context overflow, so the output budget is a quarter of it (32768 today).

**Unit env precedence bug, found while wiring this up.** `EnvironmentFile=` is applied *before*
`Environment=`, so a key written inline in the unit silently wins over the secrets file. The
`LLAMA_CPP_API_KEY` / `LLAMA_SWAP_API_KEY` lines are now removed from the unit and live only in
`~/.config/middleware-secrets.env` (0600). Symptom was `_llama_context_length()` hitting 401 and
falling back to the default - correct-looking output from a broken path.

Verified: `llama.cpp reports n_ctx=131072` in the journal; a full DSH turn returned
`finish_reason: stop` in **19.3 s** with `/tmp/final/result.txt` = `PERSIST_TEST`; the record landed
in `.state/dsh_jobs/`.

### The fallback hop was silently dead (2026-10-23, round 3)

Adding `--api-key` to llama.cpp (round 3 of the auth work) broke the DSH fallback route, and nothing
noticed because the primary route kept working. The fallback spawned with
`api_key="local-no-key"`, a placeholder that was harmless *while llama.cpp ignored credentials* and
became a hard 401 the moment it enforced one:

```
dsh: AUTH: 401: {"message":"Invalid API Key",...}
```

Fixes:

* `DSH_FALLBACK_API_KEY` (defaults to `LLAMA_CPP_API_KEY`) is what the fallback hop sends.
* The profile's fallback provider now reads `DSH_FALLBACK_API_KEY`, not `DSH_LOCAL_API_KEY`.
* `DSH_LOCAL_API_KEY` no longer silently falls back to the fallback key; the two routes are distinct
  credentials for distinct endpoints.

**The subtle part:** repointing only the *model id* at the profile's `local-fallback` provider does
nothing, because `agent-default-model` pins `provider: local-openai`. A fallback spawn must repoint
**that provider's base URL and credential together**, which is what `_dsh_spawn(baseurl=, api_key=)`
now does. Symptom of getting this wrong is another 401 even though the key is correct.

Verified end to end: forced-failure test (dead primary base URL) -> primary `error` -> automatic
respawn -> `status: done` in 8.4 s with `AUTOFB_OK`. Primary route unaffected: a full turn created
`/tmp/z/f.txt` = `ZZZ` in 14.1 s with `finish_reason: stop`.

Note on testing this class of bug: running the checks from a plain shell reads *no* systemd
environment, so `DSH_FALLBACK_API_KEY` looks empty and every key-dependent test fails for the wrong
reason. Read the worker's real environment from `/proc/<MainPID>/environ` before concluding
anything.

### Cloudflare 524 through the tunnel (2026-10-23, round 4)

Symptom: the app (served from GitHub Pages) calling the middleware through
`docker-llm.friendsalot66.ccwu.cc` failed with **524**, while the same turn worked on localhost.

Root cause, from the journal: the request entered at `12:49:07` and **never logged a matching
`<<<` line** — Cloudflare closed the connection first. It had taken the non-streaming path
(`stream: false`), so the whole agent loop ran with **zero bytes written to the socket**. The turn
spent 15.8 s on the first llama.cpp call, then ran `run_dsh_task` and `check_dsh_task(…, wait_seconds=300)`,
which alone blocks for five minutes. Cloudflare's idle limit is ~100 s, so 524 was inevitable.

Two independent fixes, because either one alone leaves a hole:

1. **The app no longer takes the non-streaming path when tools are delegated.** The branch
   `useToolsEnabled && protocol === 'openai' && !hasSearchEndpoint()` used to call `callAPI`
   (`stream: false`) whenever `streamMode` was off. It now always calls `streamResponse`, which
   sends `use_tools` *and* `stream: true`. Verified in a real browser: with
   `useTools:true, streamMode:false, hasEndpoint:false` the routing branch calls `streamResponse`
   (it called `callAPI` before).
2. **The stream actually carries traffic now.** `run_agent_loop` had a `progress_queue` parameter
   that **nothing ever wrote to** — the keep-alive in `stream_response` only fires between queue
   reads, so a silent loop produced no frames at all. It now emits progress on every round and tool
   call through `emit_progress()`. Because tool executors are reached through the registry (they get
   only their own arguments), the queue is published via a `threading.local` (`_set_progress_queue`)
   rather than threaded through every call site.
3. `check_dsh_task` emits `[waiting for DSH job <id>... Ns]` every `DSH_HEARTBEAT_SECONDS` (20 s)
   while it blocks, and its default wait dropped 240 s -> `DSH_POLL_WAIT` 90 s so a single tool call
   stays well under the tunnel's idle limit.

Measured **through the real Cloudflare tunnel** with a 50-second DSH task: `http=200`, **80.5 s**
total, 3 keep-alives and 13 progress lines, no 524, and `/tmp/cf/cf.txt` really contained `CFPASS`.
The same test on localhost: 85.5 s, 10 progress lines, 3 keep-alives.

Note: the non-streaming JSON path is kept for direct/local callers, but it is inherently unsafe
behind a proxy with an idle timeout — any tool-using turn there can still be cut off.

### Diagnosing a 524 in one log line (2026-10-23, round 5)

`/v1/chat/completions` now logs, for every turn:

```
mode: tools=True stream=False client=210.6.73.210
```

and adds a warning when a tool-using turn is **not** streaming. That single line
answers the only question that matters when a proxy reports 524: did the client
ask for a stream, and did the request actually come through the tunnel (a real
`CF-Connecting-IP` rather than `127.0.0.1`)? Before this, streaming and
non-streaming tool turns were indistinguishable in the journal, and a turn cut
off by Cloudflare simply had no `<<<` line at all.

Verified both shapes: `stream=True` logs `tools=True stream=True`, and a
`stream=False` tool turn logs both the mode line and the warning. Through the
tunnel the client field shows the public IP.

### Build marker + one-command deploy (2026-10-23)

GitHub Pages serves `index.html` with `cache-control: max-age=600`, and the CDN
also keeps its own copy, so a freshly pushed fix can be invisible for up to ~10
minutes even after `Ctrl+Shift+R`. That made "is the fix live?" indistinguishable
from "the fix does not work".

Every page now carries a build marker:

```js
const BUILD_INFO = { version: 'v5.0.1', build: '20261023-144842',
                     commit: '011e769', deployed: '2026-10-23 14:48' };
```

It surfaces in three places so a stale page is obvious without devtools:

* the header chip next to the title (`v5.0.1 · 20261023-144842`)
* `document.title`
* `window.BUILD_INFO` and a `[BUILD]` line in the console

**Deploy through `code/deploy.sh`, never a bare `git push`** — it stamps the
marker, syntax-checks the inline script, refuses a diff that looks like an API
key, then commits and pushes:

```bash
./code/deploy.sh -m "fix: ..."              # patch bump
./code/deploy.sh -m "feat: ..." --minor
./code/deploy.sh -m "docs: ..."  --no-bump
```

`code/bump_build.py` does the stamping (and owns `code/VERSION`, the semver
source of truth). Verified end to end: after deploy the live page reported
`build: 20261023-144842` in `BUILD_INFO`, the chip, and the title, and the
streaming fix was still present.

Practical rule when a fix "does not work": check the chip first. If it shows the
old build, it is cache, not code.

### Four defects found by auditing a real 15-minute run (2026-10-23, round 6)

A real turn wrote nothing for 15 minutes and ended with `{"type":"final","text":""}`.
The journal showed 38 tool rounds, the last one `cat` on a large HTML file, then silence.

1. **Tool output was unbounded.** `cat` of a ~300 KB HTML file pushed the whole
   thing back into the conversation, and every later round re-sends the history,
   so the prompt grew until each call took minutes. `_execute_terminal_command`
   now truncates to `TERMINAL_OUTPUT_MAX_CHARS` (16000) keeping head **and** tail,
   with an explicit "... N characters omitted ... narrow it with head/tail/grep"
   note so the model retries differently instead of re-running `cat`.
   Verified: a 500 KB file came back as 16142 chars with the notice.
2. **`_dsh_refresh` only ran when someone asked.** A job that died at second 30
   reported `running` until the model polled it or the deadline forced a refresh.
   A daemon `dsh-reaper` thread now settles jobs every `DSH_REAPER_INTERVAL`
   (10 s), independent of any request. Verified: a forged `running` record with
   `exit=0` became `done` in 14 s with nobody polling.
3. **`DSH_MAX_SECONDS` 900 -> 300.** Nothing in the logs ever succeeded after
   ~5 minutes; every 900 s job ended in `timeout` with an empty answer. Failing
   sooner turns a dead end into a visible error.
4. **Concurrency miscounted dead jobs.** `_dsh_active_jobs()` counted anything
   still marked `running`, so a dead job kept `DSH_MAX_CONCURRENT` saturated and
   the next request was refused with "2 DSH task(s) already running". With the
   reaper settling records, the count is now accurate - verified `active jobs: 0`
   after the stuck jobs resolved.

End to end after the fixes: a real DSH turn returned `finish_reason: stop` in
**42.9 s**, 8 progress frames, and `/tmp/e2e2/note.txt` = `HELLO_E2E`.

**Why large single files keep failing (not a bug, a shape problem).** DSH's own
tools are `bash` (243 calls), `read`, `glob`, `grep`, `write`. Asking a model to
emit 300 KB of HTML token by token will always hit an output cap or a context
wall. The fix is delegation, not more tokens: DSH ships
`@deepseek-ai/dsh-tool-subagent` + `dsh-subagent-spawn-in-process`, so a task can
be split into children that each write one part and test it. Not wired into the
headless profile yet - it is a composition change, not a middleware change.

## Deployment

- Push `index.html` to `main` → GitHub Pages rebuilds automatically.
- `worker.js` (Cloudflare Worker) is tracked here but must be deployed to Cloudflare separately.
- Never commit `*.bak-*` (ignored) or `index_v5.0.0.html` (source drop, ignored).
