import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Detect anomalies using Isolation Forest."""

    def __init__(self, contamination: float = 0.10, n_estimators: int = 100,
                 random_state: int = 42):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model = None

    def fit(self, features: np.ndarray):
        """Fit Isolation Forest model."""
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.model.fit(features)
        return self

    def detect(self, transaction_df: pd.DataFrame,
               feature_vector: np.ndarray) -> List[Dict[str, Any]]:
        """Detect anomalies in transactions."""
        if self.model is None:
            return []

        anomalies = []

        # Score each transaction against behavioral pattern
        for idx, row in transaction_df.iterrows():
            trans_amount = row["amount"]
            monthly_avg = transaction_df["amount"].mean()
            deviation = abs(trans_amount - monthly_avg) / (monthly_avg + 1)

            # Detect spending spikes
            if trans_amount > monthly_avg * 3:
                anomalies.append({
                    "index": idx,
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "type": "SPENDING_SPIKE",
                    "score": min(0.95, 0.5 + deviation * 0.5),
                    "amount": trans_amount,
                    "reason": f"Amount {trans_amount:.2f} is 3x typical spending"
                })

        # Detect behavioral changes using model
        if len(feature_vector) > 0:
            predictions = self.model.predict(feature_vector)
            scores = self.model.score_samples(feature_vector)

            if predictions[0] == -1:  # Anomaly detected
                anomaly_score = 1 - (scores[0] + 0.5) / 1.5  # Normalize to 0-1
                anomalies.append({
                    "index": 0,
                    "date": transaction_df.iloc[-1]["date"].strftime("%Y-%m-%d"),
                    "type": "BEHAVIOR_CHANGE",
                    "score": max(0.0, min(1.0, anomaly_score)),
                    "amount": None,
                    "reason": "Behavioral pattern deviation detected"
                })

        return anomalies

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
            spending_change = (monthly_spending.iloc[-1] - monthly_spending.iloc[0]) / monthly_spending.iloc[0]
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
