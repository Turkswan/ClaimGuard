from claimguard.data import FEATURES_CAT, FEATURES_NUM, TARGET, generate_claims


def test_schema_has_every_feature_and_target():
    df = generate_claims(n_rows=500)
    assert set(FEATURES_NUM + FEATURES_CAT + [TARGET]) <= set(df.columns)


def test_fraud_rate_is_realistic():
    rate = generate_claims(n_rows=5000)[TARGET].mean()
    assert 0.02 < rate < 0.25


def test_drift_changes_claim_amounts():
    base = generate_claims(n_rows=5000, drift=0.0).claim_amount.median()
    drifted = generate_claims(n_rows=5000, drift=0.6).claim_amount.median()
    assert drifted > base * 1.5
