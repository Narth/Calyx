# Grok External Node Spec v0.1

## 0. Purpose

Define Grok as a governed external LLM node within Station Calyx, with strictly bounded capabilities, explicit logging, and CP14-R / CP18-R oversight.

This spec treats Grok as a *tool*, not an authority: advisory-only, no direct control over Station internals.

---

## 1. Identity

- node_id: GROK-EXT-01
- node_role: external_llm_grok4
- node_class: external_tool
- substrate: remote_API (xAI Grok)
- authority: advisory-only, no autonomy, no scheduling

---

## 2. Transport & API

- transport: HTTPS
- base_url: `https://api.x.ai`
- primary endpoint: `/v1/chat/completions` (or equivalent current Grok chat endpoint)
- auth: Bearer token stored in local secure config (never logged in plaintext)
- timeout: 30s (configurable, default 30)

### 2.1 Request Shape (conceptual)

```jsonc
{
  "model": "grok-4",
  "messages": [
    { "role": "system", "content": "<system_prompt>" },
    { "role": "user", "content": "<task_prompt>" }
  ]
}
