param(
    [int]$Interval = 60
)
# Starts the Windows-first adaptive supervisor. Use -Interval to override the check cadence.
$ErrorActionPreference = 'SilentlyContinue'
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path) | Out-Null
Set-Location -Path (Resolve-Path '..')
python -u .\tools\svc_supervisor_adaptive.py --interval $Interval
