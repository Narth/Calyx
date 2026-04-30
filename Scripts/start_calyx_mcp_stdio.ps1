param(
    [switch]$Validate,
    [switch]$SmokeTest
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv_cbohub311\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

if ($Validate) {
    & $python -m calyx.mcp_server.server --validate
    exit $LASTEXITCODE
}

if ($SmokeTest) {
    & $python (Join-Path $repoRoot "Scripts\mcp_stdio_smoke.py")
    exit $LASTEXITCODE
}

& $python -m calyx.mcp_server.server --stdio
