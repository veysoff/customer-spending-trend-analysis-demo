"""Database initialization with idempotent data generation."""

import logging
from sqlalchemy.orm import Session
from .database import SessionLocal, create_tables
from .models import Customer, Transaction
from ..ml.data_generator import SyntheticDataGenerator

logger = logging.getLogger(__name__)


def initialize_database():
    """Create tables and seed data if empty (idempotent).

    This function is safe to call multiple times:
    - First run: Creates tables, generates 1000 customers + 335k transactions
    - Subsequent runs: Checks if data exists, skips generation
    """
    # Create all tables
    logger.info("Creating database tables...")
    create_tables()
    logger.info("Database tables created")

    # Check if data already exists
    db = SessionLocal()
    try:
        customer_count = db.query(Customer).count()

        if customer_count == 0:
            logger.info("Database empty. Generating synthetic data...")
            _generate_synthetic_data(db)
            logger.info("Data generation complete")
        else:
            logger.info(f"Database has {customer_count} customers. Skipping generation.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        db.close()


def _generate_synthetic_data(db: Session):
    """Generate and insert synthetic banking data into database.

    Args:
        db: SQLAlchemy session for database operations

    Process:
    1. Generate 1000 customers + ~336k transactions using SyntheticDataGenerator
    2. Extract unique customers and insert
    3. Batch insert transactions (1000 per batch) to avoid memory overflow
    """
    logger.info("Initializing SyntheticDataGenerator...")
    generator = SyntheticDataGenerator(n_customers=1000, n_months=12)

    logger.info("Generating synthetic data...")
    df = generator.generate()
    logger.info(f"Generated {len(df)} transactions for {df['customer_id'].nunique()} customers")

    # Step 1: Extract and insert unique customers
    logger.info("Inserting customers...")
    customers_df = df[["customer_id", "pattern"]].drop_duplicates()

    customers = []
    for _, row in customers_df.iterrows():
        customer_transactions = df[df["customer_id"] == row["customer_id"]]
        customer = Customer(
            id=row["customer_id"],
            pattern=row["pattern"],
            first_transaction_date=customer_transactions["date"].min(),
            last_transaction_date=customer_transactions["date"].max(),
        )
        customers.append(customer)

    db.bulk_save_objects(customers)
    db.commit()
    logger.info(f"Inserted {len(customers)} customers")

    # Step 2: Batch insert transactions
    logger.info("Inserting transactions (batched)...")
    batch_size = 1000
    transactions_batch = []

    for idx, (_, row) in enumerate(df.iterrows()):
        transaction_dict = {
            "id": row["transaction_id"],
            "customer_id": row["customer_id"],
            "date": row["date"],
            "amount": row["amount"],
            "mcc": row["mcc"],
            "mcc_category": row["mcc_category"],
            "channel": row["channel"],
            "merchant": row["merchant"],
            "country": row["country"],
            "time_of_day": row["time_of_day"],
        }
        transactions_batch.append(transaction_dict)

        # Bulk insert every N records
        if len(transactions_batch) >= batch_size:
            db.bulk_insert_mappings(Transaction, transactions_batch)
            db.commit()
            logger.debug(f"Inserted {idx + 1} transactions...")
            transactions_batch = []

    # Insert remaining transactions
    if transactions_batch:
        db.bulk_insert_mappings(Transaction, transactions_batch)
        db.commit()
        logger.debug(f"Inserted final batch of {len(transactions_batch)} transactions")

    logger.info(f"All {len(df)} transactions inserted successfully")
