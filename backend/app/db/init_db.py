"""Database initialization with idempotent data generation."""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from .database import SessionLocal, create_tables
from .models import Customer, Transaction
from ..ml.persona_registry import PERSONA_REGISTRY
from ..ml.data_generator import SyntheticDataGenerator
from ..ml.demo_personas import DEMO_PERSONAS_REGISTRY
from .. import config

logger = logging.getLogger(__name__)


def _backfill_transaction_dates(db: Session) -> int:
    """Backfill first/last transaction dates for customers where the field is NULL.

    Idempotent: only touches rows where first_transaction_date IS NULL.
    Returns the count of rows updated.
    """
    customers_missing = db.query(Customer).filter(
        Customer.first_transaction_date.is_(None)
    ).all()

    updated = 0
    for customer in customers_missing:
        result = db.query(
            func.min(Transaction.date), func.max(Transaction.date)
        ).filter(Transaction.customer_id == customer.id).one()

        if result[0] is not None:
            customer.first_transaction_date = result[0]
            customer.last_transaction_date = result[1]
            updated += 1

    if updated > 0:
        db.commit()
        logger.info(f"Backfilled first/last transaction dates for {updated} customers")

    return updated


def initialize_database():
    """Create tables and seed demo personas + synthetic data if empty (idempotent).

    Safe to call multiple times - checks if data exists before generating.

    First-run generation order (~10-12 minutes):
    1. Generate 40 named demo personas (with diverse patterns & edge cases)
    2. Generate TRAINING_N_CUSTOMERS (1000) background customers for ML training
    3. Train XGBoost churn model on full dataset
    4. Prune DB: keep 40 personas + DEMO_N_CUSTOMERS (10) best background customers

    Subsequent runs (<1 second):
    - DB already has customers → skip generation
    - Model .pkl already exists → skip training
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
            logger.info("No customers found. Starting full initialization...")
            logger.info(f"This will take ~10-12 minutes on first run.")

            # Step 1: Generate 40 demo personas first (named, with specific patterns)
            logger.info("Step 1/4: Generating 40 named demo personas...")
            _generate_demo_personas(db)

            # Step 2: Generate 1000 background customers for model training
            logger.info(f"Step 2/4: Generating {config.TRAINING_N_CUSTOMERS} background customers for training...")
            _generate_synthetic_data_with_churn(db, n_customers=config.TRAINING_N_CUSTOMERS)

            # Step 3: Train XGBoost churn model on all data
            logger.info("Step 3/4: Training XGBoost churn model...")
            _train_churn_model(db)

            # Step 4: Prune to demo set (keep 10 background customers)
            logger.info(f"Step 4/4: Pruning to demo set (keeping {config.DEMO_N_CUSTOMERS} background customers)...")
            _prune_to_demo_set(db, keep_count=config.DEMO_N_CUSTOMERS)

            _backfill_transaction_dates(db)
            final_count = db.query(Customer).count()
            logger.info(f"✅ Initialization complete. DB has {final_count} customers.")
        else:
            logger.info(f"Database has {total_customers} customers. Skipping generation.")
            # Ensure model exists even if DB was pre-populated
            _ensure_model_trained(db)
            # Backfill any NULL dates from older DB versions
            _backfill_transaction_dates(db)
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

    # Dynamic dates: last 24 months of data (always current, never stale)
    # 2 full years required for Prophet to detect yearly seasonality reliably (2 cycles)
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = (end_date - timedelta(days=730)).replace(day=1)

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
                generation_timestamp=datetime.now(timezone.utc),
                first_transaction_date=min(t['date'] for t in transactions) if transactions else None,
                last_transaction_date=max(t['date'] for t in transactions) if transactions else None,
                created_at=datetime.now(timezone.utc),
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


def _generate_synthetic_data_with_churn(db: Session, n_customers: int = None, background_only: bool = False):
    """Generate synthetic customers with churn patterns and credit metrics.

    Args:
        db: Database session
        n_customers: Number of customers to generate. Defaults to config.TRAINING_N_CUSTOMERS.
        background_only: Legacy parameter (ignored when n_customers is provided).

    Distribution:
    - 40% stable (no churn)
    - 30% churning (churned, high risk)
    - 20% at_risk (no churn but warning signs)
    - 10% churned (long-term inactive)
    """
    if n_customers is None:
        # Legacy fallback
        n_to_generate = config.N_CUSTOMERS
        if background_only:
            n_to_generate = max(0, config.N_CUSTOMERS - 30)
    else:
        n_to_generate = n_customers

    if n_to_generate <= 0:
        logger.info("No background customers to generate")
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


def _train_churn_model(db: Session):
    """Train XGBoost churn model on all current DB customers, save to disk.

    Skipped if model .pkl already exists (idempotent).
    """
    from ..ml.churn_model import ChurnModelTrainer

    model_path = config.MODELS_DIR / "churn_model.pkl"

    if model_path.exists():
        logger.info(f"Churn model already exists at {model_path} — skipping training")
        return

    logger.info("Training XGBoost churn model on full dataset...")
    trainer = ChurnModelTrainer(db)
    try:
        metrics = trainer.train_and_save(db)
        logger.info(
            f"✅ Model training complete: F1={metrics['f1']:.3f}, "
            f"AUC={metrics['roc_auc']:.3f}, Recall={metrics['recall']:.3f}"
        )
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        raise


def _ensure_model_trained(db: Session):
    """Ensure churn model exists; train if missing (for pre-populated DBs)."""
    model_path = config.MODELS_DIR / "churn_model.pkl"

    if not model_path.exists():
        logger.info("Churn model missing. Training on existing DB data...")
        _train_churn_model(db)
    else:
        logger.info("Churn model already exists. No training needed.")


def _prune_to_demo_set(db: Session, keep_count: int = 10):
    """Prune background customers to keep only the best demo-representative ones.

    Keeps all persona_* customers intact. Selects the best background customers
    per pattern to cover the full churn risk gradient.

    Selection strategy (deterministic, seed=42 in data generator):
    - 3 normal (stable, 0-10% risk)
    - 3 silent_churn (high risk, 90-99%)
    - 3 at_risk (medium risk, 40-80%)
    - 1 lifestyle_shift (churn type variety)

    Args:
        db: Database session
        keep_count: Total background customers to keep (default 10)
    """
    # Get all background customers (not personas)
    all_background = db.query(Customer).filter(
        ~Customer.id.like("persona_%")
    ).all()

    total_background = len(all_background)
    logger.info(f"Found {total_background} background customers. Selecting {keep_count} to keep...")

    # Allocate slots per pattern
    patterns_allocation = {
        "normal": 3,
        "silent_churn": 3,
        "at_risk": 3,
        "lifestyle_shift": 1,
    }

    # Adjust if keep_count differs from default 10
    if keep_count != 10:
        per_pattern = keep_count // 4
        remainder = keep_count % 4
        patterns_allocation = {
            "normal": per_pattern + (1 if remainder > 0 else 0),
            "silent_churn": per_pattern + (1 if remainder > 1 else 0),
            "at_risk": per_pattern + (1 if remainder > 2 else 0),
            "lifestyle_shift": per_pattern,
        }

    to_keep_ids = set()
    for pattern, count in patterns_allocation.items():
        matching = [c for c in all_background if c.pattern == pattern]
        selected = matching[:count]
        for c in selected:
            to_keep_ids.add(c.id)
        logger.info(f"  Pattern '{pattern}': found {len(matching)}, keeping {len(selected)}")

    # Delete all background customers not in keep list
    to_delete = [c for c in all_background if c.id not in to_keep_ids]
    deleted_customers = 0
    deleted_transactions = 0

    logger.info(f"Deleting {len(to_delete)} background customers and their transactions...")

    for customer in to_delete:
        tx_count = db.query(Transaction).filter(
            Transaction.customer_id == customer.id
        ).delete(synchronize_session=False)
        deleted_transactions += tx_count
        db.delete(customer)
        deleted_customers += 1

        if deleted_customers % 100 == 0:
            db.commit()
            logger.info(f"  Pruned {deleted_customers}/{len(to_delete)} customers...")

    db.commit()

    kept_count = len(to_keep_ids)
    persona_count = db.query(Customer).filter(Customer.id.like("persona_%")).count()
    logger.info(
        f"✅ Pruning complete: deleted {deleted_customers} customers "
        f"({deleted_transactions} transactions). "
        f"Kept {kept_count} background + {persona_count} personas = "
        f"{kept_count + persona_count} total."
    )


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
            generation_timestamp=datetime.now(timezone.utc),
            first_transaction_date=min(t['date'] for t in transactions) if transactions else None,
            last_transaction_date=max(t['date'] for t in transactions) if transactions else None,
            created_at=datetime.now(timezone.utc),
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
