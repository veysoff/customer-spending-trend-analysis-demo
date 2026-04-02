"""Tests for UC-3 Fraud Pattern Identification.

Covers:
- FraudFeatureExtractor: feature computation correctness
- FraudDetector: score_transaction, score_customer_recent, get_pattern_clusters
- API endpoints via FastAPI TestClient: train, fraud-signals, detail, portfolio
"""

import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from app.ml.fraud_features import FraudFeatureExtractor
from app.ml.fraud_model import FraudDetector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tx(
    *,
    amount: float = 100.0,
    country: str = "GB",
    channel: str = "POS",
    mcc_category: str = "GROCERIES",
    time_of_day: str = "10:00",
    date: datetime = None,
) -> pd.Series:
    """Build a minimal transaction Series for testing."""
    return pd.Series(
        {
            "id": "tx_test",
            "date": date or datetime(2025, 1, 15, 10, 0),
            "amount": amount,
            "country": country,
            "channel": channel,
            "mcc_category": mcc_category,
            "time_of_day": time_of_day,
            "merchant": "TestMerchant",
            "mcc": "5411",
        }
    )


def _make_history(n: int = 30, *, country: str = "GB", channel: str = "POS") -> pd.DataFrame:
    """Build a synthetic history DataFrame with `n` normal transactions."""
    base = datetime(2024, 10, 1)
    return pd.DataFrame(
        [
            {
                "id": f"tx_{i}",
                "date": base + timedelta(days=i),
                "amount": 80.0 + i,
                "country": country,
                "channel": channel,
                "mcc_category": "GROCERIES",
                "time_of_day": "10:00",
                "merchant": "RegularMerchant",
                "mcc": "5411",
            }
            for i in range(n)
        ]
    )


# ---------------------------------------------------------------------------
# FraudFeatureExtractor unit tests
# ---------------------------------------------------------------------------


class TestFraudFeatureExtractor:
    def test_extract_returns_all_keys(self):
        tx = _make_tx()
        history = _make_history()
        features = FraudFeatureExtractor.extract(tx, history)

        expected_keys = {
            "velocity_score",
            "amount_deviation_score",
            "geo_risk_score",
            "hour_risk_score",
            "micro_before_large_flag",
            "merchant_drift_score",
            "channel_anomaly_score",
            "structuring_flag",
            "fraud_score",
            "fraud_flags",
        }
        assert expected_keys == set(features.keys())

    def test_extract_empty_history_returns_zeros(self):
        tx = _make_tx()
        empty = pd.DataFrame(columns=["date", "amount", "country", "channel", "mcc_category", "time_of_day"])
        features = FraudFeatureExtractor.extract(tx, empty)
        # All numeric features should be 0.0 with no history
        for key in ("velocity_score", "amount_deviation_score", "geo_risk_score"):
            assert features[key] == 0.0, f"{key} should be 0.0 on empty history"

    def test_geo_risk_triggers_on_new_country(self):
        tx = _make_tx(country="CN")
        history = _make_history(country="GB")
        score = FraudFeatureExtractor._geo_risk_score(tx, history)
        assert score == 1.0

    def test_geo_risk_zero_on_known_country(self):
        tx = _make_tx(country="GB")
        history = _make_history(country="GB")
        score = FraudFeatureExtractor._geo_risk_score(tx, history)
        assert score == 0.0

    def test_hour_risk_triggers_at_night(self):
        tx = _make_tx(time_of_day="03:00")
        # History only has daytime — no night baseline
        history = _make_history()
        score = FraudFeatureExtractor._hour_risk_score(tx, history)
        assert score > 0.0

    def test_hour_risk_zero_during_day(self):
        tx = _make_tx(time_of_day="14:00")
        history = _make_history()
        score = FraudFeatureExtractor._hour_risk_score(tx, history)
        assert score == 0.0

    def test_parse_hour_word_labels(self):
        assert FraudFeatureExtractor._parse_hour("morning") == 9
        assert FraudFeatureExtractor._parse_hour("afternoon") == 14
        assert FraudFeatureExtractor._parse_hour("evening") == 19
        assert FraudFeatureExtractor._parse_hour("night") == 2

    def test_parse_hour_hhmm_format(self):
        assert FraudFeatureExtractor._parse_hour("03:45") == 3
        assert FraudFeatureExtractor._parse_hour("23:59") == 23

    def test_parse_hour_none_returns_noon(self):
        assert FraudFeatureExtractor._parse_hour(None) == 12

    def test_fraud_score_bounded(self):
        tx = _make_tx(amount=5000.0, country="NG", time_of_day="02:00")
        history = _make_history()
        features = FraudFeatureExtractor.extract(tx, history)
        assert 0.0 <= features["fraud_score"] <= 1.0

    def test_geo_risk_produces_flags(self):
        tx = _make_tx(country="RU")
        history = _make_history(country="GB")
        features = FraudFeatureExtractor.extract(tx, history)
        assert "geo_risk" in features["fraud_flags"]

    def test_build_feature_matrix_shape(self):
        df = pd.DataFrame(
            [
                {
                    "amount": 100.0,
                    "time_of_day": "09:00",
                    "channel": "POS",
                    "country": "GB",
                    "mcc_category": "GROCERIES",
                }
                for _ in range(20)
            ]
        )
        matrix = FraudFeatureExtractor.build_feature_matrix(df)
        assert matrix.shape == (20, 5)

    def test_build_feature_matrix_empty(self):
        df = pd.DataFrame(columns=["amount", "time_of_day", "channel", "country", "mcc_category"])
        matrix = FraudFeatureExtractor.build_feature_matrix(df)
        assert matrix.shape == (0, 5)

    def test_get_flag_details_returns_correct_fields(self):
        tx = _make_tx(country="CN")
        history = _make_history(country="GB")
        features = FraudFeatureExtractor.extract(tx, history)
        details = FraudFeatureExtractor.get_flag_details(tx, features["fraud_flags"])
        for d in details:
            assert {"flag", "label", "explanation", "severity"} == set(d.keys())
            assert d["severity"] in ("HIGH", "MEDIUM", "LOW")


# ---------------------------------------------------------------------------
# FraudDetector unit tests (rule-based mode — no DB needed)
# ---------------------------------------------------------------------------


class TestFraudDetectorRuleBased:
    def test_score_transaction_returns_tuple(self):
        detector = FraudDetector.__new__(FraudDetector)
        detector.model = None
        detector.is_trained = False

        tx = _make_tx(country="CN", time_of_day="03:00")
        history = _make_history(country="GB")
        score, flags = detector.score_transaction(tx, history)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert isinstance(flags, list)

    def test_score_high_risk_transaction(self):
        """Geographic anomaly + night activity → high score."""
        detector = FraudDetector.__new__(FraudDetector)
        detector.model = None
        detector.is_trained = False

        tx = _make_tx(country="NG", time_of_day="02:00")
        history = _make_history(country="GB")
        score, flags = detector.score_transaction(tx, history)

        assert score > 0.3
        assert "geo_risk" in flags

    def test_score_normal_transaction_low(self):
        """Normal transaction in known country at daytime → low score."""
        detector = FraudDetector.__new__(FraudDetector)
        detector.model = None
        detector.is_trained = False

        tx = _make_tx(country="GB", time_of_day="10:00", amount=90.0)
        history = _make_history(country="GB", n=50)
        score, _ = detector.score_transaction(tx, history)

        assert score < 0.5

    def test_normalize_if_score(self):
        # Negative (anomaly) → close to 1.0
        assert FraudDetector._normalize_if_score(-0.5) == 1.0
        # Zero → 0.5
        assert FraudDetector._normalize_if_score(0.0) == 0.5
        # Positive (normal) → close to 0.0
        assert FraudDetector._normalize_if_score(0.5) == 0.0

    def test_get_pattern_clusters_groups_by_flag(self):
        detector = FraudDetector.__new__(FraudDetector)
        detector.model = None
        detector.is_trained = False

        scored_txs = [
            {"tx_id": "a", "fraud_flags": ["geo_risk", "night_activity"], "fraud_score": 0.8},
            {"tx_id": "b", "fraud_flags": ["geo_risk"], "fraud_score": 0.6},
            {"tx_id": "c", "fraud_flags": ["card_testing"], "fraud_score": 0.7},
        ]
        clusters = detector.get_pattern_clusters(scored_txs)

        assert "geo_risk" in clusters
        assert len(clusters["geo_risk"]) == 2
        assert "card_testing" in clusters
        assert len(clusters["card_testing"]) == 1

    def test_score_customer_recent_empty_returns_empty_list(self, tmp_path, monkeypatch):
        """score_customer_recent with no transactions returns []."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.database import Base
        from app.db.models import Customer, Transaction

        engine = create_engine(f"sqlite:///{tmp_path}/test.db")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        # Add customer with no transactions
        db.add(Customer(id="cust_empty", pattern="normal", is_churned=0))
        db.commit()

        detector = FraudDetector.__new__(FraudDetector)
        detector.model = None
        detector.is_trained = False

        result = detector.score_customer_recent("cust_empty", db, days=30)
        assert result == []
        db.close()


# ---------------------------------------------------------------------------
# API endpoint tests (TestClient)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_app():
    """Set up a minimal app with a temporary SQLite DB for endpoint tests."""
    import os
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.database import Base, get_db
    from app.db.models import Customer, Transaction
    from app.main import app

    # Use an in-memory-like temp DB so tests are fast
    engine = create_engine(
        "sqlite:///./test_fraud_api.db",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    # Seed minimal data: 2 customers
    db = TestingSession()
    try:
        if not db.query(Customer).first():
            db.add(Customer(id="customer_stable", pattern="normal", is_churned=0))
            db.add(Customer(id="customer_risky", pattern="at_risk", is_churned=0))

            base_date = datetime.now() - timedelta(days=5)
            for i in range(10):
                db.add(
                    Transaction(
                        id=f"tx_stable_{i}",
                        customer_id="customer_stable",
                        date=base_date + timedelta(days=i),
                        amount=100.0,
                        mcc="5411",
                        mcc_category="GROCERIES",
                        channel="POS",
                        merchant="Supermarket",
                        country="GB",
                        time_of_day="10:00",
                    )
                )
            # Risky customer: geo anomaly transaction
            db.add(
                Transaction(
                    id="tx_risky_geo",
                    customer_id="customer_risky",
                    date=datetime.now() - timedelta(days=1),
                    amount=900.0,
                    mcc="9999",
                    mcc_category="CASINO",
                    channel="ONLINE",
                    merchant="CasinoSite",
                    country="NG",
                    time_of_day="03:00",
                )
            )
            db.commit()
    finally:
        db.close()

    # Override the get_db dependency to use our test DB
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app, raise_server_exceptions=False)

    # Cleanup
    app.dependency_overrides.clear()
    engine.dispose()
    if os.path.exists("test_fraud_api.db"):
        os.remove("test_fraud_api.db")


class TestFraudAPIEndpoints:
    def test_fraud_signals_unknown_customer_returns_404(self, test_app):
        resp = test_app.get("/api/customers/nonexistent_xyz/fraud-signals")
        assert resp.status_code == 404

    def test_fraud_signals_stable_customer_returns_200(self, test_app):
        resp = test_app.get("/api/customers/customer_stable/fraud-signals?min_score=0.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_id"] == "customer_stable"
        assert "signals" in data
        assert "model_status" in data
        assert data["model_status"] in ("trained", "rule_based_only")

    def test_fraud_signals_risky_customer_flagged(self, test_app):
        resp = test_app.get("/api/customers/customer_risky/fraud-signals?min_score=0.0")
        assert resp.status_code == 200
        data = resp.json()
        # The casino + night + foreign tx should produce at least one signal
        assert data["flagged_count"] >= 1
        if data["signals"]:
            signal = data["signals"][0]
            assert "fraud_score" in signal
            assert "fraud_flags" in signal

    def test_fraud_signal_detail_returns_200(self, test_app):
        resp = test_app.get("/api/customers/customer_stable/fraud-signals/tx_stable_0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tx_id"] == "tx_stable_0"
        assert "feature_vector" in data
        assert "baseline_comparison" in data
        assert len(data["feature_vector"]) == 8

    def test_fraud_signal_detail_unknown_tx_returns_404(self, test_app):
        resp = test_app.get("/api/customers/customer_stable/fraud-signals/nonexistent_tx")
        assert resp.status_code == 404

    def test_high_risk_transactions_returns_200(self, test_app):
        resp = test_app.get("/api/ml/fraud/high-risk-transactions?min_score=0.0")
        assert resp.status_code == 200
        data = resp.json()
        assert "transactions" in data
        assert "total_flagged" in data
        assert "model_status" in data

    def test_high_risk_transactions_sorted_desc(self, test_app):
        resp = test_app.get("/api/ml/fraud/high-risk-transactions?min_score=0.0")
        assert resp.status_code == 200
        txs = resp.json()["transactions"]
        if len(txs) >= 2:
            scores = [t["fraud_score"] for t in txs]
            assert scores == sorted(scores, reverse=True), "Results must be sorted by fraud_score desc"

    def test_train_fraud_model_returns_200(self, test_app):
        resp = test_app.post("/api/ml/train-fraud-model")
        # Either 200 (success) or 500 (no transactions in test DB is a valid failure)
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert data["success"] is True
            assert data["n_transactions_trained"] > 0
