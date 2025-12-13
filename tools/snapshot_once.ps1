# Station Calyx — Single snapshot entry

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$ts = (Get-Date).ToUniversalTime().ToString('o')
$count = (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
$obj = [pscustomobject]@{
    timestamp = $ts
    count     = $count
    note      = "scheduled snapshot"
}
$obj | ConvertTo-Json -Compress | Add-Content -Path (Join-Path $root 'logs/system_snapshots.jsonl')
Write-Host "[snapshot] $ts count=$count"
