/**
 * Calyx Governance Plugin — WO_OPENCLAW_UNIFIED_EXECUTOR
 *
 * OpenClaw cannot be modified to route all messages to CBO — the message:received
 * hook cannot suppress the native LLM. For governed Discord, use the harness:
 *
 *   .\Scripts\start_station_governed.ps1
 *
 * That script uses Calyx Discord Gateway (Discord → CBO only) and stops OpenClaw
 * from owning Discord. No activity reaches this machine without Station vetting.
 */
export default function register(api: { logger?: { warn: (s: string) => void } }) {
  api.logger?.warn?.(
    "[calyx-governance] Discord via OpenClaw does NOT route to CBO. For governed Discord, run: Scripts\\start_station_governed.ps1"
  );
}
