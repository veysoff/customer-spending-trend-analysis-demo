import pandas as pd
import numpy as np
from prophet import Prophet
import logging

logger = logging.getLogger(__name__)

class TrendDetector:
    """Detect spending trends using Prophet."""

    def __init__(self, yearly_seasonality=True, weekly_seasonality=True,
                 interval_width=0.80, growth="linear"):
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.interval_width = interval_width
        self.growth = growth

    def detect_trend(self, customer_df: pd.DataFrame, periods_ahead: int = 3) -> dict:
        """Fit Prophet model and return forecast."""
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
                changepoint_prior_scale=0.05
            )
            model.fit(daily_spending)

            # Forecast ahead
            future = model.make_future_dataframe(periods=periods_ahead)
            forecast = model.predict(future)

            # Extract trend component
            trend_component = forecast["trend"].values
            trend_slope = np.polyfit(np.arange(len(trend_component)), trend_component, 1)[0]

            return {
                "forecast_data": self._format_forecast(daily_spending, forecast),
                "trend_slope": float(trend_slope),
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
