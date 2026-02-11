# Station Calyx CLI - Quick Start Guide

## Introduction

The Station Calyx CLI is your command-line interface to communicate with CBO (Calyx Bridge Overseer) and steer Station Calyx operations. It provides both direct command execution and LLM-powered conversational interaction.

## Quick Start

### 1. Start CBO API

Before using the CLI, ensure CBO API is running:

```bash
python -m calyx.cbo.api
```

The API will start on `http://localhost:8080` by default.

### 2. Launch the CLI

Open a new terminal and run:

```bash
python tools/calyx_cli.py
```

### 3. Basic Commands

Try these commands in the interactive shell:

```
Calyx> status          # Check system status
Calyx> report          # View detailed report
Calyx> objective       # Submit a new objective
Calyx> chat            # Enter conversational mode
Calyx> help            # Show all commands
```

## Common Workflows

### Workflow 1: Monitor Station Status

```bash
# Check current status
python tools/calyx_cli.py --status

# Or in interactive mode
Calyx> status
```

### Workflow 2: Submit an Objective

```bash
# From command line
python tools/calyx_cli.py --objective "Optimize agent performance" --priority 7

# Or interactively
Calyx> objective
Objective description: Optimize agent performance
Priority (1-10): 7
```

### Workflow 3: Have a Conversation with CBO

```bash
# Enter chat mode
python tools/calyx_cli.py --chat

# Example conversation:
You> What's the current status?
CBO> Current status: 2 tasks queued, 1 objective pending...

You> Can you tell me about TES scores?
CBO> TES (Task Execution Score) metrics show...
```

### Workflow 4: Quick Health Check

```bash
# One-liner to check heartbeat
python tools/calyx_cli.py --status
```

## Integration with Dashboard

The CLI works alongside the HTML dashboard:

- **Dashboard** (`outgoing/system_dashboard.html`): Visual monitoring, auto-refresh
- **CLI**: Direct commands, conversational interaction, scriptable

Both share the same CBO API backend.

## LLM Features

When local LLM models are configured:

1. **Automatic Loading**: CLI detects available models
2. **GPU Acceleration**: Uses GPU if available
3. **Contextual Responses**: LLM receives current system state
4. **Graceful Fallback**: Uses rule-based responses if LLM unavailable

### Requirements for LLM Mode

- Model in `tools/models/MODEL_MANIFEST.json`
- `llama-cpp-python` installed
- Model file downloaded

### Testing LLM Integration

```bash
# Enter chat mode - LLM will auto-load if available
python tools/calyx_cli.py --chat

You> Hello CBO
# If LLM available: Contextual AI response
# If not: Simple rule-based response
```

## Advanced Usage

### Custom API URL

```bash
python tools/calyx_cli.py --api-url http://192.168.1.100:8080
```

### Batch Operations

```bash
# Submit multiple objectives
for task in "Task1" "Task2" "Task3"; do
    python tools/calyx_cli.py --objective "$task"
done
```

### Script Integration

```python
#!/usr/bin/env python3
"""Example script using CLI components"""
from tools.calyx_cli import CBOClient

client = CBOClient()
result = client.submit_objective("Automated task", priority=5)
print(f"Submitted: {result.get('objective_id')}")
```

## Troubleshooting

### "CBO API offline"

**Problem**: CLI can't connect to CBO API

**Solution**: 
```bash
# Start CBO API
python -m calyx.cbo.api

# Verify it's running
curl http://localhost:8080/heartbeat
```

### "LLM loading error"

**Problem**: LLM conversation not working

**Solution**: 
```bash
# Install llama-cpp-python
pip install llama-cpp-python

# Or continue with rule-based responses (works fine)
```

### Model not found

**Problem**: CLI says "LLM unavailable"

**Solution**: Ensure model exists:
```bash
ls tools/models/*.gguf
```

## Next Steps

1. Explore all commands: `Calyx> help`
2. Check detailed documentation: `tools/CALYX_CLI_README.md`
3. Integrate with your workflows
4. Build custom scripts using CLI components

## Comparison: CLI vs Dashboard

| Feature | CLI | Dashboard |
|---------|-----|-----------|
| Direct Commands | ✅ | ❌ |
| Conversational AI | ✅ | ❌ |
| Visual Monitoring | ❌ | ✅ |
| Status Updates | ✅ | ✅ |
| Objective Submission | ✅ | ❌ |
| Scriptable | ✅ | ❌ |
| Auto-refresh | ❌ | ✅ |

**Use CLI for**: Commands, conversations, automation, scripting  
**Use Dashboard for**: Visual monitoring, quick health checks, overview

Both tools complement each other perfectly!

## Support

For issues or questions:
- Check `tools/CALYX_CLI_README.md` for detailed documentation
- Review CBO API logs in `logs/cbo_dispatch.log`
- Check CBO objectives in `runtime/cbo/objectives.jsonl`

