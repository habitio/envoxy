#!/bin/sh
set -euo pipefail

echo "=== Patching uwsgiconfig.py to remove Python library linking ==="

# The first argument (optional) is the Python interpreter path that cibuildwheel provides
# when running CIBW_BEFORE_BUILD via the {python} placeholder. Use it if present so all
# diagnostics and the uwsgiconfig build run with the same interpreter.
PY_BIN=${1:-python}

# Work on a backup so we can inspect differences in the build logs.
cp -a uwsgiconfig.py uwsgiconfig.py.orig

echo "--- Before (relevant lines) ---"
# Use Python to print matching lines (portable inside manylinux image)
${PY_BIN} - <<'PY'
import sys
fn = 'uwsgiconfig.py'
for i, l in enumerate(open(fn, 'r'), 1):
	if 'ldflag' in l or 'lpython' in l:
		sys.stdout.write(f"{i}:{l}")
PY

# Try a few safe regexes to match common ways uWSGI builds the ldflags.
# 1) ldflag_lang = '-lpython' + python_version
# 2) patterns that include "-lpython" concatenation with variables/spaces

patched=0

# Pattern 1: direct assignment with concatenation
if ${PY_BIN} - <<'PY'
import re,sys
s = open('uwsgiconfig.py').read()
sys.exit(0 if re.search(r'ldflag_lang.*-lpython.*python_version', s) else 1)
PY
then
	sed -E "s/^[[:space:]]*ldflag_lang[[:space:]]*=[[:space:]]*'\\-lpython'[[:space:]]*\+[[:space:]]*python_version/    ldflag_lang = ''/g" uwsgiconfig.py > uwsgiconfig_temp.py && mv uwsgiconfig_temp.py uwsgiconfig.py && patched=1
fi

# Pattern 2: occurrences of \"-lpython" followed by + python_version anywhere
if [ "$patched" -eq 0 ] && ${PY_BIN} - <<'PY'
import re,sys
s = open('uwsgiconfig.py').read()
sys.exit(0 if re.search(r"-lpython.*\+.*python_version", s) else 1)
PY
then
	sed -E "s/'-lpython'\s*\+\s*python_version/''/g" uwsgiconfig.py > uwsgiconfig_temp.py && mv uwsgiconfig_temp.py uwsgiconfig.py && patched=1
fi

# Pattern 3: remove any literal -lpythonX.Y inserted into ldflags (fallback)
if [ "$patched" -eq 0 ]; then
	# Replace occurrences like '-lpython3.12' (only literal strings) with empty string.
	sed -E "s/\\-lpython[0-9]+(\\.[0-9]+)?//g" uwsgiconfig.py > uwsgiconfig_temp.py && mv uwsgiconfig_temp.py uwsgiconfig.py && patched=1 || true
fi

echo "--- After (relevant lines) ---"
${PY_BIN} - <<'PY'
import sys
fn = 'uwsgiconfig.py'
for i, l in enumerate(open(fn, 'r'), 1):
	if 'ldflag' in l or 'lpython' in l:
		sys.stdout.write(f"{i}:{l}")
PY

if ${PY_BIN} - <<'PY'
import sys
s = open('uwsgiconfig.py').read()
sys.exit(0 if '-lpython' in s else 1)
PY
then
	echo "!!! Warning: -lpython still present in uwsgiconfig.py; build may fail. Showing full file for debugging:"
	sed -n '1,240p' uwsgiconfig.py || true
fi

echo "=== Building uWSGI ==="
# Show Python sysconfig values that may contribute linker flags
echo "--- Python sysconfig (diagnostics) ---"
${PY_BIN} - <<'PY'
import sys, sysconfig
keys = ["LIBS", "LINKFORSHARED", "LDLIBRARY", "LIBDIR", "SO"]
for k in keys:
	try:
		print(k + ':', repr(sysconfig.get_config_var(k)))
	except Exception as e:
		print(k + ':', 'ERROR', e)
print('sys.version:', sys.version)
PY

# Clean LDFLAGS from any -lpythonX.Y occurrences that break linking in manylinux
# Default to empty if LDFLAGS is unset
LDFLAGS=${LDFLAGS:-}
echo "Original LDFLAGS: '${LDFLAGS}'"
clean_ldflags=$(printf "%s" "${LDFLAGS}" | sed -E "s/\\-lpython[0-9]+(\\.[0-9]+)?//g")
export LDFLAGS="${clean_ldflags}"
echo "Cleaned LDFLAGS: '${LDFLAGS}'"

# Instead of disabling the plugin logic, patch the plugin so it will append the
# full path to the static libpython archive (if present). This is less intrusive
# and ensures the archive appears in the final LIBS list (after objects).

# Patch plugins/python/uwsgiplugin.py inside the source tree so it will append
# LIBDIR/LDLIBRARY when LDLIBRARY is a .a file and exists. The patch is idempotent.
PLUGIN_FILE="plugins/python/uwsgiplugin.py"
if [ -f "${PLUGIN_FILE}" ]; then
	if ! grep -q "# envoxy: append static libpython if present" "${PLUGIN_FILE}"; then
		echo "Patching ${PLUGIN_FILE} to prefer explicit static lib path if available"
		cp -a "${PLUGIN_FILE}" "${PLUGIN_FILE}.orig"
		cat >> "${PLUGIN_FILE}" <<'PYPATCH'
# envoxy: append static libpython if present
try:
	import sysconfig, os
	_ldlib = sysconfig.get_config_var('LDLIBRARY') or ''
	_libdir = sysconfig.get_config_var('LIBDIR') or ''
	if _ldlib.endswith('.a'):
		_candidate = os.path.join(_libdir, _ldlib)
		if os.path.exists(_candidate):
			try:
				if _candidate not in LIBS:
					LIBS.append(_candidate)
			except Exception:
				pass
except Exception:
	pass
PYPATCH
	else
		echo "${PLUGIN_FILE} already patched"
	fi
else
	echo "Warning: ${PLUGIN_FILE} not found; skipping plugin patch"
fi

# If the Python interpreter in the build environment provides a static libpython (e.g. libpython3.X.a),
# link that archive explicitly so Python API symbols are satisfied at link time.
PY_LIB_INFO=$(${PY_BIN} - <<'PY'
import sysconfig
ld = sysconfig.get_config_var('LDLIBRARY') or ''
libdir = sysconfig.get_config_var('LIBDIR') or ''
print(libdir + '||' + ld)
PY
)
PY_LIBDIR=${PY_LIB_INFO%%||*}
PY_LDLIB=${PY_LIB_INFO##*||}
if [ -n "${PY_LDLIB}" ] && printf "%s" "${PY_LDLIB}" | grep -q "\.a$"; then
	# Add full path to static libpython to LDFLAGS so ld pulls in the archive
	PY_STATIC_PATH="${PY_LIBDIR%/}/${PY_LDLIB}"
	echo "Detected static python library: ${PY_STATIC_PATH}"
	# Only append if not already present
	case " ${LDFLAGS} " in
		*" ${PY_STATIC_PATH} "*) echo "static python lib already in LDFLAGS" ;;
		*) export LDFLAGS="${LDFLAGS} ${PY_STATIC_PATH}" ; echo "Updated LDFLAGS: '${LDFLAGS}'" ;;
	esac
fi

# Choose a sane build profile: prefer 'flask' if present, otherwise fall back to
# a known python-enabled profile (default, pyonly, pyuwsgi). This avoids
# FileNotFoundError when a specific profile name isn't shipped in the uwsgi
# sources used by the repo.
PROFILE=""
for p in flask default pyonly pyuwsgi; do
	if [ -f "buildconf/${p}.ini" ]; then
		PROFILE=${p}
		break
	fi
done
if [ -z "${PROFILE}" ]; then
	echo "No known build profile found in buildconf/; running uwsgiconfig.py without --build (default behaviour)"
	${PY_BIN} uwsgiconfig.py
else
	echo "using profile: buildconf/${PROFILE}.ini"
	${PY_BIN} uwsgiconfig.py --build "${PROFILE}"
fi
