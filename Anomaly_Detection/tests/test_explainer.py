"""
Unit tests for deterministic root-cause explainability.
"""

from anomaly_engine.explainer import AnomalyExplainer


def test_explainer_nominal(pipeline, normal_reading_dict):
    explainer = pipeline.explainer
    factors, diagnosis, action = explainer.explain(
        raw_values=normal_reading_dict,
        is_anomaly=False,
        severity="NORMAL",
    )

    assert len(factors) == 0
    assert "Nominal Operation" in diagnosis
    assert "standard continuous monitoring" in action


def test_explainer_air_leak(pipeline, air_leak_reading_dict):
    explainer = pipeline.explainer
    factors, diagnosis, action = explainer.explain(
        raw_values=air_leak_reading_dict,
        is_anomaly=True,
        severity="CRITICAL",
    )

    assert len(factors) > 0
    factor_sensors = {f.sensor: f for f in factors}

    # Should detect high TP2 and/or low H1 and/or high Motor_current
    assert "TP2" in factor_sensors or "H1" in factor_sensors or "Motor_current" in factor_sensors

    if "TP2" in factor_sensors:
        assert factor_sensors["TP2"].direction == "HIGH"
        assert factor_sensors["TP2"].deviation_sigma > 0

    if "H1" in factor_sensors:
        assert factor_sensors["H1"].direction == "LOW"
        assert factor_sensors["H1"].deviation_sigma < 0

    assert len(diagnosis) > 0
    assert len(action) > 0
