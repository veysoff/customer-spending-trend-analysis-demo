import numpy as np
import pandas as pd
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class ExplainabilityEngine:
    """Generate SHAP-based explanations for predictions."""

    FEATURE_NAMES = [
        "trend_slope",
        "spending_volatility",
        "spending_change",
        "transaction_count",
        "unique_categories",
        "avg_transaction_amount",
        "channel_diversity",
        "country_diversity"
    ]

    @staticmethod
    def explain_churn_risk(features: np.ndarray, churn_risk: float,
                          feature_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Generate explanation for churn risk prediction."""

        # Simulate SHAP values (in production, use actual SHAP library)
        shap_values = ExplainabilityEngine._compute_feature_importance(
            features, churn_risk
        )

        top_features = sorted(
            zip(ExplainabilityEngine.FEATURE_NAMES, shap_values[0]),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:5]

        drivers = []
        for feat_name, shap_val in top_features:
            direction = "↑" if shap_val > 0 else "↓"
            impact = abs(shap_val)
            drivers.append(f"{feat_name} ({direction} {impact:.3f})")

        return {
            "prediction": ExplainabilityEngine._get_risk_category(churn_risk),
            "confidence": min(1.0, churn_risk * 1.2),
            "top_drivers": drivers,
            "shap_values": {
                name: float(val)
                for name, val in zip(ExplainabilityEngine.FEATURE_NAMES, shap_values[0])
            },
            "explainability_method": "weighted_approximation",
        }

    @staticmethod
    def explain_anomaly(anomaly_type: str, anomaly_score: float,
                       transaction: Dict[str, Any],
                       features: np.ndarray) -> Dict[str, Any]:
        """Generate explanation for anomaly detection."""

        if anomaly_type == "SPENDING_SPIKE":
            drivers = [
                f"Transaction amount {transaction.get('amount', 0):.2f} is unusual",
                "Deviation from baseline spending patterns",
                f"Merchant: {transaction.get('merchant', 'Unknown')}"
            ]
        else:  # BEHAVIOR_CHANGE
            shap_values = ExplainabilityEngine._compute_feature_importance(
                features, anomaly_score
            )
            top_features = sorted(
                zip(ExplainabilityEngine.FEATURE_NAMES, shap_values[0]),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:3]
            drivers = [f"{name} change ({val:.3f})" for name, val in top_features]

        return {
            "anomaly_type": anomaly_type,
            "confidence": min(1.0, anomaly_score),
            "top_drivers": drivers,
            "shap_values": {},
            "explainability_method": "weighted_approximation",
        }

    @staticmethod
    def _compute_feature_importance(features: np.ndarray,
                                   prediction: float) -> np.ndarray:
        """Compute approximate SHAP-like feature importance."""
        # Simple approximation: weighted average of features
        weights = np.array([
            0.3,   # trend_slope
            0.15,  # spending_volatility
            0.2,   # spending_change
            0.1,   # transaction_count
            0.05,  # unique_categories
            0.1,   # avg_transaction_amount
            0.05,  # channel_diversity
            0.05   # country_diversity
        ])

        # Normalize features
        features_normalized = features.copy()
        for i in range(features.shape[1]):
            if features[0, i] != 0:
                features_normalized[0, i] = features[0, i] / (abs(features[0, i]) + 1)

        # Weighted contribution
        shap_approx = features_normalized * weights * prediction

        return shap_approx

    @staticmethod
    def _get_risk_category(churn_risk: float) -> str:
        """Categorize churn risk level."""
        if churn_risk >= 0.8:
            return "CRITICAL"
        elif churn_risk >= 0.6:
            return "HIGH"
        elif churn_risk >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def generate_summary_explanation(customer_profile: Dict[str, Any]) -> str:
        """Generate human-readable explanation summary."""
        trend = customer_profile["spending_trend"]
        risk = customer_profile["churn_risk"]

        if trend == "DECREASING" and risk > 0.7:
            return "Customer shows declining spending pattern with high churn risk. Recommended action: Retention campaign."
        elif customer_profile.get("behavior_change"):
            return f"Behavior change detected: {customer_profile['behavior_change']}. Monitor closely."
        elif risk > 0.5:
            return "Medium churn risk detected. Consider targeted offer."
        else:
            return "Customer engagement stable."
