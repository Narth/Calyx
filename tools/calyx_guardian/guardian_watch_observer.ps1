param(
    [string]$OutDir = "logs\calyx_guardian",
    [string]$WatchId,
    [int]$WatchHours = 8,
    [int]$IntervalMinutes = 60,
    [int]$MaxIterations = 8
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WatchId)) {
    throw "WatchId is required"
}

$MaxPreview = 800
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$recordsWritten = 0
$writeFailed = $false

function Write-JsonLine {
    param([string]$Path, [string]$JsonLine)
    $writer = New-Object System.IO.StreamWriter($Path, $true, $Utf8NoBom)
    try {
        $writer.WriteLine($JsonLine)
    } finally {
        $writer.Dispose()
    }
}

function Get-Sha256 {
    param([string]$Text)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $hashBytes = $sha256.ComputeHash($bytes)
    ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Get-HostId {
    $computerName = $env:COMPUTERNAME
    $machineGuid = ""
    try {
        $machineGuid = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Cryptography" -Name "MachineGuid").MachineGuid
    } catch {
        $machineGuid = ""
    }
    Get-Sha256 ($computerName + $machineGuid)
}

function Write-RunLog {
    param(
        [string]$Stage,
        [string]$Message,
        [string]$Level = "info"
    )
    $entry = [ordered]@{
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        stage = $Stage
        level = $Level
        message = $Message
        watch_id = $WatchId
    }
    $jsonLine = $entry | ConvertTo-Json -Compress
    Write-JsonLine -Path $RunLogPath -JsonLine $jsonLine
}

function Write-EvidenceRecord {
    param(
        [string]$Source,
        [string]$Command,
        [string]$ResultSummary,
        [string]$RawOutput,
        [string]$SeverityHint,
        [string]$Notes
    )
    if ($null -eq $RawOutput) {
        $RawOutput = ""
    }
    $rawHash = Get-Sha256 $RawOutput
    $rawPreview = if ($RawOutput.Length -gt $MaxPreview) { $RawOutput.Substring(0, $MaxPreview) } else { $RawOutput }
    $record = [ordered]@{
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        host_id = $HostId
        source = $Source
        command = $Command
        result_summary = $ResultSummary
        raw_hash = $rawHash
        raw_preview = $rawPreview
        severity_hint = $SeverityHint
        notes = $Notes
        watch_id = $WatchId
    }
    try {
        $jsonLine = $record | ConvertTo-Json -Compress -Depth 6
        Write-JsonLine -Path $EvidencePath -JsonLine $jsonLine
        $script:recordsWritten += 1
    } catch {
        $script:writeFailed = $true
    }
}

function Invoke-Check {
    param(
        [string]$Source,
        [string]$Command,
        [scriptblock]$ScriptBlock,
        [scriptblock]$SummaryBlock,
        [string]$SeverityHint = "info",
        [string]$Notes = ""
    )
    try {
        $result = & $ScriptBlock
        $summary = & $SummaryBlock $result
        $rawOutput = $result | ConvertTo-Json -Compress -Depth 6
        Write-EvidenceRecord -Source $Source -Command $Command -ResultSummary $summary -RawOutput $rawOutput -SeverityHint $SeverityHint -Notes $Notes
    } catch {
        $errorMessage = $_.Exception.Message
        $errorType = $_.Exception.GetType().FullName
        $notes = "check failed: " + $errorType + ": " + $errorMessage
        Write-EvidenceRecord -Source $Source -Command $Command -ResultSummary ("error: " + $errorMessage) -RawOutput $errorMessage -SeverityHint "error" -Notes $notes
    }
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$EvidencePath = Join-Path $OutDir "watch_evidence.jsonl"
$RunLogPath = Join-Path $OutDir "watch_run_log.jsonl"
$HostId = Get-HostId

$startTime = Get-Date
$endTime = $startTime.AddHours($WatchHours)
$iteration = 0

Write-RunLog -Stage "watch_start" -Message "Night watch observer loop started"
Write-EvidenceRecord -Source "watch:start" -Command "guardian_watch_observer.ps1" -ResultSummary "watch start" -RawOutput "" -SeverityHint "info" -Notes "watch start"

while ($iteration -lt $MaxIterations -and (Get-Date) -lt $endTime) {
    $iteration += 1
    Write-RunLog -Stage "watch_iteration" -Message "Iteration $iteration" -Level "info"

    Invoke-Check -Source "powershell:Get-HotFix" -Command "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 HotFixID, InstalledOn" -ScriptBlock {
        Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 -Property HotFixID, InstalledOn
    } -SummaryBlock {
        param($hotfixes)
        $count = if ($null -eq $hotfixes) { 0 } else { @($hotfixes).Count }
        $latest = if ($count -gt 0) { @($hotfixes)[0] } else { $null }
        $summary = [ordered]@{
            count = $count
            latest_hotfix = if ($null -ne $latest) { $latest.HotFixID } else { "" }
            latest_installed_on = if ($null -ne $latest -and $null -ne $latest.InstalledOn) { $latest.InstalledOn.ToUniversalTime().ToString("o") } else { "" }
        }
        $summary | ConvertTo-Json -Compress
    } -Notes "Night watch patch sample."

    Invoke-Check -Source "powershell:Get-PSDrive" -Command "Get-PSDrive -PSProvider FileSystem" -ScriptBlock {
        Get-PSDrive -PSProvider FileSystem | Sort-Object Name
    } -SummaryBlock {
        param($drives)
        $summary = @()
        foreach ($drive in $drives) {
            $total = [double]($drive.Used + $drive.Free)
            $freePct = if ($total -gt 0) { [math]::Round(($drive.Free / $total) * 100, 2) } else { 0 }
            $summary += [ordered]@{
                Name = $drive.Name
                FreeBytes = [int64]$drive.Free
                TotalBytes = [int64]$total
                FreePct = $freePct
            }
        }
        $summary | ConvertTo-Json -Compress
    } -Notes "Night watch disk free space."

    Invoke-Check -Source "powershell:Get-PhysicalDisk" -Command "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, HealthStatus, OperationalStatus, Size" -ScriptBlock {
        Get-PhysicalDisk | Select-Object FriendlyName, MediaType, HealthStatus, OperationalStatus, Size | Sort-Object FriendlyName
    } -SummaryBlock {
        param($disks)
        $summary = @($disks | ForEach-Object {
            [ordered]@{
                FriendlyName = $_.FriendlyName
                MediaType = $_.MediaType
                HealthStatus = $_.HealthStatus
                OperationalStatus = $_.OperationalStatus
                Size = $_.Size
            }
        })
        $summary | ConvertTo-Json -Compress
    } -Notes "Night watch physical disk status."

    Invoke-Check -Source "powershell:FileHistory" -Command "Get-Service -Name fhsvc; Test-Path HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\FileHistory" -ScriptBlock {
        $service = Get-Service -Name fhsvc
        $configured = Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\FileHistory"
        [ordered]@{
            ServiceStatus = $service.Status.ToString()
            Configured = $configured
        }
    } -SummaryBlock {
        param($fh)
        $summary = [ordered]@{
            ServiceStatus = $fh.ServiceStatus
            Configured = $fh.Configured
        }
        $summary | ConvertTo-Json -Compress
    } -Notes "Night watch backup presence (File History)."

    Invoke-Check -Source "powershell:OneDrivePresence" -Command "Get-Command OneDrive.exe" -ScriptBlock {
        $command = Get-Command OneDrive.exe -ErrorAction SilentlyContinue
        $present = $false
        if ($null -ne $command) {
            $present = $true
        } elseif (Test-Path "$env:LOCALAPPDATA\Microsoft\OneDrive\OneDrive.exe") {
            $present = $true
        } elseif (Test-Path "$env:PROGRAMFILES\Microsoft OneDrive\OneDrive.exe") {
            $present = $true
        }
        [ordered]@{
            Present = $present
        }
    } -SummaryBlock {
        param($onedrive)
        $summary = [ordered]@{
            Present = $onedrive.Present
        }
        $summary | ConvertTo-Json -Compress
    } -Notes "Night watch OneDrive presence only."

    Invoke-Check -Source "powershell:RDPEnabled" -Command "Get-ItemProperty -Path HKLM:\System\CurrentControlSet\Control\Terminal Server -Name fDenyTSConnections" -ScriptBlock {
        $value = (Get-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections").fDenyTSConnections
        [ordered]@{
            RdpEnabled = ($value -eq 0)
        }
    } -SummaryBlock {
        param($rdp)
        $summary = [ordered]@{
            RdpEnabled = $rdp.RdpEnabled
        }
        $summary | ConvertTo-Json -Compress
    } -Notes "Night watch RDP enabled flag."

    if ($iteration -lt $MaxIterations -and (Get-Date) -lt $endTime) {
        Start-Sleep -Seconds ($IntervalMinutes * 60)
    }
}

Write-RunLog -Stage "watch_end" -Message "Night watch observer loop completed"
if ($writeFailed -eq $true -or $recordsWritten -eq 0) {
    Write-EvidenceRecord -Source "watch:end" -Command "guardian_watch_observer.ps1" -ResultSummary "watch end" -RawOutput "" -SeverityHint "error" -Notes "watch fatal: evidence write failure or no records"
    exit 1
}
Write-EvidenceRecord -Source "watch:end" -Command "guardian_watch_observer.ps1" -ResultSummary "watch end" -RawOutput "" -SeverityHint "info" -Notes "watch outcome: success"
exit 0
