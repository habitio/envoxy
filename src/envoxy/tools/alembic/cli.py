"""Small CLI wrapper to run the framework-packaged Alembic configuration.

The module is import-safe (does not import alembic at import time). The
`main()` function locates the bundled `alembic.ini` via importlib.resources and
delegates to Alembic's CommandLine. This script is intended to be exposed as
`envoxy-alembic` via console_scripts so services can run migrations without
needing to know package installation paths.
"""

from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path
import tempfile
import configparser
import os


def _find_bundled_paths():
    pkg_root = resources.files("envoxy")
    base_dir = pkg_root.joinpath("tools", "alembic")
    ini_path = base_dir.joinpath("alembic.ini")
    script_dir = base_dir.joinpath("alembic")
    return ini_path, script_dir


def main(argv: list[str] | None = None) -> int:
    """Run Alembic CLI using the packaged alembic.ini.

    argv: list of arguments (without program name). Returns exit code.
    """
    argv = list(argv or sys.argv[1:])
    ini_path, packaged_script_dir = _find_bundled_paths()

    # Defer importing alembic until runtime so importing this module is safe
    try:
        from alembic.config import CommandLine
    except Exception as exc:  # pragma: no cover - env dependent
        print(
            "ERROR: the 'alembic' package is not installed in this Python environment.",
            file=sys.stderr,
        )
        print("Install it with: pip install alembic", file=sys.stderr)
        print(
            "Or install project dev requirements: pip install -r requirements.dev",
            file=sys.stderr,
        )
        print("Full error:", exc, file=sys.stderr)
        return 2

    # Ensure script_location is absolute so services need not have a local 'alembic' dir.
    tmp_ini_path = None
    # Allow service override of script directory
    override_dir_env = os.environ.get("SERVICE_ALEMBIC_DIR") or os.environ.get(
        "ENVOXY_ALEMBIC_DIR"
    )
    if override_dir_env:
        custom_dir = Path(override_dir_env).resolve()
        versions_dir = custom_dir / "versions"
        try:
            custom_dir.mkdir(parents=True, exist_ok=True)
            versions_dir.mkdir(parents=True, exist_ok=True)
            # Provide env.py without duplicating: prefer symlink to packaged env.py, else generate a thin proxy.
            env_py_src = packaged_script_dir / "env.py"
            env_py_dst = custom_dir / "env.py"
            if env_py_src.is_file() and not env_py_dst.exists():
                # Always create lightweight proxy delegating to packaged env (no symlink to ease cross-platform support)
                try:
                    env_py_dst.write_text(
                        """# Auto-generated proxy to framework env.py\nfrom envoxy.tools.alembic.alembic.env import *  # noqa\n""",
                        encoding="utf-8",
                    )
                except OSError as pe:  # pragma: no cover
                    print(f"WARNING: could not create proxy env.py: {pe}")
            # Optional script.py.mako: if user wants customization they can copy it; otherwise
            # Alembic will fall back to built-in or packaged template because env.py lives in package.
            # (No mandatory copy to keep service repo clean.)
            # Final guard: ensure versions directory still exists (race or cleanup)
            if not versions_dir.exists():
                versions_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:  # pragma: no cover
            print(f"WARNING: could not prepare custom alembic dir {custom_dir}: {e}")
        effective_script_dir = custom_dir
    else:
        effective_script_dir = packaged_script_dir

    try:
        cp = configparser.ConfigParser()
        with ini_path.open("r", encoding="utf-8") as fh:
            cp.read_file(fh)
        if cp.has_section("alembic"):
            loc = cp.get("alembic", "script_location", fallback="alembic")
            need_rewrite = False
            # If an override dir is requested, always rewrite to guarantee the local target
            if override_dir_env:
                need_rewrite = True
            else:
                # Otherwise only rewrite if different
                if Path(loc).resolve() != effective_script_dir:
                    need_rewrite = True
            if need_rewrite:
                cp.set("alembic", "script_location", str(effective_script_dir))
                fd, tmp_name = tempfile.mkstemp(prefix="envoxy-alembic-", suffix=".ini")
                try:
                    with open(tmp_name, "w", encoding="utf-8") as out_fh:
                        cp.write(out_fh)
                    tmp_ini_path = Path(tmp_name)
                finally:  # ensure fd closed
                    try:
                        os.close(fd)
                    except OSError:
                        pass
    except Exception:  # pragma: no cover
        tmp_ini_path = None

    effective_ini = tmp_ini_path or ini_path

    # prepend the -c <ini> so alembic uses the (possibly rewritten) config
    full_argv = ["-c", str(effective_ini)] + argv
    from typing import Optional

    exit_code_raw: Optional[int]
    try:
        exit_code_raw = CommandLine().main(full_argv)
    except SystemExit as se:  # pragma: no cover
        exit_code_raw = int(getattr(se, "code", 0) or 0)
    if exit_code_raw is None:
        return 0
    return int(exit_code_raw)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
