<#
.SYNOPSIS
  Register scheduled tasks for Station Calyx services on Windows.

.DESCRIPTION
  This script can register Windows Scheduled Tasks to run key Station Calyx
  background services such as the alerts cleanup cron and the autonomy monitor.
  Without switches it performs a dry-run and prints the exact Register-ScheduledTask
  commands it would run. Use -Install to actually create the scheduled tasks.

  The script attempts to register tasks to run as SYSTEM when run elevated; if not
  elevated it will register under the current user account.

.EXAMPLE
  # Dry-run (default)
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\register_calyx_scheduled_tasks.ps1

  # Install tasks (will prompt for elevation or fail if not permitted)
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\register_calyx_scheduled_tasks.ps1 -Install
#>

param(
    [switch]$Install,
    [switch]$Force,
    [switch]$UseSystem,
    [string]$PythonPath = "python"
)

function Is-Admin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object System.Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([System.Security.Principal.WindowsBuiltinRole]::Administrator)
}

$root = (Resolve-Path "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)\..\").Path

$tasks = @(
    # housekeeping
    @{ Name = 'Calyx Alerts Cleanup'; Script = 'tools\\alerts_cron.py'; Args = '--run-once --keep 100 --max-age-days 90'; Trigger = 'Daily'; IntervalSeconds = 86400 },
    # monitoring/autonomy
    @{ Name = 'Calyx Autonomy Monitor'; Script = 'tools\\autonomy_monitor.py'; Args = '--interval 30'; Trigger = 'AtStartup'; IntervalSeconds = 0 },
    # watchdog and remediation
    @{ Name = 'Calyx Watchdog Repair'; Script = 'tools\\watchdog_mem_autorepair.py'; Args = '--force'; Trigger = 'Daily'; IntervalSeconds = 3600 },
    # periodic probes and metrics
    @{ Name = 'Calyx Triage Probe'; Script = 'tools\\triage_probe.py'; Args = '--interval 300'; Trigger = 'Daily'; IntervalSeconds = 3600 },
    @{ Name = 'Calyx Metrics Cron'; Script = 'tools\\metrics_cron.py'; Args = '--interval 900'; Trigger = 'Daily'; IntervalSeconds = 3600 },
    @{ Name = 'Calyx Observability Snapshot'; Script = 'tools\\observability_phase1.py'; Args = ''; Trigger = 'Daily'; IntervalSeconds = 86400 },
    # adaptive supervisor (long-running, start at boot)
    @{ Name = 'Calyx Supervisor Adaptive'; Script = 'tools\\svc_supervisor_adaptive.py'; Args = '--interval 60 --include-scheduler --scheduler-interval 150'; Trigger = 'AtStartup'; IntervalSeconds = 0 }
)

$isAdmin = Is-Admin
Write-Host "Station Calyx scheduled task helper"
Write-Host "Repository root: $root"
Write-Host "Running elevated:" $isAdmin
if ($UseSystem) { Write-Host "Using SYSTEM account for registration (specified -UseSystem)" }

# Resolve Python executable to an absolute path when possible so SYSTEM tasks have a valid executable
if ($PythonPath -eq 'python' -or $PythonPath -eq 'py') {
    try {
        $cmd = Get-Command $PythonPath -ErrorAction SilentlyContinue
        if ($cmd) {
            $PythonPath = $cmd.Source
            Write-Host "Resolved Python path to: $PythonPath"
        } else {
            Write-Host "Warning: could not resolve 'python' on PATH; leaving as-is. Consider passing -PythonPath with full path."
        }
    } catch {
        Write-Host "Warning: failed to resolve python path: $_"
    }
} else {
    # If a path was provided, expand it to full path
    if (Test-Path $PythonPath) {
        $PythonPath = (Resolve-Path $PythonPath).ProviderPath
        Write-Host "Using provided PythonPath: $PythonPath"
    }
}

foreach ($t in $tasks) {
    $taskName = $t.Name
    $scriptPath = Join-Path $root $t.Script
    $args = $t.Args
    # Use a PowerShell launcher so SYSTEM tasks can reliably run with logs
    $launcherPath = Join-Path $root 'tools\calyx_task_launcher.ps1'
    # Create a small one-line wrapper .bat for this task so Task Scheduler executes a simple command
    $safeName = ($taskName -replace '\\s+','_') -replace '[^A-Za-z0-9_\-]',''
    $wrapperPath = Join-Path $root ("tools\{0}_wrapper.bat" -f $safeName)
        # Note: the wrapper command string used here was causing parse errors when the
        # script is invoked via -Command due to complex quoting. The concrete wrapper
        # is created below as $wrapperContent and written to disk; $wrapperCmd was
        # previously only used for display and is not required.

    # Resolve cmd.exe path for the scheduled task action
    $cmdExe = $env:ComSpec
    $action = ("New-ScheduledTaskAction -Execute '{0}' -Argument '{1}' -WorkingDirectory '{2}'" -f $cmdExe, $wrapperPath, $root)

    if ($t.Trigger -eq 'Daily') {
        # Start 5 minutes from now
        $startTime = (Get-Date).AddMinutes(5)
        # If the interval is a full day or more, use a daily trigger. Otherwise use a one-shot with repetition within a day.
        if ($t.IntervalSeconds -ge 86400) {
            $trigger = "New-ScheduledTaskTrigger -Daily -At '$($startTime.ToString('s'))'"
        } else {
            $trigger = "New-ScheduledTaskTrigger -Once -At '$($startTime.ToString('s'))' -RepetitionInterval (New-TimeSpan -Seconds $($t.IntervalSeconds)) -RepetitionDuration (New-TimeSpan -Days 1)"
        }
    } else {
        # AtStartup triggers sometimes require elevated registration; fall back to user logon when not elevated
        if ($UseSystem -or $isAdmin) {
            $trigger = "New-ScheduledTaskTrigger -AtStartup"
        } else {
            $trigger = "New-ScheduledTaskTrigger -AtLogOn"
        }
    }

    if ($UseSystem) {
        $principal = "-User 'SYSTEM' -RunLevel Highest"
    } elseif ($isAdmin) {
        # Elevated but user requested non-system registration: register under current user
        $user = $env:USERNAME
        $principal = "-User '$user'"
    } else {
        $user = $env:USERNAME
        $principal = "-User '$user'"
    }

    $registerCmd = "Register-ScheduledTask -TaskName `"$taskName`" -Action ($action) -Trigger ($trigger) $principal -Force"

    Write-Host "\nPlanned task: $taskName"
    Write-Host "  Script: $scriptPath"
    Write-Host "  Args: $args"
    Write-Host "  Wrapper (to be written): $wrapperPath"
    Write-Host "  Action command: $action"
    Write-Host "  Trigger command: $trigger"
    Write-Host "  Register command: $registerCmd"

    if ($Install) {
        try {
            if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
                if ($Force) {
                    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
                    Write-Host "Removed existing task $taskName because -Force specified"
                } else {
                    Write-Host "Task $taskName already exists. Use -Force to replace. Skipping."
                    continue
                }
            }

            # Build action and trigger objects concretely
                # Ensure wrapper exists on disk (so Task Scheduler runs a simple one-line command)
                $wrapperDir = Split-Path $wrapperPath -Parent
                if (-not (Test-Path $wrapperDir)) { New-Item -ItemType Directory -Path $wrapperDir -Force | Out-Null }
                # Wrapper executes the PowerShell launcher explicitly so Task Scheduler runs the script rather than opening it in an editor.
                $wrapperContent = "@echo off`r`npowershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$launcherPath`" --script `"$scriptPath`" --scriptArgs `"$args`" --taskName `"$taskName`" --pythonPath `"$PythonPath`""
                # Write wrapper with UTF8 no BOM
                Set-Content -Path $wrapperPath -Value $wrapperContent -Encoding UTF8

                # Construct the action object using cmd.exe to invoke the wrapper (avoids Task Scheduler argument mangling)
                $actionObj = New-ScheduledTaskAction -Execute $cmdExe -Argument "/c `"$wrapperPath`"" -WorkingDirectory $root
            if ($t.Trigger -eq 'Daily') {
                $startTime = (Get-Date).AddMinutes(5)
                if ($t.IntervalSeconds -ge 86400) {
                    $triggerObj = New-ScheduledTaskTrigger -Daily -At $startTime
                } else {
                    $triggerObj = New-ScheduledTaskTrigger -Once -At $startTime -RepetitionInterval (New-TimeSpan -Seconds $t.IntervalSeconds) -RepetitionDuration (New-TimeSpan -Days 1)
                }
            } else {
                if ($UseSystem -or $isAdmin) {
                    $triggerObj = New-ScheduledTaskTrigger -AtStartup
                } else {
                    $triggerObj = New-ScheduledTaskTrigger -AtLogOn
                }
            }

            if ($UseSystem) {
                Register-ScheduledTask -TaskName $taskName -Action $actionObj -Trigger $triggerObj -User 'SYSTEM' -RunLevel Highest -Force
            } else {
                Register-ScheduledTask -TaskName $taskName -Action $actionObj -Trigger $triggerObj -User $env:USERNAME -Force
            }

            Write-Host "Registered task: $taskName"
        } catch {
            Write-Host ("Failed to register task {0}: {1}" -f $taskName, $_)
        }
    }
}

if (-not $Install) {
    Write-Host "\nDry-run complete. Rerun with -Install to actually register the tasks."
}
