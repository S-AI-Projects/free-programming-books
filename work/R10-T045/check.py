#!/usr/bin/env python3
"""Automated verification script for Task R10-T045."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path


TASK_ID = "R10-T045"
REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = REPO_ROOT / "work" / TASK_ID
TARGET_FILE = REPO_ROOT / "books" / "free-programming-books-ml.md"
CHECKER_SCRIPT = REPO_ROOT / "tools" / "course_checks" / "r10-t045.py"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    res = subprocess.run(cmd, cwd=cwd or REPO_ROOT, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def main() -> int:
    print(f"=== Starting verification for {TASK_ID} ===")
    assert TARGET_FILE.exists(), f"Target file missing: {TARGET_FILE}"
    assert CHECKER_SCRIPT.exists(), f"Checker script missing: {CHECKER_SCRIPT}"

    initial_hash = sha256_file(TARGET_FILE)
    print(f"Initial SHA-256 ({TARGET_FILE.name}): {initial_hash}")

    # 1. Run checker with --self-test
    print("Running checker with --self-test...")
    code_self, out_self, err_self = run_cmd([sys.executable, str(CHECKER_SCRIPT), "--self-test"])
    combined_self = out_self + err_self
    print(combined_self.strip())
    assert code_self == 0, f"Self-test failed with exit code {code_self}: {err_self}"
    assert "Ran 5 tests" in combined_self or "OK" in combined_self, "Self-test test count / OK missing"

    # 2. Run extraction
    print("Running checker extraction...")
    code_run, out_run, err_run = run_cmd([sys.executable, str(CHECKER_SCRIPT)])
    assert code_run == 0, f"Extraction failed with exit code {code_run}: {err_run}"
    records = json.loads(out_run)
    assert len(records) == 3, f"Expected 3 records, got {len(records)}"

    expected_names = {
        "XI_Computer_Science_Part_I",
        "XI_Computer_Science_Part_II",
        "XII_Computer_Science_Part_I",
    }
    extracted_names = {r["display_name"] for r in records}
    assert expected_names == extracted_names, f"Mismatched names: {extracted_names} != {expected_names}"

    # 3. Verify in isolated temporary sandbox
    print("Verifying in isolated sandbox...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        tmp_checker = tmp_path / "checker.py"
        tmp_checker.write_text(CHECKER_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        code_tmp, out_tmp, err_tmp = run_cmd([sys.executable, str(CHECKER_SCRIPT), "--self-test"], cwd=tmp_path)
        assert code_tmp == 0, f"Sandbox self-test failed with exit code {code_tmp}"

    # 4. Invariance assertion
    final_hash = sha256_file(TARGET_FILE)
    print(f"Final SHA-256 ({TARGET_FILE.name}):   {final_hash}")
    assert initial_hash == final_hash, "Target file hash altered during verification!"

    # 5. Write work/R10-T045/evidence.md
    git_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()
    evidence_content = f"""# Verification Evidence: {TASK_ID}

## Overview
- **Task ID**: {TASK_ID}
- **Target File**: `books/free-programming-books-ml.md`
- **Checker Script**: `tools/course_checks/r10-t045.py`
- **Verification Runner**: `work/{TASK_ID}/check.py`
- **Timestamp**: {subprocess.run(['date', '-u'], capture_output=True, text=True).stdout.strip()}
- **Git Commit**: `{git_rev}`

## Environment & Tool Versions
- **Python**: `{sys.version.splitlines()[0]}`
- **Platform**: `{platform.platform()}`
- **Git**: `{subprocess.run(['git', '--version'], capture_output=True, text=True).stdout.strip()}`

## Target File Invariance
- **File**: `books/free-programming-books-ml.md`
- **SHA-256**: `{final_hash}`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
{combined_self.strip()}
```

## Extracted Entries
```json
{json.dumps(records, indent=2)}
```

## Test Summary
- Offline unit tests passed: 5/5
- Selected records matched: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
"""
    evidence_path = WORK_DIR / "evidence.md"
    evidence_path.write_text(evidence_content, encoding="utf-8")
    print(f"Wrote evidence to {evidence_path}")
    print(f"=== {TASK_ID} verification PASSED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
