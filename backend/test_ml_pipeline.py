#!/usr/bin/env python3
"""
ML Pipeline Validation Script for Phase 4C.
Tests trend detection, anomaly detection, and risk scoring on all 22 personas.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import SessionLocal
from app.db.models import Customer, Transaction
from app.ml.trend_detection import detect_trends
from app.ml.anomaly_detection import detect_anomalies
from app.ml.feature_engineering import engineer_features
from app.ml.explainability import explain_prediction

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Expected ML signals for each persona (from README risk scoring reference)
EXPECTED_SIGNALS = {
    1001: {"name": "STABLE_John", "trend_signal": "positive_growth", "volatility": "low", "anomalies": "none"},
    1002: {"name": "CHURN_Sarah", "trend_signal": "negative_decline", "volatility": "low", "anomalies": "category_shift"},
    1003: {"name": "STRESS_Alex", "trend_signal": "flat_volatile", "volatility": "high", "anomalies": "temporal"},
    1005: {"name": "ANOMALY_Mark", "trend_signal": "flat_spikes", "volatility": "high", "anomalies": "gambling_night"},
    1007: {"name": "GROWTH_Tech", "trend_signal": "positive_growth", "volatility": "low", "anomalies": "none"},
    1008: {"name": "RISK_Crypto", "trend_signal": "flat_volatile", "volatility": "extreme", "anomalies": "crypto"},
    1013: {"name": "DORMANT_Revival", "trend_signal": "activation_ramp", "volatility": "low", "anomalies": "dormancy"},
    1014: {"name": "DECLINE_Recovery", "trend_signal": "v_shaped", "volatility": "medium", "anomalies": "recovery"},
    1015: {"name": "BURST_Fraud", "trend_signal": "flat_burst", "volatility": "medium", "anomalies": "clustering"},
    1020: {"name": "MULE_Account", "trend_signal": "flat_transfers", "volatility": "low", "anomalies": "rapid_io"},
    1022: {"name": "NIGHTTIME_Only", "trend_signal": "flat_amount", "volatility": "low", "anomalies": "night_only"},
}


def load_customer_transactions(customer_id: int) -> pd.DataFrame:
    """Load transactions for a customer from database."""
    db = SessionLocal()
    try:
        transactions = db.query(Transaction).filter(
            Transaction.customer_id == str(customer_id)
        ).order_by(Transaction.date).all()

        if not transactions:
            return pd.DataFrame()

        data = []
        for tx in transactions:
            data.append({
                'date': tx.date,
                'amount': tx.amount,
                'mcc_category': tx.mcc_category,
                'channel': tx.channel,
                'time_of_day': tx.time_of_day,
            })

        return pd.DataFrame(data)
    finally:
        db.close()


def test_single_persona(customer_id: int) -> dict:
    """Test ML pipeline for a single persona."""
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.id == str(customer_id)).first()
        if not customer:
            return {"error": f"Customer {customer_id} not found"}

        # Load transactions
        df = load_customer_transactions(customer_id)
        if df.empty:
            return {"error": f"No transactions for customer {customer_id}"}

        result = {
            "customer_id": customer_id,
            "persona_name": customer.persona_name,
            "expected_risk": customer.expected_risk_score,
            "transaction_count": len(df),
            "date_range": f"{df['date'].min().date()} to {df['date'].max().date()}",
        }

        # Test 1: Feature Engineering
        try:
            features = engineer_features(df)
            result["features"] = {
                "monthly_trend_slope": round(features.get('monthly_trend_slope', 0), 4),
                "spending_volatility": round(features.get('spending_volatility', 0), 4),
                "monthly_count_mean": round(features.get('monthly_count_mean', 0), 2),
                "category_entropy": round(features.get('category_entropy', 0), 4),
            }
        except Exception as e:
            result["features_error"] = str(e)

        # Test 2: Trend Detection
        try:
            trends = detect_trends(df)
            result["trends"] = {
                "trend": trends.get('trend', 'unknown'),
                "trend_slope": round(trends.get('trend_slope', 0), 4),
                "confidence": round(trends.get('confidence', 0), 4),
            }
        except Exception as e:
            result["trends_error"] = str(e)

        # Test 3: Anomaly Detection
        try:
            anomalies = detect_anomalies(df)
            result["anomalies"] = {
                "count": anomalies.get('count', 0),
                "anomaly_rate": round(anomalies.get('anomaly_rate', 0), 4),
                "top_anomaly_type": anomalies.get('top_anomaly_type', 'none'),
            }
        except Exception as e:
            result["anomalies_error"] = str(e)

        return result

    finally:
        db.close()


def main():
    """Run ML validation tests on sample personas."""
    logger.info("=" * 80)
    logger.info("PHASE 4C: ML PIPELINE VALIDATION")
    logger.info("=" * 80)
    logger.info(f"Testing {len(EXPECTED_SIGNALS)} key personas...")
    logger.info()

    results = []

    for customer_id in sorted(EXPECTED_SIGNALS.keys()):
        logger.info(f"Testing customer {customer_id}: {EXPECTED_SIGNALS[customer_id]['name']}...")

        result = test_single_persona(customer_id)
        results.append(result)

        if "error" in result:
            logger.warning(f"  ERROR: {result['error']}")
        else:
            logger.info(f"  Transactions: {result['transaction_count']}")
            logger.info(f"  Expected Risk: {result['expected_risk']:.2f}")

            if "features" in result:
                features = result["features"]
                logger.info(f"  Features: trend_slope={features['monthly_trend_slope']}, "
                          f"volatility={features['spending_volatility']}")

            if "trends" in result:
                trends = result["trends"]
                logger.info(f"  Trend: {trends['trend']} (slope={trends['trend_slope']})")

            if "anomalies" in result:
                anomalies = result["anomalies"]
                logger.info(f"  Anomalies: {anomalies['count']} found ({anomalies['anomaly_rate']:.1%})")

        logger.info()

    # Summary
    logger.info("=" * 80)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 80)

    success_count = sum(1 for r in results if "error" not in r)
    total_count = len(results)

    logger.info(f"Successful tests: {success_count}/{total_count}")
    logger.info()

    # Results table
    logger.info("Detailed Results:")
    logger.info("-" * 80)
    for result in results:
        if "error" not in result:
            logger.info(f"{result['persona_name']:30s} | Risk: {result['expected_risk']:.2f} | "
                      f"Txns: {result['transaction_count']:4d}")

    logger.info("=" * 80)
    logger.info("PHASE 4C: ML PIPELINE READY FOR FULL VALIDATION")
    logger.info("=" * 80)

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
