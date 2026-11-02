from claimguard.data import FEATURES_CAT, FEATURES_NUM, TARGET, generate_claims
from claimguard.train import build_pipeline, evaluate


def test_model_learns_better_than_chance():
    df = generate_claims(n_rows=4000, seed=1)
    X, y = df[FEATURES_NUM + FEATURES_CAT], df[TARGET]
    model = build_pipeline(n_estimators=50, max_depth=8).fit(X[:3000], y[:3000])
    metrics = evaluate(model, X[3000:], y[3000:])
    assert metrics["roc_auc"] > 0.65
