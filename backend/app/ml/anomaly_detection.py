import pandas as pd
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Detect spending spike anomalies using statistical thresholds."""

    def detect(self, transaction_df: pd.DataFrame,
               feature_vector: np.ndarray) -> List[Dict[str, Any]]:
        """Detect anomalies in transactions.

        Uses adaptive threshold: mean + 2*std (95th percentile of normal spend).
        Anomaly score is z-score based (graduated, not fixed at 0.95).
        """
        anomalies = []

        # Issue #17 fix: Filter NULL amounts before calculating mean/std
        amounts = transaction_df["amount"].dropna().values
        if len(amounts) == 0:
            return []

        mean_amount = amounts.mean()
        std_amount = amounts.std()

        if np.isnan(mean_amount) or np.isnan(std_amount):
            return []

        # Threshold = mean + 2*std (flags top ~5% of transactions)
        # Falls back to 3x mean for zero-variance customers
        if std_amount > 0:
            spike_threshold = mean_amount + (2 * std_amount)
        else:
            spike_threshold = mean_amount * 3

        for idx, row in transaction_df.iterrows():
            trans_amount = row["amount"]
            if pd.isna(trans_amount):
                continue

            if trans_amount > spike_threshold:
                safe_std = std_amount if std_amount > 0 else 1.0
                z_score = (trans_amount - mean_amount) / safe_std
                # Graduated score: z=2 → 0.50, z=3 → 0.67, z=5 → 0.83, z=10 → 0.95 cap
                score = min(0.95, z_score / (z_score + 2.0))
                # Issue #17 fix: Check for NULL date before formatting
                date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "Unknown"
                anomalies.append({
                    "index": idx,
                    "date": date_str,
                    "type": "SPENDING_SPIKE",
                    "score": round(score, 3),
                    "amount": trans_amount,
                    "reason": f"Amount {trans_amount:.2f} is {z_score:.1f}σ above typical spending"
                })

        # Sort by score descending so top anomalies surface first
        anomalies.sort(key=lambda x: x["score"], reverse=True)
        return anomalies

    @staticmethod
    def get_anomaly_features(customer_df: pd.DataFrame) -> np.ndarray:
        """Extract features for anomaly detection (kept for API compatibility)."""
        if len(customer_df) < 7:
            return np.array([[0] * 8])

        monthly_spending = customer_df.groupby(
            customer_df["date"].dt.to_period("M")
        )["amount"].sum()

        if len(monthly_spending) > 1:
            spending_volatility = monthly_spending.std()
            trend_slope = np.polyfit(np.arange(len(monthly_spending)),
                                     monthly_spending.values, 1)[0]
            if monthly_spending.iloc[0] != 0:
                spending_change = (monthly_spending.iloc[-1] - monthly_spending.iloc[0]) / monthly_spending.iloc[0]
            else:
                spending_change = 0.0
        else:
            spending_volatility = 0
            trend_slope = 0
            spending_change = 0

        trans_count = len(customer_df)
        unique_categories = customer_df["mcc_category"].nunique()
        avg_amount = customer_df["amount"].mean()

        return np.array([[
            trend_slope,
            spending_volatility,
            spending_change,
            trans_count,
            unique_categories,
            avg_amount,
            customer_df["channel"].nunique(),
            customer_df["country"].nunique()
        ]])

    @staticmethod
    def get_anomaly_features(customer_df: pd.DataFrame) -> np.ndarray:
        """Extract features for anomaly detection."""
        if len(customer_df) < 7:
            return np.array([[0] * 8])

        monthly_spending = customer_df.groupby(
            customer_df["date"].dt.to_period("M")
        )["amount"].sum()

        if len(monthly_spending) > 1:
            spending_volatility = monthly_spending.std()
            trend_slope = np.polyfit(np.arange(len(monthly_spending)),
                                     monthly_spending.values, 1)[0]
            # Safe division: avoid ZeroDivisionError if first month = 0
            if monthly_spending.iloc[0] != 0:
                spending_change = (monthly_spending.iloc[-1] - monthly_spending.iloc[0]) / monthly_spending.iloc[0]
            else:
                spending_change = 0.0  # Cannot compare to zero baseline
        else:
            spending_volatility = 0
            trend_slope = 0
            spending_change = 0

        trans_count = len(customer_df)
        unique_categories = customer_df["mcc_category"].nunique()
        avg_amount = customer_df["amount"].mean()

        return np.array([[
            trend_slope,
            spending_volatility,
            spending_change,
            trans_count,
            unique_categories,
            avg_amount,
            customer_df["channel"].nunique(),
            customer_df["country"].nunique()
        ]])
