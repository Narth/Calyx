# Run byte-compile for all .py files under tools\ using provided python path (or 'python' if not provided)
param(
    [string]$PythonPath = "C:\Users\jncr0\AppData\Local\Programs\Python\Python314\python.exe"
)
Write-Host "Using Python executable: $PythonPath"
$fails = @()
$files = Get-ChildItem -Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) "*.py") -ErrorAction SilentlyContinue
if (-not $files) { Write-Host 'No .py files found under tools\'; exit 0 }
foreach ($f in $files) {
    Write-Host "Compiling: $($f.Name)"
    try {
        & $PythonPath -m py_compile $f.FullName
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  OK: $($f.Name)"
        } else {
            Write-Host "  FAIL (exitcode $LASTEXITCODE): $($f.Name)"
            $fails += $f.Name
        }
    } catch {
        Write-Host "  ERROR compiling $($f.Name): $_"
        $fails += $f.Name
    }
}
if ($fails.Count -gt 0) {
    Write-Host "Files failed to compile:"; $fails | ForEach-Object { Write-Host " - $_" }
    exit 2
} else {
    Write-Host 'All tools\*.py compiled successfully.'
}
