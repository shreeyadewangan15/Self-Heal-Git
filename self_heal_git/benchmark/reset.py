import os

BUGGY_SAMPLE_APP = '''"""Target benchmark module containing missing comma and indexing error."""

def get_pipeline_configuration() -> dict:
    config = {
        "app_name": "AutonomousSelfHeal",
        "environment": "production",
        "timeout_seconds": 30
        "retry_attempts": 3,
    }
    return config


def get_latest_metric_sample(metrics: list) -> float:
    if not metrics:
        return 0.0
    # Bug: Off-by-one indexing error raises IndexError: list index out of range
    return float(metrics[len(metrics)])
'''

def reset_sample_app() -> str:
    """Reset benchmark/sample_app.py to its original buggy state."""
    benchmark_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(benchmark_dir, "sample_app.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(BUGGY_SAMPLE_APP)
    return file_path
