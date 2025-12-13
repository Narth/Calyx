# GitHub Repository Preparation Checklist

This document tracks the preparation of Calyx Terminal for public GitHub cloning and viewing.

## ✅ Completed Tasks

### 1. Gitignore Configuration
- ✅ Created comprehensive `.gitignore` file
- ✅ Excluded virtual environments (.venv, .venv311, venvs/)
- ✅ Excluded Python cache (__pycache__, *.pyc)
- ✅ Excluded keys and secrets (keys/, *.key, *.pk.b64, *.sk.b64)
- ✅ Excluded logs directory and log files
- ✅ Excluded runtime state (state/, outgoing/, incoming/, staging/)
- ✅ Excluded temporary files (temp_*, nohup.out)
- ✅ Excluded IDE files (.vscode, .cursor)
- ✅ Excluded large model files (*.bin, *.pt, *.onnx, *.safetensors)

### 2. License
- ✅ Created MIT License file
- ✅ Attributed to Station Calyx / AI-For-All Project

### 3. Documentation
- ✅ README.md exists and is public-ready
- ✅ Contains clear project description
- ✅ Contains quickstart instructions
- ✅ Contains agent onboarding information
- ✅ References comprehensive documentation in docs/

## ⚠️ Security Review Required

### Files That Should NEVER Be Committed

1. **keys/** directory - Contains cryptographic keys:
   - `cp20_ed25519.pk.b64` (public key)
   - `cp20_ed25519.sk.b64` (SECRET private key)
   
2. **Config.yaml** - May contain sensitive paths:
   - Currently has local Windows paths (C:\Calyx_Terminal\...)
   - Should be reviewed or have a template version

3. **Runtime directories** (already in .gitignore):
   - `outgoing/` - Contains agent runtime state, locks, and operational data
   - `logs/` - Contains detailed system logs
   - `state/` - Contains runtime state
   - `memory/` - Contains agent memory snapshots

## 📋 Pre-Commit Actions Required

### Before First Push:

1. **Review config.yaml**:
   ```powershell
   # Option A: Create a template version
   Copy-Item config.yaml config.template.yaml
   # Then edit config.template.yaml to remove/generalize sensitive paths
   
   # Option B: Add config.yaml to .gitignore if it contains secrets
   echo "config.yaml" >> .gitignore
   ```

2. **Verify .gitignore is working**:
   ```powershell
   git status
   # Ensure keys/, outgoing/, logs/, state/ are NOT listed
   ```

3. **Check for accidental secrets**:
   ```powershell
   # Search for potential API keys or tokens
   git grep -i "api_key\|secret\|password\|token" -- ':!*.md' ':!GITHUB_PREP_CHECKLIST.md'
   ```

4. **Clean up tracked files** (if any secrets were previously committed):
   ```powershell
   git rm --cached keys/*
   git rm --cached config.yaml  # if sensitive
   git commit -m "Remove sensitive files from tracking"
   ```

## 🔍 Repository Structure Audit

### Public-Safe Directories:
- ✅ `asr/` - ASR pipeline code
- ✅ `Scripts/` - Runnable scripts
- ✅ `tools/` - Utility tools
- ✅ `docs/` - Documentation
- ✅ `samples/` - Sample data
- ✅ `templates/` - Templates
- ✅ `agent_doctrine/` - Agent guidelines
- ✅ `governance_schemas/` - Governance schemas

### May Need Review:
- ⚠️ `security/` - Review contents before publishing
- ⚠️ `identity/` - May contain agent identities/credentials
- ⚠️ `canon/` - Review for sensitive content

### Runtime (Excluded):
- 🚫 `keys/` - EXCLUDED
- 🚫 `logs/` - EXCLUDED
- 🚫 `outgoing/` - EXCLUDED
- 🚫 `incoming/` - EXCLUDED
- 🚫 `state/` - EXCLUDED
- 🚫 `memory/` - EXCLUDED
- 🚫 `staging/` - EXCLUDED
- 🚫 `.venv/`, `venvs/` - EXCLUDED

## 🎯 Recommended GitHub Setup

### Repository Settings:
1. **Description**: "Local real-time speech processing system with wake-word detection and multi-agent orchestration framework"
2. **Topics**: `speech-recognition`, `wake-word`, `faster-whisper`, `multi-agent`, `local-first`, `python`
3. **License**: MIT (already included)
4. **README**: Already comprehensive

### Branch Protection:
- Consider protecting `main` branch
- Require pull request reviews for critical changes

### GitHub Actions (Optional):
- Add CI/CD for pytest
- Add linting checks (if desired)

## 📝 Final Steps

Before making repository public:

1. **Initialize git (if not already)**:
   ```powershell
   git init
   git add .gitignore LICENSE README.md
   git commit -m "Initial commit: Add gitignore and license"
   ```

2. **Review staged files**:
   ```powershell
   git add -A
   git status
   # Carefully review what will be committed
   ```

3. **Create initial commit**:
   ```powershell
   git commit -m "Initial public release of Calyx Terminal"
   ```

4. **Add remote and push**:
   ```powershell
   git remote add origin https://github.com/YOUR_USERNAME/Calyx_Terminal.git
   git branch -M main
   git push -u origin main
   ```

## ⚡ Quick Command Summary

```powershell
# 1. Ensure sensitive files are not tracked
git rm --cached keys/* -r
git rm --cached logs/* -r
git rm --cached outgoing/* -r
git rm --cached state/* -r
git rm --cached memory/* -r
git rm --cached incoming/* -r

# 2. Stage public files
git add .gitignore LICENSE README.md GITHUB_PREP_CHECKLIST.md
git add asr/ Scripts/ tools/ docs/ requirements.txt

# 3. Commit
git commit -m "Initial public release"

# 4. Add remote and push
git remote add origin YOUR_REPO_URL
git push -u origin main
```

## 🔒 Post-Publication Security

After making public, remember:
- Never commit secrets or API keys
- Review all PRs carefully for sensitive data
- Use GitHub's secret scanning feature
- Add `.env.example` for any environment variables needed
- Keep keys/ directory strictly local

---

**Status**: Repository prepared for GitHub publication  
**Date**: 2024-12-13  
**Prepared by**: GitHub Copilot CLI  
**Review Required**: YES - Manual verification of config.yaml and security/ directory contents recommended
