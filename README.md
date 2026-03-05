# RiskPredict — ML Risk Prediction Platform

A full-stack ML experimentation platform for uploading datasets, training classification models, evaluating performance, and running predictions.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  React + TS  │────▶│   FastAPI     │────▶│  PostgreSQL  │
│  (Nginx/Vite)│     │  (Python 3.11)│     │     16       │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                     ┌──────▼───────┐
                     │  ML Engine   │
                     │ (scikit-learn)│
                     └──────────────┘
```

---

## Quick Start (Local Development)

```bash
# 1. Clone and configure
cp .env.example .env

# 2. Start everything
docker-compose up --build

# 3. Open
#    Frontend:  http://localhost:5173
#    API docs:  http://localhost:8001/docs
#    Health:    http://localhost:8001/health
```

## Production (Docker)

```bash
# Build and run production images
docker-compose -f docker-compose.prod.yml up --build -d

# Frontend served via Nginx on port 80
# API on port 8000
```

---

## Features

- **Dataset Management** — Upload CSV, inspect columns and metadata
- **Model Training** — Logistic Regression, Random Forest, Gradient Boosting
- **Experiment Tracking** — Accuracy, Precision, Recall, F1, ROC-AUC, confusion matrices, feature importance
- **Smart Predictions** — Dropdown selectors for categorical features, range indicators for numeric inputs
- **Dashboard** — Compare models with interactive charts

---

## API Endpoints

| Method | Endpoint              | Description              |
|--------|-----------------------|--------------------------|
| GET    | `/health`             | Service health + DB status |
| GET    | `/metrics`            | Platform statistics      |
| POST   | `/datasets/upload`    | Upload CSV dataset       |
| GET    | `/datasets`           | List all datasets        |
| GET    | `/datasets/{id}`      | Get dataset details      |
| POST   | `/experiments/train`  | Train a new model        |
| GET    | `/experiments`        | List all experiments     |
| GET    | `/experiments/{id}`   | Get experiment details   |
| POST   | `/predict`            | Make a prediction        |

### Example API Requests

```bash
# Health check
curl http://localhost:8001/health

# Upload dataset
curl -X POST http://localhost:8001/datasets/upload \
  -F "file=@data.csv"

# Train model
curl -X POST http://localhost:8001/experiments/train \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": 1, "model_type": "random_forest", "target_column": "loan_status", "test_size": 0.2}'

# List experiments
curl http://localhost:8001/experiments

# Make prediction
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"experiment_id": 1, "features": {"person_age": 30, "person_income": 60000, "loan_amnt": 10000}}'

# Metrics
curl http://localhost:8001/metrics
```

---

## Project Structure

```
riskpredict/
├── .github/workflows/
│   └── ci-cd.yml              # GitHub Actions pipeline
├── backend/
│   ├── Dockerfile             # Multi-stage (builder → production → development)
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py            # FastAPI app with middleware
│   │   ├── api/               # Route handlers
│   │   ├── core/              # Config, logging, middleware
│   │   ├── db/                # Database connection
│   │   ├── ml/                # ML pipeline
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   └── services/          # Business logic
│   └── tests/
├── frontend/
│   ├── Dockerfile             # Multi-stage (builder → nginx → development)
│   ├── .dockerignore
│   ├── nginx.conf             # Production reverse proxy + SPA routing
│   ├── package.json
│   └── src/
│       ├── App.tsx
│       ├── components/
│       ├── pages/
│       └── services/
├── deploy/
├── docker-compose.yml         # Development
├── docker-compose.prod.yml    # Production
├── render.yaml                # Render Blueprint
├── railway.json               # Railway config
├── .env.example
└── README.md
```

---

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) runs on every push to `main`:

```
Push to main
    │
    ├─► Run pytest (with PostgreSQL service container)
    │
    ├─► Build backend Docker image (multi-stage, production target)
    ├─► Build frontend Docker image (multi-stage, nginx target)
    │
    ├─► Push images to GitHub Container Registry (ghcr.io)
    │
    └─► Trigger deployment via Render deploy hooks
```

### Setup Required

1. The workflow uses `GITHUB_TOKEN` (automatic) for GHCR pushes
2. Add these **repository secrets** for deployment:
   - `RENDER_DEPLOY_HOOK_BACKEND` — Render deploy hook URL for the API service
   - `RENDER_DEPLOY_HOOK_FRONTEND` — Render deploy hook URL for the frontend

---

## Deployment

### Option A: Render (Recommended)

1. Fork this repo to your GitHub account
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New → Blueprint** and connect your repo
4. Render reads `render.yaml` and creates:
   - `riskpredict-api` — Docker web service (backend)
   - `riskpredict-web` — Static site (frontend)
   - `riskpredict-db` — Managed PostgreSQL
5. All environment variables are auto-configured

### Option B: Railway

1. Go to [Railway](https://railway.app) → **New Project**
2. Connect your GitHub repo
3. Add a **PostgreSQL** plugin
4. Set environment variables:
   - `DATABASE_URL` — from Railway's PostgreSQL plugin
   - `CORS_ORIGINS` — `["https://your-frontend.up.railway.app"]`
   - `ENVIRONMENT` — `production`
   - `LOG_LEVEL` — `WARNING`
5. Deploy backend using the `railway.json` config
6. Create a second service for frontend (static build from `frontend/`)

### Option C: Self-hosted with Docker Compose

```bash
# On your server
git clone <repo-url> && cd riskpredict
cp .env.example .env
# Edit .env with production values

docker-compose -f docker-compose.prod.yml up -d
```

---

## Environment Variables

| Variable         | Required | Default                  | Description                          |
|------------------|----------|--------------------------|--------------------------------------|
| `DATABASE_URL`   | Yes      | (local postgres)         | PostgreSQL connection string         |
| `MODELS_DIR`     | No       | `/app/storage/models`    | Path to store trained models         |
| `DATASETS_DIR`   | No       | `/app/storage/datasets`  | Path to store uploaded CSVs          |
| `CORS_ORIGINS`   | No       | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `LOG_LEVEL`      | No       | `INFO`                   | DEBUG, INFO, WARNING, ERROR          |
| `ENVIRONMENT`    | No       | `development`            | `development` or `production`        |
| `JWT_SECRET`     | No       | —                        | Reserved for future auth             |

---

## Docker Images

### Backend (multi-stage)
- **builder** — installs gcc + pip deps
- **production** — lean runtime with non-root user, health check, 2 workers
- **development** — adds reload + debugpy

### Frontend (multi-stage)
- **builder** — runs `npm run build`
- **production** — serves via nginx with gzip, caching, SPA routing
- **development** — Vite dev server with HMR

---

## Running Tests

```bash
# Inside Docker
docker-compose exec backend pytest tests/ -v

# Locally
cd backend
pip install -r requirements.txt
DATABASE_URL=sqlite:///./test.db pytest tests/ -v
```
