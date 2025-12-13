param(
    [Parameter(Mandatory=$true)][string]$TaskName
)

$cleanKey = ($TaskName -replace '[^A-Za-z0-9]','')
$xmlPath = Join-Path $PSScriptRoot "..\outgoing\tasks\${cleanKey}_task.xml"
$fixedPath = Join-Path $PSScriptRoot "..\outgoing\tasks\${cleanKey}_task_fixed.xml"

Write-Output "Exporting task XML to: $xmlPath"
schtasks /Query /TN "\$TaskName" /XML > $xmlPath

if (-not (Test-Path $xmlPath)) {
    Write-Output "Failed to export task XML: $xmlPath not found"
    exit 2
}

[xml]$x = Get-Content $xmlPath
$argsNode = $x.GetElementsByTagName('Arguments')
if ($argsNode.Count -gt 0) {
    Write-Output "Original Arguments: $($argsNode[0].InnerText)"
    $argsNode[0].InnerText = ($argsNode[0].InnerText -replace '\\s+',' ')
    Write-Output "Fixed Arguments: $($argsNode[0].InnerText)"
} else {
    Write-Output "No <Arguments> node found in XML"
}

$x.Save($fixedPath)
Write-Output "Saved fixed XML to: $fixedPath"

Write-Output "Re-registering task from fixed XML (force)..."
schtasks /Create /TN "\$TaskName" /XML $fixedPath /F

Write-Output "Starting task: $TaskName"
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 6

Write-Output "Latest outgoing/tasks entries:"
Get-ChildItem (Join-Path $PSScriptRoot '..\outgoing\tasks\') | Sort-Object LastWriteTime -Descending | Select-Object -First 8 Name,LastWriteTime,Length | Format-Table -AutoSize
