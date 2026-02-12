# Workflow Python Compilation Fix

**Date:** 2026-02-12  
**Status:** ✅ **FIXED AND PUSHED**

---

## Issue Identified

**Problem:** Workflow failed at Python compilation step because it tried to compile files that were removed during repo curation.

**Error:** `[Errno 2] No such file or directory` for:
- `dashboard/backend/main.py`
- `dashboard/backend/auth.py`
- `dashboard/backend/api/chat.py`
- `station_calyx/api/server.py`
- `station_calyx/api/routes.py`

**Root Cause:** Hardcoded file list in workflow referenced pre-curation files that no longer exist in the curated repository.

---

## Fix Applied

**Approach:** Option B (recommended) - Use `git ls-files` to dynamically find Python files that exist in the curated repo.

**Implementation:**
```yaml
- name: Compile Python modules
  run: |
    files=$(git ls-files 'calyx/**/*.py' 'tools/*.py' | tr '\n' ' ')
    if [ -n "$files" ]; then
      python -m py_compile $files
    else
      echo "No Python files found to compile."
    fi
```

**Rationale:**
- ✅ Deterministic: Uses `git ls-files` to find tracked files only
- ✅ Portable: Works in any Git repository
- ✅ Maintainable: Automatically includes new Python files without workflow updates
- ✅ Safe: Checks if files exist before attempting compilation
- ✅ Focused: Compiles only `calyx/` and `tools/` Python modules (core governance code)

---

## Changes Made

### Workflow Update (`.github/workflows/public-repo-hygiene.yml`)

**Before:**
```yaml
- name: Compile critical Python modules
  run: |
    python -m py_compile \
      dashboard/backend/main.py \
      dashboard/backend/auth.py \
      dashboard/backend/api/chat.py \
      station_calyx/api/server.py \
      station_calyx/api/routes.py
```

**After:**
```yaml
- name: Compile Python modules
  run: |
    files=$(git ls-files 'calyx/**/*.py' 'tools/*.py' | tr '\n' ' ')
    if [ -n "$files" ]; then
      python -m py_compile $files
    else
      echo "No Python files found to compile."
    fi
```

**Improvements:**
- ✅ Dynamic file discovery (no hardcoded paths)
- ✅ Only compiles files that exist in curated repo
- ✅ Handles edge case (no files found)
- ✅ Focuses on core governance modules (`calyx/` and `tools/`)

---

## Files Compiled

**Pattern:** `calyx/**/*.py` and `tools/*.py`

**Expected files:**
- `calyx/cbo/**/*.py` - CBO core modules
- `calyx/mail/*.py` - Calyx Mail Protocol Layer v0.1
- `calyx/core/*.py` - Shared primitives
- `calyx/compute/*.py` - Compute stewardship
- `tools/calyx_mail.py` - Mail CLI
- `tools/migrate_mailbox_v0_to_v0_1.py` - Migration tool

**Excluded:** Removed pre-curation files (dashboard/, station_calyx/api/, etc.)

---

## Verification

### Governance Invariants Check

✅ **No network imports** - Verified (grep check passed)  
✅ **No runtime artifacts tracked** - Verified (0 files)  
✅ **No secrets** - Verified (all credential-shaped strings replaced with placeholders)  
✅ **No dynamic execution** - Verified (only legitimate SQLite/domain execution)  
✅ **Mail content non-executable** - Verified (Calyx Mail v0.1 design)  
✅ **No control-plane semantics** - Verified (v0.1 design)

**Result:** ✅ **ALL GOVERNANCE INVARIANTS MAINTAINED**

---

## Commit Details

**Commit:** `79f384b`  
**Message:** "Fix Python compilation to use existing files only"  
**Files Changed:** 1 file
- `.github/workflows/public-repo-hygiene.yml` - Updated Python compilation step

---

## Expected Workflow Behavior

After push, the Public Repo Hygiene workflow should:

1. ✅ **Forbidden paths check** - Run successfully using `grep -E`
   - Expected log: `No forbidden tracked paths detected.`

2. ✅ **Gitleaks scan** - Load config from `.gitleaks.toml` and scan repository
   - Expected log: `no leaks found` or similar success message

3. ✅ **Python compilation** - Compile all Python files in `calyx/` and `tools/`
   - Expected log: `py_compile completed with exit code 0` or successful compilation

4. ✅ **Workflow passes** - All checks green

---

## Next Steps

1. ⏳ **Verify GitHub Actions workflow passes** (check Actions tab after push)
2. ⏳ **Confirm forbidden paths check** - Log shows "No forbidden tracked paths detected."
3. ⏳ **Confirm gitleaks scan** - Log shows "no leaks found"
4. ⏳ **Confirm Python compilation** - Log shows successful compilation with exit code 0

---

**Status:** ✅ **FIX APPLIED AND PUSHED**

**Pending:** GitHub Actions workflow verification (requires manual check after workflow completes)
