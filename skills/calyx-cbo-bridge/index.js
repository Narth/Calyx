/**
 * Calyx–CBO bridge skill: get_state, send_to_cbo, sponsorship, execute.
 * Connects OpenClaw (Discord, etc.) to Station Calyx CBO Core and STATE.
 */

const DEFAULT_CBO_BASE = "http://127.0.0.1:7778";

function getBaseUrl(config) {
  const url = config?.cboBaseUrl?.trim?.();
  return url || DEFAULT_CBO_BASE;
}

export default {
  async get_state(params, { config }) {
    const base = getBaseUrl(config);
    try {
      const res = await fetch(`${base}/state`, { method: "GET" });
      if (!res.ok) {
        return {
          success: false,
          error: `CBO Core returned ${res.status}`,
          state_md: null,
        };
      }
      const data = await res.json();
      return {
        success: true,
        state_md: data.state_md || "",
        summary: "Station Calyx STATE (use state_md for full document).",
      };
    } catch (e) {
      return {
        success: false,
        error: e.message || String(e),
        state_md: null,
        hint: "Ensure CBO Core is running (Scripts\\start_calyx_core_services.ps1).",
      };
    }
  },

  async send_to_cbo(params, { config }) {
    const { message, model_role = "workhorse" } = params || {};
    if (!message || typeof message !== "string" || !message.trim()) {
      return { success: false, error: "message is required", reply_text: null };
    }
    const base = getBaseUrl(config);
    const body = {
      user_text: message.trim(),
      session_id: "openclaw_bridge",
      mode: "dev",
      allow_tools: true,
      model_role: model_role.trim().toLowerCase(),
      allow_second_opinion: model_role === "second_opinion",
    };
    try {
      const res = await fetch(`${base}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Calyx-Source": "openclaw_bridge",
        },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        return {
          success: false,
          error: data.detail || `HTTP ${res.status}`,
          reply_text: null,
        };
      }
      return {
        success: true,
        reply_text: data.reply_text ?? "",
        receipt_sha256: data.receipt_sha256 ?? null,
        second_opinion_text: data.second_opinion_text ?? null,
      };
    } catch (e) {
      return {
        success: false,
        error: e.message || String(e),
        reply_text: null,
        hint: "Ensure CBO Core is running (Scripts\\start_calyx_core_services.ps1).",
      };
    }
  },

  async sponsorship(params, { config }) {
    const base = getBaseUrl(config);
    try {
      const res = await fetch(`${base}/sponsorship`, { method: "GET" });
      if (!res.ok) {
        return {
          success: false,
          valid: false,
          error: `CBO Core returned ${res.status}`,
        };
      }
      const data = await res.json();
      return {
        success: true,
        valid: data.valid ?? false,
        reason: data.reason ?? "",
        proposal_id: data.proposal_id ?? null,
      };
    } catch (e) {
      return {
        success: false,
        valid: false,
        error: e.message || String(e),
        hint: "Ensure CBO Core is running (Scripts\\start_calyx_core_services.ps1).",
      };
    }
  },

  async execute(params, { config }) {
    const { task_type = "doc_update", scope, constraints, intent_summary } = params || {};
    const base = getBaseUrl(config);
    const body = {
      task_type: task_type.trim(),
      scope: scope || null,
      constraints: constraints || null,
      intent_summary: (intent_summary || "").trim() || null,
    };
    try {
      const res = await fetch(`${base}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        return {
          success: false,
          error: data.detail || `HTTP ${res.status}`,
          envelope_id: null,
          processed: 0,
          denied: 0,
        };
      }
      return {
        success: true,
        envelope_id: data.envelope_id ?? null,
        intent_id: data.intent_id ?? null,
        processed: data.processed ?? 0,
        denied: data.denied ?? 0,
      };
    } catch (e) {
      return {
        success: false,
        error: e.message || String(e),
        envelope_id: null,
        processed: 0,
        denied: 0,
        hint: "Ensure CBO Core is running (Scripts\\start_calyx_core_services.ps1).",
      };
    }
  },
};
