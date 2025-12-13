# BloomOS Core Check-In Validation v1 (Ceremonial)

* Safe Mode: true
* No dispatch/scheduling/autonomy/gating/enforcement observed
* No cores/saplings/blooms created
* Snapshot stored: logs/bloomos/validation/core_checkin_sample.json

## Import Check
[
  {
    "module": "bloomos.core.checkin",
    "imported": true,
    "error": null
  },
  {
    "module": "bloomos.ui.core_checkin_cli",
    "imported": true,
    "error": null
  }
]

## Sample Snapshot (excerpt)
{
  "safe_mode": true,
  "policy_snapshot": {
    "allow_api": 0.0,
    "max_cpu_pct": 70.0,
    "max_ram_pct": 80.0,
    "allow_unregistered_agents": 0.0,
    "log_manifest_required": 1.0,
    "restart_on_violation": 1.0
  },
  "lifecycle_state": {
    "available_states": [
      "SEED",
      "SEEDLING_REFLECTION_ONLY"
    ],
    "current_state": "SEED"
  },
  "telemetry_summary": {
    "tes": {
      "present": true,
      "latest": {
        "iso_ts": "2025-10-28T05:46:59+00:00",
        "tes": "97.2",
        "stability": "1.0",
        "velocity": "0.906",
        "footprint": "1.0",
        "duration_s": "166.2",
        "status": "done",
        "applied": "0",
        "changed_files": "0",
        "run_tests": "1",
        "autonomy_mode": "apply_tests",
        "model_id": "tinyllama-1.1b-chat-q5_k_m",
        "run_dir": "outgoing/agent_run_1761630336",
        "hint": "",
        "compliance": "",
        "ethics": "",
        "coherence": "",
        "tes_v3": "",
        "tes_schema": ""
      },
      "value": "97.2"
    },
    "agii": {
      "present": true
    },
    "cas": {
      "present": true,
      "latest": {
        "task_id": "T-2025-11-30-001",
        "agent_id": "triage",
        "started_at": "2025-11-30T18:20:00Z",
        "ended_at": "2025-11-30T18:22:00Z",
        "difficulty": "normal",
        "metrics": {
          "IFCR": 1,
          "HTI": 0,
          "SRR": 1,
          "CTC": 0.28,
          "SFT": 1,
          "RHR": 1
        },
        "cost": {
          "tokens": 1823,
          "usd": 0.012,
          "wall_time_sec": 120
        },
        "notes": "Synthetic event for CAS pipeline validation",
        "audit": {
          "toolspec_sha256": "synthetic",
          "raw_trace_uri": "synthetic"
        },
        "cas": 0.3719999999999999,
        "cas_version": "0.1"
      }
    },
    "foresight": {
      "present": true,
      "forecast_latest": {
        "timestamp": "2025-10-28T04:19:00.903465+00:00",
        "tes_forecast": {
          "forecast": 100.0,
          "confidence": 0.652500076,
          "trend": "improving",
          "horizon_minutes": 60,
          "baseline": 88.47400000000002,
          "method": "linear"
        },
        "resource_forecast": {
          "memory": 70.0,
          "confidence": 0.0
        },
        "risk_assessment": {
          "risk": 0.029200000000000018,
          "confidence": 0.9997888,
          "current_tes": 97.08
        },
        "anomalies": [
          {
            "index": 0,
            "value": 47.0,
            "z_score": 2.224838884922859,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 2,
            "value": 41.8,
            "z_score": 2.5037886414353454,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 3,
            "value": 47.6,
            "z_score": 2.1926523745560336,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 4,
            "value": 48.0,
            "z_score": 2.17119470097815,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 5,
            "value": 47.8,
            "z_score": 2.181923537767092,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 6,
            "value": 47.8,
            "z_score": 2.181923537767092,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 7,
            "value": 48.2,
            "z_score": 2.160465864189208,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 8,
            "value": 48.0,
            "z_score": 2.17119470097815,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 9,
            "value": 47.8,
            "z_score": 2.181923537767092,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 10,
            "value": 47.3,
            "z_score": 2.2087456297394463,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 11,
            "value": 47.1,
            "z_score": 2.219474466528388,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 13,
            "value": 48.2,
            "z_score": 2.160465864189208,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 14,
            "value": 47.9,
            "z_score": 2.176559119372621,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 15,
            "value": 47.7,
            "z_score": 2.1872879561615624,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 16,
            "value": 48.0,
            "z_score": 2.17119470097815,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 17,
            "value": 48.0,
            "z_score": 2.17119470097815,
            "severity": "medium",
            "timestamp": ""
          },
          {
            "index": 18,
            "value": 46.6,
            "z_score": 2.246296558500742,
            "severity": "medium",
            "timestamp": ""
          }
        ],
        "exhaustion_prediction": {
          "current_memory": 82.5,
          "trend_rate": 0.02333333333333461,
          "minutes_to_limit": -53.571428571425635,
          "exhaustion_likely": true,
          "confidence": 0.6
        }
      },
      "warning_latest": {
        "timestamp": "2025-10-28T04:23:06.352828+00:00",
        "type": "resource_exhaustion",
        "severity": "high",
        "message": "Resource exhaustion predicted within -31 minutes",
        "prediction": {
          "current_memory": 82.5,
          "trend_rate": 0.03999999999999979,
          "minutes_to_limit": -31.25000000000016,
          "exhaustion_likely": true,
          "confidence": 0.55
        },
        "recommendation": "Take immediate action to reduce memory usage"
      }
    }
  },
  "canon_integrity": {
    "genesis": {
      "present": true
    },
    "doctrine": {
      "present": true
    },
    "heartwood": {
      "present": true
    },
    "bloomos_canon": {
      "present": true
    },
    "hash_chain_tip": "670C9E26EFB67855AFF8BB6C530B528D8ACBF91376C261A7425F844D4264D475"
  }
}