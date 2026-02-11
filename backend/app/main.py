from contextlib import asynccontextmanager
from typing import Generator, List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import pandas as pd
import logging
from sqlalchemy.orm import Session

from . import config
from .models import (
    GenerateDataRequest, GenerateDataResponse,
    CustomerProfileResponse, TrendResponse, AnomalyResponse, AtRiskResponse,
    ChurnPredictionResponse, BatchChurnPredictionResponse, FeatureImportanceResponse,
    ModelTrainingResponse, AIInsightResponse
)
from .db import initialize_database, get_db, CustomerRepository, TransactionRepository
from .db.models import Customer, Transaction
from .ml.data_generator import SyntheticDataGenerator
from .ml.feature_engineering import FeatureEngineer
from .ml.trend_detection import TrendDetector
from .ml.anomaly_detection import AnomalyDetector
from .ml.explainability import ExplainabilityEngine
from .ml.narrative_engine import NarrativeEngine, NarrativeCache

# Configure logging
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Global model cache (loaded once at startup)
MODEL_CACHE = {
    "churn_model": None,
    "feature_scaler": None,
    "loaded": False
}

def load_cached_models():
    """Load ML models once and cache them in memory."""
    import pickle
    from pathlib import Path

    if MODEL_CACHE["loaded"]:
        return MODEL_CACHE

    try:
        model_path = Path(__file__).parent / "ml" / "models" / "churn_model.pkl"
        scaler_path = Path(__file__).parent / "ml" / "models" / "feature_scaler.pkl"

        if model_path.exists() and scaler_path.exists():
            with open(model_path, "rb") as f:
                MODEL_CACHE["churn_model"] = pickle.load(f)
            with open(scaler_path, "rb") as f:
                MODEL_CACHE["feature_scaler"] = pickle.load(f)
            MODEL_CACHE["loaded"] = True
            logger.info("✅ ML models loaded and cached in memory")
        else:
            logger.warning("⚠️ ML model files not found")
    except Exception as e:
        logger.error(f"❌ Failed to load cached models: {e}")

    return MODEL_CACHE

# Allowed CORS origins (restrict in production)
ALLOWED_ORIGINS: List[str] = [
    origin.strip()
    for origin in config.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("Initializing database...")
    initialize_database()
    logger.info("Loading ML models into memory...")
    load_cached_models()
    logger.info("API ready")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Customer Spending Trend Analysis API",
    description="ML-powered banking analytics PoC",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        customer_count = CustomerRepository(db).get_customer_count()
        return {"status": "healthy", "database_ready": True, "customer_count": customer_count}
    except Exception as e:
        logger.error("Health check failed: %s", e, exc_info=True)
        return {"status": "unhealthy", "database_ready": False, "error": "Database unavailable"}


@app.get("/api/customers")
async def get_all_customers(db: Session = Depends(get_db)):
    """Get list of all customers from database.

    Used by frontend to populate customer selector.
    Returns customer_id and name for each customer.

    Must come before /api/customers/{customer_id} to avoid routing conflict!
    """
    logger.info("Fetching all customers from database")

    try:
        customers = db.query(Customer).all()

        customer_list = [
            {
                "customer_id": c.id,
                "name": f"Customer {c.id[-6:]}" if c.id.startswith("customer_") else c.id,
                "status": "active"
            }
            for c in customers
        ]

        return {
            "total": len(customer_list),
            "customers": customer_list
        }
    except Exception as e:
        logger.error(f"Error fetching customers: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch customers"
        )


@app.post("/api/data/generate", response_model=GenerateDataResponse)
async def generate_data(
    request: GenerateDataRequest, db: Session = Depends(get_db)
) -> GenerateDataResponse:
    """Generate synthetic transaction data and persist to database."""
    logger.info(
        "Generating %d customers for %d months",
        request.n_customers,
        request.months,
    )

    generator = SyntheticDataGenerator(
        n_customers=request.n_customers,
        n_months=request.months,
    )

    df = generator.generate()

    # Calculate distribution before saving
    distribution: dict[str, float] = {}
    for pattern in ["normal", "silent_churn", "lifestyle_shift"]:
        count = len(df[df["pattern"] == pattern])
        distribution[pattern] = count / len(df) if len(df) > 0 else 0

    # Persist generated data to the database
    generator.save_to_db(db)
    logger.info("Generated %d transactions with distribution: %s", len(df), distribution)

    return GenerateDataResponse(
        status="Generated",
        n_records=len(df),
        distribution=distribution,
    )


@app.get("/api/customers/{customer_id}", response_model=CustomerProfileResponse)
async def get_customer_profile(
    customer_id: str, db: Session = Depends(get_db)
) -> CustomerProfileResponse:
    """Get customer profile with risk assessment."""
    repo = CustomerRepository(db)

    customer, transactions = repo.get_customer_with_transactions(customer_id)
    if not customer or not transactions:
        raise HTTPException(
            status_code=404, detail=f"Customer {customer_id} not found"
        )

    customer_df = _transactions_to_dataframe(transactions)

    # Extract features
    features = FeatureEngineer.engineer_features(customer_df)

    # Detect trend
    trend_detector = TrendDetector(
        yearly_seasonality=config.PROPHET_YEARLY_SEASONALITY,
        weekly_seasonality=config.PROPHET_WEEKLY_SEASONALITY,
    )
    trend_result = trend_detector.detect_trend(customer_df)
    trend_slope = trend_result["trend_slope"]
    trend_category = TrendDetector.get_trend_category(trend_slope)

    # Detect behavior change
    behavior_change = _detect_behavior_change(customer_df)

    # Build persona metadata if available
    persona_metadata = None
    if customer.persona_name and customer.expected_risk_score:
        from .models import PersonaMetadata
        persona_metadata = PersonaMetadata(
            persona_id=customer.persona_id,
            persona_name=customer.persona_name,
            narrative=customer.narrative,
            expected_risk_score=customer.expected_risk_score
        )

    return CustomerProfileResponse(
        customer_id=customer_id,
        total_transactions=len(customer_df),
        date_range=[
            customer_df["date"].min().strftime("%Y-%m-%d"),
            customer_df["date"].max().strftime("%Y-%m-%d"),
        ],
        current_monthly_spending=features["current_monthly_spending"],
        spending_trend=trend_category,
        behavior_change=behavior_change,
        persona=persona_metadata,
    )


@app.get("/api/customers/{customer_id}/trends", response_model=TrendResponse)
async def get_customer_trends(customer_id: str, db: Session = Depends(get_db)) -> TrendResponse:
    """Get spending trend forecast."""
    repo = CustomerRepository(db)
    _, transactions = repo.get_customer_with_transactions(customer_id)

    if not transactions:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    # Convert to DataFrame
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
    } for t in transactions]).sort_values("date")

    trend_detector = TrendDetector()
    # Forecast 90 days ahead (~3 months) for better visibility
    trend_result = trend_detector.detect_trend(customer_df, periods_ahead=90)

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
        trend_slope_per_month=trend_result.get("trend_slope_per_month", 0.0),  # Corrected calculation
        trend_slope_per_day=trend_result.get("trend_slope_per_day", 0.0),  # Reference
        trend_slope=trend_result.get("trend_slope", 0.0),  # Backward compatibility
        trend_slope_unit="AED/month",
        seasonality_pattern="yearly_and_weekly" if trend_result.get("has_seasonality") else "none",
        seasonality_amplitude=trend_result.get("seasonality_amplitude", 0.0),
        has_seasonality=trend_result.get("has_seasonality", False),
        data_span_days=trend_result.get("data_span_days", 0),
        metadata=trend_result.get("metadata", {})
    )


@app.get("/api/customers/{customer_id}/anomalies", response_model=AnomalyResponse)
async def get_customer_anomalies(customer_id: str, db: Session = Depends(get_db)) -> AnomalyResponse:
    """Get detected anomalies with explanations."""
    repo = CustomerRepository(db)
    _, transactions = repo.get_customer_with_transactions(customer_id)

    if not transactions:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    # Convert to DataFrame
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
    } for t in transactions]).sort_values("date")

    # Detect anomalies
    anomaly_detector = AnomalyDetector(
        contamination=config.ISOLATION_FOREST_CONTAMINATION,
        n_estimators=config.ISOLATION_FOREST_N_ESTIMATORS
    )
    feature_vector = AnomalyDetector.get_anomaly_features(customer_df)
    anomalies = anomaly_detector.detect(customer_df, feature_vector)

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
async def get_high_risk_customers(db: Session = Depends(get_db)) -> AtRiskResponse:
    """Get list of high-risk customers using cached churn risk scores."""
    repo = CustomerRepository(db)
    customers = repo.get_all(limit=None)  # Get all customers

    if not customers:
        raise HTTPException(status_code=500, detail="No customers found in database")

    at_risk = []
    churn_risks = []

    for customer in customers:
        # Use cached churn_risk_score from database if available
        if customer.churn_risk_score is not None:
            churn_risk = customer.churn_risk_score
            churn_risks.append(churn_risk)

            if churn_risk >= 0.6:  # High risk threshold
                at_risk.append({
                    "customer_id": customer.id,
                    "churn_risk": churn_risk,
                    "risk_category": customer.risk_category or _get_risk_category(churn_risk),
                    "primary_signal": customer.primary_signal or "Activity pattern anomaly detected",
                    "recommended_action": customer.recommended_action or _get_recommended_action(churn_risk)
                })

    # Sort by churn_risk
    at_risk.sort(key=lambda x: x["churn_risk"], reverse=True)

    return AtRiskResponse(
        customers=at_risk[:50],  # Top 50
        total_at_risk=len(at_risk),
        avg_churn_risk=sum(churn_risks) / len(churn_risks) if churn_risks else 0
    )


# Helper functions

def _transactions_to_dataframe(transactions: List[Transaction]) -> pd.DataFrame:
    """Convert Transaction ORM objects to DataFrame."""
    if not transactions:
        return pd.DataFrame()

    data = []
    for t in transactions:
        data.append({
            'date': t.date,
            'amount': t.amount,
            'mcc': t.mcc,
            'mcc_category': t.mcc_category,
            'channel': t.channel,
            'merchant': t.merchant,
            'country': t.country,
            'time_of_day': t.time_of_day,
        })

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df


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


# ============================================================================
# Phase 4: Persona Endpoints
# ============================================================================

@app.get("/api/personas", response_model=dict)
async def list_personas():
    """List all 22 Phase 4 personas with their metadata (10 core + 12 edge cases)."""
    from .ml.persona_registry import list_personas as get_personas
    return {"personas": get_personas()}


@app.get("/api/customers/personas/{persona_id}", response_model=dict)
async def get_customers_by_persona(persona_id: int, db: Session = Depends(get_db)):
    """Get all customers for a specific persona."""
    from .db.models import Customer

    customers = db.query(Customer).filter(
        Customer.persona_id == persona_id
    ).all()

    return {
        "persona_id": persona_id,
        "customers": [
            {
                "id": c.id,
                "persona_name": c.persona_name,
                "narrative": c.narrative,
                "expected_risk_score": c.expected_risk_score,
                "transaction_count": len(c.transactions.all()),
            }
            for c in customers
        ],
    }


# ============================================================================
# Phase 5D: Churn Prediction API Endpoints
# ============================================================================

@app.post("/api/ml/train-churn-model", response_model=ModelTrainingResponse)
async def train_churn_model(db: Session = Depends(get_db)) -> ModelTrainingResponse:
    """Retrain churn prediction model on current database.

    This endpoint:
    1. Loads features for all customers from database
    2. Trains XGBoost binary classifier
    3. Validates metrics against success criteria (F1≥0.80, AUC≥0.85)
    4. Generates SHAP explanations
    5. Persists model to disk

    Returns: Training results with metrics and timestamp
    """
    from datetime import datetime
    from .ml.churn_model import ChurnModelTrainer

    logger.info("Training churn prediction model...")

    try:
        trainer = ChurnModelTrainer(db)
        result = trainer.train_full_pipeline()

        if result["success"]:
            metrics = result["metrics"]
            training_timestamp = datetime.utcnow().isoformat()

            logger.info(
                "Model training successful - F1: %.4f, AUC: %.4f",
                metrics["f1"],
                metrics["roc_auc"]
            )

            return ModelTrainingResponse(
                success=True,
                message="Model training completed successfully",
                model_metrics=metrics,
                training_timestamp=training_timestamp,
                customers_trained=1000
            )
        else:
            error_msg = result.get("error", "Unknown error during training")
            logger.error("Model training failed: %s", error_msg)
            raise HTTPException(
                status_code=500,
                detail=f"Model training failed: {error_msg}"
            )

    except Exception as e:
        logger.error("Unexpected error during model training: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Model training failed due to internal error"
        )


@app.get("/api/customers/{customer_id}/churn-prediction", response_model=ChurnPredictionResponse)
async def get_customer_churn_prediction(
    customer_id: str, db: Session = Depends(get_db)
) -> ChurnPredictionResponse:
    """Get churn prediction for a single customer.

    This endpoint:
    1. Uses cached XGBoost model (loaded at startup)
    2. Engineers 15 features for the customer
    3. Generates churn probability prediction
    4. Returns SHAP-based explanation of top 5 contributing factors
    5. Includes account metrics (balance, utilization, dormancy, etc.)

    Performance: <50ms per customer (model cached in memory)
    """
    import json
    from .ml.churn_model import ChurnModelTrainer
    from .ml.churn_features import ChurnFeatureEngineer
    from .models import ChurnPredictionDetail

    logger.info("Getting churn prediction for customer: %s", customer_id)

    try:
        # Check if customer exists
        repo = CustomerRepository(db)
        customer = repo.get_by_id(customer_id)
        if not customer:
            raise HTTPException(
                status_code=404,
                detail=f"Customer {customer_id} not found"
            )

        # Get cached model and scaler (loaded at startup)
        cached = load_cached_models()
        model = cached.get("churn_model")
        scaler = cached.get("feature_scaler")

        if not model or not scaler:
            raise HTTPException(
                status_code=503,
                detail="Churn model not trained yet. Please train the model first."
            )

        # Engineer features for customer
        features_dict = ChurnFeatureEngineer.engineer_churn_features(customer_id, db)
        feature_names = list(features_dict.keys())
        feature_values = [features_dict[name] for name in feature_names]

        # Scale features
        X = pd.DataFrame([feature_values], columns=feature_names)
        X_scaled = scaler.transform(X)

        # Get prediction and probability
        prediction = model.predict(X_scaled)[0]
        probability = model.predict_proba(X_scaled)[0]
        churn_probability = float(probability[1])  # Probability of churn (class 1)

        # Get SHAP explanation
        try:
            import shap
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_scaled)

            # Get top 5 features by absolute SHAP value
            if isinstance(shap_values, list):
                shap_vals = shap_values[1]  # Class 1 (churn)
            else:
                shap_vals = shap_values

            top_indices = np.argsort(np.abs(shap_vals[0]))[-5:][::-1]
            top_5_factors = [
                ChurnPredictionDetail(
                    feature_name=feature_names[idx],
                    feature_value=float(feature_values[idx]),
                    shap_value=float(shap_vals[0][idx]),
                    contribution_direction="increases_churn" if shap_vals[0][idx] > 0 else "decreases_churn"
                )
                for idx in top_indices
            ]
        except Exception as e:
            logger.warning("Failed to generate SHAP explanation: %s", str(e))
            top_5_factors = []

        # Build response
        return ChurnPredictionResponse(
            customer_id=customer_id,
            churn_probability=churn_probability,
            churn_prediction="churned" if prediction == 1 else "stable",
            confidence=float(max(probability)),
            top_5_factors=top_5_factors,
            account_metrics={
                "credit_limit": float(customer.credit_limit or 0),
                "current_balance": float(customer.current_balance or 0),
                "utilization_ratio": float(features_dict.get("utilization_ratio", 0)),
                "dormancy_days": float(features_dict.get("dormancy_days", 0)),
                "payment_delay_score": float(features_dict.get("payment_delay_score", 0)),
                "support_sentiment_score": float(features_dict.get("support_sentiment_score", 0)),
                "inactive_months_count": float(features_dict.get("inactive_months_count", 0)),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error during churn prediction: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate churn prediction"
        )


@app.post("/api/ml/predict-all-churn", response_model=BatchChurnPredictionResponse)
async def predict_all_customers_churn(
    db: Session = Depends(get_db)
) -> BatchChurnPredictionResponse:
    """Get churn predictions for all customers (batch prediction).

    This endpoint:
    1. Loads trained XGBoost model
    2. Engineers features for all 1000 customers
    3. Generates predictions for all customers
    4. Returns ranked list (sorted by churn probability)
    5. Includes summary statistics

    Performance: <10s for 1000 customers
    """
    import pickle
    import numpy as np
    from pathlib import Path
    from .ml.churn_features import ChurnFeatureEngineer
    from .models import ChurnPredictionDetail

    logger.info("Predicting churn for all customers...")

    try:
        # Load model and scaler
        model_path = Path(__file__).parent / "ml" / "models" / "churn_model.pkl"
        scaler_path = Path(__file__).parent / "ml" / "models" / "feature_scaler.pkl"

        if not model_path.exists() or not scaler_path.exists():
            raise HTTPException(
                status_code=503,
                detail="Churn model not trained yet. Please train the model first."
            )

        with open(model_path, "rb") as f:
            model = pickle.load(f)
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)

        # Get all customers
        repo = CustomerRepository(db)
        all_customers = repo.get_all(limit=None)

        if not all_customers:
            raise HTTPException(
                status_code=500,
                detail="No customers found in database"
            )

        predictions_list = []
        churned_count = 0
        stable_count = 0
        total_probability = 0.0

        for i, customer in enumerate(all_customers):
            if (i + 1) % 100 == 0:
                logger.info("Processed %d/%d customers", i + 1, len(all_customers))

            try:
                # Engineer features
                features_dict = ChurnFeatureEngineer.engineer_churn_features(customer.id, db)
                feature_names = list(features_dict.keys())
                feature_values = [features_dict[name] for name in feature_names]

                # Scale and predict
                X = pd.DataFrame([feature_values], columns=feature_names)
                X_scaled = scaler.transform(X)
                prediction = model.predict(X_scaled)[0]
                probability = model.predict_proba(X_scaled)[0]
                churn_probability = float(probability[1])

                # Count results
                if prediction == 1:
                    churned_count += 1
                else:
                    stable_count += 1
                total_probability += churn_probability

                # Build prediction response
                pred_response = ChurnPredictionResponse(
                    customer_id=customer.id,
                    churn_probability=churn_probability,
                    churn_prediction="churned" if prediction == 1 else "stable",
                    confidence=float(max(probability)),
                    top_5_factors=[],
                    account_metrics={
                        "credit_limit": float(customer.credit_limit or 0),
                        "current_balance": float(customer.current_balance or 0),
                        "utilization_ratio": float(features_dict.get("utilization_ratio", 0)),
                        "dormancy_days": float(features_dict.get("dormancy_days", 0)),
                        "inactive_months_count": float(features_dict.get("inactive_months_count", 0)),
                    }
                )
                predictions_list.append(pred_response)

            except Exception as e:
                logger.warning("Failed to predict for customer %s: %s", customer.id, str(e))
                continue

        # Sort by churn probability (descending)
        predictions_list.sort(key=lambda x: x.churn_probability, reverse=True)

        logger.info(
            "Batch prediction complete - Churned: %d, Stable: %d, Avg Probability: %.4f",
            churned_count,
            stable_count,
            total_probability / len(all_customers) if all_customers else 0
        )

        return BatchChurnPredictionResponse(
            total_customers=len(all_customers),
            churned_count=churned_count,
            stable_count=stable_count,
            average_churn_probability=total_probability / len(all_customers) if all_customers else 0,
            predictions=predictions_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error during batch churn prediction: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Batch prediction failed"
        )


@app.get("/api/customers/{customer_id}/insights", response_model=AIInsightResponse)
async def get_customer_insights(
    customer_id: str, db: Session = Depends(get_db)
) -> AIInsightResponse:
    """Get AI-generated insight narrative for customer.

    This endpoint:
    1. Loads cached narrative if available (7-day TTL)
    2. Otherwise, engineers 15 features for the customer
    3. Generates professional analyst briefing (Summary → Findings → Advice → Evidence)
    4. Connects UC-1 trends + UC-2 churn prediction into business narrative
    5. Caches result in ai_interpretations table

    Response includes:
    - Summary: HEALTHY / MEDIUM / WARNING / CRITICAL
    - Key Findings: 3-4 business insights from features + SHAP
    - Business Advice: Actionable recommendation with urgency level
    - Technical Evidence: Hidden JSON with formulas + confidence

    Performance: <100ms (first call with cache miss), <1ms (cache hit)
    """
    from .ml.churn_features import ChurnFeatureEngineer
    import json

    logger.info("Getting AI insights for customer: %s", customer_id)

    try:
        # Check if customer exists
        repo = CustomerRepository(db)
        customer = repo.get_by_id(customer_id)
        if not customer:
            raise HTTPException(
                status_code=404,
                detail=f"Customer {customer_id} not found"
            )

        # Try to get cached narrative
        cached = NarrativeCache.get_cached_narrative(customer_id, db)
        if cached:
            logger.info("Returning cached narrative for customer: %s", customer_id)
            return AIInsightResponse(
                customer_id=customer_id,
                summary=cached["summary"],
                summary_icon=cached.get("summary_icon", ""),
                risk_category=cached.get("risk_category", ""),
                key_findings=json.loads(cached["key_findings"]) if isinstance(cached["key_findings"], str) else cached["key_findings"],
                business_advice=cached["business_advice"],
                technical_evidence=json.loads(cached["technical_evidence"]) if isinstance(cached["technical_evidence"], str) else cached["technical_evidence"],
                generated_at=cached["generated_at"],
                confidence_score=cached["confidence_score"],
                cached=True
            )

        # Load cached churn model
        cached_models = load_cached_models()
        model = cached_models.get("churn_model")
        scaler = cached_models.get("feature_scaler")

        if not model or not scaler:
            raise HTTPException(
                status_code=503,
                detail="Churn model not trained yet. Please train the model first."
            )

        # Engineer features for customer
        features_dict = ChurnFeatureEngineer.engineer_churn_features(customer_id, db)
        feature_names = list(features_dict.keys())
        feature_values = [features_dict[name] for name in feature_names]

        # Scale features and get prediction
        X = pd.DataFrame([feature_values], columns=feature_names)
        X_scaled = scaler.transform(X)
        prediction = model.predict(X_scaled)[0]
        probability = model.predict_proba(X_scaled)[0]
        churn_probability = float(probability[1])

        # Get SHAP values
        shap_values_dict = {}
        try:
            import shap
            import numpy as np

            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_scaled)

            if isinstance(shap_values, list):
                shap_vals = shap_values[1]  # Class 1 (churn)
            else:
                shap_vals = shap_values

            # Handle NaN values and convert to float
            shap_values_dict = {}
            for i in range(len(feature_names)):
                val = float(shap_vals[0][i])
                # Replace NaN with 0 (no contribution)
                if np.isnan(val):
                    val = 0.0
                shap_values_dict[feature_names[i]] = val
        except Exception as e:
            logger.warning("Failed to generate SHAP values: %s", str(e))

        # Add churn probability to features for narrative
        features_with_prob = {**features_dict, "churn_probability": churn_probability}

        # Generate narrative
        narrative = NarrativeEngine.generate_narrative(
            customer_id=customer_id,
            features=features_with_prob,
            churn_probability=churn_probability,
            shap_values=shap_values_dict if shap_values_dict else None
        )

        # Cache the narrative
        NarrativeCache.save_narrative(customer_id, narrative, db)

        logger.info(
            "Generated narrative for customer %s: summary=%s, confidence=%.2f",
            customer_id,
            narrative["summary"],
            narrative["confidence_score"]
        )

        # Build response
        return AIInsightResponse(
            customer_id=customer_id,
            summary=narrative["summary"],
            summary_icon=narrative.get("summary_icon", ""),
            risk_category=narrative.get("risk_category", ""),
            key_findings=narrative["key_findings"],
            business_advice=narrative["business_advice"],
            technical_evidence=narrative["technical_evidence"],
            generated_at=narrative["generated_at"],
            confidence_score=narrative["confidence_score"],
            cached=False
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating AI insights: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate AI insights"
        )


@app.get("/api/ml/churn-model/feature-importance", response_model=FeatureImportanceResponse)
async def get_feature_importance(db: Session = Depends(get_db)) -> FeatureImportanceResponse:
    """Get feature importance ranking from trained churn model.

    This endpoint:
    1. Loads trained XGBoost model
    2. Extracts feature importance scores
    3. Ranks features by importance
    4. Provides interpretation for each feature
    5. Returns model performance metrics

    Importance interpretation:
    - Dormancy & Inactivity: Strong churn signals
    - Payment Behavior: Risk indicators
    - Spending Patterns: Activity signals
    - Credit Metrics: Utilization indicators
    """
    import pickle
    import json
    from pathlib import Path

    logger.info("Retrieving feature importance from trained model...")

    try:
        # Load model and metrics
        model_path = Path(__file__).parent / "ml" / "models" / "churn_model.pkl"
        metrics_path = Path(__file__).parent / "ml" / "models" / "metrics.json"

        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail="Churn model not trained yet. Please train the model first."
            )

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        # Get feature importance from XGBoost
        importance_scores = model.feature_importances_
        feature_names = model.get_booster().feature_names

        if not feature_names:
            # Fallback to known feature names
            feature_names = [
                'trend_slope', 'spending_volatility', 'category_entropy',
                'transaction_count_trend', 'pos_ratio', 'online_ratio',
                'avg_transaction_amount', 'utilization_ratio', 'dormancy_days',
                'payment_delay_score', 'support_sentiment_score',
                'campaign_engagement_score', 'account_age_months',
                'balance_to_spending_ratio', 'inactive_months_count'
            ]

        # Create ranking with interpretation
        feature_interpretations = {
            "dormancy_days": "Days since last transaction - strong churn signal",
            "inactive_months_count": "Number of inactive months - recent activity metric",
            "balance_to_spending_ratio": "Spending activity indicator",
            "support_sentiment_score": "Customer satisfaction from support interactions",
            "payment_delay_score": "Payment behavior risk indicator",
            "utilization_ratio": "Credit utilization level",
            "trend_slope": "Monthly spending trend direction",
            "spending_volatility": "Transaction amount variation",
            "category_entropy": "Spending diversity across categories",
            "transaction_count_trend": "Transaction frequency trend",
            "account_age_months": "Account tenure (older = lower risk)",
            "campaign_engagement_score": "Marketing engagement level",
            "pos_ratio": "In-store transaction percentage",
            "online_ratio": "Online transaction percentage",
            "avg_transaction_amount": "Average transaction size",
        }

        # Build ranked list
        importance_list = [
            {
                "rank": i + 1,
                "feature_name": feature_names[idx],
                "importance_score": float(importance_scores[idx]),
                "interpretation": feature_interpretations.get(feature_names[idx], "Feature contribution to churn")
            }
            for i, idx in enumerate(np.argsort(importance_scores)[::-1])
        ]

        # Load model metrics
        model_metrics = {}
        if metrics_path.exists():
            with open(metrics_path, "r") as f:
                metrics_data = json.load(f)
                model_metrics = {
                    "f1_score": float(metrics_data.get("f1", 0)),
                    "precision": float(metrics_data.get("precision", 0)),
                    "recall": float(metrics_data.get("recall", 0)),
                    "roc_auc": float(metrics_data.get("roc_auc", 0)),
                }

        from .models import FeatureImportanceItem
        return FeatureImportanceResponse(
            total_features=len(feature_names),
            top_features=[
                FeatureImportanceItem(
                    rank=item["rank"],
                    feature_name=item["feature_name"],
                    importance_score=item["importance_score"],
                    interpretation=item["interpretation"]
                )
                for item in importance_list
            ],
            model_performance=model_metrics
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving feature importance: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve feature importance"
        )


# ============================================================================
# UC-4: COMPREHENSIVE ANALYTICS (Monthly Analysis - Unified View)
# ============================================================================



