"""
Unit tests for data preprocessing and leakage prevention.
"""

import pytest
import numpy as np
import pandas as pd
from anomaly_engine.preprocessor import TelemetryPreprocessor
from anomaly_engine.config import ALL_FEATURES


def test_preprocessor_fitting(normal_reading_dict, air_leak_reading_dict):
    df_sample = pd.DataFrame([normal_reading_dict, air_leak_reading_dict])
    preprocessor = TelemetryPreprocessor()
    preprocessor.fit(df_sample)

    assert preprocessor.is_fitted is True
    for feat in ALL_FEATURES:
        assert feat in preprocessor.baseline_stats
        assert "median" in preprocessor.baseline_stats[feat]
        assert "robust_sigma" in preprocessor.baseline_stats[feat]
        assert preprocessor.baseline_stats[feat]["robust_sigma"] > 0


def test_preprocessor_transform_shape(normal_reading_dict):
    df = pd.DataFrame([normal_reading_dict])
    preprocessor = TelemetryPreprocessor()
    preprocessor.fit(df)
    X = preprocessor.transform(df)

    assert isinstance(X, np.ndarray)
    assert X.shape == (1, len(ALL_FEATURES))


def test_preprocessor_handles_nan_gracefully(normal_reading_dict):
    df = pd.DataFrame([normal_reading_dict, normal_reading_dict])
    preprocessor = TelemetryPreprocessor()
    preprocessor.fit(df)

    # Inject NaN in test row
    df_nan = pd.DataFrame([normal_reading_dict])
    df_nan.loc[0, "TP2"] = np.nan

    # Transform should impute using fitted baseline median without error
    X = preprocessor.transform(df_nan)
    assert not np.isnan(X).any()


def test_preprocessor_raises_before_fit(normal_reading_dict):
    preprocessor = TelemetryPreprocessor()
    df = pd.DataFrame([normal_reading_dict])
    with pytest.raises(RuntimeError):
        preprocessor.transform(df)


def test_preprocessor_raises_on_missing_column(normal_reading_dict):
    preprocessor = TelemetryPreprocessor()
    df = pd.DataFrame([normal_reading_dict])
    preprocessor.fit(df)

    df_invalid = df.drop(columns=["TP2"])
    with pytest.raises(ValueError):
        preprocessor.transform(df_invalid)
