"""Bounded Python source snapshots, correction evidence, and fixed Ruff adapters."""

import ast
import difflib
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

MAX_FILES = 200
MAX_BYTES = 10 * 1024 * 1024
EXCLUDED = {
    ".git",
    ".task-engine",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    ".agents",
    ".codex",
    ".aws",
}


def source_files(repository: Path) -> list[Path]:
    files = []
    for directory, directories, names in os.walk(repository, followlinks=False):
        directories[:] = sorted(
            name for name in directories if name not in EXCLUDED and not name.startswith(".venv")
        )
        for name in directories:
            path = Path(directory) / name
            if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
                raise ValueError("source tree may not contain directory links")
        for name in sorted(names):
            if name.endswith(".py"):
                path = Path(directory) / name
                if path.is_symlink() or not path.resolve().is_relative_to(repository):
                    raise ValueError("Python source must remain inside repository")
                if path.stat().st_nlink != 1:
                    raise ValueError("hardlinked Python source is not supported")
                files.append(path)
                if len(files) > MAX_FILES:
                    raise ValueError(f"source scope exceeds {MAX_FILES} files")
    if not files:
        raise ValueError("maintenance operation requires Python source files")
    return sorted(files)


def snapshot(repository: Path) -> dict[str, Any]:
    files, total = {}, 0
    for path in source_files(repository):
        remaining = MAX_BYTES - total
        with path.open("rb") as handle:
            content = handle.read(remaining + 1)
        total += len(content)
        if total > MAX_BYTES:
            raise ValueError("source scope exceeds 10 MiB")
        files[path.relative_to(repository).as_posix()] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "content": content.decode("utf-8"),
        }
    return {"files": files, "total_bytes": total}


def save_snapshot(repository: Path, artifacts: Path, operation: str) -> dict[str, Any]:
    before = snapshot(repository)
    (artifacts / f"{operation}-before.json").write_text(
        json.dumps(before, indent=2), encoding="utf-8"
    )
    return before


def hashes(data: dict[str, Any]) -> dict[str, str]:
    return {name: item["sha256"] for name, item in data["files"].items()}


def collect_changes(repository: Path, artifacts: Path, before: dict[str, Any]) -> dict[str, Any]:
    after = snapshot(repository)
    patch, changed, semantic_preserved = [], [], True
    for name in sorted(set(before["files"]) | set(after["files"])):
        original = before["files"].get(name, {"content": "", "sha256": None})
        current = after["files"].get(name, {"content": "", "sha256": None})
        if original["sha256"] != current["sha256"]:
            try:
                semantic_preserved = semantic_preserved and (
                    ast.dump(ast.parse(original["content"]))
                    == ast.dump(ast.parse(current["content"]))
                )
            except SyntaxError:
                semantic_preserved = False
            changed.append(
                {
                    "path": name,
                    "before_sha256": original["sha256"],
                    "after_sha256": current["sha256"],
                }
            )
            patch.extend(
                difflib.unified_diff(
                    original["content"].splitlines(keepends=True),
                    current["content"].splitlines(keepends=True),
                    fromfile=f"a/{name}",
                    tofile=f"b/{name}",
                )
            )
    patch_path = artifacts / "format.patch"
    patch_path.write_text("".join(patch), encoding="utf-8", newline="")
    evidence = {
        "changed_files": changed,
        "before_hashes": hashes(before),
        "after_hashes": hashes(after),
        "patch": str(patch_path),
        "patch_sha256": hashlib.sha256(patch_path.read_bytes()).hexdigest(),
        "scope_valid": set(before["files"]) == set(after["files"]),
        "semantic_preserved": semantic_preserved,
    }
    (artifacts / "format-changes.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return evidence


def execute(operation: str, repository: Path, artifacts: Path) -> int:
    if operation not in {"format_check", "format_fix", "lint"}:
        raise ValueError("maintenance operation is not allowlisted")
    before = json.loads((artifacts / f"{operation}-before.json").read_text(encoding="utf-8"))
    current = snapshot(repository)
    if hashes(current) != hashes(before):
        raise ValueError("source changed after operation snapshot")
    files = [str(repository / name) for name in before["files"]]
    prefix = [sys.executable, "-I", "-m", "ruff"]
    if operation == "lint":
        argv = [
            *prefix,
            "check",
            "--isolated",
            "--no-cache",
            "--output-format",
            "json",
            "--select",
            "E4,E7,E9,F",
            "--target-version",
            "py311",
            *files,
        ]
    else:
        argv = [
            *prefix,
            "format",
            "--isolated",
            "--no-cache",
            "--line-length",
            "100",
            "--target-version",
            "py311",
        ]
        if operation == "format_check":
            argv.extend(["--check", "--diff"])
        argv.extend(files)
    completed = subprocess.run(argv, capture_output=True, check=False)
    sys.stdout.buffer.write(completed.stdout)
    sys.stderr.buffer.write(completed.stderr)
    # Full artifacts are separate from the runner's bounded display output.
    (artifacts / f"{operation}-stdout.txt").write_bytes(completed.stdout)
    (artifacts / f"{operation}-stderr.txt").write_bytes(completed.stderr)
    diagnostics = json.loads(completed.stdout) if operation == "lint" else None
    evidence = {
        "operation": operation,
        "exit_code": completed.returncode,
        "argv": argv,
        "before_hashes": hashes(before),
        "after_hashes": hashes(snapshot(repository)),
        "diagnostics": diagnostics,
        "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
    }
    (artifacts / f"{operation}-evidence.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    return completed.returncode


if __name__ == "__main__":
    try:
        sys.exit(execute(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])))
    except (OSError, ValueError) as exc:
        print(f"maintenance error: {exc}", file=sys.stderr)
        sys.exit(2)
