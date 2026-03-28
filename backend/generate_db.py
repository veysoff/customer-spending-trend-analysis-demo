#!/usr/bin/env python3
"""
Script to initialize database with all 22 personas.
Run this after deleting the old spending.db file.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.init_db import initialize_database
from app.config import DATABASE_PATH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("DATABASE INITIALIZATION WITH 22 PERSONAS")
    logger.info("=" * 80)
    logger.info(f"Database path: {DATABASE_PATH}")
    logger.info(f"Database file exists: {DATABASE_PATH.exists()}")

    try:
        logger.info("Starting database initialization...")
        initialize_database()

        if DATABASE_PATH.exists():
            size_mb = DATABASE_PATH.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Database created successfully!")
            logger.info(f"   File size: {size_mb:.2f} MB")
            logger.info(f"   Location: {DATABASE_PATH}")
            logger.info("=" * 80)
            logger.info("PHASE 4B COMPLETE: Database ready with 22 personas")
            logger.info("=" * 80)
        else:
            logger.error("❌ Database file not created!")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        sys.exit(1)
