import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .models import Result
from .store import now

OUTPUT_LIMIT = 64 * 1024

TOOLS = {
    "inspect": {
        "id": "repository.inspect",
        "version": "1.0",
        "description": "Inspect project metadata",
        "input_schema": {"repository": "existing absolute directory"},
        "output_schema": {
            "repository": "string",
            "pyproject_present": "boolean",
            "tests_present": "boolean",
        },
        "permissions": ["repository.read"],
        "timeout_seconds": 30,
        "retry_eligible": True,
        "idempotent": True,
        "side_effect": "none",
        "approval_required": True,
        "execution_budget": {"max_attempts": 3, "max_timeout_seconds": 300},
    },
    "test": {
        "id": "repository.test",
        "version": "1.0",
        "description": "Run authorized pytest suite",
        "input_schema": {"repository": "existing absolute directory"},
        "output_schema": {"exit_code": "integer", "junit": "XML artifact"},
        "permissions": ["repository.execute"],
        "timeout_seconds": 30,
        "retry_eligible": False,
        "idempotent": False,
        "side_effect": "executes repository Python",
        "approval_required": True,
        "execution_budget": {"max_attempts": 1, "max_timeout_seconds": 300},
    },
}

for operation in ("format_check", "format_fix", "lint"):
    mutates = operation == "format_fix"
    TOOLS[operation] = {
        "id": f"repository.{operation}",
        "version": "1.0",
        "description": "Apply approved Ruff formatting" if mutates else f"Check {operation}",
        "input_schema": {"repository": "existing directory with bounded UTF-8 Python source"},
        "output_schema": {"exit_code": "integer", "evidence": "JSON artifact"},
        "permissions": ["repository.write" if mutates else "repository.read"],
        "timeout_seconds": 30,
        "retry_eligible": not mutates,
        "idempotent": not mutates,
        "side_effect": "modifies scoped Python source" if mutates else "none",
        "approval_required": True,
        "execution_budget": {"max_attempts": 1 if mutates else 3, "max_timeout_seconds": 300},
    }


def command(operation: str, repository: Path, artifact_dir: Path) -> list[str]:
    if operation in {"format_check", "format_fix", "lint"}:
        return [
            sys.executable,
            "-I",
            str(Path(__file__).with_name("maintenance.py")),
            operation,
            str(repository),
            str(artifact_dir),
        ]
    if operation == "inspect":
        return [
            sys.executable,
            "-I",
            str(Path(__file__).with_name("inspect_repo.py")),
            str(repository),
        ]
    if operation == "test":
        return [
            sys.executable,
            "-I",
            "-m",
            "pytest",
            str(repository / "tests"),
            "-q",
            "-o",
            "addopts=",
            "-o",
            "cache_dir=" + str(artifact_dir / "pytest-cache"),
            "--junitxml=" + str(artifact_dir / "junit.xml"),
        ]
    raise ValueError("operation is not allowlisted")


def stop_tree(process: subprocess.Popen, job=None) -> None:
    if os.name == "nt":
        if job is not None:
            job.close()
        if process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=10)


class Runner:
    def run(
        self, operation: str, repository: Path, artifact_dir: Path, timeout: float, attempt: int
    ) -> Result:
        argv = command(operation, repository, artifact_dir)
        started_at, started = now(), time.monotonic()
        timed_out, error, exit_code = False, None, None
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper()
            in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "LANG", "LC_ALL"}
        }
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = None
            job = None
            try:
                launch_argv = argv
                if os.name == "nt":
                    from .windows_job import WindowsJob

                    job = WindowsJob()
                    launch_argv = [
                        sys.executable,
                        "-I",
                        str(Path(__file__).with_name("process_gate.py")),
                        *argv,
                    ]
                process = subprocess.Popen(
                    launch_argv,
                    cwd=repository,
                    env=env,
                    stdin=subprocess.PIPE if job is not None else subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    shell=False,
                    start_new_session=os.name != "nt",
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                )
                if job is not None:
                    job.attach(process)
                    process.stdin.write(b"execute\n")
                    process.stdin.close()
                try:
                    exit_code = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    stop_tree(process, job)
                    exit_code = process.returncode
            except BaseException as exc:
                if process is not None and process.poll() is None:
                    stop_tree(process, job)
                if not isinstance(exc, Exception):
                    raise
                error = f"{type(exc).__name__}: {exc}"
            finally:
                if job is not None:
                    job.close()
            stdout.seek(0)
            stderr.seek(0)
            out, err = stdout.read(OUTPUT_LIMIT + 1), stderr.read(OUTPUT_LIMIT + 1)
        return Result(
            operation=operation,
            attempt=attempt,
            argv=argv,
            started_at=started_at,
            finished_at=now(),
            duration_seconds=time.monotonic() - started,
            exit_code=exit_code,
            timed_out=timed_out,
            error=error,
            stdout=out[:OUTPUT_LIMIT].decode("utf-8", errors="replace"),
            stderr=err[:OUTPUT_LIMIT].decode("utf-8", errors="replace"),
            output_truncated=len(out) > OUTPUT_LIMIT or len(err) > OUTPUT_LIMIT,
        )
