"""
Data preprocessing, feature ordering, and baseline statistics estimation.
Ensures zero data leakage by computing transformations strictly on baseline healthy periods.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

from anomaly_engine.config import ALL_FEATURES, ANALOG_FEATURES, DIGITAL_FEATURES


class TelemetryPreprocessor:
    """
    Robust preprocessor for multi-sensor APU telemetry.
    Fitted exclusively on normal/baseline operational data to prevent contamination.
    """

    def __init__(self, feature_names: Optional[List[str]] = None):
        self.feature_names = feature_names or ALL_FEATURES
        self.scaler = RobustScaler()
        self.baseline_stats: Dict[str, Dict[str, float]] = {}
        self.is_fitted = False

    def fit(self, df: pd.DataFrame) -> "TelemetryPreprocessor":
        """
        Fits the scaler and computes robust baseline statistics (median, IQR, mean, std).
        Must be invoked only on pristine baseline normal data.
        """
        df_clean = self._validate_and_order(df)

        # Fit RobustScaler
        self.scaler.fit(df_clean.values)

        # Compute robust baseline statistics for each feature
        self.baseline_stats = {}
        for col in self.feature_names:
            series = df_clean[col].dropna()
            q25 = float(series.quantile(0.25))
            q75 = float(series.quantile(0.75))
            iqr = q75 - q25
            median = float(series.median())
            mean = float(series.mean())
            std = float(series.std())

            # Fallback for near-zero IQR to prevent division by zero in robust sigma
            # Apply realistic physical noise floors (e.g. pressure gauge noise ~0.15 bar, current ~0.25 A)
            noise_floor = {
                "TP2": 0.20,
                "TP3": 0.15,
                "H1": 0.20,
                "DV_pressure": 0.15,
                "Reservoirs": 0.15,
                "Oil_temperature": 1.0,
                "Motor_current": 0.25,
            }.get(col, 0.5)

            raw_sigma = (iqr / 1.349) if iqr > 1e-4 else (std if std > 1e-4 else 1.0)
            robust_sigma = max(raw_sigma, noise_floor)

            self.baseline_stats[col] = {
                "median": median,
                "q25": q25,
                "q75": q75,
                "iqr": iqr,
                "mean": mean,
                "std": std,
                "robust_sigma": robust_sigma,
            }

        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Transforms input telemetry data using the fitted scaler and handles missing values.
        """
        if not self.is_fitted:
            raise RuntimeError("Preprocessor must be fitted before transform can be called.")

        df_clean = self._validate_and_order(df)

        # Safe imputation using baseline medians if any NaN is encountered
        for col in self.feature_names:
            if df_clean[col].isnull().any():
                df_clean[col] = df_clean[col].fillna(self.baseline_stats[col]["median"])

        return self.scaler.transform(df_clean.values)

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        return self.fit(df).transform(df)

    def _validate_and_order(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensures all expected features are present and strictly ordered.
        """
        missing_features = [f for f in self.feature_names if f not in df.columns]
        if missing_features:
            raise ValueError(f"Input DataFrame is missing required features: {missing_features}")

        return df[self.feature_names].copy()
