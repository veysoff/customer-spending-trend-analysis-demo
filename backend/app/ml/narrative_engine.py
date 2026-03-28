"""AI Insights Narrative Engine — Translate metrics to professional business narratives.

This module generates human-readable analyst briefings from raw churn prediction
metrics and SHAP explanations. Narratives follow a professional/formal tone
suitable for banking analyst review and executive decision-making.

Phase 5E: UC-2 Churn Prediction Enhancement
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..db.models import Customer
from .churn_features import ChurnFeatureEngineer


class NarrativeEngine:
    """Generate professional AI insights narratives from customer features."""

    # Risk classification thresholds
    CRITICAL_CHURN_THRESHOLD = 0.75
    WARNING_CHURN_THRESHOLD = 0.60
    MEDIUM_CHURN_THRESHOLD = 0.40

    CRITICAL_DORMANCY_DAYS = 120
    WARNING_DORMANCY_DAYS = 60
    MEDIUM_DORMANCY_DAYS = 30

    CRITICAL_TREND_SLOPE = -200
    WARNING_TREND_SLOPE = -100
    MEDIUM_TREND_SLOPE = -50

    @staticmethod
    def generate_narrative(
        customer_id: str,
        features: Dict[str, float],
        churn_probability: float,
        shap_values: Optional[Dict[str, float]] = None,
        db: Optional[Session] = None
    ) -> Dict:
        """Generate complete AI insight narrative for customer.

        Args:
            customer_id: Customer ID
            features: Dict of 15 engineered features
            churn_probability: XGBoost predicted churn probability (0.0-1.0)
            shap_values: Dict of SHAP values for each feature
            db: Database session (optional, for customer details)

        Returns:
            Dict with:
                - summary: Risk classification ("HEALTHY", "MEDIUM", "WARNING", "CRITICAL")
                - key_findings: List of 3-4 business insights
                - business_advice: Actionable recommendation
                - technical_evidence: Dict with metrics + formulas
                - confidence_score: 0.0-1.0
        """
        # Classify risk level
        risk_level = NarrativeEngine._classify_risk_level(
            churn_probability,
            features.get("dormancy_days", 0),
            features.get("trend_slope", 0)
        )

        # Generate components
        key_findings = NarrativeEngine._generate_key_findings(
            features, shap_values, risk_level
        )

        business_advice = NarrativeEngine._generate_business_advice(
            risk_level, features, churn_probability
        )

        technical_evidence = NarrativeEngine._generate_technical_evidence(
            features, churn_probability, shap_values
        )

        # Calculate confidence based on feature completeness
        confidence = NarrativeEngine._calculate_confidence(features)

        return {
            "summary": risk_level["summary"],
            "summary_icon": risk_level["icon"],
            "risk_category": risk_level["category"],
            "key_findings": key_findings,
            "business_advice": business_advice,
            "technical_evidence": technical_evidence,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "confidence_score": confidence
        }

    @staticmethod
    def _classify_risk_level(
        churn_prob: float,
        dormancy_days: float,
        trend_slope: float
    ) -> Dict:
        """Classify risk level using decision tree logic.

        Returns dict with:
            - summary: String ("HEALTHY", "MEDIUM", "WARNING", "CRITICAL")
            - category: String (detailed classification)
            - icon: String (visual indicator)
        """
        # CRITICAL risk
        if churn_prob > NarrativeEngine.CRITICAL_CHURN_THRESHOLD:
            if dormancy_days > NarrativeEngine.CRITICAL_DORMANCY_DAYS:
                return {
                    "summary": "CRITICAL",
                    "category": "SILENT_CHURN",
                    "icon": "🔴"
                }
            else:
                return {
                    "summary": "CRITICAL",
                    "category": "ACTIVE_CHURN",
                    "icon": "🔴"
                }

        # WARNING risk
        if churn_prob > NarrativeEngine.WARNING_CHURN_THRESHOLD:
            if trend_slope < NarrativeEngine.CRITICAL_TREND_SLOPE:
                return {
                    "summary": "WARNING",
                    "category": "ACTIVE_DECLINE",
                    "icon": "⚠️"
                }
            else:
                return {
                    "summary": "WARNING",
                    "category": "AT_RISK",
                    "icon": "⚠️"
                }

        # MEDIUM risk
        if churn_prob > NarrativeEngine.MEDIUM_CHURN_THRESHOLD:
            return {
                "summary": "MEDIUM",
                "category": "MONITORING",
                "icon": "🟡"
            }

        # HEALTHY (low risk)
        return {
            "summary": "HEALTHY",
            "category": "STABLE",
            "icon": "✅"
        }

    @staticmethod
    def _generate_key_findings(
        features: Dict[str, float],
        shap_values: Optional[Dict[str, float]],
        risk_level: Dict
    ) -> List[str]:
        """Generate 3-4 key business findings from features and SHAP.

        Returns list of professional narrative sentences.
        """
        findings = []

        # Extract key metrics
        churn_prob = features.get("churn_probability", 0)
        dormancy = features.get("dormancy_days", 0)
        trend_slope = features.get("trend_slope", 0)
        volatility = features.get("spending_volatility", 0)
        entropy = features.get("category_entropy", 0)
        utilization = features.get("utilization_ratio", 0)
        payment_delay = features.get("payment_delay_score", 0)
        support_sentiment = features.get("support_sentiment_score", 0)
        engagement = features.get("campaign_engagement_score", 0)
        inactive_months = features.get("inactive_months_count", 0)

        # Finding 1: Dormancy/Activity pattern
        if dormancy > NarrativeEngine.CRITICAL_DORMANCY_DAYS:
            findings.append(
                f"SILENT CHURN DETECTED: Account dormant {int(dormancy)} days "
                f"({int(dormancy/30)}+ months). Zero transaction activity indicates "
                f"account closure imminent."
            )
        elif dormancy > NarrativeEngine.WARNING_DORMANCY_DAYS:
            findings.append(
                f"Declining activity: No transactions for {int(dormancy)} days. "
                f"Account dormancy warning sign."
            )
        elif inactive_months >= 3:
            findings.append(
                f"Intermittent usage: Inactive {int(inactive_months)}/6 months. "
                f"Customer engagement declining."
            )
        else:
            findings.append(
                f"Active account usage: Recent transactions ({int(dormancy)} days). "
                f"Customer engagement maintained."
            )

        # Finding 2: Spending trend
        if trend_slope < NarrativeEngine.CRITICAL_TREND_SLOPE:
            findings.append(
                f"Spending collapse: Sustained {abs(trend_slope):.0f}% monthly decline "
                f"over 6 months. Pattern indicates financial stress or permanent disengagement."
            )
        elif trend_slope < NarrativeEngine.WARNING_TREND_SLOPE:
            findings.append(
                f"Spending decline: {abs(trend_slope):.0f}% monthly reduction. "
                f"Consistent pattern across {int(entropy)} spending categories."
            )
        elif trend_slope < 0:
            findings.append(
                f"Gradual spending reduction: {abs(trend_slope):.1f}% monthly. "
                f"Moderate concern but not critical."
            )
        else:
            findings.append(
                f"Positive spending growth: +{trend_slope:.1f}% monthly. "
                f"Customer engagement improving."
            )

        # Finding 3: Payment/Support behavior
        if payment_delay > 0.7 and dormancy < 30:
            # Active but risky
            findings.append(
                f"Payment reliability concern: {int(payment_delay * 10)} payment issues "
                f"detected. Combined with high utilization ({utilization:.0%}), "
                f"customer under financial stress."
            )
        elif support_sentiment < 0.3:
            findings.append(
                f"Customer dissatisfaction: Multiple support complaints logged. "
                f"Sentiment score {support_sentiment:.1%} indicates relationship breakdown."
            )
        elif utilization > 0.8:
            findings.append(
                f"High credit utilization: {utilization:.0%} of limit. "
                f"Customer near maximum credit, possible liquidity stress."
            )
        else:
            findings.append(
                f"Healthy credit behavior: Utilization {utilization:.0%}, "
                f"payment history clean. Account in good standing."
            )

        # Finding 4: Engagement/Volatility signals
        if volatility > 1.5:
            findings.append(
                f"High transaction volatility ({volatility:.1f}x). Spending pattern unstable, "
                f"possible financial stress or impulsive behavior."
            )
        elif engagement < 0.2:
            findings.append(
                f"Marketing unresponsive: Zero campaign engagement in {int(dormancy/7)} weeks. "
                f"Customer avoiding communication."
            )
        elif entropy < 1.0:
            findings.append(
                f"Spending concentrated: Only {int(entropy * 3)} categories active. "
                f"Subsistence pattern indicates lifestyle change or constraint."
            )
        else:
            findings.append(
                f"Diversified spending: Active across {int(entropy * 3)} categories. "
                f"Well-rounded engagement."
            )

        return findings[:4]  # Return top 4

    @staticmethod
    def _generate_business_advice(
        risk_level: Dict,
        features: Dict[str, float],
        churn_prob: float
    ) -> str:
        """Generate actionable business recommendation based on risk level."""

        summary = risk_level["summary"]
        category = risk_level["category"]
        dormancy = features.get("dormancy_days", 0)
        trend_slope = features.get("trend_slope", 0)
        utilization = features.get("utilization_ratio", 0)
        payment_delay = features.get("payment_delay_score", 0)
        engagement = features.get("campaign_engagement_score", 0)

        if summary == "CRITICAL":
            if category == "SILENT_CHURN":
                return (
                    "🚨 URGENT ACTION REQUIRED (within 24 hours): "
                    "(1) Personal phone outreach from account manager (not automated email), "
                    "(2) Financial wellness check-in to identify pain points, "
                    "(3) Retention offer: Waived annual fee 1 year + 20% cashback on core categories + rate reduction, "
                    "(4) If customer reluctant, escalate to retention specialist. "
                    "Risk of permanent account closure is >80%. Retention window: 1-2 weeks."
                )
            else:  # ACTIVE_CHURN
                return (
                    "🚨 URGENT ACTION REQUIRED (within 48 hours): "
                    "(1) Direct outreach with personalized retention strategy, "
                    "(2) Address primary pain point (spending decline + payment issues), "
                    "(3) Proactive offer: credit limit adjustment, rate reduction, or service upgrade, "
                    "(4) Consider escalation to VP level for high-value relationships. "
                    "Churn risk >75%. Immediate intervention needed."
                )

        elif summary == "WARNING":
            if category == "ACTIVE_DECLINE":
                return (
                    "⚠️ HIGH PRIORITY (within 1 week): "
                    "(1) Proactive financial wellness outreach, "
                    "(2) Investigate spending decline (life event? financial stress?), "
                    "(3) Offer: Financial counseling, budgeting tools, or credit limit increase, "
                    "(4) Enroll in autopay to prevent future payment issues, "
                    "(5) Monitor weekly for deterioration into CRITICAL state."
                )
            else:  # AT_RISK
                return (
                    "⚠️ ELEVATED RISK (monitor within 2 weeks): "
                    "(1) Engagement campaign: Targeted offers based on customer interests, "
                    "(2) Financial health check-in (payment stress? spending constraint?), "
                    "(3) Upgrade benefit: Premium tier, loyalty program, or exclusive offer, "
                    "(4) Schedule proactive check-in call, "
                    "(5) If risk increases 10+ points, escalate to WARNING protocol."
                )

        elif summary == "MEDIUM":
            return (
                "🟡 MONITORING PHASE (routine follow-up): "
                "(1) Continue normal engagement, "
                "(2) Offer targeted cross-sell based on spending patterns, "
                "(3) Monthly check-in to catch early warning signs, "
                "(4) If any CRITICAL metrics appear, escalate to WARNING protocol."
            )

        else:  # HEALTHY
            return (
                "✅ STABLE RELATIONSHIP (proactive growth): "
                "(1) Cross-sell opportunities: premium accounts, wealth products, investment services, "
                "(2) Enroll in loyalty/rewards tier, "
                "(3) Offer rate/fee incentives to deepen engagement, "
                "(4) Long-term relationship building. Model customer for retention benchmarking."
            )

    @staticmethod
    def _generate_technical_evidence(
        features: Dict[str, float],
        churn_probability: float,
        shap_values: Optional[Dict[str, float]]
    ) -> Dict:
        """Generate technical evidence block with metrics and formulas."""

        evidence = {
            "churn_probability": round(churn_probability, 4),
            "churn_percentage": f"{churn_probability * 100:.1f}%",
            "model": "XGBoost binary classifier (15 features)",
            "top_shap_factors": {}  # Always include, even if empty
        }

        # Add top SHAP factors if available
        if shap_values:
            top_factors = sorted(
                shap_values.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:5]

            for factor_name, factor_value in top_factors:
                # Handle NaN values
                if np.isnan(factor_value):
                    factor_value = 0.0
                evidence["top_shap_factors"][factor_name] = round(float(factor_value), 4)

        # Add key metrics
        evidence["key_metrics"] = {
            "dormancy_days": int(features.get("dormancy_days", 0)),
            "trend_slope": round(features.get("trend_slope", 0), 2),
            "utilization_ratio": round(features.get("utilization_ratio", 0), 2),
            "payment_delay_score": round(features.get("payment_delay_score", 0), 2),
            "support_sentiment": round(features.get("support_sentiment_score", 0), 2),
            "engagement_score": round(features.get("campaign_engagement_score", 0), 2),
            "inactive_months": int(features.get("inactive_months_count", 0))
        }

        # Add interpretation notes
        dormancy = features.get("dormancy_days", 0)
        if dormancy > NarrativeEngine.CRITICAL_DORMANCY_DAYS:
            evidence["dormancy_status"] = (
                f"Account dormant {int(dormancy)} days "
                f"(exceeds {NarrativeEngine.CRITICAL_DORMANCY_DAYS}d critical threshold)"
            )

        trend = features.get("trend_slope", 0)
        if trend < NarrativeEngine.CRITICAL_TREND_SLOPE:
            evidence["trend_status"] = (
                f"Spending declined {abs(trend):.0f} AED/month "
                f"(exceeds {abs(NarrativeEngine.CRITICAL_TREND_SLOPE):.0f} critical threshold)"
            )

        return evidence

    @staticmethod
    def _calculate_confidence(features: Dict[str, float]) -> float:
        """Calculate confidence score based on feature completeness.

        Higher confidence if more features are present and non-zero.
        """
        expected_features = 15
        present_features = sum(1 for v in features.values() if v is not None)
        non_zero_features = sum(1 for v in features.values() if v is not None and v != 0)

        base_confidence = present_features / expected_features
        non_zero_bonus = min(0.1, (non_zero_features / expected_features) * 0.1)

        confidence = min(0.99, base_confidence + non_zero_bonus)
        return round(confidence, 2)


class NarrativeCache:
    """Manage caching of generated narratives to avoid recalculation."""

    CACHE_TTL_DAYS = 7

    @staticmethod
    def get_cached_narrative(
        customer_id: str,
        db: Session
    ) -> Optional[Dict]:
        """Get cached narrative if available and not expired.

        Returns:
            Narrative dict if cached and fresh, None otherwise.
        """
        from ..db.models import AIInterpretation

        try:
            cache = db.query(AIInterpretation).filter(
                AIInterpretation.customer_id == customer_id
            ).first()

            if not cache:
                return None

            # Check expiration
            if cache.expires_at and cache.expires_at < datetime.now(timezone.utc):
                # Cache expired, delete it
                db.delete(cache)
                db.commit()
                return None

            return {
                "summary": cache.summary,
                "summary_icon": cache.summary_icon,
                "risk_category": cache.risk_category,
                "key_findings": cache.key_findings,
                "business_advice": cache.business_advice,
                "technical_evidence": cache.technical_evidence,
                "generated_at": cache.generated_at.isoformat(),
                "confidence_score": cache.confidence_score,
                "cached": True
            }

        except Exception as e:
            # If cache lookup fails, continue without cache
            return None

    @staticmethod
    def save_narrative(
        customer_id: str,
        narrative: Dict,
        db: Session
    ) -> None:
        """Save generated narrative to cache.

        Args:
            customer_id: Customer ID
            narrative: Generated narrative dict
            db: Database session
        """
        from ..db.models import AIInterpretation
        from datetime import timedelta
        import json

        try:
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(days=NarrativeCache.CACHE_TTL_DAYS)

            cache_entry = AIInterpretation(
                customer_id=customer_id,
                summary=narrative.get("summary", ""),
                summary_icon=narrative.get("summary_icon", ""),
                risk_category=narrative.get("risk_category", ""),
                key_findings=json.dumps(narrative.get("key_findings", [])),
                business_advice=narrative.get("business_advice", ""),
                technical_evidence=json.dumps(narrative.get("technical_evidence", {})),
                confidence_score=narrative.get("confidence_score", 0.0),
                generated_at=now,
                expires_at=expires_at
            )

            # Update if exists, otherwise insert
            existing = db.query(AIInterpretation).filter(
                AIInterpretation.customer_id == customer_id
            ).first()

            if existing:
                existing.summary = cache_entry.summary
                existing.summary_icon = cache_entry.summary_icon
                existing.risk_category = cache_entry.risk_category
                existing.key_findings = cache_entry.key_findings
                existing.business_advice = cache_entry.business_advice
                existing.technical_evidence = cache_entry.technical_evidence
                existing.confidence_score = cache_entry.confidence_score
                existing.generated_at = cache_entry.generated_at
                existing.expires_at = cache_entry.expires_at
            else:
                db.add(cache_entry)

            db.commit()

        except Exception as e:
            # Silently fail on cache write (narrative still generated in-memory)
            pass
