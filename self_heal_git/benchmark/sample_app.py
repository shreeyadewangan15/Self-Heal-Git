"""Target benchmark module containing missing comma and indexing error."""

def get_pipeline_configuration() -> dict:
    config = {
        "app_name": "AutonomousSelfHeal",
        "environment": "production",
        "timeout_seconds": 30,
        "retry_attempts": 3,
    }
    return config


def get_latest_metric_sample(metrics: list) -> float:
    if not metrics:
        return 0.0
    # Bug: Off-by-one indexing error raises IndexError: list index out of range
    return float(metrics[len(metrics) - 1])
