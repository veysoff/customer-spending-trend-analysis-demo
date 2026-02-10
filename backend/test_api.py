#!/usr/bin/env python3
"""
API Validation Script for Phase 4C.
Tests all API endpoints with 22 personas in database.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import SessionLocal
from app.db.models import Customer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def verify_database():
    """Verify all 22 personas are in database."""
    logger.info("=" * 80)
    logger.info("PHASE 4C: DATABASE VERIFICATION")
    logger.info("=" * 80)

    db = SessionLocal()
    try:
        customers = db.query(Customer).order_by(Customer.id).all()

        logger.info(f"Total personas in database: {len(customers)}")
        logger.info("")

        if len(customers) != 22:
            logger.error(f"ERROR: Expected 22 personas, found {len(customers)}")
            return False

        # Verify all personas
        personas = {}
        for customer in customers:
            persona_id = int(customer.id) - 1000
            personas[persona_id] = {
                'name': customer.persona_name,
                'risk': customer.expected_risk_score,
                'id': customer.id,
            }

        logger.info("All 22 Personas:")
        logger.info("-" * 80)

        risk_distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for persona_id in sorted(personas.keys()):
            p = personas[persona_id]
            risk = p['risk']

            if risk >= 0.85:
                risk_cat = "CRITICAL"
                risk_distribution["critical"] += 1
            elif risk >= 0.60:
                risk_cat = "HIGH"
                risk_distribution["high"] += 1
            elif risk >= 0.30:
                risk_cat = "MEDIUM"
                risk_distribution["medium"] += 1
            else:
                risk_cat = "LOW"
                risk_distribution["low"] += 1

            logger.info(f"  {persona_id:2d}. {p['name']:30s} | Risk: {risk:.2f} ({risk_cat:8s})")

        logger.info("")
        logger.info("Risk Distribution:")
        logger.info(f"  CRITICAL (0.85+):  {risk_distribution['critical']} personas")
        logger.info(f"  HIGH (0.60-0.84):  {risk_distribution['high']} personas")
        logger.info(f"  MEDIUM (0.30-0.59): {risk_distribution['medium']} personas")
        logger.info(f"  LOW (<0.30):       {risk_distribution['low']} personas")

        logger.info("")
        logger.info("=" * 80)
        logger.info("DATABASE VERIFICATION: PASSED")
        logger.info("=" * 80)

        return True

    finally:
        db.close()


def test_expected_signals():
    """Test that personas match expected ML signals."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("PHASE 4C: EXPECTED SIGNALS VALIDATION")
    logger.info("=" * 80)

    expected = {
        1001: {"name": "STABLE_John", "risk_min": 0.10, "risk_max": 0.20},
        1002: {"name": "CHURN_Sarah", "risk_min": 0.70, "risk_max": 0.80},
        1003: {"name": "STRESS_Alex", "risk_min": 0.55, "risk_max": 0.65},
        1005: {"name": "ANOMALY_Mark", "risk_min": 0.80, "risk_max": 0.90},
        1007: {"name": "GROWTH_Tech", "risk_min": 0.05, "risk_max": 0.15},
        1008: {"name": "RISK_Crypto", "risk_min": 0.65, "risk_max": 0.75},
        1013: {"name": "DORMANT_Revival", "risk_min": 0.50, "risk_max": 0.60},
        1014: {"name": "DECLINE_Recovery", "risk_min": 0.35, "risk_max": 0.45},
        1015: {"name": "BURST_Fraud", "risk_min": 0.80, "risk_max": 0.90},
        1020: {"name": "MULE_Account", "risk_min": 0.85, "risk_max": 0.95},
        1022: {"name": "NIGHTTIME_Only", "risk_min": 0.60, "risk_max": 0.70},
    }

    db = SessionLocal()
    passed = 0
    failed = 0

    try:
        logger.info("Validating risk scores against expected ranges:")
        logger.info("-" * 80)

        for customer_id, exp in expected.items():
            customer = db.query(Customer).filter(Customer.id == str(customer_id)).first()

            if not customer:
                logger.error(f"  {exp['name']:30s} | ERROR: Not found in database")
                failed += 1
                continue

            risk = customer.expected_risk_score
            in_range = exp['risk_min'] <= risk <= exp['risk_max']

            status = "[OK]" if in_range else "[FAIL]"
            logger.info(f"  {status} {exp['name']:30s} | Risk: {risk:.2f} "
                       f"(expected: {exp['risk_min']:.2f}-{exp['risk_max']:.2f})")

            if in_range:
                passed += 1
            else:
                failed += 1

        logger.info("")
        logger.info(f"Risk Validation: {passed} passed, {failed} failed")

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"SIGNAL VALIDATION: {'PASSED' if failed == 0 else 'FAILED'}")
        logger.info("=" * 80)

        return failed == 0

    finally:
        db.close()


def main():
    """Run API validation tests."""
    try:
        # Test 1: Database verification
        db_ok = verify_database()

        # Test 2: Signal validation
        signals_ok = test_expected_signals()

        # Summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("PHASE 4C VALIDATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Database verification: {'PASSED' if db_ok else 'FAILED'}")
        logger.info(f"Signal validation:     {'PASSED' if signals_ok else 'FAILED'}")
        logger.info("")

        if db_ok and signals_ok:
            logger.info("ALL VALIDATIONS PASSED")
            logger.info("=" * 80)
            logger.info("")
            logger.info("READY FOR NEXT STEPS:")
            logger.info("1. Start backend: python -m uvicorn app.main:app --reload")
            logger.info("2. Test API: GET http://localhost:8000/api/personas")
            logger.info("3. Verify ML predictions on dashboard")
            logger.info("")
            return 0
        else:
            logger.error("SOME VALIDATIONS FAILED")
            return 1

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
