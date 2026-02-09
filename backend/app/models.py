from pydantic import BaseModel, Field
from typing import List, Dict, Optional


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
    actual: float
    forecast: float
    lower_bound: float
    upper_bound: float


class TrendResponse(BaseModel):
    customer_id: str
    trend_data: List[TrendDataPoint]
    trend_slope: float
    seasonality_pattern: str
    seasonality_amplitude: float


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
    churn_risk: float
    behavior_change: Optional[str]
    risk_category: str


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
