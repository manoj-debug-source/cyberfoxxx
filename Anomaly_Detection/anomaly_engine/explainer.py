"""
Explainability engine providing deterministic root-cause attribution and physical diagnostics.
Calculates robust standardized deviations against historical baseline distributions.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np

from anomaly_engine.config import (
    ALL_FEATURES,
    EXPLAINER_SIGMA_THRESHOLD,
    MAX_EXPLANATION_FACTORS,
    SENSOR_METADATA,
)
from anomaly_engine.schema import PrimaryFactor


class AnomalyExplainer:
    """
    Deterministic explainability engine based on robust baseline statistical deviations.
    """

    def __init__(self, baseline_stats: Dict[str, Dict[str, float]]):
        self.baseline_stats = baseline_stats

    def explain(
        self,
        raw_values: Dict[str, float],
        is_anomaly: bool,
        severity: str,
    ) -> Tuple[List[PrimaryFactor], str, str]:
        """
        Analyzes sensor values against healthy baseline distributions.
        Returns:
            - primary_factors: List of PrimaryFactor objects
            - diagnostic_summary: Human-readable explanation of root cause
            - recommended_action: Prescriptive engineering recommendation
        """
        deviations = []

        for sensor in ALL_FEATURES:
            if sensor not in raw_values:
                continue

            observed = float(raw_values[sensor])
            stats = self.baseline_stats.get(sensor)
            if not stats:
                continue

            median = stats["median"]
            sigma = stats["robust_sigma"]

            # Compute standardized robust z-score
            diff = observed - median
            z_score = diff / sigma if sigma > 1e-6 else 0.0

            direction = "HIGH" if z_score > 0 else "LOW"
            deviations.append({
                "sensor": sensor,
                "name": SENSOR_METADATA.get(sensor, {}).get("name", sensor),
                "observed": round(observed, 3),
                "baseline_median": round(median, 3),
                "deviation_sigma": round(float(z_score), 2),
                "abs_z": abs(z_score),
                "direction": direction,
            })

        # If normal, return nominal diagnosis with no anomaly factors
        if not is_anomaly:
            return (
                [],
                "Nominal Operation: All monitored pneumatic, electrical, and thermal parameters are within expected baseline operating thresholds.",
                "Continue standard continuous monitoring.",
            )

        # Rank sensors by absolute deviation magnitude
        deviations.sort(key=lambda x: x["abs_z"], reverse=True)

        # Select significant factors
        significant = [
            d for d in deviations if d["abs_z"] >= EXPLAINER_SIGMA_THRESHOLD
        ][:MAX_EXPLANATION_FACTORS]

        # If flagged as anomaly but no single sensor passed threshold, take top 2 factors
        if not significant:
            significant = deviations[:2]

        primary_factors = [
            PrimaryFactor(
                sensor=d["sensor"],
                name=d["name"],
                observed=d["observed"],
                baseline_median=d["baseline_median"],
                deviation_sigma=d["deviation_sigma"],
                direction=d["direction"],
            )
            for d in significant
        ]

        # Generate diagnostic text and recommendations
        diagnostic_summary, recommended_action = self._synthesize_diagnosis(
            is_anomaly=is_anomaly,
            severity=severity,
            factors=significant,
        )

        return primary_factors, diagnostic_summary, recommended_action

    def _synthesize_diagnosis(
        self,
        is_anomaly: bool,
        severity: str,
        factors: List[Dict],
    ) -> Tuple[str, str]:
        """
        Synthesizes factual physical diagnostics based on observed sensor deviations.
        """
        if not is_anomaly:
            return (
                "Nominal Operation: All monitored pneumatic, electrical, and thermal parameters are within expected baseline operating thresholds.",
                "Continue standard continuous monitoring.",
            )

        factor_sensors = {f["sensor"]: f for f in factors}
        diagnoses = []
        actions = []

        # Check for signature Air Leak / Pneumatic Stress pattern (Spike in TP2, drop in H1, continuous load)
        if "TP2" in factor_sensors and factor_sensors["TP2"]["direction"] == "HIGH":
            if "H1" in factor_sensors and factor_sensors["H1"]["direction"] == "LOW":
                diagnoses.append(
                    "Pneumatic Air Leak / Continuous Overload: Compressor outlet pressure (TP2) is elevated under continuous effort while separator filter pressure (H1) has collapsed."
                )
                actions.append(
                    "Inspect pneumatic circuit, check cyclonic separator valve seals and pipe couplings for active air leaks."
                )

        # Check for Overheating
        if "Oil_temperature" in factor_sensors and factor_sensors["Oil_temperature"]["direction"] == "HIGH":
            diagnoses.append(
                f"Thermal Stress: Oil temperature ({factor_sensors['Oil_temperature']['observed']}°C) exceeds baseline normal operating range."
            )
            actions.append(
                "Inspect compressor lubrication oil level and heat exchanger cooling fan operation."
            )

        # Check for Motor Overcurrent
        if "Motor_current" in factor_sensors and factor_sensors["Motor_current"]["direction"] == "HIGH":
            diagnoses.append(
                f"Electrical Motor Overload: Motor phase current drawing {factor_sensors['Motor_current']['observed']}A under heavy continuous load."
            )
            actions.append(
                "Check motor windings and electrical contactors for phase imbalance or mechanical binding."
            )

        # Check for Low Delivery Pressure in Reservoirs / TP3
        if "Reservoirs" in factor_sensors and factor_sensors["Reservoirs"]["direction"] == "LOW":
            diagnoses.append(
                f"Insufficient Reservoir Delivery: Downstream pressure dropped to {factor_sensors['Reservoirs']['observed']} bar."
            )
            actions.append(
                "Inspect check-valves and reservoir pressure retention lines."
            )

        # If generic anomaly without specific combined rule
        if not diagnoses and factors:
            top_sensor = factors[0]
            diagnoses.append(
                f"Sensor Anomaly: {top_sensor['name']} ({top_sensor['sensor']}) observed at {top_sensor['observed']} ({top_sensor['direction']} by {abs(top_sensor['deviation_sigma'])}σ from baseline)."
            )
            actions.append(
                f"Verify calibration and wiring for {top_sensor['name']} ({top_sensor['sensor']})."
            )

        summary = " | ".join(diagnoses) if diagnoses else f"Unusual multivariate operational telemetry pattern detected with {severity} severity."
        action = " | ".join(actions) if actions else "Schedule immediate technical inspection of the Air Production Unit."

        return summary, action
