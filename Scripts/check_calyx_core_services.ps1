# Probe Calyx CBO Hub core/support services (7777, 7778, 7780, 7781) and output checks for STATE.md / metrics.
# Authority labels are emitted by sunrise, STATE, heartbeat, service snapshot, and topology surfaces; this probe keeps the legacy checks line stable for callers.
# Usage: .\Scripts\check_calyx_core_services.ps1
# Output: checks line e.g. dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok (or =fail)
# Hardened: 3s timeout per port so we never hang; exit code 0 only when all ok.

$ConnectTimeoutMs = 3000
# cbo_core = CBO (Calyx Bridge Overseer) — orchestrator for Station Calyx
$ports = @{ 7777 = "dev_harness"; 7778 = "cbo_core"; 7780 = "avatar_web"; 7781 = "telemetry_gateway" }
$results = @()
foreach ($p in $ports.Keys | Sort-Object) {
    $name = $ports[$p]
    $conn = New-Object System.Net.Sockets.TcpClient
    try {
        $ar = $conn.BeginConnect("127.0.0.1", $p, $null, $null)
        $ok = $ar.AsyncWaitHandle.WaitOne($ConnectTimeoutMs, $false)
        if ($ok) {
            $conn.EndConnect($ar)
            $results += "$name=ok"
        } else {
            $results += "$name=fail"
        }
    } catch {
        $results += "$name=fail"
    } finally {
        try { $conn.Close() } catch { }
        try { $conn.Dispose() } catch { }
    }
}
$line = $results -join ","
Write-Output $line
# Exit 0 only if all ok (callers can use this for automation)
$allOk = ($results | Where-Object { $_ -match "=ok$" }).Count -eq $ports.Count
exit $(if ($allOk) { 0 } else { 1 })
