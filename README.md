# Customer Spending Trend Analysis — ML PoC

AI-powered banking analytics platform for detecting customer spending trends, anomalies, and churn risk.

## 🎯 What It Does

- 📊 **Trend Forecasting** — Predicts customer spending patterns using Prophet
- 🚨 **Anomaly Detection** — Flags risky behavior using Isolation Forest
- 💡 **Explainability** — Shows why each prediction matters using SHAP
- 🎨 **Interactive Dashboard** — Visualize insights in real-time via Vue.js

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
2. ✅ Create SQLite database schema (`backend/data/spending.db`)
3. ✅ Generate 40 named demo personas with transaction histories
4. ✅ **Train & cache ML models** (Prophet, Isolation Forest, XGBoost)
5. ✅ Start API on `http://localhost:8000`
6. ✅ Start Dashboard on `http://localhost:3000`

**First run takes 2-3 minutes** (generation + training). Subsequent restarts take ~10 seconds (models load from cache).

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

1. **Database Generation** (~60 seconds)
   - 40 named demo personas (with specific behavioral patterns, ~150 transactions each)
   - ~6,000 transactions total from all personas
   - Created in SQLite with indexed queries

2. **Model Training** (~90 seconds)
   - **Prophet**: Trend forecasting model trained per customer
   - **Isolation Forest**: Anomaly detection on spending patterns
   - **XGBoost**: Churn prediction classifier
   - Models cached in memory for fast inference

3. **Database Indexing** (~30 seconds)
   - Customer lookups optimized
   - Transaction queries indexed

**Subsequent restarts**: ~10 seconds
- Database already exists → skip generation
- Models cached in memory → load instantly
- API starts immediately

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
3. Generate 40 demo personas with transaction histories (~6k transactions total)
     ↓
4. Train ML models on generated data:
     ├─ Prophet: Learns spending trends for each customer
     ├─ Isolation Forest: Learns anomaly patterns
     └─ XGBoost: Learns churn prediction (binary classifier)
     ↓
5. Cache models in memory for fast inference
     ↓
6. API ready ✅ (takes 2-3 minutes total)
```

**All models are trained on first startup, then cached:**
- Models are saved to `backend/data/*.pkl` files
- On restart, cached models load in <1 second
- No retraining needed unless database is deleted

---

## 📊 What Gets Generated Automatically

### Synthetic Customer Data
- **40 named demo personas** with diverse, realistic behavioral patterns
- **~6,000 transactions** across all personas (24 months per persona)
- **Stored in SQLite** (`backend/data/spending.db`, ~2-3 MB)
- **Deterministic** — Same data on each run (seed-based generation)

### Example Demo Personas
- `STABLE_John` — Normal spending, low risk ✅
- `CHURN_Sarah` — Declining spending, high churn risk 🔴
- `ANOMALY_Mark` — Risky patterns (gambling, night transactions) ⚠️
- `GROWTH_Tech` — Consistent growth, stable ✅
- `MULE_Account` — Money laundering simulation (fraud detection test) 🔴
- ... 35 more edge cases

### Trained Models (Cached)
All models are **trained automatically** on first startup and cached:

- **Prophet** — Trend forecasting (learns spending patterns per customer)
- **Isolation Forest** — Anomaly detection (identifies unusual spending)
- **XGBoost** — Churn prediction classifier (binary: churned or not)
- **SHAP** — Feature importance explanations

Models are pickled to `backend/data/` and loaded in <1 second on subsequent restarts.

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
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── main.py            # REST API endpoints
│   │   ├── config.py          # Configuration
│   │   ├── models.py          # Pydantic schemas
│   │   ├── db/                # Database layer
│   │   │   ├── models.py      # SQLAlchemy ORM
│   │   │   ├── database.py    # Engine & sessions
│   │   │   ├── init_db.py     # Auto-initialization
│   │   │   └── repositories.py
│   │   └── ml/                # Machine learning
│   │       ├── data_generator.py
│   │       ├── feature_engineering.py
│   │       ├── trend_detection.py
│   │       ├── anomaly_detection.py
│   │       ├── churn_features.py
│   │       ├── churn_model.py
│   │       └── narrative_engine.py
│   ├── data/                  # Generated database & models
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                  # Vue.js 3 dashboard
│   ├── src/
│   │   ├── components/        # Vue components
│   │   ├── stores/            # Pinia state management
│   │   ├── services/          # API client
│   │   └── App.vue
│   ├── package.json
│   └── Dockerfile
│
├── documents/                 # Technical documentation
│   ├── core/                  # Specifications
│   ├── phases/                # Phase completion reports
│   └── guides/                # How-to guides
│
├── docker-compose.yml         # Container orchestration
└── README.md                  # This file
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/customers/{id}` | GET | Customer profile with risk score |
| `/api/customers/{id}/trends` | GET | Spending forecast with confidence intervals |
| `/api/customers/{id}/anomalies` | GET | Detected anomalies with SHAP explanations |
| `/api/customers/{id}/insights` | GET | AI narrative analysis |
| `/api/customers/risk/high` | GET | List high-risk customers |
| `/api/personas` | GET | List all personas |
| `/docs` | GET | Interactive API documentation (Swagger UI) |

**Example API Call:**
```bash
curl http://localhost:8000/api/customers/customer_000000
```

Response:
```json
{
  "customer_id": "customer_000000",
  "risk_score": 0.15,
  "risk_category": "LOW",
  "trend_slope": 0.002,
  "spending_volatility": 0.04
}
```

---

## 🧠 ML Pipeline

**Data Generation** (Synthetic personas with realistic patterns)
  ↓
**Feature Engineering** (15 features: spending trends, volatility, categories, etc.)
  ↓
**Model Training** (Prophet, Isolation Forest, XGBoost)
  ↓
**Explainability** (SHAP values show top contributing features)
  ↓
**Risk Scoring** (6 categories: STABLE, MONITORING, AT_RISK, DECLINE, SILENT_CHURN, ACTIVE_CHURN)

**Features Used:**
- Monthly spending trends
- Transaction frequency & amounts
- Category diversification
- Temporal patterns (day/night, weekday/weekend)
- Payment delays & compliance
- Account age & dormancy

---

## 📊 Dashboard Features

- **Customer Profile** — View individual customer details
- **Spending Trends** — Prophet forecast with confidence intervals
- **Anomaly Alerts** — Detect unusual patterns
- **Risk Ranking** — See high-risk customers
- **AI Insights** — Professional narrative explaining predictions
- **SHAP Explainability** — Understand what drives each score

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

## 📚 Documentation

**Deep Dives:**
- **[CLAUDE.md](./CLAUDE.md)** — Full project context & architecture decisions
- **[documents/INDEX.md](./documents/INDEX.md)** — Documentation navigation hub
- **[documents/core/](./documents/core/)** — Current specifications (API, ML pipeline, deployment)
- **[documents/phases/](./documents/phases/)** — Phase completion reports (historical)

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.11) |
| Frontend | Vue.js 3 + Tailwind CSS |
| Database | SQLite + SQLAlchemy ORM |
| Trends | Prophet |
| Anomalies | Scikit-learn Isolation Forest |
| Churn | XGBoost |
| Explainability | SHAP |
| Charts | ApexCharts |
| Container | Docker + Docker Compose |

---

## ❓ FAQ

**Q: How long does first startup take?**
A: 2-3 minutes. It's generating 40 demo personas with transactions, creating database indexes, and training ML models.

**Q: Can I use real data instead of synthetic?**
A: Yes. Modify `backend/app/db/init_db.py` to load from your data source instead of the persona generator.

**Q: What database is used?**
A: SQLite for simplicity. For production, migrate to PostgreSQL (no code changes needed thanks to SQLAlchemy).

**Q: Are the synthetic personas reproducible?**
A: Yes. Seed-based generation means the same customers are created on each run.

**Q: Can I add more personas?**
A: Yes. Edit `backend/app/ml/data_generator.py` to add new generator classes.

**Q: How do I reset the database?**
A: `docker-compose down -v && rm -rf backend/data/spending.db && docker-compose up`

**Q: What's the difference between development and production?**
A: Development uses SQLite & in-memory caching. Production should use PostgreSQL, Redis, and horizontal scaling.

---

## 📝 License & Notes

- Uses **synthetic data** to simulate real banking scenarios
- **No external dependencies** beyond Docker (all packages in requirements.txt)
- **Full source transparency** — All code documented and reviewed
- Built for **PoC & learning** — Suitable for production with architectural enhancements
