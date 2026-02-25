import pandas as pd
import numpy as np
from scipy.stats import entropy
from typing import Dict, Any

class FeatureEngineer:
    """Extract features from transaction data."""

    @staticmethod
    def engineer_features(customer_df) -> Dict[str, Any]:
        """Engineer all features for a customer.

        Args:
            customer_df: pandas DataFrame or list of ORM Transaction objects

        Returns:
            Dictionary of engineered features
        """
        # Convert ORM objects to DataFrame if needed
        if isinstance(customer_df, list) and len(customer_df) > 0:
            if hasattr(customer_df[0], '__tablename__'):  # ORM object detection
                customer_df = pd.DataFrame([{
                    'customer_id': t.customer_id,
                    'date': t.date,
                    'amount': t.amount,
                    'mcc': t.mcc,
                    'mcc_category': t.mcc_category,
                    'channel': t.channel,
                    'merchant': t.merchant,
                    'country': t.country,
                    'time_of_day': t.time_of_day
                } for t in customer_df])

        features = {}

        # Safety check: ensure we have data
        if len(customer_df) == 0:
            # Return default empty features
            features["monthly_spending"] = []
            features["transaction_count"] = []
            features["avg_transaction_amount"] = []
            features["unique_categories"] = []
            features["spending_volatility"] = [0]
            features["trend_slope"] = 0.0
            features["category_entropy"] = 0.0
            features["pos_ratio"] = 0
            features["online_ratio"] = 0
            features["atm_ratio"] = 0
            features["weekend_ratio"] = 0
            features["current_monthly_spending"] = 0
            features["current_trans_count"] = 0
            return features

        # Aggregate by month
        customer_df = customer_df.copy()

        # Remove rows with NULL dates before processing
        if customer_df["date"].isnull().any():
            customer_df = customer_df.dropna(subset=['date'])

        # Recheck after dropping NULLs
        if len(customer_df) == 0:
            # Return default empty features if all dates were NULL
            features["monthly_spending"] = []
            features["transaction_count"] = []
            features["avg_transaction_amount"] = []
            features["unique_categories"] = []
            features["spending_volatility"] = [0]
            features["trend_slope"] = 0.0
            features["category_entropy"] = 0.0
            features["pos_ratio"] = 0
            features["online_ratio"] = 0
            features["atm_ratio"] = 0
            features["weekend_ratio"] = 0
            features["current_monthly_spending"] = 0
            features["current_trans_count"] = 0
            return features

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

        # Trend slope (simple linear regression) — slope per month
        if len(monthly_data) > 1:
            x = np.arange(len(monthly_data))  # Month index (0, 1, 2, ...)
            y = monthly_data["monthly_sum"].values  # Spending values
            slope_per_month = np.polyfit(x, y, 1)[0]  # AED per month
            features["trend_slope"] = float(slope_per_month)
        else:
            features["trend_slope"] = 0.0

        # Category entropy (diversity) - safe calculation
        if len(customer_df) == 0:
            features["category_entropy"] = 0.0
        else:
            category_counts = customer_df["mcc_category"].value_counts()
            if len(category_counts) == 0:
                features["category_entropy"] = 0.0
            else:
                category_probs = (category_counts / len(customer_df)).values
                features["category_entropy"] = float(entropy(category_probs))

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
    def get_rolling_averages(df: pd.DataFrame) -> Dict[str, float]:
        """Compute rolling average daily spend over 7, 30, and 90 day windows.

        Returns:
            Dict with keys "7d", "30d", "90d" and mean daily spend values.
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        daily = df.set_index("date").resample("D")["amount"].sum().fillna(0)
        return {
            "7d": round(float(daily.tail(7).mean()), 2),
            "30d": round(float(daily.tail(30).mean()), 2),
            "90d": round(float(daily.tail(90).mean()), 2),
        }

    @staticmethod
    def get_channel_trend(df: pd.DataFrame) -> list:
        """Compute per-month channel ratios (online/pos/atm) over transaction history.

        Returns:
            List of dicts with "month", "online_ratio", "pos_ratio", "atm_ratio".
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.to_period("M").astype(str)
        result = []
        for month, group in df.groupby("month"):
            dist = group["channel"].value_counts(normalize=True)
            result.append({
                "month": month,
                "online_ratio": round(float(dist.get("ONLINE", 0)), 3),
                "pos_ratio": round(float(dist.get("POS", 0)), 3),
                "atm_ratio": round(float(dist.get("ATM", 0)), 3),
            })
        return result

    @staticmethod
    def get_feature_vector(features: Dict[str, Any]) -> np.ndarray:
        """Convert features to numpy array for ML models."""
        # Safe extraction of list-based features (handle empty lists)
        # Check length explicitly, not just truthiness (e.g., [0] is truthy but may be placeholder)
        spending_volatility = features.get("spending_volatility", [0])
        spending_vol_value = float(spending_volatility[-1]) if len(spending_volatility) > 0 else 0.0

        unique_categories = features.get("unique_categories", [0])
        unique_cat_value = float(unique_categories[-1]) if len(unique_categories) > 0 else 0.0

        avg_trans_amount = features.get("avg_transaction_amount", [0])
        avg_amount_value = float(avg_trans_amount[-1]) if len(avg_trans_amount) > 0 else 0.0

        return np.array([
            features.get("trend_slope", 0),
            spending_vol_value,
            features.get("current_monthly_spending", 0),
            unique_cat_value,
            features.get("category_entropy", 0),
            features.get("online_ratio", 0),
            features.get("weekend_ratio", 0),
            avg_amount_value,
        ]).reshape(1, -1)
