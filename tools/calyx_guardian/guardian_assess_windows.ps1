param(
    [string]$OutDir = "logs\calyx_guardian"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$MaxPreview = 800
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$recordsWritten = 0
$writeFailed = $false

function Write-JsonLine {
    param(
        [string]$Path,
        [string]$JsonLine
    )
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
$EvidencePath = Join-Path $OutDir "evidence.jsonl"
$RunLogPath = Join-Path $OutDir "run_log.jsonl"
$HostId = Get-HostId
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-RunLog -Stage "start" -Message "Phase 0 assessment started"
Write-EvidenceRecord -Source "collector:start" -Command "guardian_assess_windows.ps1" -ResultSummary "collector start" -RawOutput "" -SeverityHint "info" -Notes "collector start"
Write-EvidenceRecord -Source "collector:elevation" -Command "guardian_assess_windows.ps1" -ResultSummary ("is_admin=" + $isAdmin) -RawOutput ("is_admin=" + $isAdmin) -SeverityHint "info" -Notes ("collector elevation status: " + $isAdmin)

Invoke-Check -Source "powershell:Get-ComputerInfo" -Command "Get-ComputerInfo | Select-Object OsName, OsVersion, OsBuildNumber, WindowsVersion" -ScriptBlock {
    Get-ComputerInfo | Select-Object OsName, OsVersion, OsBuildNumber, WindowsVersion
} -SummaryBlock {
    param($info)
    $summary = [ordered]@{
        OsName = $info.OsName
        OsVersion = $info.OsVersion
        OsBuildNumber = $info.OsBuildNumber
        WindowsVersion = $info.WindowsVersion
    }
    $summary | ConvertTo-Json -Compress
} -Notes "Read-only OS metadata."

Invoke-Check -Source "powershell:Get-HotFix" -Command "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 25 HotFixID, InstalledOn, Description" -ScriptBlock {
    Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 25 -Property HotFixID, InstalledOn, Description
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
} -Notes "Sampled hotfix list only; not full update history."

Invoke-Check -Source "powershell:WindowsUpdateClientEvents" -Command "Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WindowsUpdateClient'} -MaxEvents 200" -ScriptBlock {
    Get-WinEvent -FilterHashtable @{LogName = "System"; ProviderName = "Microsoft-Windows-WindowsUpdateClient"} -MaxEvents 200 | Sort-Object TimeCreated -Descending | Select-Object TimeCreated, Id, LevelDisplayName
} -SummaryBlock {
    param($events)
    $count = if ($null -eq $events) { 0 } else { @($events).Count }
    $latest = if ($count -gt 0) { @($events)[0].TimeCreated.ToUniversalTime().ToString("o") } else { "" }
    $summary = [ordered]@{
        count = $count
        most_recent_utc = $latest
    }
    $summary | ConvertTo-Json -Compress
} -Notes "Event log summary only; full update details not collected."

Invoke-Check -Source "powershell:Get-MpComputerStatus" -Command "Get-MpComputerStatus" -ScriptBlock {
    Get-MpComputerStatus | Select-Object AMServiceEnabled, AntispywareEnabled, AntivirusEnabled, RealTimeProtectionEnabled, NISEnabled, IsTamperProtected, QuickScanAge, FullScanAge
} -SummaryBlock {
    param($status)
    $summary = [ordered]@{
        AMServiceEnabled = $status.AMServiceEnabled
        AntispywareEnabled = $status.AntispywareEnabled
        AntivirusEnabled = $status.AntivirusEnabled
        RealTimeProtectionEnabled = $status.RealTimeProtectionEnabled
        NISEnabled = $status.NISEnabled
        IsTamperProtected = $status.IsTamperProtected
        QuickScanAge = $status.QuickScanAge
        FullScanAge = $status.FullScanAge
    }
    $summary | ConvertTo-Json -Compress
} -Notes "Windows Defender status only."

Invoke-Check -Source "powershell:Get-NetFirewallProfile" -Command "Get-NetFirewallProfile | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction" -ScriptBlock {
    Get-NetFirewallProfile | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction | Sort-Object Name
} -SummaryBlock {
    param($profiles)
    $summary = @($profiles | ForEach-Object {
        [ordered]@{
            Name = $_.Name
            Enabled = $_.Enabled
            DefaultInboundAction = $_.DefaultInboundAction
            DefaultOutboundAction = $_.DefaultOutboundAction
        }
    })
    $summary | ConvertTo-Json -Compress
} -Notes "Firewall profile summary."

Invoke-Check -Source "powershell:Get-BitLockerVolume" -Command "Get-BitLockerVolume | Select-Object MountPoint, VolumeStatus, ProtectionStatus" -ScriptBlock {
    Get-BitLockerVolume | Select-Object MountPoint, VolumeStatus, ProtectionStatus | Sort-Object MountPoint
} -SummaryBlock {
    param($volumes)
    $summary = @($volumes | ForEach-Object {
        [ordered]@{
            MountPoint = $_.MountPoint
            VolumeStatus = $_.VolumeStatus
            ProtectionStatus = $_.ProtectionStatus
        }
    })
    $summary | ConvertTo-Json -Compress
} -Notes "BitLocker status; may require elevation."

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
} -Notes "File system free space only."

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
} -Notes "SMART data not collected; vendor tools may provide more detail."

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
} -Notes "File History presence only; no file inspection."

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
} -Notes "Presence only; sign-in status not checked."

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
} -Notes "RDP enabled flag only; no network scanning."

Write-RunLog -Stage "complete" -Message "Phase 0 assessment completed"
if ($writeFailed -eq $true -or $recordsWritten -eq 0) {
    Write-EvidenceRecord -Source "collector:end" -Command "guardian_assess_windows.ps1" -ResultSummary "collector end" -RawOutput "" -SeverityHint "error" -Notes "collector fatal: evidence write failure or no records"
    exit 1
}
$collectorOutcome = if ($recordsWritten -gt 0) { "success" } else { "partial_success" }
Write-EvidenceRecord -Source "collector:end" -Command "guardian_assess_windows.ps1" -ResultSummary "collector end" -RawOutput "" -SeverityHint "info" -Notes ("collector outcome: " + $collectorOutcome)
exit 0
