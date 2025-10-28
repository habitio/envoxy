#!/usr/bin/env bash
# Do NOT use set -e: we want this script to be best-effort and never fail the build
set -uo pipefail
# Print commands for debugging inside manylinux container
set -x

echo "CI: patch_uwsgi.sh starting (idempotent)"

# Log errors but continue - this is a best-effort helper script
trap 'echo "CI: patch_uwsgi.sh encountered an error at line $LINENO (exit $?). Continuing."' ERR

# This script runs inside the manylinux container (cibuildwheel mounts the repo at /project)
# It performs minimal, idempotent patches to the vendored uWSGI sources so the Python
# plugin will link correctly when the container Python is static (libpython*.a).


PY_BIN=${1:-python}

# Upgrade pip, setuptools, and wheel inside the manylinux container to ensure modern
# packaging tools are used (avoids legacy License-File metadata generation).
echo "CI: upgrading pip, setuptools, wheel in manylinux container"
${PY_BIN} -m pip install --upgrade pip setuptools wheel || echo "CI: pip upgrade failed (non-fatal)"

# Detect package manager and attempt to install common build dependencies used by
# the Ubuntu-based publish workflow. Manylinux images vary; try several managers
# and make installs best-effort (non-fatal) so diagnostics remain useful.
echo "CI: detecting package manager inside container"
PKG_MGR=""
if command -v apt-get >/dev/null 2>&1; then
    PKG_MGR=apt-get
elif command -v yum >/dev/null 2>&1; then
    PKG_MGR=yum
elif command -v dnf >/dev/null 2>&1; then
    PKG_MGR=dnf
elif command -v microdnf >/dev/null 2>&1; then
    PKG_MGR=microdnf
elif command -v zypper >/dev/null 2>&1; then
    PKG_MGR=zypper
elif command -v apk >/dev/null 2>&1; then
    PKG_MGR=apk
fi

echo "CI: package manager detected: ${PKG_MGR:-none}"
if [ -n "${PKG_MGR}" ]; then
    echo "CI: attempting to install native build dependencies (best-effort)"
    case "${PKG_MGR}" in
        apt-get)
            apt-get update || true
            DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
                build-essential gcc make pkg-config python3-dev libpython3-dev \
                libsystemd-dev libssl-dev zlib1g-dev libpq-dev || true
            ;;
        yum|dnf)
            ${PKG_MGR} install -y gcc make pkgconfig python3-devel redhat-rpm-config \
                systemd-devel openssl-devel zlib-devel postgresql-devel || true
            ;;
        microdnf)
            microdnf install -y gcc make pkg-config python3-devel systemd-devel \
                openssl-devel zlib-devel postgresql-devel || true
            ;;
        zypper)
            zypper --non-interactive install -y gcc make pkg-config python3-devel \
                libsystemd-devel libopenssl-devel zlib-devel postgresql-devel || true
            ;;
        apk)
            apk add --no-cache build-base pkgconfig python3-dev libressl-dev zlib-dev \
                postgresql-dev linux-headers || true
            ;;
        *)
            echo "CI: unknown package manager ${PKG_MGR}; skipping native deps install"
            ;;
    esac
else
    echo "CI: no package manager detected; skipping native deps install"
fi

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
    # Note: Vendor packages like envoxyd have their own pyproject.toml committed
    # to the repository, so no need to copy or patch them.

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
# operate on the absolute file under $TARGET to avoid truncation when the
# script is invoked from a different working directory. Back up first and only
# run the sed replacement if the file exists and the backup succeeds.
UWSGI_CFG_SRC="$TARGET/uwsgiconfig.py"
UWSGI_CFG_BAK="${UWSGI_CFG_SRC}.ci-orig"
if [ -f "${UWSGI_CFG_SRC}" ]; then
    echo "CI: backing up ${UWSGI_CFG_SRC} -> ${UWSGI_CFG_BAK}"
    cp -a "${UWSGI_CFG_SRC}" "${UWSGI_CFG_BAK}" || {
        echo "CI: backup failed; skipping sed replacement"
    }
    if [ -f "${UWSGI_CFG_BAK}" ]; then
        echo "CI: removing literal -lpython* occurrences from ${UWSGI_CFG_SRC} (safe)"
        sed -E "s/\-lpython[0-9]+(\.[0-9]+)?//g" "${UWSGI_CFG_BAK}" > "${UWSGI_CFG_SRC}.ci-sed" || true
        # if sed produced a file, replace the original atomically
        if [ -s "${UWSGI_CFG_SRC}.ci-sed" ]; then
            mv "${UWSGI_CFG_SRC}.ci-sed" "${UWSGI_CFG_SRC}" || true
            echo "CI: applied sed patch to ${UWSGI_CFG_SRC}"
        else
            echo "CI: sed produced empty or missing output; restoring backup"
            cp -a "${UWSGI_CFG_BAK}" "${UWSGI_CFG_SRC}" || true
            rm -f "${UWSGI_CFG_SRC}.ci-sed" || true
        fi
    fi
else
    echo "CI: ${UWSGI_CFG_SRC} not found; skipping uwsgiconfig sed patch"
fi

echo "CI: Build static Python library for portable uWSGI embedding"

# Get Python version from running interpreter
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
PYTHON_SHORT_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "CI: Detected Python version: $PYTHON_VERSION (short: $PYTHON_SHORT_VERSION)"

# Set build paths
STATIC_PYTHON_PREFIX="/tmp/python-static-${PYTHON_VERSION}"
STATIC_LIB_PATH="${STATIC_PYTHON_PREFIX}/lib/libpython${PYTHON_SHORT_VERSION}.a"

# Check if static library already exists (from cache or previous run)
if [ -f "${STATIC_LIB_PATH}" ]; then
    echo "CI: Static Python library already exists at ${STATIC_LIB_PATH}"
else
    echo "CI: Building static Python ${PYTHON_VERSION} from source..."
    
    # Download Python source
    PYTHON_TAR_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
    PYTHON_SRC_DIR="/tmp/Python-${PYTHON_VERSION}"
    
    echo "CI: Downloading Python source from ${PYTHON_TAR_URL}"
    curl -L -o "/tmp/Python-${PYTHON_VERSION}.tgz" "${PYTHON_TAR_URL}" || {
        echo "CI: ERROR - Failed to download Python source"
        exit 1
    }
    
    echo "CI: Extracting Python source..."
    tar -xzf "/tmp/Python-${PYTHON_VERSION}.tgz" -C /tmp || {
        echo "CI: ERROR - Failed to extract Python source"
        exit 1
    }
    
    cd "${PYTHON_SRC_DIR}" || {
        echo "CI: ERROR - Failed to cd to Python source directory"
        exit 1
    }
    
    echo "CI: Configuring Python with --enable-static..."
    # Disable SSL and other optional modules that may have compatibility issues
    # uWSGI only needs the core interpreter, not SSL or other optional extensions
    ./configure \
        --prefix="${STATIC_PYTHON_PREFIX}" \
        --enable-static \
        --disable-shared \
        --without-ensurepip \
        --disable-test-modules \
        --without-ssl 2>&1 | tail -50 || {
        echo "CI: ERROR - Python configure failed"
        exit 1
    }
    
    echo "CI: Explicitly disabling problematic modules in Modules/Setup.local..."
    # Python's configure still tries to build some modules even with flags,
    # so we explicitly disable them in the Setup file
    # - _ssl: requires OpenSSL 3.0+ (manylinux has 1.1.1)
    # - _hashlib: depends on OpenSSL
    # - _locale: requires libintl which isn't available separately in manylinux
    echo "*disabled*" >> Modules/Setup.local
    echo "_ssl" >> Modules/Setup.local
    echo "_hashlib" >> Modules/Setup.local
    echo "_locale" >> Modules/Setup.local
    
    echo "CI: Building Python (this may take several minutes)..."
    make -j$(nproc) 2>&1 | tail -100 || {
        echo "CI: ERROR - Python build failed"
        exit 1
    }
    
    echo "CI: Installing Python to ${STATIC_PYTHON_PREFIX}..."
    make install 2>&1 | tail -50 || {
        echo "CI: ERROR - Python install failed"
        exit 1
    }
    
    # Return to original directory
    cd "${TARGET}" || exit 1
    
    # Verify static library was created
    if [ -f "${STATIC_LIB_PATH}" ]; then
        echo "CI: SUCCESS - Static library created at ${STATIC_LIB_PATH}"
        ls -lh "${STATIC_LIB_PATH}"
    else
        echo "CI: ERROR - Static library not found at ${STATIC_LIB_PATH}"
        echo "CI: Contents of ${STATIC_PYTHON_PREFIX}/lib:"
        ls -la "${STATIC_PYTHON_PREFIX}/lib/" 2>/dev/null || echo "Directory does not exist"
        exit 1
    fi
fi

echo "CI: Patch uwsgiconfig.py to inject static Python library before linking"

UWSGI_CONFIG="$TARGET/uwsgiconfig.py"
if [ -f "${UWSGI_CONFIG}" ]; then
    if ! grep -q "# CI: Inject static Python library" "${UWSGI_CONFIG}"; then
        cp -a "${UWSGI_CONFIG}" "${UWSGI_CONFIG}.ci-orig" || true
        
        # Find the line with '*** uWSGI linking ***' and inject our code before it
        # Export environment variables for Python script
        export UWSGI_CONFIG
        export STATIC_LIB_PATH
        python3 <<'PYPATCH'
import sys
import os

uwsgi_config = os.environ['UWSGI_CONFIG']
static_lib_path = os.environ.get('STATIC_LIB_PATH', '')

with open(uwsgi_config, 'r') as f:
    lines = f.readlines()

# Find the line with 'print("*** uWSGI linking ***")'
inject_index = None
for i, line in enumerate(lines):
    if '*** uWSGI linking ***' in line and 'print' in line:
        inject_index = i
        break

if inject_index is None:
    print("ERROR: Could not find linking section in uwsgiconfig.py", file=sys.stderr)
    sys.exit(1)

# Inject our static library code just before the linking print statement
# Note: os module is already imported at top of uwsgiconfig.py, don't re-import it
injection = '''    # CI: Inject static Python library before linking
    try:
        # Remove dynamic Python library references
        libs[:] = [l for l in libs if not (isinstance(l, str) and l.startswith('-lpython'))]
        print("CI: Removed dynamic -lpython* from libs", file=sys.stderr)
        
        # Use the static library built in CI
        static_lib_path = os.environ.get('STATIC_LIB_PATH', '')
        
        if static_lib_path and os.path.isfile(static_lib_path):
            print(f"CI: Using CI-built static library: {static_lib_path}", file=sys.stderr)
            if static_lib_path not in libs:
                libs.append(static_lib_path)
                print(f"CI: Added static library to libs", file=sys.stderr)
            
            # Static linking requires explicitly adding all dependencies
            # Note: _locale module is disabled, so we don't need -lintl
            required_libs = [
                '-lpthread',   # threading support
                '-ldl',        # dynamic loading support
                '-lutil',      # pty and login utilities
                '-lm',         # math library
            ]
            
            for lib in required_libs:
                if lib not in libs:
                    libs.append(lib)
                    print(f"CI: Added {lib} for static Python", file=sys.stderr)
        else:
            print(f"CI: ERROR - Static library not found at: {static_lib_path}", file=sys.stderr)
            print("CI: Attempting to continue anyway, but linking will likely fail", file=sys.stderr)
        
        print(f"CI: Total libs count: {len(libs)}", file=sys.stderr)
        print(f"CI: Python-related libs: {[l for l in libs if 'python' in str(l).lower()]}", file=sys.stderr)
    except Exception as ex:
        import traceback
        print(f"CI: Error injecting Python library: {ex}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    
'''

lines.insert(inject_index, injection)

with open(uwsgi_config, 'w') as f:
    f.writelines(lines)

print(f"Successfully patched {uwsgi_config}")
PYPATCH
        
        if [ $? -eq 0 ]; then
            echo "CI: Successfully patched ${UWSGI_CONFIG}"
        else
            echo "ERROR: Failed to patch ${UWSGI_CONFIG}"
            exit 1
        fi
    else
        echo "CI: ${UWSGI_CONFIG} already patched"
    fi
else
    echo "CI: ${UWSGI_CONFIG} not found; cannot patch"
    exit 1
fi

echo "CI: diagnostics: sysconfig variables (LDLIBRARY, LIBDIR)"
"${PY_BIN}" - <<'PY'
import sysconfig, pprint
info = {k: sysconfig.get_config_var(k) for k in ('LDLIBRARY','LIBDIR','LIBPL')}
pprint.pprint(info)
import sys
print('python:', sys.version)
PY

echo "CI: attempt to build uWSGI binary if the vendor expects it"
# The vendor package expects a binary at vendors/src/envoxyd/envoxyd
DEST_BIN="/project/vendors/src/envoxyd/envoxyd"
if [ ! -f "$DEST_BIN" ]; then
    echo "CI: $DEST_BIN not present; attempting build in $TARGET"
    if [ -f "./uwsgiconfig.py" ]; then
        # Copy all uwsgi template files from envoxyd into uwsgi source directory
        echo "CI: copying uwsgi template files from envoxyd"
        if [ -d "/project/vendors/envoxyd/templates/uwsgi" ]; then
            cp -r /project/vendors/envoxyd/templates/uwsgi/* . || true
            echo "CI: copied all uwsgi template files (buildconf, embed, etc.)"
            ls -lah buildconf embed 2>/dev/null || echo "CI: template directories copied"
        fi
        # Also copy run.py from templates root into embed directory if it exists
        if [ -f "/project/vendors/envoxyd/templates/run.py" ]; then
            mkdir -p embed
            cp /project/vendors/envoxyd/templates/run.py embed/ || true
            echo "CI: copied run.py into embed directory"
        fi
        
        echo "CI: running uwsgiconfig.py --build flask (with verbose output)"
        echo "CI: listing current directory before build:"
        ls -lah . | head -20
        
        # Run the build with full output visible
        "${PY_BIN}" uwsgiconfig.py --build flask 2>&1 | tee /tmp/uwsgi-build.log || {
            echo "ERROR: uwsgiconfig build failed! Last 50 lines of output:"
            tail -50 /tmp/uwsgi-build.log || true
            exit 1
        }
        
        echo "CI: build command completed. Listing directory after build:"
        ls -lah . | head -30
        echo "CI: build command completed. Listing directory after build:"
        ls -lah . | head -30
        
        echo "CI: searching for any files named uwsgi* or containing 'uwsgi' in name:"
        find . -maxdepth 2 -type f -iname '*uwsgi*' -ls || true

        # common output names - the flask profile produces a binary named 'envoxyd'
        for cand in envoxyd uwsgi uwsgi-core uwsgi.bin; do
            if [ -f "$cand" ] && [ -x "$cand" ]; then
                # Verify it's a real binary, not a script
                if file "$cand" | grep -q 'ELF'; then
                    mkdir -p "$(dirname "$DEST_BIN")"
                    cp "$cand" "$DEST_BIN" || true
                    chmod +x "$DEST_BIN" || true
                    echo "CI: copied built ELF binary $cand to $DEST_BIN"
                    break
                fi
            fi
        done

        # fallback: search for any executable ELF binary in the current directory
        if [ ! -f "$DEST_BIN" ]; then
            foundbin=$(find . -maxdepth 1 -type f -executable -exec file {} \; | grep 'ELF' | head -1 | cut -d: -f1 || true)
            if [ -n "$foundbin" ]; then
                mkdir -p "$(dirname "$DEST_BIN")"
                cp "$foundbin" "$DEST_BIN" || true
                chmod +x "$DEST_BIN" || true
                echo "CI: copied found ELF binary $foundbin to $DEST_BIN"
            else
                echo "ERROR: no uwsgi ELF binary found after build!"
                exit 1
            fi
        fi
    else
        echo "ERROR: no uwsgiconfig.py in $TARGET; cannot build!"
        exit 1
    fi
else
    echo "CI: $DEST_BIN already present; skipping build"
fi

echo "CI: =========================================="
echo "CI: Final binary verification"
echo "CI: =========================================="
if [ -f "$DEST_BIN" ]; then
    echo "CI: SUCCESS - Binary exists at: $DEST_BIN"
    ls -lh "$DEST_BIN"
    file "$DEST_BIN" || true
    ldd "$DEST_BIN" 2>&1 | head -20 || true
    
    # Set RPATH to allow auditwheel to properly bundle libraries
    echo "CI: Setting RPATH for auditwheel compatibility"
    if command -v patchelf >/dev/null 2>&1; then
        # Set RPATH to find bundled .so files
        # Binary will be in: {prefix}/bin/envoxyd
        # Libs will be in: {prefix}/lib/python${PYTHON_SHORT_VERSION}/site-packages/envoxyd.libs/
        # Relative path from bin/ to libs: ../lib/python${PYTHON_SHORT_VERSION}/site-packages/envoxyd.libs
        patchelf --set-rpath "\$ORIGIN/../lib/python${PYTHON_SHORT_VERSION}/site-packages/envoxyd.libs" "$DEST_BIN" || {
            echo "WARNING: patchelf failed to set RPATH, continuing anyway"
        }
        echo "CI: RPATH set for $DEST_BIN"
        patchelf --print-rpath "$DEST_BIN" || true
    else
        echo "WARNING: patchelf not available, RPATH not set. Install it for proper library bundling."
    fi
else
    echo "CI: ERROR - Binary NOT found at: $DEST_BIN"
    echo "CI: Searching for any uwsgi binaries in /project/vendors:"
    find /project/vendors -name '*uwsgi*' -type f -executable -ls 2>/dev/null || true
    exit 1
fi

echo "CI: patch_uwsgi.sh complete"
