# backend/app/ml/weighted_trend.py
"""
Calculate forward-looking trend using weighted regression.
Gives more importance to recent data points (recency bias).
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class WeightedTrendCalculator:
    """Calculate trend using weighted least squares (recent data weighted higher)."""

    @staticmethod
    def calculate_weighted_trend(
        customer_df: pd.DataFrame,
        window_days: int = 90,
        recency_weight: float = 3.0
    ) -> Dict[str, Any]:
        """
        Calculate trend using weighted least squares regression.

        Recent data points are weighted 3x more than old data.
        This gives a forward-looking bias vs backward-looking trend.

        Args:
            customer_df: Transaction DataFrame with 'date' and 'amount' columns
            window_days: Look back period (90 days = ~3 months)
            recency_weight: How much to weight recent data (3.0 = 3x weight)

        Returns:
            Dict with:
            - trend_slope_per_day: AED/day (future direction)
            - trend_slope_per_month: AED/month (future direction)
            - trend_direction: INCREASING, STABLE, or DECREASING
            - confidence: R² value (0.0-1.0)
            - explanation: Human-readable interpretation
            - data_points_used: Number of days in calculation
            - window_days: Window used
            - recency_weight: Weight applied
        """
        if len(customer_df) == 0:
            return {
                "trend_slope_per_day": 0.0,
                "trend_slope_per_month": 0.0,
                "trend_direction": "INSUFFICIENT_DATA",
                "confidence": 0.0,
                "explanation": "No transaction data",
                "data_points_used": 0,
                "window_days": window_days,
                "recency_weight": recency_weight
            }

        # Get last N days of spending
        cutoff_date = customer_df["date"].max() - timedelta(days=window_days)
        recent_df = customer_df[customer_df["date"] >= cutoff_date].copy()

        if len(recent_df) < 7:
            return {
                "trend_slope_per_day": 0.0,
                "trend_slope_per_month": 0.0,
                "trend_direction": "INSUFFICIENT_DATA",
                "confidence": 0.0,
                "explanation": f"Fewer than 7 days of data in {window_days}-day window",
                "data_points_used": len(recent_df),
                "window_days": window_days,
                "recency_weight": recency_weight
            }

        # Aggregate by day
        daily_spending = recent_df.groupby(recent_df["date"].dt.date).agg(
            {"amount": "sum"}
        ).reset_index()
        daily_spending.columns = ["date", "amount"]
        daily_spending["date"] = pd.to_datetime(daily_spending["date"])

        # Create weights: linear from 1.0 to recency_weight
        # Old days = 1.0 weight, recent days = recency_weight
        n_days = len(daily_spending)
        weights = np.linspace(1.0, recency_weight, n_days)

        # X = days since start, Y = spending amounts
        x = np.arange(n_days)
        y = daily_spending["amount"].values

        try:
            # Weighted least squares regression: fit trend line
            # y = slope * x + intercept
            coefficients = np.polyfit(x, y, deg=1, w=weights)
            slope_per_day = float(coefficients[0])

            # Convert to per month (30 days)
            slope_per_month = slope_per_day * 30

            # Calculate confidence: R² of the fit
            y_pred = np.polyval(coefficients, x)
            ss_res = np.sum(weights * (y - y_pred) ** 2)
            ss_tot = np.sum(weights * (y - y.mean()) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            confidence = float(np.clip(r_squared, 0, 1))

            # Determine direction
            threshold = 50  # AED/month (±50 = stable, >50 = increasing, <-50 = decreasing)

            if slope_per_month > threshold:
                direction = "INCREASING"
                explanation = f"Spending trending UP: +{slope_per_month:.1f} AED/month (confidence: {confidence*100:.0f}%)"
            elif slope_per_month < -threshold:
                direction = "DECREASING"
                explanation = f"Spending trending DOWN: {slope_per_month:.1f} AED/month (confidence: {confidence*100:.0f}%)"
            else:
                direction = "STABLE"
                explanation = f"Spending relatively stable: {slope_per_month:+.1f} AED/month (confidence: {confidence*100:.0f}%)"

            return {
                "trend_slope_per_day": slope_per_day,
                "trend_slope_per_month": slope_per_month,
                "trend_direction": direction,
                "confidence": confidence,
                "explanation": explanation,
                "data_points_used": n_days,
                "window_days": window_days,
                "recency_weight": recency_weight,
                "last_30_days_avg": float(daily_spending.tail(30)["amount"].mean())
            }

        except Exception as e:
            logger.error(f"Weighted trend calculation error: {e}")
            return {
                "trend_slope_per_day": 0.0,
                "trend_slope_per_month": 0.0,
                "trend_direction": "ERROR",
                "confidence": 0.0,
                "explanation": f"Calculation error: {str(e)}",
                "data_points_used": len(recent_df),
                "window_days": window_days,
                "recency_weight": recency_weight
            }

    @staticmethod
    def calculate_acceleration(customer_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate trend acceleration (is spending changing faster?).

        Compares recent trend to earlier trend.
        Positive acceleration = spending declining faster (churn risk signal!)

        Args:
            customer_df: Transaction DataFrame

        Returns:
            Dict with:
            - acceleration: AED/month² (rate of change of trend)
            - acceleration_direction: ACCELERATING_DOWN, STABLE, ACCELERATING_UP
            - early_period_trend: Trend in first 45 days
            - recent_period_trend: Trend in last 45 days
            - explanation: Human-readable interpretation
        """
        if len(customer_df) < 14:
            return {
                "acceleration": 0.0,
                "acceleration_direction": "INSUFFICIENT_DATA",
                "early_period_trend": 0.0,
                "recent_period_trend": 0.0,
                "explanation": "Need 14+ days of data"
            }

        # Split into two 45-day periods (90-day window)
        cutoff_date = customer_df["date"].max() - timedelta(days=90)
        recent_df = customer_df[customer_df["date"] >= cutoff_date].copy()

        if len(recent_df) < 14:
            return {
                "acceleration": 0.0,
                "acceleration_direction": "INSUFFICIENT_DATA",
                "early_period_trend": 0.0,
                "recent_period_trend": 0.0,
                "explanation": f"Need 90 days of data (have {(recent_df['date'].max() - recent_df['date'].min()).days})"
            }

        # Split point: mid-date
        mid_date = cutoff_date + timedelta(days=45)
        period_1 = recent_df[recent_df["date"] < mid_date]
        period_2 = recent_df[recent_df["date"] >= mid_date]

        def calc_slope(df):
            """Helper: calculate slope for a period."""
            if len(df) < 3:
                return 0.0

            daily = df.groupby(df["date"].dt.date)["amount"].sum().values
            if len(daily) < 2:
                return 0.0

            slope = np.polyfit(np.arange(len(daily)), daily, 1)[0]
            return slope * 30  # Per month

        trend_1 = calc_slope(period_1)
        trend_2 = calc_slope(period_2)

        # Acceleration = change in trend
        acceleration = trend_2 - trend_1

        # Threshold: ±50 AED/month² is "significant acceleration"
        accel_threshold = 50

        if acceleration < -accel_threshold:
            direction = "ACCELERATING_DOWN"  # Decline is getting worse!
            description = "⚠️ Spending decline is ACCELERATING (churn risk!)"
        elif acceleration > accel_threshold:
            direction = "ACCELERATING_UP"  # Improvement is accelerating
            description = "✅ Spending growth is ACCELERATING"
        else:
            direction = "STABLE"
            description = "Spending trend is stable (not accelerating)"

        return {
            "acceleration": float(acceleration),
            "acceleration_direction": direction,
            "early_period_trend": float(trend_1),
            "recent_period_trend": float(trend_2),
            "acceleration_threshold": accel_threshold,
            "explanation": description,
            "early_days": (period_1["date"].max() - period_1["date"].min()).days if len(period_1) > 0 else 0,
            "recent_days": (period_2["date"].max() - period_2["date"].min()).days if len(period_2) > 0 else 0
        }

    @staticmethod
    def compare_with_historical(
        customer_df: pd.DataFrame,
        recent_window_days: int = 30,
        historical_window_days: int = 120
    ) -> Dict[str, Any]:
        """
        Compare recent spending to historical average (simple vs. sophisticated).

        For quick alerts: "Is this month unusual?"

        Args:
            customer_df: Transaction DataFrame
            recent_window_days: How many days back is "recent"?
            historical_window_days: How many days back is "historical"?

        Returns:
            Dict with recent_avg, historical_avg, change_percent, etc.
        """
        if len(customer_df) < 30:
            return {
                "recent_avg": 0.0,
                "historical_avg": 0.0,
                "change_percent": 0.0,
                "explanation": "Insufficient data"
            }

        # Recent period
        cutoff_recent = customer_df["date"].max() - timedelta(days=recent_window_days)
        recent_df = customer_df[customer_df["date"] >= cutoff_recent]
        recent_avg = recent_df["amount"].sum() / max(len(recent_df.groupby(recent_df["date"].dt.date)), 1)

        # Historical period (exclude recent)
        cutoff_historical = customer_df["date"].max() - timedelta(days=historical_window_days)
        hist_df = customer_df[
            (customer_df["date"] >= cutoff_historical) & (customer_df["date"] < cutoff_recent)
        ]
        historical_avg = hist_df["amount"].sum() / max(len(hist_df.groupby(hist_df["date"].dt.date)), 1)

        if historical_avg == 0:
            change_percent = 0.0
        else:
            change_percent = ((recent_avg - historical_avg) / historical_avg) * 100

        if change_percent < -30:
            alert = "🔴 ALERT: Recent spending DOWN 30%+ (churn risk!)"
        elif change_percent < -10:
            alert = "🟡 WARNING: Recent spending DOWN 10-30%"
        elif change_percent > 30:
            alert = "🟢 POSITIVE: Recent spending UP 30%+"
        else:
            alert = "Normal: No significant change"

        return {
            "recent_avg": float(recent_avg),
            "historical_avg": float(historical_avg),
            "change_percent": float(change_percent),
            "alert": alert,
            "recent_window_days": recent_window_days,
            "historical_window_days": historical_window_days
        }
