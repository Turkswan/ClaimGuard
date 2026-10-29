import os

import numpy as np
from fastapi.testclient import TestClient

os.environ["SKIP_MODEL_LOAD"] = "1"
from serving.app import app  # noqa: E402

SAMPLE = {
    "claim_amount": 4200.0,
    "policy_age_days": 40,
    "customer_age": 31,
    "previous_claims": 3,
    "days_to_report": 21,
    "vehicle_age": 9,
    "claim_type": "theft",
    "police_report": "no",
    "witness_present": "no",
}


class StubModel:
    """Stands in for the real model so the test needs no MLflow server."""

    def predict_proba(self, X):
        return np.tile([0.2, 0.8], (len(X), 1))


def client_with_stub():
    app.state.model, app.state.model_version = StubModel(), "test"
    return TestClient(app)


def test_predict_flags_high_score():
    r = client_with_stub().post("/predict", json=SAMPLE)
    assert r.status_code == 200
    assert r.json()["flag_for_review"] is True


def test_invalid_claim_is_rejected():
    r = client_with_stub().post("/predict", json={**SAMPLE, "claim_type": "boat"})
    assert r.status_code == 422


def test_metrics_endpoint_exposes_counters():
    client = client_with_stub()
    client.post("/predict", json=SAMPLE)
    assert "claimguard_predictions_total" in client.get("/metrics").text
