#!/usr/bin/env pwsh
<##
Diagnostic launcher for Clawdbot gateway.

Usage:
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\launch_gateway.ps1

This script verifies Node and the installed Clawdbot entry point, then
launches the gateway and captures stdout/stderr to a temp log for inspection.
#>

function Write-Log($s){ Write-Host "[diag] $s" }

$nodePaths = @("C:\Program Files\nodejs\node.exe", "C:\Program Files (x86)\nodejs\node.exe")
$node = $null
foreach($p in $nodePaths){ if(Test-Path $p){ $node = $p; break } }
if(-not $node){
    Write-Log "node.exe not found at standard locations; trying 'node' from PATH"
    try{ $ver = & node -v 2>$null; if($LASTEXITCODE -eq 0){ $node = "node" } } catch { }
}
if(-not $node){ Write-Log "ERROR: node executable not found. Install Node.js or adjust PATH."; exit 2 }

$entry = Join-Path $env:APPDATA "npm\node_modules\clawdbot\dist\entry.js"
if(-not (Test-Path $entry)){
    Write-Log "ERROR: Clawdbot entry.js not found at $entry"
    Write-Log "Verify 'npm install -g clawdbot' succeeded and gateway.cmd references the correct path.";
    exit 3
}

$port = 18789
$log = Join-Path $env:TEMP "clawdbot-run.log"
if(Test-Path $log){ Remove-Item $log -Force }

Write-Log "Node: $node"
Write-Log "Entry: $entry"
Write-Log "Starting gateway on port $port; logging to $log"

# Launch gateway in a new PowerShell window so output/exit do not affect this session.
# The child window will run the node command and tee output into the log file.
$psCmd = "& `"$node`" `"$entry`" gateway --port $port 2>&1 | Tee-Object -FilePath `"$log`""
Write-Log "Launching gateway in new window with command: $psCmd"
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-NoExit","-Command",$psCmd -WindowStyle Normal
Write-Log "Launcher started a new PowerShell window for the gateway. Log will be written to: $log"
