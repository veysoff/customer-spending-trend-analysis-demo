# Customer Spending Trend Analysis PoC — Project Memory

## Project Overview

**Goal**: Develop a full-stack ML PoC for bank to detect customer spending trends, anomalies, and churn risk.

**Tech Stack**:
- Backend: FastAPI (Python)
- Frontend: Vue.js 3 + Tailwind CSS + ApexCharts
- ML: Pandas, Prophet (trends), Scikit-learn (anomalies), SHAP (explainability)
- Deployment: Docker + Docker Compose

---

## Phase 1: Planning & Architecture ✅ COMPLETED

### Deliverables Created
1. **documents/architecture.md** — Comprehensive system design
   - Data schema with 3 customer behavior patterns (Normal, Silent Churn, Lifestyle Shift)
   - ML pipeline: Feature engineering → Prophet trend detection → Isolation Forest anomalies → SHAP explanation
   - 5 REST API endpoints design
   - Docker & docker-compose setup
   - Success metrics defined

### Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Prophet for trends | Handles seasonality, uncertainty intervals, and business interpretability |
| Isolation Forest for anomalies | Unsupervised, handles multivariate anomalies, O(n log n) complexity |
| SHAP for explainability | Industry standard, provides feature contribution waterfall plots |
| SQLite/CSV for data | Lightweight, no external DB dependency, suitable for PoC |
| FastAPI | Async support, automatic Swagger docs, modern Python framework |
| Vue 3 Composition API | Reactive, performant, easier testing than Options API |
| ApexCharts | Lightweight, interactive, supports time series well |
| Docker Compose | Single `up` command for full stack, networking built-in |

### Data Generation Strategy
- **Size**: 1000 customers × 12 months = ~450k transactions
- **Patterns**:
  - 40% Normal (baseline behavior)
  - 30% Silent Churn (10% monthly decline over 6 months)
  - 30% Lifestyle Shift (category distribution change)
- **Features**: Amount, date, MCC, channel, merchant, country, time_of_day

### ML Features Engineered
1. Monthly spending trends (sum, rolling mean, rolling std)
2. Frequency metrics (transaction count, avg amount)
3. Category diversification (unique categories, entropy)
4. Temporal patterns (weekend/weekday, time of day)
5. Channel distribution (POS, Online, ATM ratios)

### API Endpoints Designed
1. `GET /api/customers/{customer_id}` — Profile with risk score
2. `GET /api/customers/{customer_id}/trends` — Trend forecast with confidence intervals
3. `GET /api/customers/{customer_id}/anomalies` — Detected anomalies with SHAP values
4. `POST /api/data/generate` — Generate synthetic data
5. `GET /api/customers/risk/high` — List at-risk customers

---

## Phase 2: Implementation (PENDING USER APPROVAL)

### Phase 2a: Backend Implementation

**Status**: ⏳ Waiting for "Go" signal

**Tasks**:
- [ ] Setup FastAPI project structure
- [ ] Implement synthetic data generator
- [ ] Implement feature engineering module
- [ ] Integrate Prophet model for trend detection
- [ ] Integrate Isolation Forest for anomalies
- [ ] Implement SHAP explainability
- [ ] Create REST API endpoints
- [ ] Add error handling & validation
- [ ] Create backend requirements.txt

### Phase 2b: Frontend Implementation

**Status**: ⏳ Waiting for backend

**Tasks**:
- [ ] Setup Vue 3 project with Vite
- [ ] Create Dashboard component
- [ ] Create TrendChart with ApexCharts
- [ ] Create AnomalyAlert component
- [ ] Create ExplainabilityPanel (SHAP waterfall)
- [ ] Setup API service layer
- [ ] Setup Pinia store for state management
- [ ] Add Tailwind CSS styling
- [ ] Create responsive layout

### Phase 2c: Docker & Deployment

**Status**: ⏳ Waiting for Phase 2a & 2b

**Tasks**:
- [ ] Create backend Dockerfile
- [ ] Create frontend Dockerfile
- [ ] Create docker-compose.yml
- [ ] Test local deployment
- [ ] Create deployment guide

### Phase 2d: Documentation & Testing

**Status**: ⏳ Waiting for Phase 2c

**Tasks**:
- [ ] Create documents/data_schema.md
- [ ] Create documents/ml_pipeline.md
- [ ] Create documents/api_specification.md
- [ ] Create documents/deployment.md
- [ ] Update README.md
- [ ] Add docstrings to code
- [ ] Test full PoC end-to-end

---

## Project Structure

```
customer-spending-trend-analysis-demo/
├── backend/                      # FastAPI + ML
├── frontend/                     # Vue.js 3 dashboard
├── documents/
│   ├── architecture.md          # ✅ Created
│   ├── data_schema.md           # ⏳ Pending
│   ├── ml_pipeline.md           # ⏳ Pending
│   ├── api_specification.md     # ⏳ Pending
│   └── deployment.md            # ⏳ Pending
├── docker-compose.yml           # ⏳ Pending
├── claude.md                    # This file
└── README.md
```

---

## Running Instructions (Will be updated after Phase 2)

```bash
# Phase 1 Complete ✅
# To view architecture: cat documents/architecture.md

# Phase 2 (Pending)
# docker-compose up --build
```

---

## Context & Notes for Future Sessions

### Key Design Patterns Used
1. **Feature Engineering Pipeline**: Transform raw transactions → engineered features
2. **Ensemble Approach**: Prophet (supervised trend) + Isolation Forest (unsupervised anomalies)
3. **Explainability Layer**: SHAP values attached to every prediction
4. **API-First Design**: RESTful, JSON responses, no tight frontend-backend coupling

### Known Trade-offs
- SQLite chosen over PostgreSQL for simplicity (no migrations needed)
- Synthetic data instead of real data (protects customer privacy)
- Batch processing instead of real-time streaming (faster PoC)
- Single model instance (no multi-tenant support yet)

### Performance Expectations
- Trend forecast: ~100ms per customer
- Anomaly detection: ~50ms per customer
- Full analysis: ~500ms per customer

### Future Enhancements (Out of Scope for PoC)
- Real-time streaming via Kafka
- Production ML model serving (BentoML, Seldon)
- Advanced seasonality detection (MSTL)
- Clustering customers by behavior
- Retention campaign recommendation engine

---

## Approval Gate

✋ **Phase 1 architecture complete. Awaiting user confirmation before Phase 2 implementation.**

**What I'm ready to do**:
- Start backend implementation (data generation, ML models, API)
- Start frontend implementation (dashboard, charts, alerts)
- Setup Docker infrastructure
- Create remaining documentation

---

**Last Updated**: 2026-02-09 — Phase 1 Architecture Created
**Session ID**: customer-spending-poc-phase1
