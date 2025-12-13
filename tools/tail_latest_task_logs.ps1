# Tail the most recent 6 launcher logs under outgoing\tasks\ and print headers
$files = Get-ChildItem -Path .\outgoing\tasks\ -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 6
if (-not $files) { Write-Host "No recent task logs found."; exit }
foreach ($f in $files) {
    Write-Host "\n===== $($f.Name) ====="
    try {
        Get-Content -Path $f.FullName -Tail 120 -ErrorAction Stop | ForEach-Object { Write-Host $_ }
    } catch {
        Write-Host "(Failed to read $($f.FullName)): $_"
    }
}
