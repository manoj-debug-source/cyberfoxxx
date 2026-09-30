"""
Model Training and Evaluation Pipeline.
Strictly separates training on baseline normal periods from evaluation on failure periods
to prevent any data leakage.
"""

import json
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from anomaly_engine.config import (
    ALL_FEATURES,
    DEFAULT_MODEL_PATH,
    MODELS_DIR,
    RAW_DATA_PATH,
)
from anomaly_engine.pipeline import AnomalyPipeline


def load_and_split_data(
    csv_path: Path = RAW_DATA_PATH,
    train_sample_size: int = 50000,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads dataset and splits into:
    1. Training Set: Baseline Normal period (2020-02-01 to 2020-04-17) strictly prior to Failure #1.
    2. Test Set: April 2020 period containing Failure #1 (2020-04-18 Air Leak) + normal periods.
    """
    print(f"Loading data from {csv_path}...")
    # Load first 750,000 records (Feb - May 2020) which covers baseline and Failure #1
    df = pd.read_csv(
        csv_path,
        nrows=750000,
        usecols=["timestamp"] + ALL_FEATURES,
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # 1. Training data: Strictly before 2020-04-17 (Pristine normal baseline)
    train_mask = df["timestamp"] < "2020-04-17 00:00:00"
    df_train_full = df[train_mask]

    # Sample uniformly across the baseline to capture diurnal/duty cycle variance
    if len(df_train_full) > train_sample_size:
        step = len(df_train_full) // train_sample_size
        df_train = df_train_full.iloc[::step].copy().reset_index(drop=True)
    else:
        df_train = df_train_full.copy().reset_index(drop=True)

    print(f"Training set: {len(df_train)} normal baseline records (Feb 01 - Apr 16, 2020)")

    # 2. Test data: 2020-04-17 to 2020-04-20 (Covers Failure #1 and surrounding normal days)
    test_mask = (df["timestamp"] >= "2020-04-17 00:00:00") & (
        df["timestamp"] <= "2020-04-20 23:59:59"
    )
    df_test = df[test_mask].copy().reset_index(drop=True)

    # Assign ground truth labels based on documented company maintenance report
    failure_mask = (df_test["timestamp"] >= "2020-04-18 00:00:00") & (
        df_test["timestamp"] <= "2020-04-18 23:59:59"
    )
    df_test["is_ground_truth_failure"] = failure_mask.astype(int)

    num_test_anomalies = df_test["is_ground_truth_failure"].sum()
    print(
        f"Test set: {len(df_test)} records ({num_test_anomalies} failure records, "
        f"{len(df_test) - num_test_anomalies} normal records)"
    )

    return df_train, df_test


def evaluate_pipeline(
    pipeline: AnomalyPipeline, df_test: pd.DataFrame
) -> Dict[str, float]:
    """
    Evaluates the fitted pipeline against the ground truth failure test set.
    """
    print("\nRunning evaluation on test set...")
    X_test_scaled = pipeline.preprocessor.transform(df_test)
    is_anom_pred, scores_pred, _, _ = pipeline.detector.predict(X_test_scaled)
    y_true = df_test["is_ground_truth_failure"].values
    y_pred = is_anom_pred.astype(int)

    # Calculate metrics
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_true, scores_pred))
    pr_auc = float(average_precision_score(y_true, scores_pred))
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    metrics = {
        "test_total_samples": int(len(df_test)),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
    }

    print("\n=== EVALUATION REPORT ===")
    print(f"True Positives (Detected Failures): {tp}")
    print(f"False Positives (Normal flagged):   {fp}")
    print(f"False Negatives (Missed Failures):  {fn}")
    print(f"True Negatives (Normal cleared):    {tn}")
    print(f"Recall (Sensitivity):               {metrics['recall'] * 100:.2f}%")
    print(f"Precision:                          {metrics['precision'] * 100:.2f}%")
    print(f"F1-Score:                           {metrics['f1_score']:.4f}")
    print(f"False Positive Rate:                {metrics['false_positive_rate'] * 100:.2f}%")
    print(f"ROC-AUC Score:                      {metrics['roc_auc']:.4f}")
    print(f"PR-AUC Score:                       {metrics['pr_auc']:.4f}")

    return metrics


def train_and_save() -> AnomalyPipeline:
    """
    Executes end-to-end training, evaluation, and artifact saving.
    """
    df_train, df_test = load_and_split_data()

    print("\nInitializing AnomalyPipeline...")
    pipeline = AnomalyPipeline()

    print("Fitting pipeline on baseline normal telemetry...")
    pipeline.fit(df_train)

    # Evaluate on unseen test set
    metrics = evaluate_pipeline(pipeline, df_test)

    # Ensure output directory exists
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Save model artifact
    saved_path = pipeline.save(DEFAULT_MODEL_PATH)
    print(f"\nModel artifact serialized to: {saved_path}")

    # Save evaluation metrics
    metrics_path = MODELS_DIR / "evaluation_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to: {metrics_path}")

    return pipeline


if __name__ == "__main__":
    train_and_save()
