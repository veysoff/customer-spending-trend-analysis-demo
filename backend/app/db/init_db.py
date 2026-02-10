"""Database initialization with idempotent data generation."""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal, create_tables
from .models import Customer, Transaction
from ..ml.persona_registry import PERSONA_REGISTRY
from ..ml.data_generator import SyntheticDataGenerator

logger = logging.getLogger(__name__)


def initialize_database():
    """Create tables and seed synthetic data + personas if empty (idempotent).

    Safe to call multiple times - checks if data exists before generating.
    """
    # Create all tables
    logger.info("Creating database tables...")
    create_tables()
    logger.info("Database tables created")

    # Check if data already exists
    db = SessionLocal()
    try:
        total_customers = db.query(Customer).count()

        if total_customers == 0:
            logger.info("No customers found. Generating synthetic data with churn patterns...")
            _generate_synthetic_data_with_churn(db)
            logger.info("Synthetic data generation complete")
        else:
            logger.info(f"Database has {total_customers} customers. Skipping generation.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        db.close()


def _generate_synthetic_data_with_churn(db: Session):
    """Generate 1000 synthetic customers with churn patterns and credit metrics.

    Distribution:
    - 400 stable (no churn)
    - 300 churning (churned, high risk)
    - 200 at_risk (no churn but warning signs)
    - 100 churned (long-term inactive)
    """
    logger.info("Generating 1000 synthetic customers with churn patterns...")

    # Generate synthetic data using updated SyntheticDataGenerator
    generator = SyntheticDataGenerator(n_customers=1000, n_months=12, seed=42)

    logger.info("Saving synthetic data to database...")
    generator.save_to_db(db)

    # Verify results
    total_customers = db.query(Customer).count()
    churned_count = db.query(Customer).filter(Customer.is_churned == 1).count()
    stable_count = db.query(Customer).filter(Customer.is_churned == 0).count()

    logger.info(f"✅ Total customers: {total_customers}")
    logger.info(f"✅ Churned customers: {churned_count} ({100*churned_count/total_customers:.1f}%)")
    logger.info(f"✅ Stable customers: {stable_count} ({100*stable_count/total_customers:.1f}%)")

    # Sample verification
    sample = db.query(Customer).first()
    if sample:
        logger.info(f"✅ Sample customer: {sample.id}")
        logger.info(f"   - Credit limit: {sample.credit_limit}")
        logger.info(f"   - Current balance: {sample.current_balance}")
        logger.info(f"   - Is churned: {sample.is_churned}")
        logger.info(f"   - Support tickets: {sample.support_tickets_count}")


def _generate_personas(db: Session):
    """Generate customer personas with transactions into database."""
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)

    logger.info(f"Generating {len(PERSONA_REGISTRY)} personas...")

    total_transactions = 0

    for persona_id, PersonaClass in PERSONA_REGISTRY.items():
        customer_id = 1000 + persona_id  # IDs 1001-1010
        customer_id_str = str(customer_id)

        logger.info(f"Generating {PersonaClass.NAME} (ID: {customer_id})...")

        generator = PersonaClass(customer_id, start_date, end_date)
        transactions = generator.generate_transactions()
        total_transactions += len(transactions)
        customer = Customer(
            id=customer_id_str,
            pattern=f"persona_{persona_id}",
            persona_id=persona_id,
            persona_name=PersonaClass.NAME,
            persona_seed=customer_id,
            narrative=PersonaClass.NARRATIVE,
            expected_risk_score=PersonaClass.EXPECTED_RISK_SCORE,
            generation_timestamp=datetime.utcnow(),
            first_transaction_date=min(t['date'] for t in transactions) if transactions else None,
            last_transaction_date=max(t['date'] for t in transactions) if transactions else None,
            created_at=datetime.utcnow(),
        )

        db.add(customer)
        db.flush()
        logger.info(f"  Inserting {len(transactions)} transactions...")
        batch_size = 1000

        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i+batch_size]
            db.bulk_insert_mappings(Transaction, batch)
            db.commit()
            logger.debug(f"    Batch {i//batch_size + 1}: {len(batch)} transactions inserted")

        logger.info(f"{PersonaClass.NAME}: {len(transactions)} transactions")

    logger.info(f"Generated {total_transactions} transactions")
