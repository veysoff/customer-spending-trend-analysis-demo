# Customer Spending Trend Analysis — ML PoC

AI-powered banking analytics platform for detecting customer spending trends, behavioral anomalies, churn risk, and fraudulent transactions.

## 🎯 What It Does

- 📊 **Trend Forecasting** — Predicts customer spending patterns using Prophet (UC-1)
- 🚨 **Anomaly Detection** — Flags risky behavior using Isolation Forest (UC-1)
- 💼 **Churn Prediction** — Identifies at-risk customers using XGBoost (UC-2)
- 🔍 **Fraud Detection** — Detects suspicious transactions with ML pattern recognition (UC-3)
- 💡 **Explainability** — Shows why each prediction matters using SHAP (UC-2) and feature analysis (UC-3)
- 🎨 **Interactive Dashboard** — Visualize insights in real-time via Vue.js 3

## 🚀 Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose installed
- ~3 GB disk space for containers + database
- 2-3 minutes for first run (auto-generates data + trains models)

### Run with One Command

```bash
git clone <repo-url>
cd customer-spending-trend-analysis-demo
docker-compose up --build
```

That's it! The application will **automatically**:

1. ✅ Build backend & frontend containers
2. ✅ Create SQLite database schema with fraud detection columns (`backend/data/spending.db`)
3. ✅ Generate 1000 customers with 335k+ transactions (22 named personas + synthetic patterns)
4. ✅ Inject fraud patterns into ~5% of background customers for testing
5. ✅ **Cache ML models ready for training** (Prophet, Isolation Forest, XGBoost, Fraud Detector)
6. ✅ Start API on `http://localhost:8000`
7. ✅ Start Dashboard on `http://localhost:3000`

**First run takes 2-3 minutes** (generation + indexing). Subsequent restarts take ~10 seconds (models load from cache).

**Important**: Before using churn or fraud predictions, train the models:
- **Churn**: `POST /api/ml/train-churn-model` (via API or dashboard)
- **Fraud**: `POST /api/ml/train-fraud-model` (via API or dashboard)

### Access the Application

```
Dashboard:    http://localhost:3000
API Docs:     http://localhost:8000/docs
Database:     backend/data/spending.db (SQLite file)
```

---

## 🛑 Troubleshooting

### Container won't start / database errors

```bash
# Reset everything to fresh state
docker-compose down -v
rm -rf backend/data/spending.db
docker-compose up --build
```

### Check logs

```bash
# Backend logs
docker-compose logs -f backend

# Frontend logs
docker-compose logs -f frontend

# All logs
docker-compose logs -f
```

### Why does first startup take 2-3 minutes?

**What happens automatically on first run:**

1. **Database Generation** (~80 seconds)
   - 1000 total customers (22 named personas + 978 synthetic background)
   - 335,802 transactions across all customers
   - Fraud patterns injected into ~50 customers (~5%) for realistic testing
   - SQLite with indexed queries

2. **Fraud Pattern Injection** (~20 seconds)
   - Geo jumps (unusual country changes)
   - Card testing (small amounts followed by large purchases)
   - Night clusters (transactions in unusual hours)
   - Merchant drift (category pattern changes)

3. **Database Indexing & Setup** (~30 seconds)
   - Customer lookups optimized
   - Transaction queries indexed
   - Fraud columns added idempotently

**Subsequent restarts**: ~10 seconds
- Database already exists → skip generation
- Models load from cache → instant
- API starts immediately

**Note**: Churn and Fraud models must be trained manually via API (see "Training Models" section below)

---

## 🏗️ Architecture

```
Vue.js Dashboard (http://localhost:3000)
        ↓
FastAPI Backend (http://localhost:8000)
        ↓
SQLite Database + ML Pipeline
```

**Automatic startup sequence:**

```
1. Container starts
     ↓
2. Check if database exists
     ├─ YES → Load database + models (10 seconds)
     └─ NO → Go to step 3
     ↓
3. Generate 1000 customers with 335k+ transactions
     ├─ 22 named demo personas
     ├─ 978 synthetic background customers
     └─ ~5% have injected fraud patterns
     ↓
4. Add fraud detection columns & indexes
     ↓
5. Load ML models (ready for training)
     ├─ Prophet: Available per-customer
     ├─ Isolation Forest (anomalies): Available per-customer
     ├─ XGBoost: Ready to train via API
     └─ Fraud Detector (IF + rules): Ready to train via API
     ↓
6. API ready ✅ (takes 2-3 minutes total)
     ↓
7. Train models via POST endpoints (optional)
     ├─ POST /api/ml/train-churn-model
     └─ POST /api/ml/train-fraud-model
```

**Models trained on demand:**
- Models are saved to `backend/data/models/*.pkl` files
- On restart, cached models load in <1 second
- Training is required before using predictions (graceful fallback to rule-based scoring if not trained)

---

## 📊 What Gets Generated Automatically

### Synthetic Customer Data

- **1000 total customers** (22 named personas + 978 synthetic background)
- **335,802 transactions** across all customers (12 months history)
- **~5% fraud patterns** injected into background customers
- **Stored in SQLite** (`backend/data/spending.db`, ~10-15 MB)
- **Deterministic** — Same data on each run (seed-based generation)

### Example Demo Personas (Named)

- `persona_john_stable` — Normal spending, low risk ✅
- `persona_sarah_churn` — Declining spending, high churn risk 🔴
- `persona_mark_anomaly` — Risky patterns (gambling, night transactions) ⚠️
- `persona_tech_growth` — Consistent growth, stable ✅
- `persona_julia_geographicanomaly` — Frequent country changes, fraud test 🔴
- ... 17 more personas with specific patterns

### ML Models (Load-on-demand)

All models are **available for training** and cached after first training:

- **Prophet** — Trend forecasting (learns spending patterns per customer)
- **Isolation Forest (UC-1)** — Per-customer anomaly detection on spending
- **Isolation Forest (UC-3)** — Global fraud detection on transactions (200 estimators, 5% contamination)
- **XGBoost** — Churn prediction classifier (15 features, binary classification)
- **Rule-based Engine** — Fraud flags (geo_risk, card_testing, structuring, night_activity, merchant_drift, channel_anomaly, amount_spike, high_velocity)
- **SHAP** — Feature importance explanations (UC-2 churn, custom weights for UC-1)

Models are pickled to `backend/data/models/` after training and load in <1 second on subsequent restarts.

---

## 💻 Local Development (Without Docker)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

API available at: `http://localhost:8000/docs`

Database auto-initializes on first startup.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev  # Vite dev server on localhost:5173
```

### Connect Frontend to Backend

Add to `frontend/.env.local`:
```
VITE_API_URL=http://localhost:8000
```

---

## 📁 Project Structure

```
.
├── backend/                              # FastAPI application
│   ├── app/
│   │   ├── main.py                      # REST API endpoints (4 sections: core, UC-1, UC-2, UC-3)
│   │   ├── config.py                    # Configuration & settings
│   │   ├── models.py                    # Pydantic response schemas
│   │   ├── db/                          # Database layer
│   │   │   ├── models.py                # SQLAlchemy ORM (Customer, Transaction, RiskProfile)
│   │   │   ├── database.py              # Engine & session factory
│   │   │   ├── init_db.py               # Auto-initialization + fraud column migration
│   │   │   └── repositories.py          # CustomerRepository, TransactionRepository
│   │   └── ml/                          # Machine learning
│   │       ├── data_generator.py        # Synthetic data generation (1000 customers)
│   │       ├── feature_engineering.py   # UC-1 trend features (15 features)
│   │       ├── trend_detection.py       # Prophet integration
│   │       ├── anomaly_detection.py     # UC-1 Isolation Forest
│   │       ├── fraud_features.py        # UC-3 fraud features (8 features)
│   │       ├── fraud_model.py           # UC-3 FraudDetector (IF + rule-based)
│   │       ├── churn_features.py        # UC-2 churn features (15 features)
│   │       ├── churn_model.py           # UC-2 XGBoost model
│   │       ├── explainability.py        # SHAP integrations
│   │       └── narrative_engine.py      # AI insights text generation
│   ├── data/                            # Generated database & model artifacts
│   │   ├── spending.db                  # SQLite (auto-generated, ~10-15 MB)
│   │   └── models/                      # Pickled models (.pkl)
│   ├── tests/                           # Unit & integration tests
│   │   └── test_fraud_detection.py      # 22 tests for UC-3
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                            # Vue.js 3 dashboard
│   ├── src/
│   │   ├── components/                  # Vue components
│   │   │   ├── Dashboard.vue            # UC-1 customer profile
│   │   │   ├── TrendChart.vue           # UC-1 Prophet forecast
│   │   │   ├── AnomalyAlert.vue         # UC-1 anomalies
│   │   │   ├── ChurnPredictionCard.vue  # UC-2 risk gauge
│   │   │   ├── FeatureImportanceChart.vue # UC-2 SHAP explanations
│   │   │   ├── HighRiskTable.vue        # UC-2 high-risk customers
│   │   │   ├── FraudSignalsTable.vue    # UC-3 fraud signals (new)
│   │   │   ├── FraudTransactionDetail.vue # UC-3 detail modal (new)
│   │   │   ├── AIInsightsPanel.vue      # AI narrative
│   │   │   └── ErrorBoundary.vue        # Error handling
│   │   ├── stores/                      # Pinia state management
│   │   │   └── customer.js              # Global customer state + fraud signals
│   │   ├── services/                    # API client
│   │   │   └── api.js                   # Axios wrapper (all UC endpoints)
│   │   └── App.vue                      # Root: tab navigation
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml                   # Container orchestration
├── .gitignore                           # Excludes .claude/, docs/, backend/data/
├── README.md                            # This file
└── CHANGELOG.md                         # Version history
```

---

## 🔌 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check + model status |
| `/api/customers/{id}` | GET | Customer profile with risk score |
| `/api/customers` | GET | List all customers (1000 total) |
| `/api/personas` | GET | List demo personas (22 named) |

### UC-1: Spending Trends & Anomalies

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/customers/{id}/trends` | GET | Spending forecast with Prophet predictions |
| `/api/customers/{id}/anomalies` | GET | Detected anomalies with Isolation Forest |

### UC-2: Churn Prediction

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/customers/{id}/churn-prediction` | GET | Churn risk score + SHAP explanations |
| `/api/customers/risk/high` | GET | List high-risk customers (churn) |
| `/api/ml/train-churn-model` | POST | Train/retrain XGBoost churn model |
| `/api/ml/predict-all-churn` | POST | Batch churn predictions (slow) |
| `/api/ml/churn-model/feature-importance` | GET | Top churn prediction factors |

### UC-3: Fraud Detection

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/customers/{id}/fraud-signals` | GET | List flagged transactions (min_score, days filters) |
| `/api/customers/{id}/fraud-signals/{tx_id}` | GET | Fraud detail + feature vector + baseline comparison |
| `/api/ml/fraud/high-risk-transactions` | GET | Portfolio view: all high-risk transactions sorted by score |
| `/api/ml/train-fraud-model` | POST | Train Isolation Forest + rule-based fraud model |

### AI Insights & Documentation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/customers/{id}/insights` | GET | AI narrative analysis (7-day cached) |
| `/docs` | GET | Interactive API documentation (Swagger UI) |

**Training Models (Required for Churn & Fraud Predictions)**

Before using churn or fraud predictions, train the models via these endpoints:

```bash
# Train churn prediction model
curl -X POST http://localhost:8000/api/ml/train-churn-model

# Train fraud detection model
curl -X POST http://localhost:8000/api/ml/train-fraud-model

# Check model status
curl http://localhost:8000/health
```

**Example API Call:**
```bash
curl http://localhost:8000/api/customers/persona_john_stable
```

Response:
```json
{
  "customer_id": "persona_john_stable",
  "name": "John (Stable)",
  "current_monthly_spending": 5234.50,
  "spending_trend": "STABLE",
  "total_transactions": 342,
  "behavior_flags": []
}
```

**Example Fraud Signals (After Training):**
```bash
curl "http://localhost:8000/api/customers/persona_julia_geographicanomaly/fraud-signals?days=30&min_score=0.3"
```

Response shows flagged transactions with fraud_score and fraud_flags (geo_risk, card_testing, etc.)

---

## 🧠 ML Pipeline

```
Data Generation (1000 customers, 335k+ transactions, ~5% fraud)
    ↓
UC-1: Spending Trends & Anomalies
├─ Feature Engineering (15 features: trends, volatility, diversity, temporal)
├─ Prophet: Forecasts spending 12 months forward
├─ Isolation Forest: Per-customer anomaly detection
└─ Custom SHAP-style: Risk score explainability

UC-2: Churn Prediction
├─ Feature Engineering (15 features: credit metrics + spending)
├─ XGBoost: Binary classifier (stable vs churned)
├─ SHAP TreeExplainer: Top 5 factors per prediction
└─ Risk Tiers: LOW / MEDIUM / HIGH

UC-3: Fraud Detection
├─ Feature Engineering (8 features: geo, time, amount, velocity, merchant, channel)
├─ Isolation Forest: Global transaction anomaly detection (200 estimators)
├─ Rule-based Engine: 8 fraud flags (geo_risk, card_testing, structuring, etc.)
├─ Composite Score: 60% IF + 40% rule-based
└─ Graceful Fallback: Rule-based only until model training
```

**UC-1 Features Used (Spending Trends):**
- Monthly spending trends & forecasts
- Transaction frequency & amounts
- Category diversification
- Temporal patterns (day/night, weekday/weekend)
- Channel usage (online/POS/ATM)
- Account age & dormancy

**UC-2 Features Used (Churn Prediction):**
- Credit metrics (limit, utilization, balance)
- Spending trends (slope, volatility, growth)
- Transaction patterns (frequency, recency)
- Account tenure & engagement
- Behavioral changes (migration, spike detection)

**UC-3 Features Used (Fraud Detection):**
- Geographic risk (country changes, new locations)
- Night activity (transactions in unusual hours)
- Card testing (micro-transactions before large amounts)
- Structuring (multiple small sequential amounts)
- Amount spike (deviation from customer baseline)
- High velocity (transaction count in time window)
- Merchant drift (category changes in history)
- Channel anomaly (unusual channel usage)

---

## 📊 Dashboard Features

### UC-1: Spending Trends & Behavior
- **Customer Profile** — View customer details, spending baseline, transaction count
- **Spending Trends Chart** — Prophet 12-month forecast with confidence intervals
- **Anomaly Alerts** — Flag unusual spending patterns with severity
- **Behavior Flags** — Channel migration, declining diversity, spending spikes, silent churn
- **Rolling Averages** — 7-day, 30-day, 90-day spending trends

### UC-2: Churn Prediction
- **Churn Risk Gauge** — Real-time probability score (0-100%)
- **Risk Tier** — LOW / MEDIUM / HIGH classification
- **SHAP Explanations** — Top 5 factors driving churn risk
- **High-Risk Customers Table** — Sortable list with risk categories
- **Feature Importance Chart** — All 15 engineered features and their weights

### UC-3: Fraud Detection (New)
- **Fraud Signals Table** — Flagged transactions with color-coded scores
- **Transaction Detail Panel** — Full feature vector + baseline comparison
- **Fraud Flags** — Visual tags (geo_risk, card_testing, night_activity, etc.)
- **Portfolio View** — High-risk transactions across all customers (sorted by score)
- **Prior History Stats** — Mean/max fraud scores for customer context

### General
- **AI Insights** — Professional narrative explaining all predictions (cached 7 days)
- **Model Status** — See which models are trained vs. rule-based only
- **Responsive Design** — Works on desktop, tablet, mobile

---

## 📈 Performance & Scale

| Metric | Value | Notes |
|--------|-------|-------|
| **Database size** | ~2-3 MB | SQLite with 40 demo personas + 6k transactions |
| **Query time** | <1 ms | Indexed lookups |
| **Model training** | ~30 seconds | XGBoost with 15 features |
| **Prediction latency** | 100-150 ms | Per customer analysis |
| **Cache hit rate** | <1 ms | Narrative caching |

---

## 🔧 Environment Variables (Optional)

Create `backend/.env`:
```
DATABASE_URL=sqlite:///./data/spending.db
LOG_LEVEL=INFO
PROPHET_INTERVAL_WIDTH=0.95
ISOLATION_FOREST_CONTAMINATION=0.1
```

---

## 🐳 Deployment Improvements Proposed

### 1. **Environment-Based Configuration**
- Separate `.env` files for dev, staging, production
- Health check endpoint validation in docker-compose
- Configurable replica counts

### 2. **Database Optimization**
- Enable WAL (Write-Ahead Logging) for better concurrency
- Automatic backups to S3 or mounted volume
- Migration system (Alembic) for schema changes

### 3. **Model Management**
- Versioned model checkpoints
- A/B testing framework for different model versions
- Automatic retraining scheduler

### 4. **Monitoring & Logging**
- ELK stack integration (Elasticsearch, Logstash, Kibana)
- Prometheus metrics endpoint
- Request/response logging with correlation IDs

### 5. **Scaling Strategy**
- Redis caching for predictions (reduce DB hits)
- Async task queue (Celery) for batch predictions
- Multi-replica backend with load balancer
- PostgreSQL instead of SQLite for production

### 6. **Security**
- API key authentication
- Rate limiting per customer ID
- Request validation & sanitization
- Secrets management (AWS Secrets Manager / HashiCorp Vault)

### 7. **Testing & CI/CD**
- Automated test suite in docker-compose
- Pre-commit hooks for code quality
- Integration tests in GitHub Actions
- Smoke tests on container startup

---

## 🧪 Testing

```bash
# Backend tests (in container)
docker-compose exec backend pytest tests/ -v

# Or locally
cd backend
pytest tests/ -v --cov=app
```

---
---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend API** | FastAPI (Python 3.11) + Uvicorn |
| **Frontend** | Vue.js 3 (Composition API) + Pinia + Vite |
| **Styling** | Tailwind CSS + Headless UI |
| **Database** | SQLite (SQLAlchemy 2.0 ORM) |
| **ML: Trends (UC-1)** | Prophet (Facebook) - time series forecasting |
| **ML: Anomalies (UC-1)** | Scikit-learn Isolation Forest - per-customer |
| **ML: Churn (UC-2)** | XGBoost - binary classifier (15 features) |
| **ML: Fraud (UC-3)** | Scikit-learn Isolation Forest (global) + rule-based hybrid |
| **Explainability** | SHAP (TreeExplainer for XGBoost, custom weights for others) |
| **Charts** | ApexCharts |
| **Containerization** | Docker + Docker Compose (multi-stage builds) |
| **Web Server** | nginx (frontend static serving + reverse proxy) |

---

## ❓ FAQ

**Q: How long does first startup take?**
A: 2-3 minutes. It generates 1000 customers (335k+ transactions), creates database indexes, and prepares ML models for training.

**Q: Do I need to train the models?**
A: Yes, for churn & fraud predictions. Use the dashboard "Train Model" buttons or API endpoints (`POST /api/ml/train-churn-model`, `POST /api/ml/train-fraud-model`). Before training, endpoints return rule-based scores only.

**Q: Can I use real data instead of synthetic?**
A: Yes. Modify `backend/app/db/init_db.py` to load from your data source instead of the persona generator. Fraud patterns will still be injected for testing.

**Q: What database is used?**
A: SQLite for simplicity. For production, migrate to PostgreSQL (no code changes needed thanks to SQLAlchemy).

**Q: Are the synthetic personas reproducible?**
A: Yes. Seed-based generation means the same 1000 customers are created on each run (22 named personas + 978 synthetic background).

**Q: Can I add more personas or customers?**
A: Yes. Edit `backend/app/ml/data_generator.py` to modify `n_customers`, add new persona classes, or adjust fraud injection percentage (~5%).

**Q: What's the fraud detection accuracy?**
A: The Isolation Forest is trained on real patterns (not labeled), so evaluation is qualitative. Rule-based flags (geo_risk, card_testing, structuring) provide interpretable signals. Combine both for best results.

**Q: How do I reset the database?**
A:
```bash
docker-compose down -v
rm -rf backend/data/spending.db backend/data/models/
docker-compose up --build
```

**Q: What's the difference between development and production?**
A: Development uses SQLite & in-memory caching. Production should use PostgreSQL, Redis, async task queues (Celery), and horizontal scaling.

**Q: Can I export fraud or churn predictions?**
A: Yes, via the API. Use batch endpoints (`POST /api/ml/predict-all-churn`) or high-risk endpoints (`GET /api/ml/fraud/high-risk-transactions`). Parse JSON and export to CSV/Excel as needed.

**Q: How long does model training take?**
A: XGBoost churn model: ~30 seconds. Isolation Forest fraud model: ~10 seconds. Both are done in-process (blocking request). For async training, use a task queue (Celery/RQ).

---

## 📝 License & Notes

- Uses **synthetic data** to simulate real banking scenarios
- **No external dependencies** beyond Docker (all packages in requirements.txt)
- Built for **PoC & learning** — Suitable for production with architectural enhancements
