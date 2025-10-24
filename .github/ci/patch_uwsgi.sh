#!/usr/bin/env bash
set -euo pipefail

echo "CI: patch_uwsgi.sh starting (idempotent)"

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
fi

cd /project/vendors/uwsgi

echo "CI: working in $(pwd)"

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
${PY_BIN} - <<'PY'
import sysconfig, pprint
info = {k: sysconfig.get_config_var(k) for k in ('LDLIBRARY','LIBDIR','LIBPL')}
pprint.pprint(info)
import sys
print('python:', sys.version)
PY

echo "CI: patch_uwsgi.sh complete"
