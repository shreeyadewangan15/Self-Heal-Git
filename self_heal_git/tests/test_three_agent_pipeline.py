import os
os.environ["TESTING"] = "true"
import pytest
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.agents.test_runner_agent import Agent1TestRunner
from app.agents.diagnostic_agent import Agent2DiagnosticRepair
from app.agents.verifier_agent import Agent3Verifier
from app.agents.orchestrator import ThreeAgentOrchestrator
from benchmark.reset import reset_sample_app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_benchmark_file():
    """Ensure benchmark file is reset to buggy state before each test."""
    reset_sample_app()
    yield
    reset_sample_app()


def test_agent1_catches_test_failure_and_stack_trace():
    """Verify Agent 1 executes unit tests, catches failure, and captures raw stack trace."""
    runner = Agent1TestRunner()
    benchmark_test = os.path.join(runner.cwd, "benchmark", "test_sample_app.py")

    res = runner.run_tests(benchmark_test)
    assert res.passed is False
    assert res.exit_code != 0
    assert "SyntaxError" in res.error_type or "SyntaxError" in res.stack_trace
    assert len(res.stack_trace) > 0


def test_agent2_diagnoses_and_surgically_repairs_defects():
    """Verify Agent 2 intercepts stack trace, identifies lines, and surgically edits file on disk."""
    runner = Agent1TestRunner()
    repair = Agent2DiagnosticRepair()
    benchmark_test = os.path.join(runner.cwd, "benchmark", "test_sample_app.py")
    target_file = os.path.join(runner.cwd, "benchmark", "sample_app.py")

    # Step 1: Get failure from Agent 1
    failure = runner.run_tests(benchmark_test)

    # Step 2: Agent 2 intercepts and diagnoses
    diagnostic = repair.intercept_and_diagnose(failure, target_file=target_file)
    assert diagnostic.success is True
    assert diagnostic.file_updated_on_disk is True
    assert len(diagnostic.identified_line_numbers) > 0
    assert len(diagnostic.patches_applied) > 0
    assert len(diagnostic.surgical_diff) > 0
    assert "Missing Comma" in diagnostic.root_cause_reasoning or "IndexError" in diagnostic.root_cause_reasoning

    # Verify disk content is valid syntax
    with open(target_file, "r", encoding="utf-8") as f:
        repaired_code = f.read()
    assert '"timeout_seconds": 30,' in repaired_code


def test_agent3_verifies_100_percent_pass_rate():
    """Verify Agent 3 re-runs test suite against healed file and verifies 100% pass rate."""
    orchestrator = ThreeAgentOrchestrator()
    target_file = os.path.join(orchestrator.cwd, "benchmark", "sample_app.py")
    test_target = os.path.join(orchestrator.cwd, "benchmark", "test_sample_app.py")

    # Run orchestrator to complete healing
    trace = orchestrator.execute_pipeline(test_target=test_target, target_file=target_file)
    assert trace.pipeline_status == "HEALED"

    # Agent 3 explicitly verifies
    verifier = Agent3Verifier(cwd=orchestrator.cwd)
    verification = verifier.verify_fix(test_target)
    assert verification.is_verified is True
    assert verification.pass_rate_percent == 100.0
    assert verification.passed_tests == 2
    assert verification.failed_tests == 0


def test_end_to_end_3agent_benchmark_orchestration():
    """Verify end-to-end 3-Agent pipeline execution produces visual diagnostic trace."""
    orchestrator = ThreeAgentOrchestrator()
    trace = orchestrator.run_benchmark()

    assert trace.pipeline_status == "HEALED"
    assert trace.total_iterations >= 1
    assert trace.final_verification is not None
    assert trace.final_verification.is_verified is True
    assert trace.final_verification.pass_rate_percent == 100.0

    # Verify visual diagnostic trace steps
    agent_names = [s.agent_name for s in trace.trace_steps]
    assert any("Agent 1" in name for name in agent_names)
    assert any("Agent 2" in name for name in agent_names)
    assert any("Agent 3" in name for name in agent_names)


def test_api_pipeline_benchmark_endpoint():
    """Verify POST /api/pipeline/benchmark triggers 3 agents and returns visual diagnostic trace."""
    res = client.post("/api/pipeline/benchmark")
    assert res.status_code == status.HTTP_200_OK

    data = res.json()
    assert data["pipeline_status"] == "HEALED"
    assert data["final_verification"]["is_verified"] is True
    assert data["final_verification"]["pass_rate_percent"] == 100.0
    assert len(data["trace_steps"]) >= 3
    assert len(data["repairs"]) >= 1
    assert "diff" in data["repairs"][0]["surgical_diff"].lower() or len(data["repairs"][0]["surgical_diff"]) > 0

    # Test GET /api/pipeline/latest-trace returns the trace
    res_latest = client.get("/api/pipeline/latest-trace")
    assert res_latest.status_code == status.HTTP_200_OK
    latest_data = res_latest.json()
    assert latest_data["pipeline_status"] == "HEALED"
