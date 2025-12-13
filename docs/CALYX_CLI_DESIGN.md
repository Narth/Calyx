# Calyx CLI — Beta/V1.0 Design Document

**Vision:** A simple command-line interface where humans and AI agents collaborate  
**Platform:** Cross-platform CLI tool  
**Goal:** Distribute Calyx technology in its simplest, most powerful form

---

## Core Concept

**One interface. Two minds. Unlimited potential.**

```
calyx> goal Improve the documentation
✓ Goal created. Agent processing...

calyx> status
Scheduler: running
Tasks: 3 active
CPU: 45%
RAM: 72%

calyx> ask What did you accomplish?
Agent: Updated README.md with clearer installation instructions.
Next step: Add troubleshooting section.

calyx> exit
```

---

## Architecture

### **Components:**

1. **Calyx CLI** (`tools/calyx_cli.py`)
   - Interactive REPL
   - Goal creation
   - Status monitoring
   - Question answering

2. **Agent Backend** (existing infrastructure)
   - `agent_runner.py` — executes goals
   - Task queue system
   - TES tracking
   - LLM integration

3. **Continuous Operation**
   - Background scheduler
   - Health monitoring
   - Self-healing

---

## Implementation Path

### **Phase 1: Basic CLI** (Current)
✅ Interactive REPL  
✅ Goal creation  
✅ Status display  
⏳ Real-time execution feedback

### **Phase 2: Conversational Interface**
- Natural language understanding
- Context-aware responses
- Learning from interactions
- Multi-turn conversations

### **Phase 3: Autonomous Integration**
- Agent processes goals automatically
- Progress updates in real-time
- Question answering from agent state
- Collaborative workflow

### **Phase 4: Distribution**
- Standalone executable
- Configuration wizard
- First-run setup
- Documentation package

---

## Technical Specs

### **Dependencies:**
- Python 3.11+
- Existing Calyx infrastructure
- LLM backend (local or API)

### **Installation:**
```bash
pip install calyx-cli
calyx init
calyx start
```

### **Usage:**
```bash
calyx                    # Start interactive CLI
calyx goal "text"        # Single goal execution
calyx status             # Check status
calyx --version          # Version info
```

---

## User Experience

### **First Launch:**
```
Welcome to Calyx!
This is your autonomous AI agent.
Let's start by setting up your workspace...

> Would you like Calyx to:
  1. Help with code development
  2. Write documentation
  3. Analyze data
  4. Custom setup

Choice: 1

✓ Calyx configured for code development
✓ Scheduler started
✓ Monitoring active

Calyx is ready. What would you like to accomplish?
```

### **Daily Use:**
```
calyx> goal Refactor the authentication module

[Agent is planning...]
[Agent is executing...]
[✓ Complete]

Results:
- Moved auth logic to separate module
- Added comprehensive tests
- Updated documentation

calyx> ask How did you decide to structure the refactor?

Agent: I analyzed code cohesion metrics and identified...
```

---

## What Makes This Different

**vs. Complex AI Platforms:**
- ✅ Single command-line interface
- ✅ No complex configuration
- ✅ Starts working immediately
- ✅ Learns your preferences

**vs. Chatbots:**
- ✅ Actually DOES work (file changes, code execution)
- ✅ Learns from results
- ✅ Autonomous improvement
- ✅ Real progress tracking

**vs. Current Station Calyx:**
- ✅ Simplified for end users
- ✅ Human-focused interaction
- ✅ Same powerful backend
- ✅ Production-ready

---

## Feasibility Assessment

### **Current Capabilities:**
✅ Goal creation and execution  
✅ Task queue system  
✅ LLM integration  
✅ TES tracking  
✅ Status monitoring  
✅ Lock files for coordination  

### **Missing Pieces:**
⏳ Real-time goal execution feedback  
⏳ Conversational Q&A integration  
⏳ Packaging as standalone tool  
⏳ Configuration wizard  
⏳ Documentation for end users  

### **Effort Estimate:**
- **Phase 1:** 1-2 days (basic CLI working)
- **Phase 2:** 1 week (conversational features)
- **Phase 3:** 2 weeks (full integration)
- **Phase 4:** 1 week (packaging/distribution)

**Total:** ~1 month to beta-ready CLI

---

## Next Steps

1. Complete basic CLI with real execution
2. Test with sample goals
3. Add Q&A capability
4. Package for distribution
5. Create user documentation
6. Beta test with real users

---

## The Promise

**From:** "Station Calyx has 15 agents, 6 services, monitoring..."  
**To:** "Calyx, help me build this feature."

**That's the simplification we're building.**

