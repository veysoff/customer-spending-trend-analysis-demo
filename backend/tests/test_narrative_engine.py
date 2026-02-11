"""Tests for AI Insights Narrative Engine (Phase 5E).

Tests verify that narratives are generated correctly for all 5 customer personas.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.ml.narrative_engine import NarrativeEngine


class TestNarrativeEngine:
    """Test suite for narrative generation."""

    def test_healthy_customer_narrative(self):
        """Test STABLE_John scenario: Healthy customer."""
        features = {
            "churn_probability": 0.15,
            "dormancy_days": 8,
            "trend_slope": 12,
            "spending_volatility": 0.18,
            "category_entropy": 3.2,
            "transaction_count_trend": 5,
            "pos_ratio": 0.68,
            "online_ratio": 0.28,
            "avg_transaction_amount": 67,
            "utilization_ratio": 0.35,
            "payment_delay_score": 0.05,
            "support_sentiment_score": 0.95,
            "campaign_engagement_score": 0.75,
            "account_age_months": 34,
            "balance_to_spending_ratio": 2.1,
            "inactive_months_count": 0
        }

        narrative = NarrativeEngine.generate_narrative(
            customer_id="customer_stable_john",
            features=features,
            churn_probability=0.15,
            shap_values=None
        )

        # Assertions
        assert narrative["summary"] == "HEALTHY"
        assert narrative["summary_icon"] == "✅"
        assert narrative["risk_category"] == "STABLE"
        assert len(narrative["key_findings"]) == 4
        assert "active" in narrative["key_findings"][0].lower() or "healthy" in narrative["key_findings"][-1].lower()
        assert "cross-sell" in narrative["business_advice"].lower() or "cross sell" in narrative["business_advice"].lower() or "proactive" in narrative["business_advice"].lower()
        assert "stable" in narrative["business_advice"].lower() or "relationship" in narrative["business_advice"].lower()
        assert narrative["confidence_score"] > 0.8

    def test_silent_churn_narrative(self):
        """Test CHURN_Sarah scenario: Silent churn pattern."""
        features = {
            "churn_probability": 0.82,
            "dormancy_days": 128,
            "trend_slope": -287,
            "spending_volatility": 0.12,
            "category_entropy": 0.6,
            "transaction_count_trend": -65,
            "pos_ratio": 0.05,
            "online_ratio": 0.02,
            "avg_transaction_amount": 45,
            "utilization_ratio": 0.05,
            "payment_delay_score": 0.80,
            "support_sentiment_score": 0.1,
            "campaign_engagement_score": 0.05,
            "account_age_months": 24,
            "balance_to_spending_ratio": 8.5,
            "inactive_months_count": 6
        }

        narrative = NarrativeEngine.generate_narrative(
            customer_id="customer_churn_sarah",
            features=features,
            churn_probability=0.82,
            shap_values=None
        )

        # Assertions
        assert narrative["summary"] == "CRITICAL"
        assert narrative["summary_icon"] == "🔴"
        assert narrative["risk_category"] == "SILENT_CHURN"
        assert len(narrative["key_findings"]) == 4
        assert any("dormant" in finding.lower() or "silent" in finding.lower() for finding in narrative["key_findings"])
        assert "urgent" in narrative["business_advice"].lower()
        assert "outreach" in narrative["business_advice"].lower()
        assert "24 hours" in narrative["business_advice"].lower()
        assert narrative["confidence_score"] > 0.85

    def test_stress_customer_narrative(self):
        """Test STRESS_Alex scenario: Financial stress pattern."""
        features = {
            "churn_probability": 0.65,
            "dormancy_days": 45,
            "trend_slope": -85,
            "spending_volatility": 1.8,
            "category_entropy": 2.1,
            "transaction_count_trend": -20,
            "pos_ratio": 0.65,
            "online_ratio": 0.30,
            "avg_transaction_amount": 89,
            "utilization_ratio": 0.95,
            "payment_delay_score": 0.72,
            "support_sentiment_score": 0.35,
            "campaign_engagement_score": 0.30,
            "account_age_months": 18,
            "balance_to_spending_ratio": 4.2,
            "inactive_months_count": 2
        }

        narrative = NarrativeEngine.generate_narrative(
            customer_id="customer_stress_alex",
            features=features,
            churn_probability=0.65,
            shap_values=None
        )

        # Assertions
        assert narrative["summary"] == "WARNING"
        assert narrative["summary_icon"] == "⚠️"
        assert narrative["risk_category"] == "AT_RISK"
        assert len(narrative["key_findings"]) == 4
        assert any("volatility" in finding.lower() or "stress" in finding.lower() or "utilization" in finding.lower() for finding in narrative["key_findings"])
        assert "financial" in narrative["business_advice"].lower() or "health check" in narrative["business_advice"].lower()
        assert "check" in narrative["business_advice"].lower() or "engagement" in narrative["business_advice"].lower()
        assert narrative["confidence_score"] > 0.80

    def test_positive_shift_narrative(self):
        """Test SHIFTER_Elena scenario: Positive lifestyle change."""
        features = {
            "churn_probability": 0.20,
            "dormancy_days": 12,
            "trend_slope": 35,
            "spending_volatility": 0.25,
            "category_entropy": 2.8,
            "transaction_count_trend": 25,
            "pos_ratio": 0.60,
            "online_ratio": 0.35,
            "avg_transaction_amount": 72,
            "utilization_ratio": 0.40,
            "payment_delay_score": 0.08,
            "support_sentiment_score": 0.88,
            "campaign_engagement_score": 0.65,
            "account_age_months": 42,
            "balance_to_spending_ratio": 2.3,
            "inactive_months_count": 0
        }

        narrative = NarrativeEngine.generate_narrative(
            customer_id="customer_shifter_elena",
            features=features,
            churn_probability=0.20,
            shap_values=None
        )

        # Assertions
        assert narrative["summary"] == "HEALTHY"
        assert narrative["summary_icon"] == "✅"
        assert len(narrative["key_findings"]) == 4
        assert any("positive" in finding.lower() or "growth" in finding.lower() or "growth" in finding.lower() for finding in narrative["key_findings"])
        assert narrative["confidence_score"] > 0.80

    def test_anomaly_customer_narrative(self):
        """Test ANOMALY_Mark scenario: Risky behavior pattern."""
        features = {
            "churn_probability": 0.72,
            "dormancy_days": 3,
            "trend_slope": 5,
            "spending_volatility": 2.1,
            "category_entropy": 3.1,
            "transaction_count_trend": 15,
            "pos_ratio": 0.20,
            "online_ratio": 0.75,
            "avg_transaction_amount": 320,
            "utilization_ratio": 1.15,
            "payment_delay_score": 0.65,
            "support_sentiment_score": 0.20,
            "campaign_engagement_score": 0.10,
            "account_age_months": 8,
            "balance_to_spending_ratio": 1.2,
            "inactive_months_count": 1
        }

        narrative = NarrativeEngine.generate_narrative(
            customer_id="customer_anomaly_mark",
            features=features,
            churn_probability=0.72,
            shap_values=None
        )

        # Assertions
        assert narrative["summary"] in ["CRITICAL", "WARNING"]  # 72% churn is high risk
        assert narrative["summary_icon"] in ["🔴", "⚠️"]
        assert len(narrative["key_findings"]) == 4
        assert any("volatility" in finding.lower() or "unusual" in finding.lower() or "high" in finding.lower() for finding in narrative["key_findings"])
        assert narrative["confidence_score"] > 0.75

    def test_narrative_structure(self):
        """Test that all narratives have correct structure."""
        features = {
            "churn_probability": 0.50,
            "dormancy_days": 50,
            "trend_slope": 0,
            "spending_volatility": 0.5,
            "category_entropy": 2.5,
            "transaction_count_trend": 0,
            "pos_ratio": 0.50,
            "online_ratio": 0.50,
            "avg_transaction_amount": 100,
            "utilization_ratio": 0.50,
            "payment_delay_score": 0.25,
            "support_sentiment_score": 0.70,
            "campaign_engagement_score": 0.50,
            "account_age_months": 20,
            "balance_to_spending_ratio": 3.0,
            "inactive_months_count": 1
        }

        narrative = NarrativeEngine.generate_narrative(
            customer_id="customer_test",
            features=features,
            churn_probability=0.50
        )

        # Check structure
        assert "summary" in narrative
        assert "summary_icon" in narrative
        assert "risk_category" in narrative
        assert "key_findings" in narrative
        assert "business_advice" in narrative
        assert "technical_evidence" in narrative
        assert "generated_at" in narrative
        assert "confidence_score" in narrative

        # Type checks
        assert isinstance(narrative["summary"], str)
        assert isinstance(narrative["key_findings"], list)
        assert isinstance(narrative["business_advice"], str)
        assert isinstance(narrative["technical_evidence"], dict)
        assert isinstance(narrative["confidence_score"], float)

        # Content validation
        assert narrative["summary"] in ["HEALTHY", "MEDIUM", "WARNING", "CRITICAL"]
        assert len(narrative["key_findings"]) >= 3
        assert len(narrative["business_advice"]) > 50
        assert narrative["confidence_score"] >= 0.0 and narrative["confidence_score"] <= 1.0

    def test_technical_evidence_completeness(self):
        """Test that technical evidence includes all key metrics."""
        features = {
            "churn_probability": 0.60,
            "dormancy_days": 100,
            "trend_slope": -150,
            "spending_volatility": 0.8,
            "category_entropy": 2.0,
            "transaction_count_trend": -10,
            "pos_ratio": 0.50,
            "online_ratio": 0.50,
            "avg_transaction_amount": 100,
            "utilization_ratio": 0.70,
            "payment_delay_score": 0.50,
            "support_sentiment_score": 0.50,
            "campaign_engagement_score": 0.40,
            "account_age_months": 30,
            "balance_to_spending_ratio": 4.5,
            "inactive_months_count": 2
        }

        shap_values = {
            "dormancy_days": 0.25,
            "trend_slope": -0.15,
            "utilization_ratio": 0.10
        }

        narrative = NarrativeEngine.generate_narrative(
            customer_id="customer_evidence_test",
            features=features,
            churn_probability=0.60,
            shap_values=shap_values
        )

        evidence = narrative["technical_evidence"]

        # Check key fields
        assert "churn_probability" in evidence
        assert "key_metrics" in evidence
        assert "dormancy_days" in evidence["key_metrics"]
        assert "trend_slope" in evidence["key_metrics"]
        assert "utilization_ratio" in evidence["key_metrics"]
        assert evidence["churn_probability"] == 0.60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
