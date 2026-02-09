from pydantic import BaseModel
from datetime import date
from typing import List, Dict, Any, Optional


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
    prediction: str
    confidence: float
    top_drivers: List[str]
    shap_values: Dict[str, float]


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
    n_customers: int = 1000
    months: int = 12
    patterns: List[str] = ["normal", "silent_churn", "lifestyle_shift"]


class GenerateDataResponse(BaseModel):
    status: str
    n_records: int
    distribution: Dict[str, float]
