from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import logging
from pathlib import Path

from . import config
from .models import (
    GenerateDataRequest, GenerateDataResponse,
    CustomerProfileResponse, TrendResponse, AnomalyResponse, AtRiskResponse
)
from .ml.data_generator import SyntheticDataGenerator
from .ml.feature_engineering import FeatureEngineer
from .ml.trend_detection import TrendDetector
from .ml.anomaly_detection import AnomalyDetector
from .ml.explainability import ExplainabilityEngine

# Configure logging
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Customer Spending Trend Analysis API",
    description="ML-powered banking analytics PoC",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
_data: pd.DataFrame = None
_anomaly_detector: AnomalyDetector = None


def load_or_generate_data() -> pd.DataFrame:
    """Load existing data or generate new."""
    global _data, _anomaly_detector

    data_path = config.DATA_DIR / "transactions.csv"

    if data_path.exists():
        logger.info("Loading existing transaction data")
        _data = pd.read_csv(data_path)
        _data["date"] = pd.to_datetime(_data["date"])
        _train_anomaly_detector()
        return _data

    logger.info("No data found. Generating synthetic data...")
    return _generate_and_save_data()


def _generate_and_save_data() -> pd.DataFrame:
    """Generate synthetic data and save to CSV."""
    global _data, _anomaly_detector

    generator = SyntheticDataGenerator(
        n_customers=config.N_CUSTOMERS,
        n_months=config.N_MONTHS
    )

    logger.info(f"Generating {config.N_CUSTOMERS} customers × {config.N_MONTHS} months")
    _data = generator.generate()

    # Save to CSV
    data_path = config.DATA_DIR / "transactions.csv"
    _data.to_csv(data_path, index=False)
    logger.info(f"Data saved to {data_path}")

    _train_anomaly_detector()
    return _data


def _train_anomaly_detector():
    """Train Isolation Forest on all customer data."""
    global _data, _anomaly_detector

    logger.info("Training anomaly detector")
    _anomaly_detector = AnomalyDetector(
        contamination=config.ISOLATION_FOREST_CONTAMINATION,
        n_estimators=config.ISOLATION_FOREST_N_ESTIMATORS
    )

    # Collect features for all customers
    all_features = []
    for customer_id in _data["customer_id"].unique()[:100]:  # Sample for speed
        customer_df = _data[_data["customer_id"] == customer_id].sort_values("date")
        features = AnomalyDetector.get_anomaly_features(customer_df)
        all_features.append(features[0])

    if all_features:
        features_array = pd.DataFrame(all_features).fillna(0).values
        _anomaly_detector.fit(features_array)
        logger.info(f"Anomaly detector trained on {len(all_features)} customers")


@app.on_event("startup")
async def startup():
    """Load or generate data on startup."""
    load_or_generate_data()
    logger.info("API ready")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "data_loaded": _data is not None}


@app.post("/api/data/generate", response_model=GenerateDataResponse)
async def generate_data(request: GenerateDataRequest) -> GenerateDataResponse:
    """Generate synthetic transaction data."""
    global _data, _anomaly_detector

    logger.info(f"Generating {request.n_customers} customers for {request.months} months")

    generator = SyntheticDataGenerator(
        n_customers=request.n_customers,
        n_months=request.months
    )

    _data = generator.generate()

    # Save to CSV
    data_path = config.DATA_DIR / "transactions.csv"
    _data.to_csv(data_path, index=False)

    # Train detector
    _train_anomaly_detector()

    # Calculate distribution
    distribution = {}
    for pattern in ["normal", "silent_churn", "lifestyle_shift"]:
        count = len(_data[_data.get("pattern") == pattern])
        distribution[pattern] = count / len(_data) if len(_data) > 0 else 0

    return GenerateDataResponse(
        status="Generated",
        n_records=len(_data),
        distribution=distribution
    )


@app.get("/api/customers/{customer_id}", response_model=CustomerProfileResponse)
async def get_customer_profile(customer_id: str) -> CustomerProfileResponse:
    """Get customer profile with risk assessment."""
    if _data is None:
        raise HTTPException(status_code=500, detail="Data not loaded")

    customer_df = _data[_data["customer_id"] == customer_id].sort_values("date")

    if len(customer_df) == 0:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    # Extract features
    feature_engineer = FeatureEngineer()
    features = feature_engineer.engineer_features(customer_df)

    # Detect trend
    trend_detector = TrendDetector(
        yearly_seasonality=config.PROPHET_YEARLY_SEASONALITY,
        weekly_seasonality=config.PROPHET_WEEKLY_SEASONALITY
    )
    trend_result = trend_detector.detect_trend(customer_df)
    trend_slope = trend_result["trend_slope"]
    trend_category = TrendDetector.get_trend_category(trend_slope)

    # Calculate churn risk
    churn_risk = _calculate_churn_risk(trend_slope, features)

    # Detect behavior change
    behavior_change = _detect_behavior_change(customer_df)

    return CustomerProfileResponse(
        customer_id=customer_id,
        total_transactions=len(customer_df),
        date_range=[
            customer_df["date"].min().strftime("%Y-%m-%d"),
            customer_df["date"].max().strftime("%Y-%m-%d")
        ],
        current_monthly_spending=features["current_monthly_spending"],
        spending_trend=trend_category,
        churn_risk=churn_risk,
        behavior_change=behavior_change,
        risk_category=_get_risk_category(churn_risk)
    )


@app.get("/api/customers/{customer_id}/trends", response_model=TrendResponse)
async def get_customer_trends(customer_id: str) -> TrendResponse:
    """Get spending trend forecast."""
    if _data is None:
        raise HTTPException(status_code=500, detail="Data not loaded")

    customer_df = _data[_data["customer_id"] == customer_id].sort_values("date")

    if len(customer_df) == 0:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    trend_detector = TrendDetector()
    trend_result = trend_detector.detect_trend(customer_df, periods_ahead=3)

    return TrendResponse(
        customer_id=customer_id,
        trend_data=[
            {
                "date": item["date"],
                "actual": item["actual"],
                "forecast": item["forecast"],
                "lower_bound": item["lower_bound"],
                "upper_bound": item["upper_bound"]
            }
            for item in trend_result["forecast_data"]
        ],
        trend_slope=trend_result["trend_slope"],
        seasonality_pattern="yearly_and_weekly",
        seasonality_amplitude=0.15
    )


@app.get("/api/customers/{customer_id}/anomalies", response_model=AnomalyResponse)
async def get_customer_anomalies(customer_id: str) -> AnomalyResponse:
    """Get detected anomalies with explanations."""
    if _data is None or _anomaly_detector is None:
        raise HTTPException(status_code=500, detail="Data or model not loaded")

    customer_df = _data[_data["customer_id"] == customer_id].sort_values("date")

    if len(customer_df) == 0:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    # Detect anomalies
    feature_vector = AnomalyDetector.get_anomaly_features(customer_df)
    anomalies = _anomaly_detector.detect(customer_df, feature_vector)

    # Convert to response format
    anomaly_details = []
    for anomaly in anomalies[:5]:  # Return top 5
        # Get transaction details if available
        anomaly_idx = anomaly.get("index", 0)
        if anomaly_idx < len(customer_df):
            trans = customer_df.iloc[anomaly_idx]
            transaction_dict = {
                "transaction_id": str(anomaly_idx),
                "customer_id": trans["customer_id"],
                "date": trans["date"].strftime("%Y-%m-%d"),
                "amount": float(trans["amount"]),
                "mcc": trans["mcc"],
                "mcc_category": trans["mcc_category"],
                "channel": trans["channel"],
                "merchant": trans["merchant"],
                "country": trans["country"]
            }
        else:
            # Fallback with placeholder data
            transaction_dict = {
                "transaction_id": "N/A",
                "customer_id": customer_id,
                "date": anomaly["date"],
                "amount": 0.0,
                "mcc": "0000",
                "mcc_category": "UNKNOWN",
                "channel": "UNKNOWN",
                "merchant": "Unknown",
                "country": "GB"
            }

        explanation = ExplainabilityEngine.explain_anomaly(
            anomaly["type"],
            anomaly["score"],
            transaction_dict,
            feature_vector
        )

        # Ensure explanation has required fields
        if "prediction" not in explanation:
            explanation["prediction"] = anomaly["type"]

        anomaly_details.append({
            "date": anomaly["date"],
            "anomaly_type": anomaly["type"],
            "anomaly_score": anomaly["score"],
            "transaction": transaction_dict,
            "explanation": explanation
        })

    return AnomalyResponse(
        customer_id=customer_id,
        anomalies=anomaly_details
    )


@app.get("/api/customers/risk/high", response_model=AtRiskResponse)
async def get_high_risk_customers() -> AtRiskResponse:
    """Get list of high-risk customers."""
    if _data is None:
        raise HTTPException(status_code=500, detail="Data not loaded")

    at_risk = []
    churn_risks = []

    for customer_id in _data["customer_id"].unique():
        customer_df = _data[_data["customer_id"] == customer_id].sort_values("date")

        feature_engineer = FeatureEngineer()
        features = feature_engineer.engineer_features(customer_df)

        trend_detector = TrendDetector()
        trend_result = trend_detector.detect_trend(customer_df)
        churn_risk = _calculate_churn_risk(trend_result["trend_slope"], features)

        churn_risks.append(churn_risk)

        if churn_risk >= 0.6:  # High risk threshold
            at_risk.append({
                "customer_id": customer_id,
                "churn_risk": churn_risk,
                "risk_category": _get_risk_category(churn_risk),
                "primary_signal": _get_primary_signal(trend_result["trend_slope"], features),
                "recommended_action": _get_recommended_action(churn_risk)
            })

    # Sort by churn_risk
    at_risk.sort(key=lambda x: x["churn_risk"], reverse=True)

    return AtRiskResponse(
        customers=at_risk[:50],  # Top 50
        total_at_risk=len(at_risk),
        avg_churn_risk=sum(churn_risks) / len(churn_risks) if churn_risks else 0
    )


# Helper functions

def _calculate_churn_risk(trend_slope: float, features: dict) -> float:
    """Calculate churn risk score."""
    risk = 0.0

    # Trend component
    if trend_slope < -100:
        risk += 0.4
    elif trend_slope < -50:
        risk += 0.2

    # Volatility component
    if features.get("spending_volatility", [0])[-1] > 1000:
        risk += 0.2

    # Frequency component
    if features.get("current_trans_count", 0) < 10:
        risk += 0.2

    # Category diversity
    if features.get("unique_categories", [0])[-1] < 2:
        risk += 0.2

    return min(1.0, risk)


def _get_risk_category(churn_risk: float) -> str:
    """Categorize risk level."""
    if churn_risk >= 0.8:
        return "CRITICAL"
    elif churn_risk >= 0.6:
        return "HIGH"
    elif churn_risk >= 0.4:
        return "MEDIUM"
    else:
        return "LOW"


def _detect_behavior_change(customer_df: pd.DataFrame) -> str:
    """Detect behavior changes."""
    if len(customer_df) < 30:
        return None

    monthly = customer_df.groupby(customer_df["date"].dt.to_period("M"))
    months = list(monthly)

    if len(months) < 2:
        return None

    first_half = customer_df.iloc[:len(customer_df)//2]
    second_half = customer_df.iloc[len(customer_df)//2:]

    first_categories = first_half["mcc_category"].value_counts(normalize=True)
    second_categories = second_half["mcc_category"].value_counts(normalize=True)

    # Check for category shift
    category_shift = 0
    for cat in first_categories.index:
        if cat in second_categories.index:
            shift = abs(first_categories[cat] - second_categories[cat])
            if shift > 0.2:
                category_shift += shift

    if category_shift > 0.3:
        return "Lifestyle Shift: Category distribution changed significantly"

    return None


def _get_primary_signal(trend_slope: float, features: dict) -> str:
    """Get primary churn signal."""
    if trend_slope < -100:
        return "Spending declining rapidly"
    elif features.get("unique_categories", [0])[-1] < 2:
        return "Reduced category diversity"
    elif features.get("current_trans_count", 0) < 10:
        return "Declining transaction frequency"
    else:
        return "Irregular spending pattern"


def _get_recommended_action(churn_risk: float) -> str:
    """Get recommended action for churn risk."""
    if churn_risk >= 0.8:
        return "Urgent: Personal outreach recommended"
    elif churn_risk >= 0.6:
        return "Retention campaign needed"
    else:
        return "Monitor closely"
