# backend/app/ml/reactive_forecaster.py
"""
Reactive forecasting using Exponential Smoothing (Holt-Winters).
More responsive to volatility than Prophet for intermittent spending data.
"""

import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ReactiveForecaster:
    """Exponential Smoothing forecast (more reactive than Prophet)."""

    def __init__(self, trend: str = "add", seasonal: str = "add", seasonal_periods: int = 7):
        """
        Initialize Reactive Forecaster.

        Args:
            trend: "add" (additive), "mul" (multiplicative), or None
            seasonal: "add", "mul", or None
            seasonal_periods: 7 (weekly), 30 (monthly), 365 (yearly)
        """
        self.trend = trend
        self.seasonal = seasonal
        self.seasonal_periods = seasonal_periods
        self.model = None
        self.fitted_model = None

    def fit_and_forecast(
        self,
        spending_series: pd.Series,
        periods_ahead: int = 90,
        alpha: float = 0.3,  # Level smoothing (0.1-0.5)
        beta: float = 0.1,   # Trend smoothing (0.01-0.2)
        gamma: float = 0.1   # Seasonal smoothing (0.01-0.2)
    ) -> Dict[str, Any]:
        """
        Fit Holt-Winters and return forecast with bounds.

        Args:
            spending_series: Daily spending amounts (pandas Series with DatetimeIndex)
            periods_ahead: Days to forecast (default: 90 days)
            alpha: Higher = more reactive to recent changes (default: 0.3)
            beta: Trend sensitivity (default: 0.1)
            gamma: Seasonal sensitivity (default: 0.1)

        Returns:
            Dict with:
            - point_forecast: Forecasted values (array)
            - lower_bounds: 95% CI lower (non-negative, array)
            - upper_bounds: 95% CI upper (array)
            - forecast_dates: Date range (pandas DatetimeIndex)
            - model_type: "exponential_smoothing"
            - parameters: Configuration used
        """
        # Ensure minimum data
        if len(spending_series) < self.seasonal_periods * 2:
            logger.warning(f"Insufficient data: {len(spending_series)} < {self.seasonal_periods * 2}")
            return self._minimal_forecast(spending_series, periods_ahead)

        # Handle zeros in spending (add small epsilon for log transformation)
        spending_adjusted = spending_series.copy()
        if (spending_adjusted == 0).any():
            # Replace zeros with 0.1 (minimum transaction value in local currency)
            spending_adjusted = spending_adjusted.replace(0, 0.1)

        try:
            # Fit Holt-Winters model
            self.model = ExponentialSmoothing(
                spending_adjusted,
                trend=self.trend,
                seasonal=self.seasonal,
                seasonal_periods=self.seasonal_periods,
                initialization_method="estimated"
            )

            # Fit with optimized parameters
            self.fitted_model = self.model.fit(
                optimized=True,
                use_boxcox=False,  # Don't use Box-Cox; we'll use constrained bounds instead
                smoothing_level=alpha,
                smoothing_trend=beta,
                smoothing_seasonal=gamma
            )

            # Get forecast with confidence intervals
            forecast_result = self.fitted_model.get_forecast(steps=periods_ahead)
            forecast_df = forecast_result.summary_frame(alpha=0.05)  # 95% CI (alpha=0.05 → 95% CI)

            # Extract values
            point_forecast = forecast_df["mean"].values
            lower_bounds_raw = forecast_df["mean_ci_lower"].values
            upper_bounds = forecast_df["mean_ci_upper"].values

            # KEY FIX: Constrain lower bounds to non-negative (physical constraint)
            lower_bounds = np.maximum(lower_bounds_raw, 0.0)

            # Generate forecast dates starting tomorrow
            last_date = spending_series.index[-1]
            forecast_dates = pd.date_range(
                start=last_date + timedelta(days=1),
                periods=periods_ahead,
                freq='D'
            )

            logger.info(f"Exponential Smoothing: Forecast {periods_ahead} days ahead")

            return {
                "point_forecast": point_forecast,
                "lower_bounds": lower_bounds,
                "upper_bounds": upper_bounds,
                "forecast_dates": forecast_dates,
                "model_type": "exponential_smoothing",
                "parameters": {
                    "alpha": alpha,
                    "beta": beta,
                    "gamma": gamma,
                    "trend": self.trend,
                    "seasonal": self.seasonal,
                    "seasonal_periods": self.seasonal_periods
                },
                "data_points_used": len(spending_series)
            }

        except Exception as e:
            logger.error(f"Holt-Winters fitting error: {e}")
            return self._minimal_forecast(spending_series, periods_ahead)

    def _minimal_forecast(self, spending_series: pd.Series, periods_ahead: int) -> Dict[str, Any]:
        """
        Fallback forecast: simple mean-based prediction when model fitting fails.

        Returns dict with same structure as fit_and_forecast.
        """
        spending_valid = spending_series[spending_series > 0]

        if len(spending_valid) == 0:
            mean_spending = spending_series.mean()
        else:
            mean_spending = spending_valid.mean()

        mean_spending = max(mean_spending, 1.0)  # Ensure positive

        # Simple bounds: ±50% of mean
        lower_bounds = np.full(periods_ahead, mean_spending * 0.5)
        upper_bounds = np.full(periods_ahead, mean_spending * 1.5)

        last_date = spending_series.index[-1] if hasattr(spending_series, 'index') else datetime.now()
        forecast_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=periods_ahead,
            freq='D'
        )

        return {
            "point_forecast": np.full(periods_ahead, mean_spending),
            "lower_bounds": lower_bounds,
            "upper_bounds": upper_bounds,
            "forecast_dates": forecast_dates,
            "model_type": "fallback_mean",
            "parameters": {},
            "data_points_used": len(spending_series)
        }

    def get_forecast_stats(self) -> Dict[str, Any]:
        """Get statistics about the fitted model."""
        if self.fitted_model is None:
            return {"model_fit": False}

        return {
            "model_fit": True,
            "aic": float(self.fitted_model.aic) if hasattr(self.fitted_model, 'aic') else None,
            "bic": float(self.fitted_model.bic) if hasattr(self.fitted_model, 'bic') else None,
            "smoothing_level": float(self.fitted_model.smoothing_level) if hasattr(self.fitted_model, 'smoothing_level') else None,
            "smoothing_trend": float(self.fitted_model.smoothing_trend) if hasattr(self.fitted_model, 'smoothing_trend') else None,
            "smoothing_seasonal": float(self.fitted_model.smoothing_seasonal) if hasattr(self.fitted_model, 'smoothing_seasonal') else None
        }
