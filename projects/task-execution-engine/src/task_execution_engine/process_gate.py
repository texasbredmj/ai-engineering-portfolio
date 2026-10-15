"""Wait for parent containment setup before starting the fixed tool on Windows."""

import subprocess
import sys

if __name__ == "__main__":
    if sys.stdin.buffer.readline() != b"execute\n":
        sys.exit(125)
    sys.exit(subprocess.call(sys.argv[1:], stdin=subprocess.DEVNULL, shell=False))
