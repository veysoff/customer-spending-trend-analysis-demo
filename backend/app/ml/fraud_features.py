"""Transaction-level fraud feature engineering for UC-3 Fraud Pattern Identification.

Extracts 8 features per transaction plus a composite fraud_score.
Handles both 'HH:MM' and word-label time_of_day values (persona data uses labels).
"""

import json
import logging
from datetime import timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Word-label → approximate hour mapping for persona transactions
_HOUR_LABELS: Dict[str, int] = {
    "morning": 9,
    "afternoon": 14,
    "evening": 19,
    "night": 2,
    "lunch": 12,
    "dinner": 19,
    "midnight": 0,
    "dawn": 5,
}

# MCC categories considered inherently higher risk
_HIGH_RISK_MCC = {"CASINO", "PAWN_SHOP", "FIREARMS"}

# Standard countries present in the synthetic data generator
_KNOWN_COUNTRIES = {"AE", "IN", "PH", "GB", "US", "FR", "DE", "ES"}


class FraudFeatureExtractor:
    """Extract 8 transaction-level fraud features and a composite fraud_score.

    Primary API::

        features = FraudFeatureExtractor.extract(tx_row, history_df)

    Parameters
    ----------
    tx_row : pd.Series
        Single transaction row being scored.
    history_df : pd.DataFrame
        All customer transactions available as context (last 90 days recommended).
        May be empty — all methods return 0.0 gracefully in that case.

    Returns
    -------
    dict with keys:
        velocity_score, amount_deviation_score, geo_risk_score, hour_risk_score,
        micro_before_large_flag, merchant_drift_score, channel_anomaly_score,
        structuring_flag, fraud_score, fraud_flags (List[str])
    """

    # Feature weights for composite fraud_score
    WEIGHTS: Dict[str, float] = {
        "velocity_score": 0.10,
        "amount_deviation_score": 0.20,
        "geo_risk_score": 0.25,        # geo jump is the strongest fraud signal
        "hour_risk_score": 0.10,
        "micro_before_large_flag": 0.15,
        "merchant_drift_score": 0.05,
        "channel_anomaly_score": 0.05,
        "structuring_flag": 0.10,
    }

    # Human-readable flag names for each feature
    FLAG_NAMES: Dict[str, str] = {
        "geo_risk_score": "geo_risk",
        "hour_risk_score": "night_activity",
        "micro_before_large_flag": "card_testing",
        "structuring_flag": "structuring",
        "amount_deviation_score": "amount_spike",
        "velocity_score": "high_velocity",
        "merchant_drift_score": "merchant_drift",
        "channel_anomaly_score": "channel_anomaly",
    }

    # Minimum feature value to trigger a flag
    FLAG_THRESHOLDS: Dict[str, float] = {
        "geo_risk_score": 0.5,
        "hour_risk_score": 0.5,
        "micro_before_large_flag": 0.5,
        "structuring_flag": 0.5,
        "amount_deviation_score": 0.7,
        "velocity_score": 0.6,
        "merchant_drift_score": 0.5,
        "channel_anomaly_score": 0.5,
    }

    # Labels and severity for flag explanations
    FLAG_METADATA: Dict[str, Dict[str, str]] = {
        "geo_risk": {
            "label": "Geographic Anomaly",
            "severity": "HIGH",
            "template": "Transaction in {country} — not seen in customer's recent history",
        },
        "night_activity": {
            "label": "Unusual Night Activity",
            "severity": "MEDIUM",
            "template": "Transaction at {hour:02d}:xx — outside customer's normal active hours",
        },
        "card_testing": {
            "label": "Card Testing / Structuring",
            "severity": "HIGH",
            "template": "Small transaction ({amount:.2f}) followed by large transaction within 30 minutes",
        },
        "structuring": {
            "label": "Micro-Transaction Cluster",
            "severity": "HIGH",
            "template": "Multiple small transactions ({amount:.2f}) within 10 minutes",
        },
        "amount_spike": {
            "label": "Unusual Amount",
            "severity": "MEDIUM",
            "template": "Amount {amount:.2f} significantly above customer's typical spending",
        },
        "high_velocity": {
            "label": "High Transaction Velocity",
            "severity": "MEDIUM",
            "template": "Multiple transactions in a short time window",
        },
        "merchant_drift": {
            "label": "New Merchant Category",
            "severity": "LOW",
            "template": "Category {category} not seen in customer's recent history",
        },
        "channel_anomaly": {
            "label": "Unusual Channel",
            "severity": "LOW",
            "template": "Channel {channel} not used by this customer recently",
        },
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def extract(tx_row: pd.Series, history_df: pd.DataFrame) -> Dict[str, Any]:
        """Compute all 8 fraud features and composite score for one transaction.

        Parameters
        ----------
        tx_row : pd.Series
            The transaction being scored.
        history_df : pd.DataFrame
            Customer transaction history for context. Should NOT include tx_row.

        Returns
        -------
        Dict with feature values, fraud_score [0,1], and fraud_flags list.
        """
        feats: Dict[str, float] = {
            "velocity_score": FraudFeatureExtractor._velocity_score(tx_row, history_df),
            "amount_deviation_score": FraudFeatureExtractor._amount_deviation_score(tx_row, history_df),
            "geo_risk_score": FraudFeatureExtractor._geo_risk_score(tx_row, history_df),
            "hour_risk_score": FraudFeatureExtractor._hour_risk_score(tx_row, history_df),
            "micro_before_large_flag": FraudFeatureExtractor._micro_before_large_flag(tx_row, history_df),
            "merchant_drift_score": FraudFeatureExtractor._merchant_drift_score(tx_row, history_df),
            "channel_anomaly_score": FraudFeatureExtractor._channel_anomaly_score(tx_row, history_df),
            "structuring_flag": FraudFeatureExtractor._structuring_flag(tx_row, history_df),
        }
        feats["fraud_score"] = FraudFeatureExtractor._compute_fraud_score(feats)
        feats["fraud_flags"] = FraudFeatureExtractor.get_triggered_flags(feats)
        return feats

    @staticmethod
    def get_flag_details(
        tx_row: pd.Series,
        fraud_flags: List[str],
    ) -> List[Dict[str, str]]:
        """Build human-readable explanation dicts for each triggered flag.

        Returns list of {flag, label, explanation, severity}.
        """
        details = []
        for flag in fraud_flags:
            meta = FraudFeatureExtractor.FLAG_METADATA.get(flag)
            if not meta:
                continue
            try:
                explanation = meta["template"].format(
                    country=tx_row.get("country", "?"),
                    hour=FraudFeatureExtractor._parse_hour(tx_row.get("time_of_day")),
                    amount=float(tx_row.get("amount", 0)),
                    category=tx_row.get("mcc_category", "?"),
                    channel=tx_row.get("channel", "?"),
                )
            except (KeyError, ValueError):
                explanation = meta["template"]
            details.append({
                "flag": flag,
                "label": meta["label"],
                "explanation": explanation,
                "severity": meta["severity"],
            })
        return details

    @staticmethod
    def get_triggered_flags(feature_values: Dict[str, float]) -> List[str]:
        """Return list of flag names for features at or above their threshold."""
        flags = []
        for feat_key, flag_name in FraudFeatureExtractor.FLAG_NAMES.items():
            threshold = FraudFeatureExtractor.FLAG_THRESHOLDS.get(feat_key, 0.5)
            if feature_values.get(feat_key, 0.0) >= threshold:
                flags.append(flag_name)
        return flags

    @staticmethod
    def build_feature_matrix(df: pd.DataFrame) -> np.ndarray:
        """Build (N, 5) feature matrix for IsolationForest training.

        Uses only history-independent features so the matrix can be built
        in one vectorized pass without per-row customer lookups.

        Features:
            0. amount (raw float)
            1. hour_of_day (0-23)
            2. channel_code (POS=0, ONLINE=1, ATM=2, MOBILE=3, OTHER=4)
            3. is_foreign_country (1 if country not in known standard set)
            4. mcc_risk_code (1 if MCC category is in high-risk set, else 0)
        """
        n = len(df)
        if n == 0:
            return np.empty((0, 5), dtype=float)

        amounts = df["amount"].fillna(0.0).values.astype(float)

        if "time_of_day" in df.columns:
            hours = np.array(
                [FraudFeatureExtractor._parse_hour(v) for v in df["time_of_day"]],
                dtype=float,
            )
        else:
            hours = np.full(n, 12.0)

        channel_map = {"POS": 0.0, "ONLINE": 1.0, "ATM": 2.0, "MOBILE": 3.0}
        if "channel" in df.columns:
            channels = np.array(
                [channel_map.get(str(v).upper(), 4.0) for v in df["channel"]],
                dtype=float,
            )
        else:
            channels = np.zeros(n)

        if "country" in df.columns:
            is_foreign = np.array(
                [0.0 if str(v).upper() in _KNOWN_COUNTRIES else 1.0 for v in df["country"]],
                dtype=float,
            )
        else:
            is_foreign = np.zeros(n)

        if "mcc_category" in df.columns:
            mcc_risk = np.array(
                [1.0 if str(v).upper() in _HIGH_RISK_MCC else 0.0 for v in df["mcc_category"]],
                dtype=float,
            )
        else:
            mcc_risk = np.zeros(n)

        return np.column_stack([amounts, hours, channels, is_foreign, mcc_risk])

    # ------------------------------------------------------------------
    # Individual feature methods
    # ------------------------------------------------------------------

    @staticmethod
    def _velocity_score(tx_row: pd.Series, history_df: pd.DataFrame) -> float:
        """Count of transactions in a ±60-minute window, normalised to [0, 1].

        score = min(count / 5.0, 1.0)   (5+ tx/hour = max score)
        Returns 0.0 if datetime info is unavailable.
        """
        if history_df.empty or "date" not in history_df.columns:
            return 0.0
        try:
            tx_dt = pd.to_datetime(tx_row.get("date"), errors="coerce")
            if pd.isna(tx_dt):
                return 0.0
            dates = pd.to_datetime(history_df["date"], errors="coerce").dropna()
            window = timedelta(hours=1)
            count = int(((dates >= tx_dt - window) & (dates <= tx_dt + window)).sum())
            return min(count / 5.0, 1.0)
        except Exception:
            return 0.0

    @staticmethod
    def _amount_deviation_score(tx_row: pd.Series, history_df: pd.DataFrame) -> float:
        """Z-score of tx amount vs 90-day mean, normalised to [0, 1].

        score = min(abs(z) / 5.0, 1.0)   (5σ = max score)
        Returns 0.0 if history has fewer than 2 rows.
        """
        if len(history_df) < 2 or "amount" not in history_df.columns:
            return 0.0
        try:
            amounts = history_df["amount"].dropna().astype(float)
            if len(amounts) < 2:
                return 0.0
            mean = float(amounts.mean())
            std = float(amounts.std())
            if std == 0:
                return 0.0
            tx_amount = float(tx_row.get("amount", 0) or 0)
            z = abs(tx_amount - mean) / std
            return min(z / 5.0, 1.0)
        except Exception:
            return 0.0

    @staticmethod
    def _geo_risk_score(tx_row: pd.Series, history_df: pd.DataFrame) -> float:
        """1.0 if this transaction's country was not seen in the customer's history."""
        if history_df.empty or "country" not in history_df.columns:
            return 0.0
        try:
            tx_country = str(tx_row.get("country", "") or "").upper()
            if not tx_country:
                return 0.0
            known = {str(c).upper() for c in history_df["country"].dropna()}
            return 1.0 if tx_country not in known else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _hour_risk_score(tx_row: pd.Series, history_df: pd.DataFrame) -> float:
        """Night-time risk: 1.0 if transaction hour in 00-05.

        Adjusted downward if the customer regularly transacts at night.
        night_baseline = fraction of history in hours 00-05
        score = (1.0 if night else 0.0) * (1.0 - min(night_baseline * 5, 0.8))
        """
        try:
            hour = FraudFeatureExtractor._parse_hour(tx_row.get("time_of_day"))
            if hour > 5:
                return 0.0
            # Compute customer's night baseline
            if history_df.empty or "time_of_day" not in history_df.columns:
                return 1.0
            hours = np.array(
                [FraudFeatureExtractor._parse_hour(v) for v in history_df["time_of_day"]],
                dtype=float,
            )
            night_baseline = float((hours <= 5).mean())
            return max(0.0, 1.0 - min(night_baseline * 5, 0.8))
        except Exception:
            return 0.0

    @staticmethod
    def _micro_before_large_flag(tx_row: pd.Series, history_df: pd.DataFrame) -> float:
        """Card-testing flag: 1.0 if this tx is small (<10) and a large tx (>500)
        follows within 30 minutes, or this tx is large (>500) and a small tx (<10)
        precedes it within 30 minutes.
        """
        if history_df.empty or "date" not in history_df.columns:
            return 0.0
        try:
            tx_amount = float(tx_row.get("amount", 0) or 0)
            tx_dt = pd.to_datetime(tx_row.get("date"), errors="coerce")
            if pd.isna(tx_dt):
                return 0.0

            dates = pd.to_datetime(history_df["date"], errors="coerce")
            amounts = history_df["amount"].fillna(0).astype(float)
            window = timedelta(minutes=30)

            if tx_amount < 10:
                # Look for large tx after this one within 30 min
                mask = (dates > tx_dt) & (dates <= tx_dt + window) & (amounts > 500)
                return 1.0 if mask.any() else 0.0
            elif tx_amount > 500:
                # Look for small tx before this one within 30 min
                mask = (dates >= tx_dt - window) & (dates < tx_dt) & (amounts < 10)
                return 1.0 if mask.any() else 0.0
            return 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _merchant_drift_score(tx_row: pd.Series, history_df: pd.DataFrame) -> float:
        """1.0 if this transaction's MCC category was not seen in the last 90 days of history.

        Limited to 90-day lookback window for more relevant pattern detection.
        Older merchant categories are not considered drift signals.
        """
        if history_df.empty or "mcc_category" not in history_df.columns:
            return 0.0
        try:
            tx_date = pd.to_datetime(tx_row.get("date"), errors="coerce")
            if pd.isna(tx_date):
                # No date context → fallback to full history
                known = {str(c).upper() for c in history_df["mcc_category"].dropna()}
            else:
                # Limit to last 90 days
                window_start = tx_date - timedelta(days=90)
                history_df_dated = history_df.copy()
                history_df_dated["date"] = pd.to_datetime(history_df_dated["date"], errors="coerce")
                recent = history_df_dated[
                    (history_df_dated["date"] >= window_start) &
                    (history_df_dated["date"] < tx_date)
                ]
                if recent.empty:
                    return 0.0  # No history in 90-day window
                known = {str(c).upper() for c in recent["mcc_category"].dropna()}

            tx_cat = str(tx_row.get("mcc_category", "") or "").upper()
            if not tx_cat:
                return 0.0
            return 1.0 if tx_cat not in known else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _channel_anomaly_score(tx_row: pd.Series, history_df: pd.DataFrame) -> float:
        """1.0 if this transaction's channel was not used by the customer in history."""
        if history_df.empty or "channel" not in history_df.columns:
            return 0.0
        try:
            tx_channel = str(tx_row.get("channel", "") or "").upper()
            if not tx_channel:
                return 0.0
            known = {str(c).upper() for c in history_df["channel"].dropna()}
            return 1.0 if tx_channel not in known else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _structuring_flag(tx_row: pd.Series, history_df: pd.DataFrame) -> float:
        """1.0 if 3+ transactions under 20 AED occur within 10 minutes of this one."""
        if history_df.empty or "date" not in history_df.columns:
            return 0.0
        try:
            tx_amount = float(tx_row.get("amount", 0) or 0)
            if tx_amount >= 20:
                return 0.0
            tx_dt = pd.to_datetime(tx_row.get("date"), errors="coerce")
            if pd.isna(tx_dt):
                return 0.0

            dates = pd.to_datetime(history_df["date"], errors="coerce")
            amounts = history_df["amount"].fillna(0).astype(float)
            window = timedelta(minutes=10)

            nearby_small = (
                (dates >= tx_dt - window)
                & (dates <= tx_dt + window)
                & (amounts < 20)
            )
            # Include the current transaction in the count
            count = int(nearby_small.sum()) + 1
            return 1.0 if count >= 3 else 0.0
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Helper: score composition
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_fraud_score(feature_values: Dict[str, float]) -> float:
        """Weighted combination of 8 features, clipped to [0.0, 1.0]."""
        score = sum(
            feature_values.get(feat, 0.0) * weight
            for feat, weight in FraudFeatureExtractor.WEIGHTS.items()
        )
        return round(float(np.clip(score, 0.0, 1.0)), 4)

    # ------------------------------------------------------------------
    # Helper: time parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_hour(value) -> int:
        """Normalise time_of_day to integer hour 0-23.

        Handles:
        - 'HH:MM' strings (synthetic data generator format)
        - Word labels ('morning', 'afternoon', 'evening', 'night', ...)
        - None / NaN / unparseable → returns 12 (noon default)
        """
        if value is None:
            return 12
        try:
            if pd.isna(value):
                return 12
        except (TypeError, ValueError):
            pass

        s = str(value).strip().lower()

        # Word label lookup
        if s in _HOUR_LABELS:
            return _HOUR_LABELS[s]

        # HH:MM format
        if ":" in s:
            try:
                return int(s.split(":")[0])
            except (ValueError, IndexError):
                pass

        # Plain integer string
        try:
            return int(float(s)) % 24
        except (ValueError, TypeError):
            return 12
