# PowerShell operator helper: create required directories for Calyx daemon and governance
$paths = @(
  "governance\intents\inbox",
  "governance\intents\outbox",
  "governance\intents\processed",
  "logs\governance",
  "logs\executor",
  "outgoing\shared_logs"
)
foreach ($p in $paths) {
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}
Write-Host "Created directories." 
Write-Host "Processes file location: outgoing\shared_logs\processes.json" 

# Note: this script only creates directories. To run daemon or gate, use python commands in operator shell.
