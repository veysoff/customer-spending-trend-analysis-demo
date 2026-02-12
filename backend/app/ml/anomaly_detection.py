import pandas as pd
import numpy as np
from typing import List, Dict, Any
import logging

from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

# Minimum transactions required to train Isolation Forest meaningfully.
# Below this threshold we fall back to the simple z-score method.
_MIN_TRANSACTIONS_FOR_IF = 20


class AnomalyDetector:
    """Detect spending anomalies using Isolation Forest (per-customer, unsupervised).

    For each customer we build a 5-dimensional feature matrix over all their
    transactions and train a fresh IsolationForest on that data.  This is
    intentionally per-customer so the model learns *that individual's* normal
    behaviour rather than a population baseline.

    Feature vector per transaction
    --------------------------------
    1. amount_zscore    – how many std-devs above/below the customer mean
    2. hour_of_day      – 0-23 (from time_of_day "HH:MM"); NULL → 12
    3. is_weekend       – 1 if Saturday/Sunday, else 0
    4. channel_code     – POS=0, ONLINE=1, ATM=2, OTHER=3
    5. category_freq    – relative frequency of the MCC category for this
                          customer (rare category → low value → more anomalous)

    Anomaly type classification
    ----------------------------
    After IsolationForest flags a transaction, we inspect its features to pick
    the most descriptive label:
      NIGHT_ACTIVITY   – transaction hour in 00-05
      SPENDING_SPIKE   – amount_zscore > 2.5
      BEHAVIOR_CHANGE  – rare category (freq < 0.03) or unusual channel
      SPENDING_SPIKE   – fallback (default)

    CONTRACT: transaction_df must have a 0-based RangeIndex (reset_index(drop=True)
    already applied in main.py).  The returned "index" field is the positional
    row number so that main.py can safely use .iloc[anomaly_idx].
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, transaction_df: pd.DataFrame,
               feature_vector: np.ndarray) -> List[Dict[str, Any]]:
        """Return anomalies sorted by score descending (most anomalous first).

        Parameters
        ----------
        transaction_df : pd.DataFrame
            Full transaction history for one customer.
            Must have a 0-based RangeIndex (reset_index already applied).
        feature_vector : np.ndarray
            Pre-computed feature vector (kept for API compatibility, not used
            internally – we re-derive features from transaction_df).

        Returns
        -------
        List of dicts with keys:
            index (positional), date, type, score (0-1), amount, reason
        """
        if len(transaction_df) < 2:
            return []

        amounts = transaction_df["amount"].dropna().values
        if len(amounts) == 0:
            return []

        mean_amount = float(amounts.mean())
        std_amount = float(amounts.std())  # numpy ddof=0, safe for N>=2

        if np.isnan(mean_amount) or np.isnan(std_amount):
            return []

        # ---- Choose detection strategy based on data volume ---------------
        if len(transaction_df) >= _MIN_TRANSACTIONS_FOR_IF:
            return self._detect_isolation_forest(
                transaction_df, mean_amount, std_amount
            )
        else:
            return self._detect_zscore(
                transaction_df, mean_amount, std_amount
            )

    # ------------------------------------------------------------------
    # Isolation Forest (primary strategy)
    # ------------------------------------------------------------------

    def _detect_isolation_forest(
        self,
        df: pd.DataFrame,
        mean_amount: float,
        std_amount: float,
    ) -> List[Dict[str, Any]]:
        """Train IsolationForest on this customer's transactions and return anomalies."""

        feature_matrix = self._build_feature_matrix(df, mean_amount, std_amount)

        model = IsolationForest(
            n_estimators=100,
            contamination=0.05,   # expect ~5% anomalies per customer
            random_state=42,
        )
        model.fit(feature_matrix)

        # decision_function: positive = normal, negative = anomaly
        raw_scores = model.decision_function(feature_matrix)
        predictions = model.predict(feature_matrix)  # -1 = anomaly, 1 = normal

        # Normalise raw_scores so that the most anomalous → score≈1.0.
        # Use moderate default (0.5) when all scores are equal (zero range).
        score_range = raw_scores.max() - raw_scores.min()
        if score_range > 0:
            normalised = (raw_scores - raw_scores.min()) / score_range
            anomaly_scores = 1.0 - normalised   # invert: low raw → high anomaly score
        else:
            # All transactions scored equally — assign moderate uniform score
            anomaly_scores = np.full(len(raw_scores), 0.5)

        anomalies = []
        # i is the positional index; idx is the DataFrame label (may differ).
        # We store i so main.py can use .iloc[i] safely.
        # feature_matrix rows correspond to df rows in the same positional order.
        for i, (idx, row) in enumerate(df.iterrows()):
            if predictions[i] != -1:
                continue  # not flagged as anomaly

            score = float(round(anomaly_scores[i], 3))

            amount = float(row["amount"]) if pd.notna(row["amount"]) else 0.0
            amount_zscore = (
                (amount - mean_amount) / std_amount if std_amount > 0 else 0.0
            )
            hour = self._parse_hour(row.get("time_of_day"))
            channel = str(row.get("channel", "")).upper()
            cat_freq = float(feature_matrix[i, 4])  # positional: same order as df

            anomaly_type = self._classify_anomaly_type(
                amount_zscore, hour, channel, cat_freq
            )

            date_str = (
                row["date"].strftime("%Y-%m-%d")
                if pd.notna(row["date"])
                else "Unknown"
            )

            reason = self._build_reason(anomaly_type, amount, amount_zscore, hour, channel)

            anomalies.append({
                "index": i,        # positional — safe for .iloc[] in main.py
                "date": date_str,
                "type": anomaly_type,
                "score": score,
                "amount": amount,
                "reason": reason,
            })

        anomalies.sort(key=lambda x: x["score"], reverse=True)
        return anomalies

    # ------------------------------------------------------------------
    # Z-score fallback (< 20 transactions)
    # ------------------------------------------------------------------

    def _detect_zscore(
        self,
        df: pd.DataFrame,
        mean_amount: float,
        std_amount: float,
    ) -> List[Dict[str, Any]]:
        """Simple mean+2*std threshold for customers with very few transactions."""
        if std_amount > 0:
            spike_threshold = mean_amount + 2 * std_amount
        else:
            spike_threshold = mean_amount * 3

        anomalies = []
        for i, (idx, row) in enumerate(df.iterrows()):  # i = positional
            amount = row["amount"]
            if pd.isna(amount) or float(amount) <= spike_threshold:
                continue

            amount = float(amount)
            safe_std = std_amount if std_amount > 0 else 1.0
            z_score = (amount - mean_amount) / safe_std
            score = min(0.95, z_score / (z_score + 2.0))

            date_str = (
                row["date"].strftime("%Y-%m-%d")
                if pd.notna(row["date"])
                else "Unknown"
            )
            anomalies.append({
                "index": i,        # positional — safe for .iloc[] in main.py
                "date": date_str,
                "type": "SPENDING_SPIKE",
                "score": round(score, 3),
                "amount": amount,
                "reason": f"Amount {amount:.2f} is {z_score:.1f}σ above typical spending",
            })

        anomalies.sort(key=lambda x: x["score"], reverse=True)
        return anomalies

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    def _build_feature_matrix(
        self,
        df: pd.DataFrame,
        mean_amount: float,
        std_amount: float,
    ) -> np.ndarray:
        """Build (N, 5) feature matrix for IsolationForest.

        Row i of the returned matrix corresponds to row i of df
        (positional order is preserved — required by _detect_isolation_forest).
        """
        safe_std = std_amount if std_amount > 0 else 1.0

        # 1. amount_zscore
        amounts = df["amount"].fillna(mean_amount).values
        amount_zscores = (amounts - mean_amount) / safe_std

        # 2. hour_of_day (0-23); default 12.0 when column missing or NULL
        if "time_of_day" in df.columns:
            hours = np.array(
                [self._parse_hour(v) for v in df["time_of_day"]],
                dtype=float,
            )
        else:
            hours = np.full(len(df), 12.0, dtype=float)

        # 3. is_weekend (0 or 1)
        # Use pd.to_datetime to handle both datetime.datetime and datetime.date
        dates = pd.to_datetime(df["date"], errors="coerce")
        weekends = np.array(
            [1.0 if pd.notna(d) and d.dayofweek >= 5 else 0.0 for d in dates],
            dtype=float,
        )

        # 4. channel_code
        channel_map = {"POS": 0.0, "ONLINE": 1.0, "ATM": 2.0}
        if "channel" in df.columns:
            channels = np.array(
                [channel_map.get(str(v).upper(), 3.0) for v in df["channel"]],
                dtype=float,
            )
        else:
            channels = np.zeros(len(df), dtype=float)  # default POS=0.0

        # 5. category_freq – relative frequency of each mcc_category
        if "mcc_category" in df.columns:
            cat_counts = df["mcc_category"].value_counts(normalize=True)
            cat_freqs = np.array(
                [float(cat_counts.get(v, 0.0)) for v in df["mcc_category"]],
                dtype=float,
            )
        else:
            cat_freqs = np.ones(len(df), dtype=float)

        return np.column_stack([
            amount_zscores,
            hours,
            weekends,
            channels,
            cat_freqs,
        ])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_hour(time_of_day) -> float:
        """Parse 'HH:MM' string → float hour 0-23.  Returns 12.0 on failure."""
        if time_of_day is None:
            return 12.0
        try:
            if pd.isna(time_of_day):
                return 12.0
        except (TypeError, ValueError):
            pass
        try:
            return float(str(time_of_day).split(":")[0])
        except (ValueError, IndexError):
            return 12.0

    @staticmethod
    def _classify_anomaly_type(
        amount_zscore: float,
        hour: float,
        channel: str,
        cat_freq: float,
    ) -> str:
        """Return the most descriptive anomaly label based on feature values."""
        if 0 <= hour <= 5:
            return "NIGHT_ACTIVITY"
        if amount_zscore > 2.5:
            return "SPENDING_SPIKE"
        if cat_freq < 0.03 or channel == "OTHER":
            return "BEHAVIOR_CHANGE"
        return "SPENDING_SPIKE"

    @staticmethod
    def _build_reason(
        anomaly_type: str,
        amount: float,
        amount_zscore: float,
        hour: float,
        channel: str,
    ) -> str:
        """Human-readable description of why this transaction is anomalous."""
        if anomaly_type == "NIGHT_ACTIVITY":
            return (
                f"Transaction at {int(hour):02d}:xx — unusual night-time activity. "
                f"Amount {amount:.2f}"
            )
        if anomaly_type == "BEHAVIOR_CHANGE":
            return (
                f"Rare spending category or unusual channel ({channel}). "
                f"Amount {amount:.2f}"
            )
        # SPENDING_SPIKE (default)
        return (
            f"Transaction amount {amount:.2f} is {amount_zscore:.1f}σ "
            "above typical spending"
        )

    # ------------------------------------------------------------------
    # Legacy helper (kept for API compatibility with main.py)
    # ------------------------------------------------------------------

    @staticmethod
    def get_anomaly_features(customer_df: pd.DataFrame) -> np.ndarray:
        """Extract summary feature vector for a customer (API compatibility).

        Returns an (1, 8) array used downstream in ExplainabilityEngine.
        Not used for anomaly detection itself (IsolationForest is trained
        inside detect()).
        """
        if len(customer_df) < 7:
            return np.array([[0] * 8])

        monthly_spending = customer_df.groupby(
            customer_df["date"].dt.to_period("M")
        )["amount"].sum()

        if len(monthly_spending) > 1:
            spending_volatility = monthly_spending.std()
            trend_slope = np.polyfit(
                np.arange(len(monthly_spending)),
                monthly_spending.values, 1
            )[0]
            first = monthly_spending.iloc[0]
            spending_change = (
                (monthly_spending.iloc[-1] - first) / first
                if first != 0 else 0.0
            )
        else:
            spending_volatility = 0.0
            trend_slope = 0.0
            spending_change = 0.0

        return np.array([[
            trend_slope,
            spending_volatility,
            spending_change,
            len(customer_df),
            customer_df["mcc_category"].nunique() if "mcc_category" in customer_df.columns else 0,
            customer_df["amount"].mean() if "amount" in customer_df.columns else 0.0,
            customer_df["channel"].nunique() if "channel" in customer_df.columns else 0,
            customer_df["country"].nunique() if "country" in customer_df.columns else 0,
        ]])
