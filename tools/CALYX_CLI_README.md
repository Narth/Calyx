# Station Calyx CLI

A command-line interface for interacting with Station Calyx's CBO (Calyx Bridge Overseer) via direct commands and LLM-powered conversations.

## Overview

The Station Calyx CLI provides two primary ways to interact with CBO:

1. **Direct Commands**: Issue objectives, check status, view reports
2. **LLM Conversation Mode**: Have natural language conversations with CBO powered by local LLM models

## Features

- ✅ Submit objectives to CBO
- ✅ Check system status and health
- ✅ View detailed reports and metrics
- ✅ Monitor TES (Task Execution Score) trends
- ✅ Interactive chat mode with LLM integration
- ✅ Automatic fallback to rule-based responses when LLM unavailable
- ✅ GPU acceleration support for LLM inference

## Prerequisites

- Python 3.11+
- CBO API running (start with `python -m calyx.cbo.api`)
- Optional: Local LLM model configured in `tools/models/MODEL_MANIFEST.json`
- Optional: `llama-cpp-python` for LLM conversation features

## Installation

The CLI is already included in the Station Calyx tools. No separate installation needed.

### Dependencies

```bash
pip install rich requests llama-cpp-python
```

## Usage

### Interactive Mode

Launch the CLI in interactive mode:

```bash
python tools/calyx_cli.py
```

Commands available in interactive mode:
- `status` - Show system status
- `report` - Show detailed report
- `objective` - Submit a new objective
- `chat` - Enter LLM conversation mode
- `heartbeat` - Check CBO heartbeat
- `policy` - Show current policy
- `help` - Show available commands
- `exit` - Exit CLI

### Command-Line Arguments

#### Check Status

```bash
python tools/calyx_cli.py --status
```

#### View Detailed Report

```bash
python tools/calyx_cli.py --report
```

#### Submit an Objective

```bash
python tools/calyx_cli.py --objective "Optimize agent task execution speed" --priority 7
```

#### Start Chat Mode

```bash
python tools/calyx_cli.py --chat
```

#### Specify CBO API URL

```bash
python tools/calyx_cli.py --api-url http://localhost:8080
```

## Examples

### Submitting an Objective

```bash
$ python tools/calyx_cli.py --objective "Improve TES velocity component"

Objective submitted: obj-a1b2c3d4e5
```

### Checking System Status

```bash
$ python tools/calyx_cli.py --status

Station Calyx Status
────────────────────────────────────────────────────
CBO: Online
Status: ok
Timestamp: 2025-10-26T00:30:00

System Metrics:
Queue Depth: 3
Objectives Pending: 2

TES Summary:
Mean TES: 89.2
Latest TES: 93.9
Samples: 469
```

### Conversational Interaction

```bash
$ python tools/calyx_cli.py --chat

Chat with CBO
────────────────────────────────────────────────────
Type 'exit' to quit, 'help' for commands

You> What's the current status?
CBO> Current status: 3 tasks queued, 2 objectives pending. System is operating normally with TES scores averaging 89.2.

You> Can you queue an objective to improve agent efficiency?
CBO> I can queue objectives for the Station. Please provide more details about what specific improvements you'd like to see.

You> exit
```

## Architecture

### Components

1. **CBOClient**: HTTP client for CBO API communication
2. **LLMConversation**: LLM-powered conversation interface
3. **Interactive Commands**: Status, report, objective submission
4. **Rich UI**: Beautiful terminal interface using `rich` library

### CBO API Integration

The CLI communicates with CBO via REST API endpoints:

- `GET /heartbeat` - Health check
- `POST /objective` - Submit objectives
- `GET /status` - System status
- `GET /report` - Detailed reports
- `GET /policy` - Current policy

### LLM Integration

When LLM models are available:

1. Loads model from `tools/models/MODEL_MANIFEST.json`
2. Attempts GPU acceleration if supported
3. Falls back to CPU if GPU unavailable
4. Falls back to rule-based responses if LLM unavailable

The LLM is provided with:
- Current system context (task queue, TES scores, etc.)
- Conversation history (last 6 messages)
- CBO role and responsibilities

## Configuration

### CBO API URL

Default: `http://localhost:8080`

Override with `--api-url` or by modifying `CBO_API_URL` in the script.

### LLM Model Selection

The CLI automatically selects models from `MODEL_MANIFEST.json`:
- Prefers models with `role: "general"`
- Falls back to first available model
- Supports GPU offloading via `tools/gpu_utils`

## Troubleshooting

### CBO API Offline

```
Error: CBO API offline: Connection refused
```

**Solution**: Start the CBO API:
```bash
python -m calyx.cbo.api
```

### LLM Not Loading

```
LLM loading error: No module named 'llama_cpp'
```

**Solution**: Install llama-cpp-python:
```bash
pip install llama-cpp-python
```

### Model Not Found

The CLI will automatically fall back to rule-based responses when no LLM is available. The conversation features will still work with basic pattern matching.

## Integration with HTML Dashboard

The CLI complements the HTML dashboard (`outgoing/system_dashboard.html`) by providing:

- **CLI**: Direct commands and conversational interface
- **Dashboard**: Visual monitoring and status visualization

Both interfaces share the same CBO API backend.

## Future Enhancements

- [ ] Real-time streaming responses from LLM
- [ ] Command aliases and shortcuts
- [ ] Objective templates and wizards
- [ ] Batch objective submission
- [ ] Configuration file support
- [ ] Export reports to various formats
- [ ] Integration with CBO task queue for progress tracking

## License

Same as Station Calyx project.

## Contributing

Report issues and submit PRs to the Station Calyx repository.

