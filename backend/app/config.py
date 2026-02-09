import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = DATA_DIR / "models"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/transactions.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ML Configuration
PROPHET_YEARLY_SEASONALITY = True
PROPHET_WEEKLY_SEASONALITY = True
PROPHET_DAILY_SEASONALITY = False
PROPHET_INTERVAL_WIDTH = 0.80
PROPHET_GROWTH = "linear"

ISOLATION_FOREST_CONTAMINATION = 0.10
ISOLATION_FOREST_N_ESTIMATORS = 100
ISOLATION_FOREST_RANDOM_STATE = 42

# Data Generation Configuration
N_CUSTOMERS = 1000
N_MONTHS = 12
BASE_MONTHLY_SPENDING = 5000.0
SPENDING_VARIANCE = 500.0
