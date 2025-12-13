# Calyx v1.0 CLI — Simplification Plan

**Date:** 2025-10-25  
**Objective:** Distribute Calyx as a simple, powerful CLI tool

---

## The Problem

Station Calyx is a complex research platform. For beta/v1.0 distribution, we need something simple and intuitive.

---

## The Solution: Calyx CLI

### **Core Concept**
**"A command line where you talk to your AI agent."**

```
$ calyx
Welcome to Calyx!
Your autonomous AI agent is ready.

calyx> goal Improve the README
✓ Goal accepted. Agent is working on it...

calyx> status
Agent: running
Current task: Updating README.md
Progress: 70%

calyx> ask What are you doing?
I'm updating the installation section with clearer steps.
Finding common issues and adding troubleshooting.

calyx> exit
Goodbye! Calyx will continue in the background.
```

---

## What We Need to Build

### **1. Continuous Operation** ✅ (Scheduler running)
**Current Status:** Agent scheduler operational  
**Action:** Ensure it stays running via scheduled task or service

### **2. Simple CLI Interface** ✅ (Prototype ready)
**Created:** `tools/calyx_cli.py`  
**Features:**
- Interactive REPL
- Goal creation (`goal <text>`)
- Status monitoring (`status`)
- Task viewing (`tasks`)
- Question answering (`ask <question>`)

### **3. Real-Time Execution**
**Missing:** Live feedback when agent executes goals  
**Solution:** Connect CLI to agent execution output

### **4. Conversational Q&A**
**Missing:** Agent answering questions about its work  
**Solution:** Add LLM chat mode to CLI

### **5. Packaging**
**Missing:** Standalone executable for distribution  
**Solution:** PyInstaller or similar

---

## Technical Architecture

```
┌─────────────────────────────────────────┐
│          Calyx CLI                      │
│  (tools/calyx_cli.py)                  │
│  - Interactive REPL                    │
│  - Goal management                      │
│  - Status monitoring                    │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│      Agent Execution Layer               │
│  - agent_runner.py                       │
│  - Goal → Tasks                          │
│  - TES tracking                          │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│      LLM Integration                     │
│  - Local or API                          │
│  - Code generation                       │
│  - Question answering                    │
└─────────────────────────────────────────┘
```

---

## What It Takes

### **Week 1: Core CLI** ✅ (80% complete)
- [x] Interactive REPL
- [x] Goal creation
- [x] Status display
- [ ] Real-time execution feedback
- [ ] Task completion notifications

### **Week 2: Conversational Features**
- [ ] Question answering integration
- [ ] Agent reasoning display
- [ ] Multi-turn conversations
- [ ] Context awareness

### **Week 3: Polish & Packaging**
- [ ] Error handling
- [ ] Configuration system
- [ ] Installation wizard
- [ ] Standalone executable

### **Week 4: Documentation & Beta**
- [ ] User guide
- [ ] Example scenarios
- [ ] Beta testing
- [ ] Iteration based on feedback

---

## Current Status

**Research Station:** ✅ Operational (scheduler running)  
**Agent Activity:** ✅ Continuous (tasks dispatched every 3 min)  
**CLI Prototype:** ✅ Created (`tools/calyx_cli.py`)  
**Missing:** Real-time execution integration

---

## Immediate Next Steps

1. **Test CLI** — Run `python tools/calyx_cli.py`
2. **Connect execution** — Link CLI to agent output
3. **Add Q&A** — Integrate conversational features
4. **Package** — Create distributable version

---

## The Big Picture

**You're building:**
- A research station (Station Calyx) ✅
- A simplified product (Calyx CLI) ✅ prototype
- Real autonomous agents ✅

**From complex platform → Simple tool → AI companion**

This is exactly what v1.0 should be.

