#!/usr/bin/env python3
"""Wrapper script to run the envoxyd binary."""
import os
import sys


def main():
    """Execute the envoxyd binary with all arguments."""
    # Find the installed envoxyd package
    import envoxyd

    # Get the binary path
    binary_path = os.path.join(os.path.dirname(envoxyd.__file__), "bin", "envoxyd")
    
    if not os.path.exists(binary_path):
        print(f"Error: envoxyd binary not found at {binary_path}", file=sys.stderr)
        sys.exit(1)

    # Execute the binary with all arguments
    os.execv(binary_path, [binary_path] + sys.argv[1:])


if __name__ == "__main__":
    main()

