"""Train the ClaimGuard fraud model, track it in MLflow, and promote it only if it beats the champion."""

import argparse
import hashlib
import os
import time

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from claimguard.data import FEATURES_CAT, FEATURES_NUM, TARGET, load_claims

MODEL_NAME = os.getenv("MODEL_NAME", "claimguard-fraud")
EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "claimguard-fraud")


def build_pipeline(n_estimators: int, max_depth: int) -> Pipeline:
    """Preprocessing and model in ONE object, so serving applies exactly the same transforms."""
    preprocess = ColumnTransformer(
        [
            ("num", StandardScaler(), FEATURES_NUM),
            ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CAT),
        ]
    )
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        class_weight="balanced",  # fraud is rare; don't let the majority class dominate
        n_jobs=-1,
        random_state=42,
    )
    return Pipeline([("preprocess", preprocess), ("model", model)])


def evaluate(model, X: pd.DataFrame, y: pd.Series, threshold: float = 0.5) -> dict:
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= threshold).astype(int)
    return {
        "roc_auc": roc_auc_score(y, proba),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred),
        "f1": f1_score(y, pred),
    }


def dataset_hash(df: pd.DataFrame) -> str:
    """Fingerprint of the exact data used, so a run can be tied to its data."""
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]


def champion_score(client: MlflowClient, X_test, y_test):
    """Score the CURRENT champion on the SAME test set, so the comparison is fair."""
    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, "champion")
    except MlflowException:
        return None, None  # first ever run: there is no champion yet
    champion = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{mv.version}")
    return mv.version, roc_auc_score(y_test, champion.predict_proba(X_test)[:, 1])


def push_training_metrics(metrics: dict, duration: float, passed: bool) -> None:
    """Optional: send run results to the Prometheus Pushgateway (Phase 9)."""
    url = os.getenv("PUSHGATEWAY_URL")
    if not url:
        return
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

    registry = CollectorRegistry()
    Gauge("claimguard_training_roc_auc", "ROC AUC of the last training run", registry=registry).set(metrics["roc_auc"])
    Gauge("claimguard_training_duration_seconds", "Training wall time", registry=registry).set(duration)
    Gauge("claimguard_training_gate_passed", "1 if the last run was promoted", registry=registry).set(int(passed))
    last_run = Gauge("claimguard_training_last_success_timestamp", "Unix time of last run", registry=registry)
    last_run.set_to_current_time()
    push_to_gateway(url, job="claimguard-training", registry=registry)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Local path or s3://bucket/key of labelled claims")
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--min-auc", type=float, default=0.70, help="Absolute floor a model must clear")
    args = parser.parse_args()

    started = time.time()
    df = load_claims(args.data)
    X, y = df[FEATURES_NUM + FEATURES_CAT], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    client = MlflowClient()
    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run() as run:
        mlflow.set_tags({"git_sha": os.getenv("GIT_SHA", "local"), "data_path": args.data})
        mlflow.log_params(
            {
                "n_estimators": args.n_estimators,
                "max_depth": args.max_depth,
                "rows": len(df),
                "fraud_rate": round(float(y.mean()), 4),
                "data_sha256": dataset_hash(df),
            }
        )

        model = build_pipeline(args.n_estimators, args.max_depth).fit(X_train, y_train)
        metrics = evaluate(model, X_test, y_test)
        mlflow.log_metrics(metrics)

        champ_version, champ_auc = champion_score(client, X_test, y_test)
        if champ_auc is not None:
            mlflow.log_metric("champion_roc_auc", champ_auc)

        info = mlflow.sklearn.log_model(
            model,
            name="model",
            registered_model_name=MODEL_NAME,
            input_example=X_test.head(3),
            # MLflow saves sklearn models with skops (safer than pickle) and asks us to
            # explicitly trust the tree class that random forests are made of.
            skops_trusted_types=["sklearn.tree._tree.Tree"],
        )
        version = info.registered_model_version

        # Quality gate: clear the floor AND beat the champion on the same test data.
        passed = metrics["roc_auc"] >= args.min_auc and (champ_auc is None or metrics["roc_auc"] > champ_auc)
        alias = "champion" if passed else "challenger"
        client.set_registered_model_alias(MODEL_NAME, alias, version)
        mlflow.set_tag("quality_gate", "passed" if passed else "failed")

        print(f"run_id={run.info.run_id} version={version} metrics={ {k: round(v, 4) for k, v in metrics.items()} }")
        print(f"champion_before=v{champ_version} champion_auc={champ_auc}")
        print(f"QUALITY_GATE={'passed' if passed else 'failed'} alias={alias}")

    push_training_metrics(metrics, time.time() - started, passed)


if __name__ == "__main__":
    main()
