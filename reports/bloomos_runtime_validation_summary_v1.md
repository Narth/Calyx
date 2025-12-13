# BloomOS Phase 0 Runtime Validation Summary (Ceremonial)

* Safe Mode: true
* Dispatch/scheduling/autonomy: none observed
* No lifecycle entities created
* Status sample: logs\bloomos\validation\status_cli_sample.txt

## Import Audit
{
  "results": [
    {
      "module": "bloomos.runtime.storage",
      "imported": true,
      "error": null,
      "import_time_ms": 143
    },
    {
      "module": "bloomos.runtime.config",
      "imported": true,
      "error": null,
      "import_time_ms": 59
    },
    {
      "module": "bloomos.runtime.ipc",
      "imported": true,
      "error": null,
      "import_time_ms": 4
    },
    {
      "module": "bloomos.identity.registry",
      "imported": true,
      "error": null,
      "import_time_ms": 4
    },
    {
      "module": "bloomos.policy.binding",
      "imported": true,
      "error": null,
      "import_time_ms": 4
    },
    {
      "module": "bloomos.safety.guard",
      "imported": true,
      "error": null,
      "import_time_ms": 4
    },
    {
      "module": "bloomos.telemetry.collectors",
      "imported": true,
      "error": null,
      "import_time_ms": 7
    },
    {
      "module": "bloomos.lifecycle.controller",
      "imported": true,
      "error": null,
      "import_time_ms": 5
    },
    {
      "module": "bloomos.ui.status_cli",
      "imported": true,
      "error": null,
      "import_time_ms": 4
    }
  ]
}

## Policy / Identity Snapshot
{
  "policy_snapshot_present": true,
  "identity_snapshot_present": true,
  "allow_unregistered_agents": 0.0,
  "max_cpu_pct": 70.0,
  "max_ram_pct": 80.0
}

## Safety Guard Results
{
  "results": [
    {
      "allowed": false,
      "reason": "Safe Mode denies all runtime actions",
      "safe_mode": true,
      "action_descriptor": "dispatch_task"
    },
    {
      "allowed": false,
      "reason": "Safe Mode denies all runtime actions",
      "safe_mode": true,
      "action_descriptor": "network_request"
    },
    {
      "allowed": false,
      "reason": "Safe Mode denies all runtime actions",
      "safe_mode": true,
      "action_descriptor": "file_write"
    }
  ]
}

## Lifecycle Validation
{
  "available_states": [
    "SEED",
    "SEEDLING_REFLECTION_ONLY"
  ],
  "automatic_transitions_detected": false,
  "dry_run_transition_allowed": false,
  "persistent_state_changed": false,
  "current_state": "SEED",
  "note": "Dry-run not executed to avoid persistence; Safe Mode maintained."
}

## Telemetry Validation
{
  "tes_sources_found": true,
  "agii_sources_found": true,
  "cas_sources_found": true,
  "foresight_sources_found": true,
  "read_errors": null
}