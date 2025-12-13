# Grants CBO overseer authority and writes a default policy
$ErrorActionPreference = 'Stop'
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -Path (Resolve-Path '..')

New-Item -ItemType Directory -Force -Path 'outgoing' | Out-Null
New-Item -ItemType Directory -Force -Path 'outgoing/gates' | Out-Null
New-Item -ItemType Directory -Force -Path 'outgoing/policies' | Out-Null

# Authority gate
$cboGate = 'outgoing/gates/cbo.ok'
'ok' | Out-File -FilePath $cboGate -Encoding utf8 -Force

# Default policy (conservative)
$policyPath = 'outgoing/policies/cbo_permissions.json'
$policy = @{
  version = 1
  granted = $true
  # Optional: grant broad capabilities; specific features may still gate behavior
  full_access = $false
  allowed_actions = @(
    'supervise_core_loops',
    'toggle_llm_gate',
    'toggle_network_gate',
    'run_metrics_cron',
    'run_housekeeping',
    'enable_agent_scheduler',
    'navigator_control',
    'adjust_intervals'
  )
  constraints = @{ 
    network_must_default_off = $true
    require_local_llm_ready_for_gpu_probe = $true
    windows_navigator_control_requires_authority_gate = $true
  }
  features = @{
    teaching_cycles = @{
      enabled = $false           # allow optimizer/overseer to run CP6/CP7 cycles
      max_parallel = 1           # cap concurrent teaching cycles (future multi-agent)
      interval_minutes_default = 30
      allowed_agents = @()       # future: names/ids of agents eligible for training cycles
    }
  }
} | ConvertTo-Json -Depth 4
$policy | Out-File -FilePath $policyPath -Encoding utf8 -Force

Write-Host 'CBO authority granted. Gate and policy created.'
