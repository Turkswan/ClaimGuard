"""Synthetic insurance claims. Stands in for Northbridge's claims warehouse."""

import argparse

import numpy as np
import pandas as pd

FEATURES_NUM = [
    "claim_amount",
    "policy_age_days",
    "customer_age",
    "previous_claims",
    "days_to_report",
    "vehicle_age",
]
FEATURES_CAT = ["claim_type", "police_report", "witness_present"]
TARGET = "is_fraud"


def generate_claims(n_rows: int = 20_000, seed: int = 42, drift: float = 0.0) -> pd.DataFrame:
    """Create labelled claims. `drift` > 0 simulates a change in claim patterns (e.g. after floods)."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "claim_amount": rng.lognormal(mean=8.0 + drift, sigma=0.8, size=n_rows).round(2),
            "policy_age_days": rng.integers(1, 3650, n_rows),
            "customer_age": rng.integers(18, 85, n_rows),
            "previous_claims": rng.poisson(0.6 + drift, n_rows),
            "days_to_report": rng.exponential(5 + 10 * drift, n_rows).round().astype(int),
            "vehicle_age": rng.integers(0, 20, n_rows),
            "claim_type": rng.choice(["motor", "home", "theft"], n_rows, p=[0.6, 0.3, 0.1]),
            "police_report": rng.choice(["yes", "no"], n_rows, p=[0.7, 0.3]),
            "witness_present": rng.choice(["yes", "no"], n_rows, p=[0.4, 0.6]),
        }
    )
    # The "true" fraud mechanism. The model never sees this formula, only examples.
    logit = (
        -3.0
        + 0.9 * (np.log(df.claim_amount) - 8)
        - 0.0006 * df.policy_age_days
        + 0.5 * df.previous_claims
        + 0.06 * df.days_to_report
        + 1.2 * (df.police_report == "no")
        + 0.8 * (df.claim_type == "theft")
        - 0.5 * (df.witness_present == "yes")
        + 1.5 * drift * (df.claim_type == "home")  # new fraud pattern appears with drift
    )
    prob = 1 / (1 + np.exp(-logit))
    df[TARGET] = (rng.random(n_rows) < prob).astype(int)
    return df


def load_claims(path: str) -> pd.DataFrame:
    """Read claims from a local path or s3://bucket/key."""
    if path.startswith("s3://"):
        import boto3

        bucket, key = path.removeprefix("s3://").split("/", 1)
        local = "/tmp/" + key.replace("/", "_")
        boto3.client("s3").download_file(bucket, key, local)
        path = local
    return pd.read_csv(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic claims data")
    parser.add_argument("--rows", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--drift", type=float, default=0.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    claims = generate_claims(args.rows, args.seed, args.drift)
    claims.to_csv(args.out, index=False)
    print(f"Wrote {len(claims)} rows to {args.out}, fraud rate {claims[TARGET].mean():.1%}")
