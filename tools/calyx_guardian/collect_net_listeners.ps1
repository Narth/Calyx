param(
    [string]$OutDir = "logs\calyx_guardian"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$EvidencePath = Join-Path $OutDir "evidence.jsonl"

function Get-Sha256([string]$Text){
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $hashBytes = $sha256.ComputeHash($bytes)
    ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

# Collect listener info
$tcp = @()
try {
    $tcp = Get-NetTCPConnection -State Listen -ErrorAction Stop | Select-Object LocalAddress,LocalPort,OwningProcess
} catch {
    $tcp = @()
}
$udp = @()
try {
    $udp = Get-NetUDPEndpoint -ErrorAction Stop | Select-Object LocalAddress,LocalPort,OwningProcess
} catch {
    $udp = @()
}

$procMap = @{}
$ids = @($tcp | ForEach-Object { $_.OwningProcess }) + @($udp | ForEach-Object { $_.OwningProcess }) | Where-Object { $_ -ne $null } | Select-Object -Unique
foreach ($id in $ids) {
    try {
        $p = Get-Process -Id $id -ErrorAction Stop | Select-Object Id, ProcessName, Path
        $procMap[$id] = $p
    } catch {
        $procMap[$id] = @{ Id = $id; ProcessName = "<unknown>"; Path = "" }
    }
}

# Convert process map to an array with string keys to avoid ConvertTo-Json errors
$procList = @()
foreach ($k in $procMap.Keys) {
    $entry = [ordered]@{
        Id = [string]$k
        ProcessName = ($procMap[$k].ProcessName -as [string])
        Path = ($procMap[$k].Path -as [string])
    }
    $procList += $entry
}

$payload = [ordered]@{
    tcp_listeners = $tcp
    udp_listeners = $udp
    processes = $procList
}
$rawOutput = ($payload | ConvertTo-Json -Compress -Depth 6)
$rawHash = Get-Sha256 $rawOutput
$rawPreview = if ($rawOutput.Length -gt 800) { $rawOutput.Substring(0,800) } else { $rawOutput }

# Get host_id from existing evidence if available
$hostId = ""
if (Test-Path $EvidencePath) {
    try {
        $firstLine = Get-Content -Path $EvidencePath -Encoding utf8 -TotalCount 1 -ErrorAction Stop
        if ($firstLine) {
            $parsed = $null
            try { $parsed = $firstLine | ConvertFrom-Json -ErrorAction Stop } catch { $parsed = $null }
            if ($parsed -and $parsed.host_id) { $hostId = $parsed.host_id }
        }
    } catch {
        $hostId = ""
    }
}

if ([string]::IsNullOrEmpty($hostId)) {
    # fallback to computer name hash
    $computerName = $env:COMPUTERNAME
    $hostId = ([System.Security.Cryptography.SHA256]::Create()).ComputeHash([System.Text.Encoding]::UTF8.GetBytes($computerName)) | ForEach-Object { $_.ToString('x2') } -join ''
}

$record = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    host_id = $hostId
    source = "powershell:NetListeners"
    command = "Get-NetTCPConnection -State Listen; Get-NetUDPEndpoint; Get-Process (per owning pid)"
    result_summary = ([ordered]@{ tcp_count = ($tcp | Measure-Object).Count; udp_count = ($udp | Measure-Object).Count } | ConvertTo-Json -Compress)
    raw_hash = $rawHash
    raw_preview = $rawPreview
    severity_hint = "info"
    notes = "Listener inventory collected for contextual firewall proposal (dry-run)."
}

$jsonLine = $record | ConvertTo-Json -Compress -Depth 6
Add-Content -Path $EvidencePath -Value $jsonLine -Encoding utf8

# Also write a separate parsed listeners file for easier consumption
$parsedPath = Join-Path $OutDir ("listeners_" + (Get-Date -Format "yyyyMMddHHmmss") + ".json")
$payload | ConvertTo-Json -Depth 6 | Set-Content -Path $parsedPath -Encoding utf8

Write-Output "COLLECTED_RAW_HASH=$rawHash"
Write-Output "PARSED_PATH=$parsedPath"
Write-Output "EVIDENCE_LINE_ADDED=$jsonLine"
