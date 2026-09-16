import subprocess
import sys
import os
import re
import time
import logging
from typing import List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("agent1_test_runner")


class TestRunResult(BaseModel):
    passed: bool
    exit_code: int
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_type: Optional[str] = None
    stack_trace: str = ""
    raw_output: str = ""
    failing_tests: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    summary: str = ""


class Agent1TestRunner:
    """Agent 1: Test Execution / CI Agent.

    Executes unit tests on code changes or incoming pushes.
    If tests pass, reports clean build.
    If tests fail, captures and intercepts the failing stack trace, error message, and test names.
    """

    def __init__(self, cwd: Optional[str] = None):
        self.cwd = cwd or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def run_tests(self, test_target: str) -> TestRunResult:
        """Run unit test suite against the target test path using pytest."""
        logger.info("Agent 1: Executing unit tests on target: %s", test_target)
        start_time = time.perf_counter()

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            test_target,
            "-v",
            "--tb=short",
            "-o",
            "cache_dir=/tmp/.pytest_cache_agent1",
        ]

        # Add project root to PYTHONPATH so imports in tests resolve
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{self.cwd}:{existing_pythonpath}"

        result = subprocess.run(
            cmd,
            cwd=self.cwd,
            capture_output=True,
            text=True,
            env=env,
        )

        duration = round(time.perf_counter() - start_time, 3)
        raw_output = (result.stdout + "\n" + result.stderr).strip()

        # Parse test counts and pass/fail
        passed = (result.returncode == 0)

        # Parse total and failed
        failed_count = 0
        passed_count = 0
        total_count = 0

        # Look for e.g. "=== 1 failed, 1 passed in 0.04s ==="
        match_failed = re.search(r"(\d+)\s+failed", raw_output)
        if match_failed:
            failed_count = int(match_failed.group(1))

        match_passed = re.search(r"(\d+)\s+passed", raw_output)
        if match_passed:
            passed_count = int(match_passed.group(1))

        match_error = re.search(r"(\d+)\s+error", raw_output)
        if match_error and failed_count == 0:
            failed_count += int(match_error.group(1))

        total_count = passed_count + failed_count
        if total_count == 0 and not passed:
            failed_count = 1
            total_count = 1

        # Extract stack trace
        stack_trace = ""
        error_type = None

        if not passed:
            # Extract traceback block
            tb_match = re.search(r"(_+\s+ERROR.*?_+|_+\s+test_.*?_+\n.*)", raw_output, re.DOTALL)
            if tb_match:
                stack_trace = tb_match.group(1).strip()
            else:
                stack_trace = raw_output

            # Identify error type
            if "SyntaxError" in raw_output:
                error_type = "SyntaxError"
            elif "IndexError" in raw_output:
                error_type = "IndexError"
            elif "ZeroDivisionError" in raw_output:
                error_type = "ZeroDivisionError"
            elif "ImportError" in raw_output or "ModuleNotFoundError" in raw_output:
                error_type = "ImportError"
            elif "TypeError" in raw_output:
                error_type = "TypeError"
            elif "AssertionError" in raw_output:
                error_type = "AssertionError"
            else:
                error_type = "TestFailure"

        # Extract failing test names
        failing_tests = []
        for line in raw_output.splitlines():
            if "FAILED " in line:
                test_name = line.split("FAILED ")[-1].strip()
                failing_tests.append(test_name)

        summary = (
            f"All {total_count} unit tests passed successfully in {duration}s."
            if passed
            else f"Unit test execution failed ({failed_count} failure(s)) in {duration}s: {error_type}"
        )

        logger.info("Agent 1: Execution completed. Passed=%s, Error=%s", passed, error_type)

        return TestRunResult(
            passed=passed,
            exit_code=result.returncode,
            total_tests=total_count,
            passed_tests=passed_count,
            failed_tests=failed_count,
            error_type=error_type,
            stack_trace=stack_trace,
            raw_output=raw_output,
            failing_tests=failing_tests,
            duration_seconds=duration,
            summary=summary,
        )
