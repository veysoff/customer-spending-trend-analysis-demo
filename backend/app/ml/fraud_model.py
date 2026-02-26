"""Fraud detection model for UC-3 Fraud Pattern Identification.

Global IsolationForest trained on a sample of all transactions.
Rule-based flags from FraudFeatureExtractor are combined with IF scores at inference.
"""

import json
import logging
import pickle
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from .. import config
from ..db.models import Customer, Transaction
from .fraud_features import FraudFeatureExtractor

logger = logging.getLogger(__name__)


class FraudDetector:
    """Global Isolation Forest for transaction-level fraud scoring.

    Unlike AnomalyDetector (per-customer), trains once on a sample of all
    transactions and scores any transaction relative to the global distribution.

    Final fraud_score = 0.6 * IF_score + 0.4 * rule_based_score when trained.
    Falls back to rule_based_score only when model is not yet trained.

    Model saved to: {config.MODELS_DIR}/fraud_detector.pkl
    """

    MODEL_PATH = config.MODELS_DIR / "fraud_detector.pkl"

    IF_PARAMS: Dict[str, Any] = {
        "n_estimators": 200,
        "contamination": 0.05,
        "max_samples": "auto",
        "random_state": 42,
    }

    def __init__(self) -> None:
        self.model: Optional[IsolationForest] = None
        self.is_trained: bool = False
        self._load_if_exists()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_if_exists(self) -> None:
        """Load model from disk if pkl exists."""
        if not self.MODEL_PATH.exists():
            return
        try:
            with open(self.MODEL_PATH, "rb") as f:
                data = pickle.load(f)
            self.model = data["model"]
            self.is_trained = True
            logger.info("Fraud model loaded from disk")
        except Exception as e:
            logger.warning(f"Failed to load fraud model: {e}")

    def save(self) -> None:
        """Persist trained model to disk."""
        config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.MODEL_PATH, "wb") as f:
            pickle.dump({"model": self.model}, f)
        logger.info(f"Fraud model saved to {self.MODEL_PATH}")

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, db: Session, sample_size: int = 50000) -> Dict[str, Any]:
        """Train IsolationForest on a sample of all transactions.

        Uses a simplified 5-feature matrix (history-independent) so training
        is fast and vectorized without per-row customer lookups.

        Features: amount, hour_of_day, channel_code, is_foreign_country, mcc_risk_code

        Args:
            db: Database session.
            sample_size: Max number of transactions to train on.

        Returns:
            Dict with n_transactions_trained, contamination_pct, timestamp.
        """
        logger.info(f"Loading up to {sample_size} transactions for fraud model training...")

        # Query a sample of transactions (ordered by id for determinism)
        query = db.query(Transaction).order_by(Transaction.id).limit(sample_size)
        transactions = query.all()

        if not transactions:
            raise ValueError("No transactions found in the database. Cannot train.")

        logger.info(f"Building feature matrix from {len(transactions)} transactions...")

        # Convert ORM objects to DataFrame
        rows = [
            {
                "amount": t.amount,
                "time_of_day": t.time_of_day,
                "channel": t.channel,
                "country": t.country,
                "mcc_category": t.mcc_category,
            }
            for t in transactions
        ]
        df = pd.DataFrame(rows)

        feature_matrix = FraudFeatureExtractor.build_feature_matrix(df)

        logger.info(f"Training IsolationForest on {len(feature_matrix)} transactions...")
        self.model = IsolationForest(**self.IF_PARAMS)
        self.model.fit(feature_matrix)
        self.is_trained = True

        self.save()

        result = {
            "n_transactions_trained": len(transactions),
            "contamination_pct": self.IF_PARAMS["contamination"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            f"Fraud model trained on {result['n_transactions_trained']} transactions"
        )
        return result

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_transaction(
        self,
        tx_row: pd.Series,
        history_df: pd.DataFrame,
    ) -> Tuple[float, List[str]]:
        """Score a single transaction for fraud risk.

        Combines IsolationForest output (when trained) with rule-based composite:
            final = 0.6 * IF_score + 0.4 * rule_score   (model trained)
            final = rule_score                            (model not trained)

        Args:
            tx_row: Single transaction as a pandas Series.
            history_df: Customer's full transaction history (excluding tx_row).

        Returns:
            (fraud_score [0.0-1.0], fraud_flags list)
        """
        features = FraudFeatureExtractor.extract(tx_row, history_df)
        rule_score = features["fraud_score"]
        flags = features["fraud_flags"]

        if self.is_trained and self.model is not None:
            feature_array = np.array([[
                float(tx_row.get("amount", 0) or 0),
                float(FraudFeatureExtractor._parse_hour(tx_row.get("time_of_day"))),
                self._channel_code(str(tx_row.get("channel", "") or "")),
                self._is_foreign(str(tx_row.get("country", "") or "")),
                self._mcc_risk(str(tx_row.get("mcc_category", "") or "")),
            ]])
            raw = float(self.model.decision_function(feature_array)[0])
            if_score = self._normalize_if_score(raw)
            final_score = round(0.6 * if_score + 0.4 * rule_score, 4)
        else:
            final_score = rule_score

        return float(np.clip(final_score, 0.0, 1.0)), flags

    def score_customer_recent(
        self,
        customer_id: str,
        db: Session,
        days: int = 30,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Score all recent transactions for a customer.

        Fetches ALL customer transactions for history context, then scores only
        transactions within the last `days` window (history may extend further back).

        Args:
            customer_id: Customer identifier.
            db: Database session.
            days: Scoring window in days (most recent).
            min_score: Only return transactions at or above this threshold.

        Returns:
            List of scored transaction dicts sorted by fraud_score desc.
        """
        all_txs = (
            db.query(Transaction)
            .filter(Transaction.customer_id == customer_id)
            .order_by(Transaction.date)
            .all()
        )

        if not all_txs:
            return []

        # Build full history DataFrame (needed for 90-day feature context)
        history_rows = [
            {
                "id": t.id,
                "date": t.date,
                "amount": t.amount,
                "mcc": t.mcc,
                "mcc_category": t.mcc_category,
                "channel": t.channel,
                "merchant": t.merchant,
                "country": t.country,
                "time_of_day": t.time_of_day,
            }
            for t in all_txs
        ]
        history_df = pd.DataFrame(history_rows)
        history_df["date"] = pd.to_datetime(history_df["date"], errors="coerce")

        # Determine scoring window cutoff
        cutoff = datetime.now() - timedelta(days=days)

        results = []
        for i, tx in enumerate(all_txs):
            tx_date = pd.to_datetime(tx.date, errors="coerce")
            if pd.isna(tx_date) or tx_date.replace(tzinfo=None) < cutoff:
                continue

            # History = all transactions BEFORE this one (positional slice)
            prior_df = history_df.iloc[:i].copy() if i > 0 else pd.DataFrame(columns=history_df.columns)

            tx_row = history_df.iloc[i]
            fraud_score, fraud_flags = self.score_transaction(tx_row, prior_df)

            if fraud_score < min_score:
                continue

            flag_details = FraudFeatureExtractor.get_flag_details(tx_row, fraud_flags)

            results.append({
                "tx_id": tx.id,
                "date": tx.date.strftime("%Y-%m-%d") if hasattr(tx.date, "strftime") else str(tx.date),
                "amount": float(tx.amount),
                "mcc_category": tx.mcc_category,
                "channel": tx.channel,
                "country": tx.country,
                "fraud_score": fraud_score,
                "fraud_flags": fraud_flags,
                "flag_details": flag_details,
                "top_factor": fraud_flags[0] if fraud_flags else "none",
            })

        results.sort(key=lambda x: x["fraud_score"], reverse=True)
        return results

    def explain(self, features: Dict[str, float]) -> List[Dict[str, str]]:
        """Return top 3 contributing factors as human-readable explanations.

        Returns list of dicts: {factor, value, explanation}
        """
        scored = sorted(
            [
                (feat, val)
                for feat, val in features.items()
                if feat in FraudFeatureExtractor.WEIGHTS
            ],
            key=lambda x: x[1] * FraudFeatureExtractor.WEIGHTS.get(x[0], 0),
            reverse=True,
        )[:3]

        result = []
        for feat, val in scored:
            flag_name = FraudFeatureExtractor.FLAG_NAMES.get(feat, feat)
            meta = FraudFeatureExtractor.FLAG_METADATA.get(flag_name, {})
            result.append({
                "factor": flag_name,
                "value": f"{val:.3f}",
                "explanation": meta.get("label", feat),
            })
        return result

    def get_pattern_clusters(
        self, scored_txs: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict]]:
        """Group flagged transactions by fraud pattern type.

        Returns: {'geo_risk': [...], 'card_testing': [...], ...}
        """
        clusters: Dict[str, List] = {}
        for tx in scored_txs:
            for flag in tx.get("fraud_flags", []):
                clusters.setdefault(flag, []).append(tx)
        return clusters

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_if_score(raw: float) -> float:
        """Map IsolationForest decision_function output to [0, 1].

        decision_function: negative = anomaly, positive = normal.
        Typical range: roughly -0.5 to +0.5.
        Maps: -0.5 → 1.0, 0.0 → 0.5, +0.5 → 0.0
        """
        return float(np.clip(0.5 - raw, 0.0, 1.0))

    @staticmethod
    def _channel_code(channel: str) -> float:
        return {"POS": 0.0, "ONLINE": 1.0, "ATM": 2.0, "MOBILE": 3.0}.get(
            channel.upper(), 4.0
        )

    @staticmethod
    def _is_foreign(country: str) -> float:
        _KNOWN = {"GB", "US", "FR", "DE", "ES"}
        return 0.0 if country.upper() in _KNOWN else 1.0

    @staticmethod
    def _mcc_risk(mcc_category: str) -> float:
        _HIGH_RISK = {"CASINO", "PAWN_SHOP", "FIREARMS", "DIRECT_MARKETING"}
        return 1.0 if mcc_category.upper() in _HIGH_RISK else 0.0
