from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class CustomerListItem(BaseModel):
    """Single customer in list response."""
    customer_id: str
    name: Optional[str] = None
    status: str = "active"


class CustomerListResponse(BaseModel):
    """Response for list of all customers."""
    total: int
    customers: List[CustomerListItem]


class PersonaMetadata(BaseModel):
    """Persona metadata for a customer."""
    persona_id: Optional[int] = None
    persona_name: Optional[str] = None
    narrative: Optional[str] = None
    expected_risk_score: Optional[float] = None


class TransactionResponse(BaseModel):
    transaction_id: str
    customer_id: str
    date: str
    amount: float
    mcc: str
    mcc_category: str
    channel: str
    merchant: str
    country: str


class TrendDataPoint(BaseModel):
    date: str
    actual: Optional[float] = None
    forecast: float
    lower_bound: float
    upper_bound: float


class TrendResponse(BaseModel):
    customer_id: str
    trend_data: List[TrendDataPoint]
    trend_slope_per_month: float  # AED per month (CORRECTED)
    trend_slope_per_day: float  # AED per day (for reference)
    trend_slope: float  # Backward compatibility (same as trend_slope_per_month)
    trend_slope_unit: str = "AED/month"  # Explicit unit
    seasonality_pattern: str
    seasonality_amplitude: float
    has_seasonality: bool
    data_span_days: int
    metadata: Optional[Dict] = None


class SHAPExplanation(BaseModel):
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    top_drivers: List[str] = []
    shap_values: Dict[str, float] = {}


class AnomalyDetail(BaseModel):
    date: str
    anomaly_type: str
    anomaly_score: float
    transaction: TransactionResponse
    explanation: SHAPExplanation


class AnomalyResponse(BaseModel):
    customer_id: str
    anomalies: List[AnomalyDetail]


class CustomerProfileResponse(BaseModel):
    customer_id: str
    total_transactions: int
    date_range: List[str]
    current_monthly_spending: float
    spending_trend: str
    behavior_change: Optional[str]
    persona: Optional[PersonaMetadata] = None


class AtRiskCustomer(BaseModel):
    customer_id: str
    churn_risk: float
    risk_category: str
    primary_signal: str
    recommended_action: str


class AtRiskResponse(BaseModel):
    customers: List[AtRiskCustomer]
    total_at_risk: int
    avg_churn_risk: float


class GenerateDataRequest(BaseModel):
    n_customers: int = Field(default=1000, ge=1, le=10000, description="Number of customers to generate")
    months: int = Field(default=12, ge=1, le=60, description="Number of months of data")
    patterns: List[str] = Field(
        default_factory=lambda: ["normal", "silent_churn", "lifestyle_shift"],
        description="Customer behavior patterns"
    )


class GenerateDataResponse(BaseModel):
    status: str
    n_records: int
    distribution: Dict[str, float]


# ============================================================================
# Phase 5D: Churn Prediction API Response Models
# ============================================================================

class ChurnPredictionDetail(BaseModel):
    """Detailed SHAP explanation for a churn prediction."""
    feature_name: str
    feature_value: float
    shap_value: float
    contribution_direction: str  # "increases_churn" or "decreases_churn"


class ChurnPredictionResponse(BaseModel):
    """Response for single customer churn prediction."""
    customer_id: str
    churn_probability: float
    churn_prediction: str  # "churned" or "stable"
    confidence: float
    top_5_factors: List[ChurnPredictionDetail] = []
    account_metrics: Dict[str, float] = {}


class BatchChurnPredictionResponse(BaseModel):
    """Response for batch churn predictions across all customers."""
    total_customers: int
    churned_count: int
    stable_count: int
    average_churn_probability: float
    predictions: List[ChurnPredictionResponse]


class FeatureImportanceItem(BaseModel):
    """Feature importance ranking."""
    rank: int
    feature_name: str
    importance_score: float
    interpretation: str


class FeatureImportanceResponse(BaseModel):
    """Response for feature importance analysis."""
    total_features: int
    top_features: List[FeatureImportanceItem]
    model_performance: Dict[str, float]


class ModelTrainingResponse(BaseModel):
    """Response for model training/retraining endpoint."""
    success: bool
    message: str
    model_metrics: Dict[str, float]
    training_timestamp: str
    customers_trained: int


# ============================================================================
# Phase 5E: AI Insights Narrative Panel Response Models
# ============================================================================

class AIInsightResponse(BaseModel):
    """Response for AI-generated insight narrative for customer."""
    customer_id: str
    summary: str  # "HEALTHY", "MEDIUM", "WARNING", "CRITICAL"
    summary_icon: str  # "✅", "🟡", "⚠️", "🔴"
    risk_category: str  # Detailed classification (STABLE, MONITORING, AT_RISK, ACTIVE_DECLINE, SILENT_CHURN, ACTIVE_CHURN)
    key_findings: List[str]  # 3-4 professional findings
    business_advice: str  # Actionable recommendation
    technical_evidence: Dict  # Hidden detail block with metrics/formulas
    generated_at: str  # ISO timestamp
    confidence_score: float  # 0.0-1.0
    cached: Optional[bool] = False  # True if loaded from cache


# ============================================================================
# UC-4: Comprehensive Analytics (Monthly Analysis)
# ============================================================================

class ComprehensiveAnalyticsResponse(BaseModel):
    """Unified response combining UC-1 trends + UC-2 churn + business actions for monthly review."""
    customer_id: str
    period: str  # "2024-01" (monthly) or custom date range

    # UC-1: Spending Trends
    spending_analysis: Dict  # {trend_slope, volatility, category_diversity, monthly_avg}
    behavior_changes: Optional[List[str]] = None  # ["Category shift detected", "Frequency decline"]

    # UC-2: Churn Prediction
    churn_probability: float  # 0.0-1.0
    churn_prediction: str  # "stable", "at_risk", "churned"
    risk_drivers: List[Dict]  # Top 5 SHAP factors

    # Professional Narrative
    ai_insights: str  # Summary narrative
    recommended_actions: List[str]  # ["Retention outreach", "Loyalty upgrade"]

    # Metrics
    account_health: Dict  # {utilization, dormancy, engagement, payment_behavior}
    generated_at: str
    confidence_score: float


class ModelPerformanceResponse(BaseModel):
    """Model evaluation metrics for transparency and audit."""
    model_type: str  # "XGBoost Binary Classifier"
    training_samples: int
    test_samples: int

    # Classification metrics
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float

    # Confusion matrix
    true_negatives: int
    false_positives: int
    false_negatives: int
    true_positives: int

    # Feature count
    total_features: int
    feature_list: List[str]

    # Model info
    last_trained: str  # ISO timestamp
    model_version: str
    threshold: float  # Default decision threshold


class ModelVersionResponse(BaseModel):
    """Available model versions for deployment."""
    current_version: str  # "1.0.0"
    available_versions: List[Dict]  # [{"version": "1.0.0", "trained_at": "...", "f1_score": 0.82}]
    training_status: str  # "idle", "training", "evaluating"
    last_retraining: Optional[str] = None
