"""Database initialization with idempotent data generation."""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal, create_tables
from .models import Customer, Transaction
from ..ml.persona_registry import PERSONA_REGISTRY

logger = logging.getLogger(__name__)


def initialize_database():
    """Create tables and seed personas if empty (idempotent).

    Safe to call multiple times - checks if data exists before generating.
    """
    # Create all tables
    logger.info("Creating database tables...")
    create_tables()
    logger.info("Database tables created")

    # Check if personas already exist
    db = SessionLocal()
    try:
        persona_count = db.query(Customer).filter(Customer.persona_id != None).count()

        if persona_count == 0:
            logger.info("No personas found. Generating personas...")
            _generate_personas(db)
            logger.info("Persona generation complete")
        else:
            logger.info(f"Database has {persona_count} personas. Skipping generation.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        db.close()


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
