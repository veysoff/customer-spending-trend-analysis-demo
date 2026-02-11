import pandas as pd
import numpy as np
from prophet import Prophet
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TrendDetector:
    """Detect spending trends using Prophet with corrected algorithms."""

    def __init__(self, yearly_seasonality=True, weekly_seasonality=True,
                 interval_width=0.95, growth="linear"):
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.interval_width = interval_width  # 95% confidence interval
        self.growth = growth
        # Minimum data spans for reliable forecasting
        self.MIN_DAYS_SPAN = 60  # 2 months minimum
        self.MIN_TRANSACTIONS = 30  # 30+ transactions
        self.MIN_DAYS_YEARLY = 365  # Need 1 year for yearly seasonality
        self.MIN_DAYS_WEEKLY = 56  # Need 8+ weeks for weekly seasonality

    def detect_trend(self, customer_df: pd.DataFrame, periods_ahead: int = 90) -> dict:
        """Fit Prophet model and return forecast with corrected calculations.

        Args:
            customer_df: DataFrame with transaction data
            periods_ahead: Number of days to forecast (default: 90 days = ~3 months)

        Returns:
            Dict with forecast_data, trend_slope_per_month, trend_slope_per_day,
            seasonality_amplitude, and metadata
        """
        # FIX #2: Proper data length validation (not just transaction count)
        if len(customer_df) < self.MIN_TRANSACTIONS:
            logger.warning(f"Too few transactions: {len(customer_df)} (need {self.MIN_TRANSACTIONS}+)")
            return self._empty_forecast()

        # Calculate date span
        date_min = customer_df["date"].min()
        date_max = customer_df["date"].max()
        days_span = (date_max - date_min).days

        if days_span < self.MIN_DAYS_SPAN:
            logger.warning(f"Data span too short: {days_span} days (need {self.MIN_DAYS_SPAN}+)")
            return self._empty_forecast()

        # FIX #5 & #6: Adaptive seasonality settings based on data span
        # Determine what seasonality we can safely use
        use_yearly_seasonality = self.yearly_seasonality and (days_span >= self.MIN_DAYS_YEARLY)
        use_weekly_seasonality = self.weekly_seasonality and (days_span >= self.MIN_DAYS_WEEKLY)

        # FIX #5: Adaptive changepoint prior based on data span
        if days_span < 180:
            # Short data: more flexible
            changepoint_prior_scale = 0.05
        elif days_span < 730:
            # Medium data: balanced
            changepoint_prior_scale = 0.01
        else:
            # Long data: strict (avoid noise)
            changepoint_prior_scale = 0.001

        # FIX #6: Adaptive seasonality prior based on data span
        if days_span >= self.MIN_DAYS_YEARLY:
            seasonality_prior_scale = 10.0  # Can be aggressive with 1+ year data
        elif days_span >= self.MIN_DAYS_WEEKLY:
            seasonality_prior_scale = 5.0  # Moderate for 8+ weeks
        else:
            seasonality_prior_scale = 1.0  # Conservative for shorter spans

        # Aggregate daily spending
        daily_spending = customer_df.groupby(customer_df["date"].dt.date).agg(
            {"amount": "sum"}
        ).reset_index()
        daily_spending.columns = ["ds", "y"]
        daily_spending["ds"] = pd.to_datetime(daily_spending["ds"])

        try:
            model = Prophet(
                yearly_seasonality=use_yearly_seasonality,
                weekly_seasonality=use_weekly_seasonality,
                daily_seasonality=False,
                interval_width=self.interval_width,
                growth=self.growth,
                seasonality_mode="additive",
                seasonality_prior_scale=seasonality_prior_scale,
                changepoint_prior_scale=changepoint_prior_scale
            )
            model.fit(daily_spending)

            # Forecast ahead
            future = model.make_future_dataframe(periods=periods_ahead)
            forecast = model.predict(future)

            # FIX #1: Calculate trend slope from FUTURE forecast (not historical)
            # CORRECTED: Use forward-looking trend to show where spending is GOING
            historical_len = len(daily_spending)

            # Calculate trend slope from future portion of forecast (next 30 days)
            # This shows the direction customer spending is heading
            if historical_len + 30 < len(forecast):
                # Extract future trend portion (30 days ahead)
                future_portion = forecast.iloc[historical_len:historical_len+30]["trend"].values

                if len(future_portion) > 1:
                    # Calculate slope from future trend (shows forecast direction)
                    x_values = np.arange(len(future_portion))
                    z = np.polyfit(x_values, future_portion, 1)
                    trend_slope_per_day = float(z[0])  # AED per day (FUTURE direction)

                    # Convert to per month (30 days)
                    trend_slope_per_month = trend_slope_per_day * 30
                else:
                    trend_slope_per_day = 0.0
                    trend_slope_per_month = 0.0
            else:
                # Fallback: if not enough future data, use last 7 days of historical
                if historical_len >= 7:
                    historical_trend = forecast.iloc[max(0, historical_len-7):historical_len]["trend"].values
                    if len(historical_trend) > 1:
                        x_values = np.arange(len(historical_trend))
                        z = np.polyfit(x_values, historical_trend, 1)
                        trend_slope_per_day = float(z[0])
                        trend_slope_per_month = trend_slope_per_day * 30
                    else:
                        trend_slope_per_day = 0.0
                        trend_slope_per_month = 0.0
                else:
                    trend_slope_per_day = 0.0
                    trend_slope_per_month = 0.0

            # FIX #3: Calculate seasonality amplitude correctly (from historical data only)
            if "seasonal" in forecast.columns:
                # Use HISTORICAL seasonality only (not forecast which includes extrapolation noise)
                historical_seasonal = forecast["seasonal"].iloc[:historical_len]
                historical_mean = daily_spending["y"].mean()

                if historical_seasonal.std() > 0 and historical_mean > 0:
                    # Amplitude = standard deviation / mean (standard definition)
                    seasonality_amplitude = historical_seasonal.std() / historical_mean
                else:
                    seasonality_amplitude = 0.0
            else:
                seasonality_amplitude = 0.0

            # Determine if seasonality exists (threshold: >5%)
            has_seasonality = seasonality_amplitude > 0.05

            return {
                "forecast_data": self._format_forecast(daily_spending, forecast),
                "trend_slope_per_day": float(trend_slope_per_day),  # Per DAY (explicit unit)
                "trend_slope_per_month": float(trend_slope_per_month),  # Per MONTH (explicit unit)
                "trend_slope": float(trend_slope_per_month),  # For backward compatibility
                "trend_slope_unit": "AED/month",  # EXPLICIT UNIT
                "seasonality_amplitude": float(seasonality_amplitude),
                "has_seasonality": has_seasonality,
                "model": model,
                "data_span_days": days_span,
                "metadata": {
                    "yearly_seasonality_enabled": use_yearly_seasonality,
                    "weekly_seasonality_enabled": use_weekly_seasonality,
                    "changepoint_prior_scale": changepoint_prior_scale,
                    "seasonality_prior_scale": seasonality_prior_scale
                }
            }
        except Exception as e:
            logger.error(f"Prophet fitting error: {e}")
            return self._empty_forecast()

    @staticmethod
    def _format_forecast(actual: pd.DataFrame, forecast: pd.DataFrame) -> list:
        """Format forecast output."""
        data = []

        # Return all forecast data (historical + future forecast)
        actual_len = len(actual)
        for i in range(len(forecast)):  # Show ALL forecast rows (not limited by actual_len)
            row = forecast.iloc[i]
            if i < actual_len:
                actual_val = actual.iloc[i]["y"]
            else:
                actual_val = None

            data.append({
                "date": row["ds"].strftime("%Y-%m-%d"),
                "actual": float(actual_val) if actual_val is not None else None,
                "forecast": float(row["yhat"]),
                "lower_bound": float(row["yhat_lower"]),
                "upper_bound": float(row["yhat_upper"])
            })

        return data

    @staticmethod
    def _empty_forecast() -> dict:
        """Return empty forecast structure."""
        return {
            "forecast_data": [],
            "trend_slope_per_day": 0.0,
            "trend_slope_per_month": 0.0,
            "trend_slope": 0.0,  # Backward compatibility
            "trend_slope_unit": "AED/month",
            "has_seasonality": False,
            "seasonality_amplitude": 0.0,
            "model": None,
            "data_span_days": 0,
            "metadata": {}
        }

    @staticmethod
    def get_trend_category(trend_slope_per_month: float) -> str:
        """Categorize trend based on monthly slope.

        Args:
            trend_slope_per_month: Slope in AED/month

        Returns:
            Category: INCREASING, STABLE, or DECREASING
        """
        # Thresholds in AED/month (adjusted for realistic values)
        if trend_slope_per_month > 50:
            return "INCREASING"
        elif trend_slope_per_month < -50:
            return "DECREASING"
        else:
            return "STABLE"
