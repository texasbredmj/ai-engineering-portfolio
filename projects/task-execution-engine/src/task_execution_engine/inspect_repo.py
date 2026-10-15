"""Fixed inspection command; never imports the target repository."""

import json
import sys
from pathlib import Path


def inspect(root):
    root = Path(root).resolve()
    return {
        "repository": str(root),
        "pyproject_present": (root / "pyproject.toml").is_file(),
        "tests_present": (root / "tests").is_dir(),
    }


if __name__ == "__main__":
    print(json.dumps(inspect(sys.argv[1])))
