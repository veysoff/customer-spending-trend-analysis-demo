import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = DATA_DIR / "models"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Database configuration
DATABASE_PATH = DATA_DIR / "spending.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# CORS Configuration - restrict origins in production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")

# ML Configuration
PROPHET_YEARLY_SEASONALITY = True
PROPHET_WEEKLY_SEASONALITY = True
PROPHET_DAILY_SEASONALITY = False
PROPHET_INTERVAL_WIDTH = 0.80
PROPHET_GROWTH = "linear"

ISOLATION_FOREST_CONTAMINATION = 0.10
ISOLATION_FOREST_N_ESTIMATORS = 100
ISOLATION_FOREST_RANDOM_STATE = 42

# Data Generation Configuration (customize via environment variables)
# Demo mode: 40 named personas + 10 background = 50 total (fast for demonstrations)
# Default: Set to demo mode for better user experience in development
N_CUSTOMERS = int(os.getenv("N_CUSTOMERS", "50"))  # Default: demo mode (40 personas + 10 background)
N_MONTHS = int(os.getenv("N_MONTHS", "12"))        # Set via N_MONTHS env var
BASE_MONTHLY_SPENDING = 5000.0
SPENDING_VARIANCE = 500.0

# Configuration notes:
# Default (demo): N_CUSTOMERS=50 → 40 named personas + 10 background (complete demo suite)
# For testing: export N_CUSTOMERS=100 → 40 personas + 60 background
# For production: export N_CUSTOMERS=1000 → 40 personas + 960 background
# Larger dataset: export N_CUSTOMERS=5000+ as needed
# Personas include: stable, at-risk, anomalies, growth, travelers, crypto traders, gamblers, etc.
