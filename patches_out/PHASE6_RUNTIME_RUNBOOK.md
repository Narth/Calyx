# Phase 6 — Runtime verification runbook (PowerShell)

**Source:** Directive planning guide (CGPT). Adapted for Station Calyx: request body uses **`user_text`** (not `message`). Copy-paste in order.

**Keep this runbook beside STATE.md** so future you (or another node) can reproduce the full validation ladder without rethinking it.

---

## 0) Preconditions (fast sanity)

From `C:\Calyx_Terminal` with `.venv_cbohub311`:

```powershell
cd C:\Calyx_Terminal
git status
```

**Expect:** clean or only the patch-applied changes you intended.

Confirm services are up:

* Dev Harness: http://127.0.0.1:7777  
* CBO Core: http://127.0.0.1:7778  

---

## 1a) Optional: Local LLM (Ollama) env vars

In the terminal you start CBO Core from (so the process inherits them):

```powershell
$env:LOCAL_LLM_BASE_URL = "http://127.0.0.1:11434"   # default
$env:LOCAL_LLM_MODEL_ID = "llama3.2"                 # or qwen2.5-coder:7b, etc.; required for model_role=local
```

Start Ollama first (`ollama serve` or the Ollama app). Then `model_role=local` will call the local model; receipt has `local_receipt` (provider, base_url, model_id, http_status).

---

## 1b) Set Kimi env vars (once per session)

In the terminal you’ll start CBO Core from:

```powershell
$env:KIMI_BASE_URL = "https://api.moonshot.ai/v1"
$env:KIMI_API_KEY = "<REDACTED>"
$env:KIMI_MODEL_ID = "<PASTE_FROM_MOONSHOT_DASHBOARD_OR_/models>"
```

If you use `MOONSHOT_API_KEY` instead, set that; one key is enough.  
**Important:** `KIMI_MODEL_ID` must be set for successful Kimi calls (no fallback).

---

## 2) Start both services

Start Dev Harness on 7777 and CBO Core on 7778 the way you normally do (no change to your workflow).

---

## 3) Helper — POST JSON to /chat (use `user_text`)

```powershell
function Post-CalyxChat($payload) {
  $json = $payload | ConvertTo-Json -Depth 20
  Invoke-RestMethod -Method Post `
    -Uri "http://127.0.0.1:7778/chat" `
    -ContentType "application/json" `
    -Body $json
}
```

**Note:** CBO Core expects **`user_text`** for the user message, not `message`.

---

## 4) The 4 acceptance tests (Phase 6)

### Test 1 — second_opinion disabled (no spend)

```powershell
$resp = Post-CalyxChat @{
  user_text = "Return ONLY: {""tool_requests"":[{""tool"":""repo_search"",""params"":{""query"":""STATE.md"",""max_hits"":5}}]}"
  model_role = "second_opinion"
  allow_second_opinion = $false
  allow_tools = $true
}
$resp
```

**Expect:**

* HTTP 200  
* Response includes a clear “second_opinion disabled” message  
* `second_opinion_text` present and indicates disabled  
* Receipt has `second_opinion_receipt.called: false`  
* **No** Kimi HTTP 200 (Kimi was not called)  

If a Kimi call happens here, that violates “no silent spend.”

---

### Test 2 — second_opinion enabled + Kimi called once

```powershell
$resp = Post-CalyxChat @{
  user_text = "Briefly summarize what the system can do right now. Cite STATE.md in your reasoning."
  model_role = "second_opinion"
  allow_second_opinion = $true
  allow_tools = $false
}
$resp
```

**Expect:**

* HTTP 200  
* `second_opinion_text` contains Kimi output  
* Receipt `second_opinion_receipt` has:  
  * `called: true`  
  * `provider: kimi`  
  * `base_url: https://api.moonshot.ai/v1`  
  * `model_id: <your KIMI_MODEL_ID>`  
  * `http_status: 200`  
  * `request_id` (if Moonshot returns it)  
* Only one Kimi call per request (receipt makes this clear)

---

### Test 3 — Missing KIMI_MODEL_ID → readable error (no crash)

Unset model id:

```powershell
Remove-Item Env:KIMI_MODEL_ID -ErrorAction SilentlyContinue
```

Then:

```powershell
$resp = Post-CalyxChat @{
  user_text = "Say hello."
  model_role = "second_opinion"
  allow_second_opinion = $true
  allow_tools = $false
}
$resp
```

**Expect:**

* HTTP 200 (not 500)  
* Readable error telling you to set `KIMI_MODEL_ID`  
* Receipt has `error_snippet` with that instruction  
* `called` false (or true with error) — either is fine if explicit and receipt-backed  

Restore:

```powershell
$env:KIMI_MODEL_ID = "<YOUR_MODEL_ID>"
```

---

### Test 4 — Tool loop for second_opinion (read-only)

```powershell
$resp = Post-CalyxChat @{
  user_text = "Output ONLY valid JSON in this exact shape: {""tool_requests"":[{""tool"":""repo_search"",""params"":{""query"":""STATE.md"",""max_hits"":5}}]}"
  model_role = "second_opinion"
  allow_second_opinion = $true
  allow_tools = $true
}
$resp
```

**Expect:**

* HTTP 200  
* Tool loop runs `repo_search`  
* Response includes appended tool results (tool_notes)  
* Receipt:  
  * `executed_tools` includes `"repo_search"`  
  * `tool_calls` has full call details  
  * Caps intact (e.g. max_hits ≤ 200)  

If tools don’t run: check `allow_tools`, tool JSON parser (expects JSON block), and Dev Harness `/repo/search` on 7777.

---

## 5) Test 5 — Workhorse tool eligibility (expanded loop)

```powershell
$resp = Post-CalyxChat @{
  user_text = "Output ONLY: {""tool_requests"":[{""tool"":""repo_list"",""params"":{""path"":""."",""max_entries"":20}}]}"
  model_role = "workhorse"
  allow_tools = $true
}
$resp
```

**Expect:**

* `repo_list` runs  
* `executed_tools` includes `"repo_list"`  

Confirms tool loop is not architect-only.

---

## 6) If Kimi fails — use the receipt

Receipt fields tell you which bucket:

* `http_status: 401/403` → key / permission / billing  
* `http_status: 404` → base_url or path (you’re on `/chat/completions`; base URL is the usual suspect)  
* `http_status: 429` → rate limit  
* Network exception, no status → connectivity / TLS / proxy  

Moonshot docs often cite base_url correctness for “model not found” / 404 with OpenAI-compatible clients.

---

## 7) Kimi happy-path smoke test (final “third voice is online” proof)

Run **in the same terminal session you start CBO Core from** so env is inherited. Set the three vars once, then start CBO Core:

```powershell
$env:KIMI_BASE_URL = "https://api.moonshot.ai/v1"
$env:KIMI_API_KEY  = "<REDACTED>"
$env:KIMI_MODEL_ID = "<YOUR_KIMI_MODEL_ID>"
# Then start CBO Core on 7778 (e.g. uvicorn cbo_hub.cbo_core.app:app --host 127.0.0.1 --port 7778)
```

Single call (keep it simple — no tools):

```powershell
$resp = Post-CalyxChat @{
  user_text = "Confirm you're receiving STATE.md context. Summarize the Allowed vs Forbidden sections in 5 bullets."
  model_role = "second_opinion"
  allow_second_opinion = $true
  allow_tools = $false
}
$resp
```

**Success:**

* Receipt: `second_opinion_receipt.called: true`, `http_status: 200`
* `second_opinion_text` is a real answer (not the KIMI_MODEL_ID / API error string)

That’s the final proof that the third voice is truly online.

---

## 8) Manual 3-call workflow (workhorse → architect → second_opinion)

Explicit spend, no automation creep. Triangulate with three calls and feed outputs manually into the next.

### Call A — Workhorse (tools allowed)

Gather repo facts via tool_requests, then a short plan.

```powershell
$A = Post-CalyxChat @{
  user_text = "Use repo_search to find where tool loop parsing and STATE.md injection live. Use repo_list if needed. Output tool_requests JSON only. After tools run, give a 10-line plan for next Phase."
  model_role = "workhorse"
  allow_tools = $true
}
$A.reply_text   # use in Call B
```

### Call B — Architect (tools allowed)

Pressure-test workhorse plan + tool outputs; choose next step.

```powershell
$B = Post-CalyxChat @{
  user_text = "Given the workhorse's findings and tool outputs below, pick the next Phase 6b/6c step that maximizes safety per token. Output: risks, mitigations, and an acceptance test checklist.

WORKHORSE REPLY:
$($A.reply_text)"
  model_role = "architect"
  allow_tools = $true
}
$B.reply_text   # use in Call C
```

### Call C — Second opinion (explicit spend; tools optional)

Audit architect decision; use tools only if you want repo verification.

```powershell
$C = Post-CalyxChat @{
  user_text = "Audit the architect's plan for hidden spend, boundary violations, or missing acceptance tests. If you need repo facts, emit tool_requests JSON; otherwise respond normally.

ARCHITECT REPLY:
$($B.reply_text)"
  model_role = "second_opinion"
  allow_second_opinion = $true
  allow_tools = $true   # set $false if no repo check needed
}
$C.reply_text
$C.second_opinion_text
```

Receipts for A, B, C give you a clear audit trail for the full triangulation.

**Local-first variant (local is wired):** You can run **Call A with model_role=local** (and `allow_tools=true`) to gather repo facts via Ollama first, then feed that into architect or workhorse. Same pattern; keeps offline-capable path.

---

## 9) Spend summary in receipts (implemented)

Each receipt now includes:

* `providers_called`: e.g. `["anthropic"]` or `["local"]` — which provider(s) were actually invoked this request
* `second_opinion_enabled`: `true` / `false` from the request

Scan the receipt line to see who was called without reading the full blob.

---

## 10) Three-voice pattern (no auto-spend)

* First request: `/chat` with `model_role="workhorse"` (or architect).  
* For a second opinion: second request with `model_role="second_opinion"` and `allow_second_opinion=true`.  
* Use `second_opinion_text` in a follow-up architect/workhorse call **only when you explicitly decide to**.  

That keeps “no silent model spending” while allowing multi-voice deliberation.

---

**Validation ladder (order):** 0 → 1a (optional local) → 1b → 2 → … → 5 (acceptance tests) → 7 (Kimi happy-path). Then 8 (3-call workflow) when you want triangulation.

**Local smoke test:** With Ollama running and `LOCAL_LLM_MODEL_ID` set, run: `Post-CalyxChat @{ user_text = "Say hello."; model_role = "local"; allow_tools = $false }` → expect 200 and local model reply; receipt has `local_receipt.http_status: 200`.

**On failure:** Share the response (keys redacted) and the relevant receipt snippet for a surgical fix (base_url, model_id, gating, parser, or dev harness).

**Reference:** Exact payloads and results for Tests 1–5 are in `patches_out/PHASE6_TEST_RUN_RESULTS.md`.
