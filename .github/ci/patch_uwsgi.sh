#!/usr/bin/env bash
set -uo pipefail
# Print commands for debugging inside manylinux container
set -x

echo "CI: patch_uwsgi.sh starting (idempotent)"

# If anything errors, trap and continue the build (we don't want this helper to
# fail the whole wheel build). Log the error code for debugging.
trap 'echo "CI: patch_uwsgi.sh encountered an error (exit $?). Continuing."' ERR

# This script runs inside the manylinux container (cibuildwheel mounts the repo at /project)
# It performs minimal, idempotent patches to the vendored uWSGI sources so the Python
# plugin will link correctly when the container Python is static (libpython*.a).


PY_BIN=${1:-python}

# Ensure the project directory being built (e.g. /project/vendors) has a pyproject.toml
# by copying the centralized /project/pyproject.toml into it when missing. This allows
# PEP 517 isolated builds inside the manylinux container to discover the build backend.
if [ -f /project/pyproject.toml ]; then
    # cibuildwheel invokes CIBW_BEFORE_BUILD from the package build dir (e.g. /project/vendors/uwsgi),
    # so compute the expected package root and ensure it contains pyproject.toml
    PKG_ROOT="/project/vendors"
    if [ ! -f "${PKG_ROOT}/pyproject.toml" ]; then
        echo "CI: copying top-level pyproject.toml into ${PKG_ROOT}"
        cp /project/pyproject.toml "${PKG_ROOT}/pyproject.toml" || true
    else
        echo "CI: ${PKG_ROOT}/pyproject.toml already present"
    fi
    # Also copy pyproject.toml into any package directories under /project/vendors
    # so that sdists produced inside the manylinux container include the file.
    for d in /project/vendors/*; do
        if [ -d "$d" ]; then
            if [ ! -f "$d/pyproject.toml" ]; then
                echo "CI: copying pyproject.toml into $d"
                cp /project/pyproject.toml "$d/pyproject.toml" || true
            fi
        fi
    done

fi

# --- CI debug: show pyproject and vendor layout to help diagnose builds ---
echo "CI: top-level /project/pyproject.toml (first 200 lines):"
sed -n '1,200p' /project/pyproject.toml || echo "CI: /project/pyproject.toml not found"

echo "CI: listing /project/vendors and each vendor directory (for debug)"
ls -lah /project/vendors || echo "CI: /project/vendors not present"
for v in /project/vendors/*; do
    if [ -e "$v" ]; then
        echo "---- vendor: $v ----"
        ls -lah "$v" || true
        if [ -f "$v/pyproject.toml" ]; then
            echo "CI: $v/pyproject.toml (first 100 lines):"
            sed -n '1,100p' "$v/pyproject.toml" || true
        fi
    fi
done

echo "CI: listing native source files under /project/vendors (c, cpp, h, a, so, uwsgi Python plugin files)"
find /project/vendors -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.a' -o -name '*.so' -o -name 'uwsgiconfig.py' -o -name 'uwsgiplugin.py' \) -ls || true

# end debug section

# Locate the uWSGI source directory robustly. cibuildwheel sets the working
# directory according to {package} and that may vary; handle several common
# layouts and fall back to searching under /project.
TARGET=""
# If current dir already looks like the uwsgi source
if [ -f "./uwsgiconfig.py" ]; then
    TARGET="$(pwd)"
fi
# Prefer the vendors/uwsgi path if present
if [ -z "$TARGET" ] && [ -d "/project/vendors/uwsgi" ]; then
    TARGET="/project/vendors/uwsgi"
fi
# Fallback: search for a directory named 'uwsgi' under /project
if [ -z "$TARGET" ]; then
    found=$(find /project -maxdepth 4 -type d -name uwsgi 2>/dev/null | head -n1 || true)
    if [ -n "$found" ]; then
        TARGET="$found"
    fi
fi

if [ -z "$TARGET" ]; then
    echo "CI: no uwsgi directory found under /project; skipping patch"
    exit 0
fi

cd "$TARGET"

echo "CI: working in $(pwd)"
echo "CI: listing current directory for debug"
ls -lah || true

echo "CI: listing /project top-level for debug"
ls -lah /project || true

echo "CI: remove literal -lpython* occurrences from uwsgiconfig.py (if any)"
cp -a uwsgiconfig.py uwsgiconfig.py.ci-orig || true
# remove literal occurrences like -lpython3.8 or -lpython3.12 present in the file
sed -E "s/\-lpython[0-9]+(\.[0-9]+)?//g" uwsgiconfig.py.ci-orig > uwsgiconfig.py || true

echo "CI: ensure plugins/python/uwsgiplugin.py has idempotent append-to-LIBS logic"
PLUGIN_FILE="plugins/python/uwsgiplugin.py"
if [ -f "${PLUGIN_FILE}" ]; then
    if ! grep -q "# ci: append static libpython to LIBS" "${PLUGIN_FILE}"; then
        cp -a "${PLUGIN_FILE}" "${PLUGIN_FILE}.ci-orig" || true
        cat >> "${PLUGIN_FILE}" <<'PYAPP'
# ci: append static libpython to LIBS
try:
    import sysconfig, os
    _ldlib = sysconfig.get_config_var('LDLIBRARY') or ''
    _libdir = sysconfig.get_config_var('LIBDIR') or ''
    # also probe common /opt/python locations used by manylinux images
    candidates = []
    if _ldlib and _libdir:
        candidates.append(os.path.join(_libdir, _ldlib))
    # include /opt/_internal (some images use this layout)
    if _ldlib:
        candidates.append(os.path.join('/opt/_internal', _ldlib))
    # probe any /opt/python/*/lib directories for the ldlib name
    for base in ('/opt/python', '/opt'): 
        try:
            for p in os.listdir(base):
                candidates.append(os.path.join(base, p, 'lib', _ldlib))
        except Exception:
            pass
    for _c in candidates:
        try:
            if _c and os.path.exists(_c):
                try:
                    if _c not in LIBS:
                        LIBS.append(_c)
                        # if the library is a static archive, ensure we also add its dir to LDFLAGS rpath
                except Exception:
                    pass
                break
        except Exception:
            pass
except Exception:
    pass
PYAPP
        echo "CI: patched ${PLUGIN_FILE}"
    else
        echo "CI: ${PLUGIN_FILE} already patched"
    fi
else
    echo "CI: ${PLUGIN_FILE} not found; skipping plugin patch"
fi

echo "CI: diagnostics: sysconfig variables (LDLIBRARY, LIBDIR)"
"${PY_BIN}" - <<'PY'
import sysconfig, pprint
info = {k: sysconfig.get_config_var(k) for k in ('LDLIBRARY','LIBDIR','LIBPL')}
pprint.pprint(info)
import sys
print('python:', sys.version)
PY

echo "CI: patch_uwsgi.sh complete"
