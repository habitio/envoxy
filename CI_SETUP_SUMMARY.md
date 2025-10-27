# CI/CD Setup Summary - Envoxy Project

**Date:** October 24, 2025  
**Branch:** feature/python3_12  
**Goal:** Produce Python 3.12 manylinux wheels for envoxyd (which includes native uWSGI plugin)

---

## Current State

### What We Have

1. **Two GitHub Actions Workflows:**

   - `.github/workflows/build-manylinux-cp312.yml` - NEW cibuildwheel-based workflow (Python 3.12 manylinux wheels)
   - `.github/workflows/build-and-publish.yml` - EXISTING generic build workflow (non-manylinux wheels)

2. **CI Scripts:**

   - `.github/ci/patch_uwsgi.sh` - Patches uWSGI inside manylinux containers to link static libpython correctly
   - `docker/dev/patch_and_build.sh` - Local dev helper (similar patching logic)

3. **Centralized Build Config:**
   - `pyproject.toml` (root) - Declares build backend, cibuildwheel defaults

### The Core Problem

**envoxyd contains a native uWSGI plugin that must be compiled.**

When building inside manylinux containers (required for PyPI binary wheels):

- The manylinux Python interpreter is often statically linked (no `libpython.so`)
- uWSGI's Python plugin tries to add `-lpython3.12` which fails in manylinux
- We need to either:
  - Skip adding `-lpython*` flags (but then get undefined Python C-API symbols), OR
  - Append the full path to the static archive `libpython*.a` to LIBS (must come AFTER object files in link order)

**Current patch approach:** `.github/ci/patch_uwsgi.sh` attempts to:

1. Remove literal `-lpython*` from `uwsgiconfig.py`
2. Append a snippet to `plugins/python/uwsgiplugin.py` that adds the static lib path to LIBS if found

**Status:** Not yet verified to work in manylinux container (need to see actual CI logs from a GitHub run).

---

## Workflow Comparison

### Option A: `build-manylinux-cp312.yml` (NEW - cibuildwheel)

**Purpose:** Produce manylinux binary wheels for Python 3.12 via cibuildwheel

**Triggers:**

- Push to `main` or `feature/python3_12`
- Pull requests
- Manual dispatch

**What it does:**

- Runs build matrix on Ubuntu 20.04, 22.04, 24.04
- Uses `pypa/cibuildwheel@v3` to build inside manylinux Docker containers
- Runs `.github/ci/patch_uwsgi.sh` via `CIBW_BEFORE_BUILD` before each build
- Uploads artifacts per runner: `manylinux-cp312-wheels-ubuntu-XX.04`
- Has a publish job that runs ONLY on tag pushes (`refs/tags/*`) - downloads all artifacts and uploads to TestPyPI

**Problems:**

1. ❌ Workflow doesn't trigger on tag pushes (missing `tags:` in `on.push`)
2. ❌ Not verified: uWSGI linking may still fail inside manylinux (need to see CI logs)
3. ❌ `pyproject.toml` copying happens on runner before cibuildwheel, but cibuildwheel runs in a different container - may not see the copied file
4. ✅ Uses proper manylinux tooling (good for PyPI)

### Option B: `build-and-publish.yml` (EXISTING - generic)

**Purpose:** Build source dist + generic platform wheel + publish to PyPI/TestPyPI

**Triggers:**

- Tag pushes `v*.*.*`
- Manual dispatch with publish target choice

**What it does:**

- Runs `python -m build` on the runner (NOT manylinux)
- Produces sdist + wheel for envoxy and envoxyd
- Has conditional publish jobs for TestPyPI and PyPI
- Also builds Docker images on tag pushes

**Problems:**

1. ❌ **Critical bug:** Artifact path mismatch
   - Upload: `vendors/dist/` → artifact `envoxyd-packages`
   - Download: downloads to `vendors-dist/` (hyphen)
   - Publish: tries to publish from `vendors-dist/` - may work by accident but inconsistent
2. ❌ Builds generic wheels, NOT manylinux wheels - won't install on other Linux systems for binary packages
3. ❌ Missing `pyproject.toml` in sdists causes PEP 517 isolated build failures (the error you saw)
4. ✅ Has working PyPI publish logic with environments/secrets

---

## Root Cause of "Infinite Cycle"

**The confusion:** You have TWO workflows that do similar but incompatible things:

- One tries to produce manylinux wheels (new, not fully working yet)
- One produces generic wheels and tries to publish (existing, has bugs)

**Neither is complete:**

- Manylinux workflow: builds wheels but publish only works on tags (and tags don't trigger it)
- Generic workflow: publishes but produces wrong wheel type and has sdist → wheel build failures

**Result:** Switching between them, hitting different errors, going in circles.

---

## Recommended Solution (Pick ONE Path)

### Path 1: Use cibuildwheel for envoxyd, fix and consolidate (RECOMMENDED)

**Goal:** Single workflow that produces correct manylinux wheels and publishes them.

**Steps:**

1. Fix `build-manylinux-cp312.yml`:

   - Add `tags: ['v*']` to trigger on tag pushes
   - Fix pyproject.toml copying to happen inside the manylinux container (move copy logic into `.github/ci/patch_uwsgi.sh`)
   - Add listing step before publish to verify wheels
   - Verify uWSGI linking works (run workflow, check logs, iterate patch script if needed)

2. Update `build-and-publish.yml`:

   - Remove envoxyd building from this workflow (or keep sdist only)
   - Use envoxy for pure-python wheels (those don't need manylinux)
   - Delegate envoxyd binary wheel building to the cibuildwheel workflow
   - Merge publish jobs into one workflow or coordinate artifacts between workflows

3. Test flow:
   - Push feature branch → cibuildwheel builds wheels, uploads as artifacts
   - Push tag → both workflows run, cibuildwheel produces binary wheels, generic produces sdist, both publish to PyPI

**Pros:**

- Correct manylinux wheels for PyPI
- Automated on tag pushes
- Uses industry-standard tooling (cibuildwheel)

**Cons:**

- More complex (two workflows coordinating)
- Need to ensure artifacts don't collide

### Path 2: Simplify - build manylinux wheels in existing workflow

**Goal:** Modify `build-and-publish.yml` to use cibuildwheel for envoxyd.

**Steps:**

1. Keep `build-and-publish.yml` as the main workflow
2. Add pyproject.toml copying step before builds
3. Replace the envoxyd `python -m build` step with cibuildwheel invocation
4. Fix artifact path bug
5. Remove the separate `build-manylinux-cp312.yml` workflow (or keep it for testing only)

**Pros:**

- Single workflow (simpler mental model)
- Already has publish logic

**Cons:**

- Mixing cibuildwheel with generic builds in one workflow can be confusing
- Existing workflow already complex with Docker builds, manual dispatch inputs, etc.

---

## Immediate Next Steps (to break the cycle)

### Step 1: Fix the pyproject.toml issue (BLOCKS BOTH WORKFLOWS)

**Problem:** sdist → wheel builds fail with `FileNotFoundError: pyproject.toml`

**Solution:** Ensure `pyproject.toml` is included in sdists.

**Action:** Add this to `vendors/setup.py` MANIFEST to include pyproject.toml:

```python
# OR create vendors/MANIFEST.in with:
include pyproject.toml
```

Alternatively, ensure the workflow copies `pyproject.toml` into `vendors/` BEFORE running `python -m build`.

### Step 2: Choose which workflow to use as primary

**Decision point:** Do you want:

- A) Manylinux wheels (required for PyPI binary packages) → use/fix `build-manylinux-cp312.yml`
- B) Simple generic wheels (fine for internal use, won't work on other Linux systems) → use `build-and-publish.yml` but fix it

### Step 3: Run ONE workflow end-to-end and iterate

Pick the workflow, push branch, watch the logs, fix ONE error at a time.

**For manylinux workflow:**

```bash
# Add tag trigger and test
git add .github/workflows/build-manylinux-cp312.yml
git commit -m "Fix manylinux workflow triggers"
git push origin feature/python3_12
# Then manually trigger from Actions tab or push a test tag
```

**For generic workflow:**

```bash
# Fix artifact paths and add pyproject copy
git add .github/workflows/build-and-publish.yml
git commit -m "Fix artifact paths and pyproject inclusion"
git push origin feature/python3_12
# Manually dispatch with publish_to: none
```

---

## Quick Reference

### Files Created/Modified in This Session

**Workflows:**

- `.github/workflows/build-manylinux-cp312.yml` - NEW cibuildwheel workflow
- `.github/workflows/build-and-publish.yml` - EXISTING (not modified by me)

**CI Scripts:**

- `.github/ci/patch_uwsgi.sh` - NEW uWSGI patcher for manylinux
- `docker/dev/patch_and_build.sh` - local dev helper
- `docker/dev/dev.sh` - local envoxy-build helper

**Config:**

- `pyproject.toml` (root) - NEW centralized build config

### Environment Variables / Secrets Needed

For TestPyPI publish:

- `TEST_PYPI_API_TOKEN` (repo secret)

For PyPI publish:

- `PYPI_API_TOKEN` (repo secret)

### How to Test Locally (without CI)

Not possible for manylinux builds (need Docker + cibuildwheel).

For generic builds:

```bash
# From repo root
cp pyproject.toml vendors/
cd vendors
python -m build
# Check if wheel builds without errors
```

---

## My Recommendation

**Do this NOW to break the cycle:**

1. **Fix pyproject.toml in sdists** (5 minutes)

   - Create `vendors/MANIFEST.in` with `include pyproject.toml`
   - OR ensure workflow copies it before build

2. **Pick ONE workflow to debug** (choose based on your goal)

   - If you need PyPI-compatible manylinux wheels: fix `build-manylinux-cp312.yml`
   - If you just need wheels that work on your systems: fix `build-and-publish.yml`

3. **Run that ONE workflow** (20 minutes)

   - Push or manually trigger
   - Look at logs
   - Fix ONE error
   - Repeat until build succeeds

4. **Only then worry about publishing**
   - First get builds working
   - Then wire up publish steps

**Stop switching between workflows.** Pick one, make it work, then integrate the other if needed.

---

## Questions to Answer (helps me help you)

1. **Do you need manylinux wheels?** (yes if publishing to PyPI, no if only using internally)
2. **Which workflow do you want to be the "main" one?**
3. **Do you want to publish automatically on tag push, or manually via workflow_dispatch?**

Answer these and I can give you a concrete 3-step fix to apply right now.
