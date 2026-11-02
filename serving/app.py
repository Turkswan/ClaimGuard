"""ClaimGuard scoring API: returns a fraud score for one claim."""

import os
import time
from contextlib import asynccontextmanager
from typing import Literal

import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException, Response
from mlflow import MlflowClient
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

MODEL_URI = os.getenv("MODEL_URI", "models:/claimguard-fraud@champion")
THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.5"))

PREDICTIONS = Counter("claimguard_predictions_total", "Claims scored", ["flagged"])
LATENCY = Histogram("claimguard_prediction_latency_seconds", "Time to score one claim")
SCORES = Histogram(
    "claimguard_fraud_score", "Distribution of fraud scores", buckets=[i / 10 for i in range(1, 11)]
)


class Claim(BaseModel):
    """The input contract. Bad requests are rejected here, before they reach the model."""

    claim_amount: float = Field(gt=0)
    policy_age_days: int = Field(ge=0)
    customer_age: int = Field(ge=17, le=110)
    previous_claims: int = Field(ge=0)
    days_to_report: int = Field(ge=0)
    vehicle_age: int = Field(ge=0)
    claim_type: Literal["motor", "home", "theft"]
    police_report: Literal["yes", "no"]
    witness_present: Literal["yes", "no"]


def resolve_model(uri: str):
    """Turn 'models:/name@alias' into a fixed version, so we know exactly what we loaded."""
    name, alias = uri.removeprefix("models:/").split("@")
    version = MlflowClient().get_model_version_by_alias(name, alias).version
    return mlflow.sklearn.load_model(f"models:/{name}/{version}"), version


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SKIP_MODEL_LOAD") != "1":  # tests inject a fake model instead
        app.state.model, app.state.model_version = resolve_model(MODEL_URI)
    yield


app = FastAPI(title="ClaimGuard", lifespan=lifespan)


@app.get("/health")
def health():
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness: the model is loaded and we can take traffic."""
    if getattr(app.state, "model", None) is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ready", "model_version": app.state.model_version}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict")
def predict(claim: Claim):
    model = getattr(app.state, "model", None)
    if model is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    start = time.perf_counter()
    score = float(model.predict_proba(pd.DataFrame([claim.model_dump()]))[0, 1])
    LATENCY.observe(time.perf_counter() - start)
    flagged = score >= THRESHOLD
    SCORES.observe(score)
    PREDICTIONS.labels(flagged=str(flagged).lower()).inc()
    return {
        "fraud_score": round(score, 4),
        "flag_for_review": flagged,
        "model_version": app.state.model_version,
    }
