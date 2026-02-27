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
PROPHET_INTERVAL_WIDTH = 0.95  # Wider confidence interval for better uncertainty quantification
PROPHET_GROWTH = "linear"

ISOLATION_FOREST_CONTAMINATION = 0.10
ISOLATION_FOREST_N_ESTIMATORS = 100
ISOLATION_FOREST_RANDOM_STATE = 42

# Data Generation Configuration (customize via environment variables)
N_CUSTOMERS = int(os.getenv("N_CUSTOMERS", "50"))  # Legacy fallback (use TRAINING_N_CUSTOMERS instead)
N_MONTHS = int(os.getenv("N_MONTHS", "12"))        # Set via N_MONTHS env var
BASE_MONTHLY_SPENDING = 5000.0
SPENDING_VARIANCE = 500.0

# Training vs Demo Configuration:
# On first startup: generate TRAINING_N_CUSTOMERS for model training, then prune to DEMO_N_CUSTOMERS
# TRAINING_N_CUSTOMERS=1000 → full dataset for quality ML model
# DEMO_N_CUSTOMERS=50 → background customers kept after pruning (+ all 55 personas = ~105 total)
TRAINING_N_CUSTOMERS: int = int(os.getenv("TRAINING_N_CUSTOMERS", "1000"))
DEMO_N_CUSTOMERS: int = int(os.getenv("DEMO_N_CUSTOMERS", "50"))
