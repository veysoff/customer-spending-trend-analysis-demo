# backend/app/ml/seasonality_detection.py
"""
Automatically detect seasonality cycles (weekly, monthly, quarterly, yearly).
Uses ACF (Auto-Correlation Function) analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.stattools import acf
except ImportError:
    logger.warning("statsmodels not installed; ACF analysis unavailable")
    acf = None


class SeasonalityDetector:
    """Automatically detect seasonality cycles (weekly, monthly, quarterly, yearly)."""

    # Standard period definitions (in days)
    PERIOD_DEFINITIONS = {
        "WEEKLY": {"min": 6, "max": 8, "expected": 7},
        "BIWEEKLY": {"min": 13, "max": 15, "expected": 14},
        "MONTHLY": {"min": 28, "max": 32, "expected": 30},
        "QUARTERLY": {"min": 80, "max": 100, "expected": 90},
        "YEARLY": {"min": 350, "max": 380, "expected": 365}
    }

    @staticmethod
    def detect_seasonality(customer_df: pd.DataFrame, min_acf_threshold: float = 0.2) -> Dict[str, Any]:
        """
        Analyze spending data for seasonality patterns using ACF.

        Args:
            customer_df: DataFrame with 'date' and 'amount' columns
            min_acf_threshold: Minimum ACF value to consider as "seasonal" (0.0-1.0)

        Returns:
            Dict with:
            - has_seasonality: Boolean
            - detected_periods: List of detected period dicts
            - confidence: Mean confidence of detected periods
            - explanation: Human-readable summary
            - acf_values: First 31 days of ACF (for visualization)
        """
        if acf is None:
            logger.warning("statsmodels not installed; using fallback seasonality detection")
            return SeasonalityDetector._fallback_detection(customer_df)

        # Need at least 8 weeks (56 days) for reliable weekly seasonality
        if len(customer_df) < 56:
            return {
                "has_seasonality": False,
                "detected_periods": [],
                "confidence": 0.0,
                "explanation": "Insufficient data (need 8+ weeks for seasonality detection)",
                "acf_values": []
            }

        # Aggregate by day
        try:
            daily_spending = customer_df.groupby(customer_df["date"].dt.date).agg(
                {"amount": "sum"}
            ).reset_index()
            daily_spending.columns = ["date", "amount"]
            daily_spending["date"] = pd.to_datetime(daily_spending["date"])
        except Exception as e:
            logger.error(f"Error aggregating daily spending: {e}")
            return SeasonalityDetector._fallback_detection(customer_df)

        spending_values = daily_spending["amount"].values

        # Handle zero/NaN values
        if np.isnan(spending_values).any() or len(spending_values) == 0:
            return {
                "has_seasonality": False,
                "detected_periods": [],
                "confidence": 0.0,
                "explanation": "Invalid spending data",
                "acf_values": []
            }

        try:
            # Calculate ACF (Auto-Correlation Function)
            # Max lag = min(180 days, len(data)-1) to find quarters, months, weeks
            max_lag = min(180, len(spending_values) - 1)
            acf_values = acf(spending_values, nlags=max_lag, fft=True)
        except Exception as e:
            logger.warning(f"ACF calculation failed: {e}")
            return SeasonalityDetector._fallback_detection(customer_df)

        # Find significant peaks (lags where ACF > threshold)
        candidates = SeasonalityDetector._find_acf_peaks(acf_values, min_acf_threshold)

        # Classify detected periods
        detected_periods = SeasonalityDetector._classify_periods(candidates)

        has_seasonality = len(detected_periods) > 0
        confidence = float(np.mean([p["confidence"] for p in detected_periods])) if detected_periods else 0.0

        explanation = SeasonalityDetector._explain_seasonality(detected_periods)

        # Return first 31 days of ACF for visualization
        acf_plot = acf_values[:31].tolist() if len(acf_values) >= 31 else acf_values.tolist()

        return {
            "has_seasonality": has_seasonality,
            "detected_periods": detected_periods,
            "confidence": confidence,
            "explanation": explanation,
            "acf_values": acf_plot,
            "acf_threshold": min_acf_threshold,
            "data_points": len(spending_values)
        }

    @staticmethod
    def _find_acf_peaks(acf_values: np.ndarray, threshold: float) -> List[tuple]:
        """Find peaks in ACF above threshold."""
        candidates = []

        for lag in range(7, len(acf_values)):  # Start at 7 days (weekly)
            if acf_values[lag] > threshold:
                # Check if this is a local maximum
                is_local_max = True

                if lag > 0 and acf_values[lag] < acf_values[lag - 1]:
                    is_local_max = False

                if lag < len(acf_values) - 1 and acf_values[lag] < acf_values[lag + 1]:
                    is_local_max = False

                if is_local_max:
                    candidates.append((lag, acf_values[lag]))

        return candidates

    @staticmethod
    def _classify_periods(candidates: List[tuple]) -> List[Dict[str, Any]]:
        """Classify ACF peaks into business periods."""
        periods = []

        for lag, acf_val in candidates:
            # Check each period definition
            for period_name, period_def in SeasonalityDetector.PERIOD_DEFINITIONS.items():
                if period_def["min"] <= lag <= period_def["max"]:
                    periods.append({
                        "period": period_name,
                        "lag_days": int(lag),
                        "confidence": float(acf_val),
                        "interpretation": SeasonalityDetector._get_period_interpretation(period_name, lag),
                        "expected_days": period_def["expected"]
                    })
                    break  # Don't match multiple periods for same lag

        return periods

    @staticmethod
    def _get_period_interpretation(period: str, lag: int) -> str:
        """Get business interpretation of detected period."""
        interpretations = {
            "WEEKLY": f"Spending pattern repeats every {lag} days. Common: payday cycles (weekly), day-of-week effects (e.g., Friday splurges, Monday restraint)",
            "BIWEEKLY": f"Spending pattern repeats every {lag} days. Common: bi-weekly paycheck cycles",
            "MONTHLY": f"Spending pattern repeats every {lag} days. Common: monthly salary, bill payments, subscription renewals",
            "QUARTERLY": f"Spending pattern repeats quarterly ({lag} days). Common: seasonal spending (tax time, insurance premiums)",
            "YEARLY": f"Spending pattern repeats annually ({lag} days). Common: holidays, vacations, annual subscriptions"
        }

        return interpretations.get(period, f"Seasonal pattern detected every {lag} days")

    @staticmethod
    def _explain_seasonality(detected_periods: List[Dict[str, Any]]) -> str:
        """Create human-readable explanation."""
        if not detected_periods:
            return "No seasonality detected in spending data"

        period_list = [p["period"] for p in detected_periods]
        strength = "strong" if any(p["confidence"] > 0.5 for p in detected_periods) else "weak"

        explanation = (
            f"Detected {strength} seasonality patterns: {', '.join(period_list)}. "
            f"Spending repeats in {', '.join([p.lower() for p in period_list])} cycles. "
            f"This can help with forecasting: model can expect regular ups/downs."
        )

        return explanation

    @staticmethod
    def _fallback_detection(customer_df: pd.DataFrame) -> Dict[str, Any]:
        """Fallback when statsmodels is unavailable (simple heuristic)."""
        if len(customer_df) < 56:
            return {
                "has_seasonality": False,
                "detected_periods": [],
                "confidence": 0.0,
                "explanation": "Insufficient data",
                "acf_values": []
            }

        # Simple heuristic: check spending variance by day-of-week
        customer_df_copy = customer_df.copy()
        customer_df_copy["day_of_week"] = customer_df_copy["date"].dt.day_name()

        dow_spending = customer_df_copy.groupby("day_of_week")["amount"].agg(["mean", "std"])

        # If std is high relative to mean, there's weekly seasonality
        overall_std = customer_df_copy["amount"].std()
        dow_std = dow_spending["std"].mean()

        if dow_std > overall_std * 0.3:  # Heuristic threshold
            periods = [{
                "period": "WEEKLY",
                "lag_days": 7,
                "confidence": 0.5,
                "interpretation": "Detected weekly spending pattern (payday, day-of-week effects)",
                "expected_days": 7
            }]
        else:
            periods = []

        return {
            "has_seasonality": len(periods) > 0,
            "detected_periods": periods,
            "confidence": 0.5 if len(periods) > 0 else 0.0,
            "explanation": "Fallback detection: weak weekly seasonality detected" if periods else "No seasonality detected",
            "acf_values": [],
            "method": "heuristic"
        }

    @staticmethod
    def get_prophet_seasonality_config(seasonality_detection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert seasonality detection results to Prophet configuration.

        Returns dict suitable for Prophet(**config)
        """
        detected = seasonality_detection.get("detected_periods", [])
        period_names = [p["period"] for p in detected]

        return {
            "yearly_seasonality": "YEARLY" in period_names,
            "weekly_seasonality": "WEEKLY" in period_names or "BIWEEKLY" in period_names,
            "daily_seasonality": False,
            "seasonality_mode": "additive",  # Additive for spending
            "seasonality_prior_scale": 10.0 if seasonality_detection.get("confidence", 0) > 0.3 else 5.0,
            "interval_width": 0.95
        }
