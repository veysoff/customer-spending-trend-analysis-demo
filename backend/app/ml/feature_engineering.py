import pandas as pd
import numpy as np
from scipy.stats import entropy
from typing import Dict, Any

class FeatureEngineer:
    """Extract features from transaction data."""

    @staticmethod
    def engineer_features(customer_df: pd.DataFrame) -> Dict[str, Any]:
        """Engineer all features for a customer."""
        features = {}

        # Aggregate by month
        customer_df = customer_df.copy()
        customer_df["year_month"] = customer_df["date"].dt.to_period("M")

        monthly_data = customer_df.groupby("year_month").agg({
            "amount": ["sum", "mean", "median", "count", "std"],
            "mcc_category": lambda x: x.nunique(),
            "channel": lambda x: (x == "ONLINE").sum() / len(x) if len(x) > 0 else 0,
        }).reset_index()

        monthly_data.columns = ["year_month", "monthly_sum", "avg_amount",
                                "median_amount", "trans_count", "amount_std",
                                "unique_categories", "online_ratio"]

        features["monthly_spending"] = monthly_data["monthly_sum"].tolist()
        features["transaction_count"] = monthly_data["trans_count"].tolist()
        features["avg_transaction_amount"] = monthly_data["avg_amount"].tolist()
        features["unique_categories"] = monthly_data["unique_categories"].tolist()

        # Volatility (rolling standard deviation)
        if len(monthly_data) > 1:
            rolling_std = monthly_data["monthly_sum"].rolling(window=3, min_periods=1).std()
            features["spending_volatility"] = rolling_std.tolist()
        else:
            features["spending_volatility"] = [0]

        # Trend slope (simple linear regression)
        if len(monthly_data) > 1:
            x = np.arange(len(monthly_data))
            y = monthly_data["monthly_sum"].values
            slope = np.polyfit(x, y, 1)[0]
            features["trend_slope"] = slope
        else:
            features["trend_slope"] = 0

        # Category entropy (diversity)
        category_counts = customer_df["mcc_category"].value_counts()
        category_probs = (category_counts / len(customer_df)).values
        features["category_entropy"] = entropy(category_probs)

        # Channel distribution
        channel_dist = customer_df["channel"].value_counts(normalize=True)
        features["pos_ratio"] = channel_dist.get("POS", 0)
        features["online_ratio"] = channel_dist.get("ONLINE", 0)
        features["atm_ratio"] = channel_dist.get("ATM", 0)

        # Temporal patterns
        customer_df["hour"] = customer_df["date"].dt.hour
        customer_df["dayofweek"] = customer_df["date"].dt.dayofweek
        weekend_trans = (customer_df["dayofweek"] >= 5).sum()
        features["weekend_ratio"] = weekend_trans / len(customer_df) if len(customer_df) > 0 else 0

        # Current month statistics
        if len(monthly_data) > 0:
            latest_month = monthly_data.iloc[-1]
            features["current_monthly_spending"] = float(latest_month["monthly_sum"])
            features["current_trans_count"] = int(latest_month["trans_count"])
        else:
            features["current_monthly_spending"] = 0
            features["current_trans_count"] = 0

        return features

    @staticmethod
    def get_feature_vector(features: Dict[str, Any]) -> np.ndarray:
        """Convert features to numpy array for ML models."""
        return np.array([
            features.get("trend_slope", 0),
            features.get("spending_volatility", [0])[-1],
            features.get("current_monthly_spending", 0),
            features.get("unique_categories", [0])[-1],
            features.get("category_entropy", 0),
            features.get("online_ratio", 0),
            features.get("weekend_ratio", 0),
            features.get("avg_transaction_amount", [0])[-1],
        ]).reshape(1, -1)
