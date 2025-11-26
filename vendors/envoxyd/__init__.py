"""envoxyd - Customized uWSGI server for Envoxy."""

import os
import sys


def _run_binary():
    """Execute the envoxyd binary.
    
    This function is used as a console_scripts entry point to run
    the compiled envoxyd binary from the installed package.
    """
    # Get the path to the installed envoxyd binary
    package_dir = os.path.dirname(__file__)
    binary_path = os.path.join(package_dir, "bin", "envoxyd")
    
    if not os.path.exists(binary_path):
        print(f"Error: envoxyd binary not found at {binary_path}", file=sys.stderr)
        print("The envoxyd package may not have been installed correctly.", file=sys.stderr)
        sys.exit(1)
    
    # Execute the binary with the same arguments
    os.execv(binary_path, [binary_path] + sys.argv[1:])


__all__ = ["_run_binary"]
