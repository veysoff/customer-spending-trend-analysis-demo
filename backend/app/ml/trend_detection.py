import pandas as pd
import numpy as np
from prophet import Prophet
import logging

logger = logging.getLogger(__name__)

class TrendDetector:
    """Detect spending trends using Prophet."""

    def __init__(self, yearly_seasonality=True, weekly_seasonality=True,
                 interval_width=0.95, growth="linear"):
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.interval_width = interval_width  # Wider confidence interval (95% vs 80%)
        self.growth = growth

    def detect_trend(self, customer_df: pd.DataFrame, periods_ahead: int = 90) -> dict:
        """Fit Prophet model and return forecast.

        Args:
            customer_df: DataFrame with transaction data
            periods_ahead: Number of days to forecast (default: 90 days = ~3 months)
        """
        if len(customer_df) < 7:
            return self._empty_forecast()

        # Aggregate daily spending
        daily_spending = customer_df.groupby(customer_df["date"].dt.date).agg(
            {"amount": "sum"}
        ).reset_index()
        daily_spending.columns = ["ds", "y"]
        daily_spending["ds"] = pd.to_datetime(daily_spending["ds"])

        try:
            model = Prophet(
                yearly_seasonality=self.yearly_seasonality,
                weekly_seasonality=self.weekly_seasonality,
                daily_seasonality=False,
                interval_width=self.interval_width,
                growth=self.growth,
                seasonality_mode="additive",  # Better for spending patterns
                seasonality_prior_scale=10.0,  # Strengthen seasonality
                changepoint_prior_scale=0.001  # Reduce sensitivity to noise (was 0.05)
            )
            model.fit(daily_spending, verbose=False)

            # Forecast ahead
            future = model.make_future_dataframe(periods=periods_ahead)
            forecast = model.predict(future)

            # Extract trend slope from FUTURE portion only (not historical)
            historical_len = len(daily_spending)
            future_trend = forecast.iloc[historical_len:]["trend"].values

            if len(future_trend) > 1:
                # Calculate slope per day for the future period
                future_dates = np.arange(len(future_trend))
                trend_slope = np.polyfit(future_dates, future_trend, 1)[0]
            else:
                trend_slope = 0.0

            # Calculate actual seasonality amplitude from forecast
            seasonality_component = forecast["seasonal"].values
            if len(seasonality_component) > 0 and forecast["yhat"].mean() > 0:
                seasonality_amplitude = (seasonality_component.max() - seasonality_component.min()) / forecast["yhat"].mean()
            else:
                seasonality_amplitude = 0.15

            return {
                "forecast_data": self._format_forecast(daily_spending, forecast),
                "trend_slope": float(trend_slope),
                "seasonality_amplitude": float(seasonality_amplitude),
                "has_seasonality": True,
                "model": model
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
            "trend_slope": 0.0,
            "has_seasonality": False,
            "model": None
        }

    @staticmethod
    def get_trend_category(trend_slope: float) -> str:
        """Categorize trend based on slope."""
        if trend_slope > 50:
            return "INCREASING"
        elif trend_slope < -50:
            return "DECREASING"
        else:
            return "STABLE"
