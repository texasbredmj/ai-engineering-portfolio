"""Validate the portfolio's claims without making external requests."""
import json
import re
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    evidence = json.loads((root / "evidence/phase1.json").read_text(encoding="utf-8"))
    expected = {"task-execution-engine": 50, "ai-tool-coordination-gateway": 30}
    assert {p["name"] for p in evidence["projects"]} == set(expected)
    for project in evidence["projects"]:
        assert project["local_tests_passed"] >= expected[project["name"]]
        assert project["local_tests_failed"] == 0
        assert re.fullmatch(r"[0-9a-f]{40}", project["published_sha"])
        assert project["repository_url"] == f"https://github.com/texasbredmj/{project['name']}"
        if evidence["checkpoint_complete"]:
            ci = project["remote_ci"]
            assert ci["head_sha"] == project["published_sha"]
            assert ci["status"] == "completed" and ci["conclusion"] == "success"
            assert len(ci["jobs"]) == 7
            assert all(job["conclusion"] == "success" for job in ci["jobs"])
            assert ci["url"].startswith(project["repository_url"] + "/actions/runs/")
            assert project["published"] is True
    assert evidence["project03_allowed"] == evidence["checkpoint_complete"]
    print(json.dumps({"evidence_valid": True, "checkpoint_complete": evidence["checkpoint_complete"]}))


if __name__ == "__main__":
    main()
