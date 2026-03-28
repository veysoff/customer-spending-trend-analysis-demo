import pandas as pd
import numpy as np
from prophet import Prophet
import logging

logger = logging.getLogger(__name__)


class TrendDetector:
    """Detect spending trends using Prophet for banking transaction data.

    Design decisions:

    1. AGGREGATION: Weekly sums for Prophet training.
       - Individual transactions: wrong unit (many per day, varying amounts)
       - Daily zero-filled: high sparsity (~38%) creates dominant weekly noise
         that completely hides the actual spending trend
       - Weekly sums: correct unit — smooths intra-week variation, reveals
         the true month-over-month spending direction
       Week buckets are ISO weeks (Monday start).

    2. DISPLAY: Daily actual values (individual transaction sums per day)
       are shown as scatter points. The forecast line is the weekly Prophet
       trend, resampled to daily for smooth rendering.

    3. SEASONALITY: With weekly aggregation, yearly seasonality is the
       meaningful signal (December +15%, August -20%).  Weekly seasonality
       is disabled (aggregation already removes it).  Use conservative
       prior so TREND dominates.

    4. CONFIDENCE INTERVAL: 80% — practical, avoids overwhelming the chart.

    5. FORECAST HORIZON: 12 weeks (~84 days).
    """

    def __init__(self, yearly_seasonality: bool = True, weekly_seasonality: bool = False,
                 interval_width: float = 0.80, growth: str = "linear"):
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.interval_width = interval_width
        self.growth = growth
        self.MIN_WEEKS = 8           # need at least 8 data points for Prophet
        self.MIN_TRANSACTIONS = 20
        self.MIN_WEEKS_YEARLY = 78   # ~1.5 years minimum for reliable yearly seasonality (2 cycles)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_weekly(customer_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate transactions to ISO-week sums.

        Returns DataFrame with columns ['ds', 'y']:
          - ds: Monday of each ISO week (no gaps; zero for weeks with no spending)
          - y: total spending that week
        """
        df = customer_df.copy()
        df["date"] = pd.to_datetime(df["date"])

        # Floor to Monday of ISO week
        df["week"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")
        df["week"] = df["week"].dt.normalize()  # strip time component

        weekly = (
            df.groupby("week")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"week": "ds", "amount": "y"})
        )
        weekly["ds"] = pd.to_datetime(weekly["ds"])

        # Fill missing weeks with 0 (no spending that week = 0 demand)
        week_range = pd.date_range(weekly["ds"].min(), weekly["ds"].max(), freq="W-MON")
        weekly = weekly.set_index("ds").reindex(week_range, fill_value=0.0).reset_index()
        weekly.columns = ["ds", "y"]

        return weekly.sort_values("ds").reset_index(drop=True)

    @staticmethod
    def _to_daily_actuals(customer_df: pd.DataFrame) -> dict:
        """Return dict of date -> daily spending sum (for display only).

        Only dates that have real transactions are included.
        """
        df = customer_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        daily = (
            df.groupby(df["date"].dt.date)["amount"]
            .sum()
        )
        return {pd.Timestamp(d): float(v) for d, v in daily.items()}

    @staticmethod
    def _compute_cv(values: np.ndarray) -> float:
        """Coefficient of variation on non-zero values only."""
        nonzero = values[values > 0]
        if len(nonzero) == 0:
            return 0.0
        mean_val = float(np.mean(nonzero))
        if mean_val <= 0:
            return 0.0
        return float(np.std(nonzero) / mean_val)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def detect_trend(self, customer_df: pd.DataFrame, periods_ahead: int = 12) -> dict:
        """Fit Prophet on weekly sums and return daily-resampled forecast + metrics.

        periods_ahead: number of weeks to forecast (default 12 = ~3 months)
        """
        if len(customer_df) < self.MIN_TRANSACTIONS:
            logger.warning(f"Too few transactions: {len(customer_df)}")
            return self._empty_forecast()

        date_min = pd.to_datetime(customer_df["date"]).min()
        date_max = pd.to_datetime(customer_df["date"]).max()
        days_span = int((date_max - date_min).days)
        weeks_span = days_span // 7

        if weeks_span < self.MIN_WEEKS:
            logger.warning(f"Data span too short: {weeks_span} weeks")
            return self._empty_forecast()

        # Weekly aggregation — correct unit for trend detection
        weekly = self._to_weekly(customer_df)

        # Daily actuals for display (scatter dots)
        daily_actuals = self._to_daily_actuals(customer_df)

        # Characterise pattern (for metadata)
        cv = self._compute_cv(weekly["y"].values)
        zero_weeks = int(np.sum(weekly["y"] == 0))
        sparsity = float(zero_weeks / len(weekly))

        # --- Seasonality flags ------------------------------------------------
        use_yearly = bool(self.yearly_seasonality and weeks_span >= self.MIN_WEEKS_YEARLY)
        # Weekly seasonality is intentionally disabled: we are already aggregating
        # by week, so there is no sub-weekly variation left to model.
        use_weekly = False

        # --- Prophet hyperparameters ------------------------------------------
        # Changepoint flexibility:
        # - Short data (<26w): high flexibility (0.3) to catch any trend
        # - Medium data (26-78w): moderate (0.15) — typical 12-month customer
        # - Long data (>=78w): conservative (0.05) to avoid overfitting
        if weeks_span < 26:
            cp_scale = 0.3
        elif weeks_span < 78:
            cp_scale = 0.15
        else:
            cp_scale = 0.05

        # Seasonality prior: keep it small so TREND is dominant in the visual
        sp_scale = 5.0 if use_yearly else 1.0

        try:
            model = Prophet(
                yearly_seasonality=use_yearly,
                weekly_seasonality=use_weekly,
                daily_seasonality=False,
                interval_width=self.interval_width,
                growth=self.growth,
                seasonality_mode="additive",
                seasonality_prior_scale=sp_scale,
                changepoint_prior_scale=cp_scale,
            )
            model.fit(weekly)

            # Forecast from last data point to today + periods_ahead weeks.
            # For dormant customers whose data ended months ago, this extends
            # the forecast all the way through the gap to the current date.
            today = pd.Timestamp.now().normalize()
            last_data_week = weekly["ds"].iloc[-1]
            weeks_to_today = max(0, int((today - last_data_week).days // 7))
            total_periods = weeks_to_today + periods_ahead

            future = model.make_future_dataframe(periods=total_periods, freq="W")
            forecast = model.predict(future)

            # --- Trend slope (forward-looking, per month) ---------------------
            hist_len = len(weekly)
            trend_slope_per_day = 0.0
            trend_slope_per_month = 0.0

            # Use future portion of forecast for forward-looking slope
            future_trend = forecast.iloc[hist_len:]["trend"].values
            if len(future_trend) > 1:
                x = np.arange(len(future_trend), dtype=float)
                # slope_per_week = change in weekly spending (AED) per week
                slope_per_week = float(np.polyfit(x, future_trend, 1)[0])
                trend_slope_per_day = slope_per_week / 7.0
                # Monthly spending change = weekly change * 4.33 weeks/month
                trend_slope_per_month = slope_per_week * 4.33
            elif hist_len >= 4:
                # Fallback: use last 4 weeks of history
                hist_trend = forecast.iloc[max(0, hist_len - 4):hist_len]["trend"].values
                if len(hist_trend) > 1:
                    x = np.arange(len(hist_trend), dtype=float)
                    slope_per_week = float(np.polyfit(x, hist_trend, 1)[0])
                    trend_slope_per_day = slope_per_week / 7.0
                    trend_slope_per_month = slope_per_week * 4.33

            # --- Seasonality amplitude ----------------------------------------
            seasonality_amplitude = 0.0
            # Prophet stores yearly seasonality in 'yearly' column if enabled
            seasonal_col = "yearly" if use_yearly and "yearly" in forecast.columns else None
            if seasonal_col:
                hist_seasonal = forecast[seasonal_col].iloc[:hist_len]
                hist_mean = float(weekly["y"].mean())
                if float(hist_seasonal.std()) > 0 and hist_mean > 0:
                    seasonality_amplitude = float(hist_seasonal.std() / hist_mean)

            has_seasonality = bool(seasonality_amplitude > 0.05)

            return {
                "forecast_data": self._format_forecast(weekly, forecast, daily_actuals),
                "trend_slope_per_day": float(trend_slope_per_day),
                "trend_slope_per_month": float(trend_slope_per_month),
                "trend_slope": float(trend_slope_per_month),  # backward compat
                "trend_slope_unit": "AED/month",
                "seasonality_amplitude": float(seasonality_amplitude),
                "has_seasonality": has_seasonality,
                "model": model,
                "data_span_days": days_span,
                "metadata": {
                    "yearly_seasonality_enabled": use_yearly,
                    "weekly_seasonality_enabled": use_weekly,
                    "changepoint_prior_scale": float(cp_scale),
                    "seasonality_prior_scale": float(sp_scale),
                    "aggregation_level": "weekly",
                    "weeks_in_history": hist_len,
                    "weeks_forecast": periods_ahead,
                    "coefficient_of_variation": float(cv),
                    "sparsity_ratio": float(sparsity),
                    "zero_weeks": zero_weeks,
                    "is_intermittent_demand": bool(cv > 0.5 or sparsity > 0.3),
                },
            }

        except Exception as e:
            logger.error(f"Prophet fitting error: {e}")
            return self._empty_forecast()

    # ------------------------------------------------------------------
    # Format output
    # ------------------------------------------------------------------

    @staticmethod
    def _format_forecast(weekly: pd.DataFrame, forecast: pd.DataFrame,
                         daily_actuals: dict) -> list:
        """Return one row per week so that actuals and forecast are on the same scale.

        Both actual and forecast represent AED spent in that ISO week (Monday–Sunday).
        This is the only correct comparison: Prophet was trained on weekly sums,
        so its output is weekly sums — the actuals must also be weekly sums.

        Returns list of dicts with keys:
          date        - Monday of the ISO week (YYYY-MM-DD)
          actual      - real weekly spending sum (None for future weeks)
          forecast    - Prophet yhat for that week
          lower_bound - yhat_lower clipped to 0
          upper_bound - yhat_upper
        """
        hist_len = len(weekly)

        # Build actual weekly sums from daily_actuals dict
        # Group daily actuals by their ISO week Monday
        weekly_actuals: dict = {}
        for day_ts, amount in daily_actuals.items():
            monday = day_ts - pd.Timedelta(days=day_ts.weekday())
            monday = monday.normalize()
            weekly_actuals[monday] = weekly_actuals.get(monday, 0.0) + amount

        # Last week in history
        history_end = weekly["ds"].iloc[hist_len - 1]

        data = []
        for _, row in forecast.iterrows():
            week_monday = row["ds"]
            is_history = week_monday <= history_end

            actual_val = weekly_actuals.get(week_monday, None) if is_history else None

            yhat = float(row["yhat"])
            yhat_lower = float(max(0.0, row["yhat_lower"]))
            yhat_upper = float(max(0.0, row["yhat_upper"]))

            data.append({
                "date": week_monday.strftime("%Y-%m-%d"),
                "actual": actual_val,
                "forecast": max(0.0, yhat),
                "lower_bound": yhat_lower,
                "upper_bound": yhat_upper,
            })

        return data

    # ------------------------------------------------------------------
    # Empty fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_forecast() -> dict:
        return {
            "forecast_data": [],
            "trend_slope_per_day": 0.0,
            "trend_slope_per_month": 0.0,
            "trend_slope": 0.0,
            "trend_slope_unit": "AED/month",
            "has_seasonality": False,
            "seasonality_amplitude": 0.0,
            "model": None,
            "data_span_days": 0,
            "metadata": {},
        }

    # ------------------------------------------------------------------
    # Category helper
    # ------------------------------------------------------------------

    @staticmethod
    def get_trend_category(trend_slope_per_month: float) -> str:
        """Categorize trend direction.

        slope_per_month = actual monthly spending change in AED/month
        (slope_per_week * 4.33 * 4.33).
        Thresholds: >+20 = INCREASING, <-20 = DECREASING, otherwise STABLE.
        Typical range: stable ~0, declining -20 to -500, growing +20 to +500.
        Lowered from ±100 to ±20 to reflect realistic monthly spending changes
        (average customer spends 200-400 AED/month, so ±10% = ±20-40 AED is significant).
        """
        if trend_slope_per_month > 20:
            return "INCREASING"
        if trend_slope_per_month < -20:
            return "DECREASING"
        return "STABLE"
