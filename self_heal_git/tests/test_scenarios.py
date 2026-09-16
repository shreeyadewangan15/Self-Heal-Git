import ast
import time
import pytest
from typing import Dict, Any

from app.agent import (
    CodeIssue,
    PatchAction,
    HealingReport,
    verify_patch_syntax,
    diagnose_and_heal,
)

# ===========================================================================
# Buggy Code Scenarios
# ===========================================================================

# Case A: Missing import and undefined variable (json.loads called without import json)
CASE_A_BROKEN = """def parse_webhook_payload(raw_payload: str):
    # Bug: missing 'import json'
    data = json.loads(raw_payload)
    return data.get("repository", {})
"""

CASE_A_PATCH = PatchAction(
    file_path="handlers/webhook.py",
    original_snippet="def parse_webhook_payload(raw_payload: str):",
    replacement_snippet="import json\n\ndef parse_webhook_payload(raw_payload: str):",
    explanation="Added missing standard library import 'import json' before function definition.",
)

# Case B: Invalid syntax and malformed dictionary literal
CASE_B_BROKEN = """def get_service_config():
    # Bug: malformed dictionary literal missing comma between key-values
    config = {
        "host": "127.0.0.1",
        "port": 8000
        "debug": True
    }
    return config
"""

CASE_B_PATCH = PatchAction(
    file_path="core/config.py",
    original_snippet='        "port": 8000\n        "debug": True',
    replacement_snippet='        "port": 8000,\n        "debug": True',
    explanation="Inserted missing comma between dictionary key-value pairs to restore valid syntax.",
)

CASE_B_FAULTY_PATCH = PatchAction(
    file_path="core/config.py",
    original_snippet='        "port": 8000\n        "debug": True',
    replacement_snippet='        "port": 8000 ::: "debug": True',
    explanation="Invalid replacement that continues to violate Python grammar.",
)

# Case C: Logical ZeroDivisionError without divisor guard
CASE_C_BROKEN = """def calculate_average_latency(total_duration_ms: float, request_count: int) -> float:
    # Bug: ZeroDivisionError occurs when request_count is 0
    average = total_duration_ms / request_count
    return round(average, 2)
"""

CASE_C_PATCH = PatchAction(
    file_path="analytics/metrics.py",
    original_snippet="average = total_duration_ms / request_count",
    replacement_snippet="average = (total_duration_ms / request_count) if request_count > 0 else 0.0",
    explanation="Introduced zero-divisor guard to safely prevent ZeroDivisionError exceptions.",
)

CASE_C_FAULTY_PATCH = PatchAction(
    file_path="analytics/metrics.py",
    original_snippet="average = total_duration_ms / request_count",
    replacement_snippet="average = total_duration_ms / ",
    explanation="Unterminated binary operator causing AST syntax error.",
)


# ===========================================================================
# Test Functions
# ===========================================================================

class TestAutonomousHealingScenarios:
    """Comprehensive automated verification suite for Self-Heal Git."""

    def test_case_a_missing_import_verification(self):
        """Case A: Verifies detection, patch application, and AST validity for missing import."""
        file_path = "handlers/webhook.py"
        start_time = time.perf_counter()

        # 1. Unpatched verification: Verify that an invalid syntax patch is rejected
        invalid_patch = PatchAction(
            file_path=file_path,
            original_snippet="data = json.loads(raw_payload)",
            replacement_snippet="data = json.loads(raw_payload",  # unclosed parenthesis
            explanation="Malformed patch",
        )
        is_valid_bad, err_bad = verify_patch_syntax(file_path, CASE_A_BROKEN, invalid_patch)
        assert is_valid_bad is False
        assert "SyntaxError" in err_bad

        # 2. Patched verification: Valid patch introduces import and passes AST validation
        is_valid, msg = verify_patch_syntax(file_path, CASE_A_BROKEN, CASE_A_PATCH)
        assert is_valid is True
        assert msg == "Syntax Valid"

        # 3. Assert resulting code compiles and executes cleanly
        patched_code = CASE_A_BROKEN.replace(CASE_A_PATCH.original_snippet, CASE_A_PATCH.replacement_snippet, 1)
        compiled = compile(patched_code, "<test_a>", "exec")
        assert compiled is not None

        # Execute in isolated namespace to verify runtime behavior
        namespace = {}
        exec(compiled, namespace)
        assert "parse_webhook_payload" in namespace
        result = namespace["parse_webhook_payload"]('{"repository": {"name": "quantum-core"}}')
        assert result == {"name": "quantum-core"}

        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"\n[Case A] Missing Import resolved in {latency_ms:.2f}ms")

    def test_case_b_syntax_and_malformed_dict_literal(self):
        """Case B: Verifies AST rejection of unpatched code and success of healed dictionary literal."""
        file_path = "core/config.py"
        start_time = time.perf_counter()

        # 1. Direct AST verification: Unpatched code MUST fail AST compilation
        with pytest.raises(SyntaxError):
            ast.parse(CASE_B_BROKEN)

        # 2. Faulty patch rejection: verify_patch_syntax rejects patches that remain syntactically invalid
        is_valid_faulty, err_faulty = verify_patch_syntax(file_path, CASE_B_BROKEN, CASE_B_FAULTY_PATCH)
        assert is_valid_faulty is False
        assert "SyntaxError" in err_faulty

        # 3. Valid patch verification: verify_patch_syntax approves the repaired code
        is_valid, msg = verify_patch_syntax(file_path, CASE_B_BROKEN, CASE_B_PATCH)
        assert is_valid is True
        assert msg == "Syntax Valid"

        # 4. AST verification on patched source
        patched_code = CASE_B_BROKEN.replace(CASE_B_PATCH.original_snippet, CASE_B_PATCH.replacement_snippet, 1)
        parsed_ast = ast.parse(patched_code)
        assert isinstance(parsed_ast, ast.Module)

        # Execute to ensure dictionary is valid at runtime
        ns = {}
        exec(patched_code, ns)
        config = ns["get_service_config"]()
        assert config == {"host": "127.0.0.1", "port": 8000, "debug": True}

        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"\n[Case B] Malformed Dict Syntax resolved in {latency_ms:.2f}ms")

    def test_case_c_logical_zero_division_guard(self):
        """Case C: Verifies remediation of unshielded divisor logic and AST validation."""
        file_path = "analytics/metrics.py"
        start_time = time.perf_counter()

        # 1. Unpatched code crashes on 0 requests
        unpatched_ns = {}
        exec(CASE_C_BROKEN, unpatched_ns)
        with pytest.raises(ZeroDivisionError):
            unpatched_ns["calculate_average_latency"](120.5, 0)

        # 2. Faulty patch rejection: verify_patch_syntax catches broken syntax
        is_valid_faulty, err_faulty = verify_patch_syntax(file_path, CASE_C_BROKEN, CASE_C_FAULTY_PATCH)
        assert is_valid_faulty is False
        assert "SyntaxError" in err_faulty

        # 3. Valid patch verification: verify_patch_syntax validates AST
        is_valid, msg = verify_patch_syntax(file_path, CASE_C_BROKEN, CASE_C_PATCH)
        assert is_valid is True
        assert msg == "Syntax Valid"

        # 4. Patched execution: safely returns 0.0 on zero requests
        patched_code = CASE_C_BROKEN.replace(CASE_C_PATCH.original_snippet, CASE_C_PATCH.replacement_snippet, 1)
        patched_ns = {}
        exec(patched_code, patched_ns)
        assert patched_ns["calculate_average_latency"](100.0, 4) == 25.0
        assert patched_ns["calculate_average_latency"](100.0, 0) == 0.0

        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"\n[Case C] ZeroDivision Guard verified in {latency_ms:.2f}ms")

    def test_end_to_end_diagnostic_and_healing_pipeline(self):
        """Tests the complete diagnostic engine and report structure on multi-file PR."""
        file_contents = {
            "core/config.py": CASE_B_BROKEN,
            "analytics/metrics.py": CASE_C_BROKEN,
        }
        git_diff = (
            "--- a/core/config.py\n+++ b/core/config.py\n@@ -3,3 +3,3 @@\n"
            "+        \"port\": 8000\n+        \"debug\": True\n"
        )

        start_time = time.perf_counter()
        report: HealingReport = diagnose_and_heal(
            repo_name="tcet-opensource/quantum-core",
            pr_number=101,
            git_diff=git_diff,
            file_contents=file_contents,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000

        assert report is not None
        assert report.confidence_score > 0.0
        assert isinstance(report.summary, str)
        assert len(report.issues) > 0
        assert len(report.patches) > 0

        # Verify every synthesized patch passes AST validation
        for patch in report.patches:
            orig = file_contents.get(patch.file_path, "")
            valid, reason = verify_patch_syntax(patch.file_path, orig, patch)
            assert valid is True, f"Patch for {patch.file_path} failed AST: {reason}"

        print(f"\n[End-to-End Pipeline] Diagnostic & Patch Synthesis completed in {latency_ms:.2f}ms with {len(report.patches)} patch(es)")
