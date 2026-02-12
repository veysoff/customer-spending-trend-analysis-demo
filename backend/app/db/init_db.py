"""Database initialization with idempotent data generation."""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal, create_tables
from .models import Customer, Transaction
from ..ml.persona_registry import PERSONA_REGISTRY
from ..ml.data_generator import SyntheticDataGenerator
from ..ml.demo_personas import DEMO_PERSONAS_REGISTRY
from .. import config

logger = logging.getLogger(__name__)


def initialize_database():
    """Create tables and seed demo personas + synthetic data if empty (idempotent).

    Safe to call multiple times - checks if data exists before generating.

    Generation order:
    1. Generate 40 named demo personas (with diverse patterns & edge cases)
    2. Generate remaining background customers (config.N_CUSTOMERS - 40)
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
            logger.info("No customers found. Generating demo personas and synthetic data...")

            # 1. Generate 40 demo personas first (named, with specific patterns)
            logger.info("Step 1: Generating 40 named demo personas...")
            _generate_demo_personas(db)

            # 2. Generate background customers
            logger.info("Step 2: Generating background customers...")
            _generate_synthetic_data_with_churn(db, background_only=True)

            logger.info("Data generation complete")
        else:
            logger.info(f"Database has {total_customers} customers. Skipping generation.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        db.close()


def _generate_demo_personas(db: Session):
    """Generate 40 named demo personas with diverse patterns.

    Each persona demonstrates a different customer behavior:
    - 8 Stable customers (low risk, consistent)
    - 8 At-Risk customers (warning signs)
    - 8 Anomaly customers (unusual patterns)
    - 6 Growth customers (positive trends)
    - 10 Advanced edge cases (travelers, crypto, gamblers, business owners, etc.)
    """
    logger.info(f"Generating {len(DEMO_PERSONAS_REGISTRY)} demo personas...")

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)

    total_transactions = 0
    total_personas = 0

    for persona_id, PersonaClass in DEMO_PERSONAS_REGISTRY.items():
        # Create deterministic customer IDs for personas
        customer_id = f"persona_{PersonaClass.NAME.lower().replace('_', '_')}"

        logger.info(f"Generating {PersonaClass.NAME} (persona_id: {persona_id})...")

        try:
            # Generate persona instance
            persona = PersonaClass(customer_id=customer_id, seed=1000 + persona_id)

            # Generate transactions
            transactions = persona.generate_transactions(start_date, end_date)
            total_transactions += len(transactions)

            # is_churned: 1 for at_risk tier (high-risk personas) and high-risk anomalies
            # Using EXPECTED_RISK_SCORE >= 0.5 as the churn label threshold
            is_churned = 1 if PersonaClass.EXPECTED_RISK_SCORE >= 0.5 else 0

            # Create customer record
            customer = Customer(
                id=customer_id,
                pattern=f"persona_{PersonaClass.TIER}",
                persona_id=persona_id,
                persona_name=PersonaClass.NAME,
                persona_tier=PersonaClass.TIER,
                persona_seed=1000 + persona_id,
                narrative=PersonaClass.NARRATIVE,
                expected_risk_score=PersonaClass.EXPECTED_RISK_SCORE,
                is_churned=is_churned,
                generation_timestamp=datetime.utcnow(),
                first_transaction_date=min(t['date'] for t in transactions) if transactions else None,
                last_transaction_date=max(t['date'] for t in transactions) if transactions else None,
                created_at=datetime.utcnow(),
            )

            db.add(customer)
            db.flush()

            # Insert transactions in batches
            if transactions:
                batch_size = 500
                tx_counter = 0
                for i in range(0, len(transactions), batch_size):
                    batch = transactions[i : i + batch_size]
                    # Add transaction IDs (required for primary key)
                    for tx in batch:
                        tx["id"] = f"{customer_id}_{tx_counter}"
                        tx_counter += 1
                    db.bulk_insert_mappings(Transaction, batch)
                    db.commit()

                logger.info(f"  ✅ {PersonaClass.NAME}: {len(transactions)} transactions")
            else:
                db.commit()
                logger.warning(f"  ⚠️  {PersonaClass.NAME}: No transactions generated")

            total_personas += 1

        except Exception as e:
            logger.error(f"Error generating persona {PersonaClass.NAME}: {e}")
            db.rollback()
            raise

    logger.info(
        f"✅ Generated {total_personas} demo personas with {total_transactions} total transactions"
    )


def _generate_synthetic_data_with_churn(db: Session, background_only: bool = False):
    """Generate synthetic customers with churn patterns and credit metrics.

    Uses config values: N_CUSTOMERS, N_MONTHS (default: 1000, 12)

    Args:
        db: Database session
        background_only: If True, generates (N_CUSTOMERS - 30) background customers.
                        If False, generates all N_CUSTOMERS.

    Distribution:
    - 40% stable (no churn)
    - 30% churning (churned, high risk)
    - 20% at_risk (no churn but warning signs)
    - 10% churned (long-term inactive)
    """
    n_to_generate = config.N_CUSTOMERS
    if background_only:
        # Reserve 30 slots for demo personas
        n_to_generate = max(0, config.N_CUSTOMERS - 30)

    if n_to_generate <= 0:
        logger.info("No background customers to generate (all slots reserved for demo personas)")
        return

    logger.info(
        f"Generating {n_to_generate} background synthetic customers ({config.N_MONTHS} months) with churn patterns..."
    )

    # Generate synthetic data using calculated values
    generator = SyntheticDataGenerator(n_customers=n_to_generate, n_months=config.N_MONTHS, seed=42)

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
