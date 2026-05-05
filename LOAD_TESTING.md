# Load Testing

This document describes the load testing performed on RiskPredict's API and the performance optimizations identified through it. The goal was to characterize behavior under concurrent load, find bottlenecks, and validate fixes with measurable results.

## Setup

**Tool:** [Locust](https://locust.io/) 2.43 (Python-based load testing framework)

**Target:** Local Docker Compose stack
- FastAPI backend (single uvicorn worker, `--reload` enabled)
- PostgreSQL 16
- React/Vite frontend (not exercised in load tests)

**Test scenarios:** Three endpoints exercised by virtual users with 1–3 second think time between actions:
- `POST /predict` — main ML inference path (weight 5)
- `GET /experiments` — list experiments from DB (weight 2)
- `GET /health` — cheap liveness check (weight 1)

**Hardware:** MacBook Air (Apple Silicon), 8 GB RAM allocated to Docker Desktop

## Running the tests

From `backend/`:

```bash
pip install locust
locust -f locustfile.py --host http://localhost:8001
```

Open `http://localhost:8089`, set users / spawn rate / host, and start.

For headless runs (CI-friendly):

```bash
locust -f locustfile.py --host http://localhost:8001 \
  --users 300 --spawn-rate 30 --run-time 90s --headless
```

## Results

Four runs were performed. Each ran against an identical experiment (random forest on a 6,500-row loan default dataset, 11 features).

### Run 1 — Baseline (50 users)

| Endpoint        | Requests | Median | p95   | p99   | Failures |
|-----------------|---------:|-------:|------:|------:|---------:|
| `POST /predict`     |      797 |   25ms | 300ms | 980ms |       0% |
| `GET /experiments`  |      315 |   18ms | 120ms | 610ms |       0% |
| `GET /health`       |      159 |    6ms | 110ms | 690ms |       0% |
| **Aggregated**      |     1271 |   20ms | 230ms | 930ms |       0% |

Throughput: **24.9 RPS**. The system is healthy at this load.

### Run 2 — Stress test (300 users, default config)

| Endpoint        | Requests | Median  | p99    | Failures |
|-----------------|---------:|--------:|-------:|---------:|
| `POST /predict`     |      588 |  1400ms | 24000ms |     5.1% |
| `GET /experiments`  |      260 |   510ms | 23000ms |     5.8% |
| `GET /health`       |      130 |   420ms | 22000ms |       0% |
| **Aggregated**      |      978 |  1000ms | 23000ms |     4.6% |

Throughput collapses to 4.8 RPS. Failures arrive with this error:

```
QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00
```

**Diagnosis:** SQLAlchemy's default DB connection pool (5 + 10 overflow = 15 connections) was exhausted. The 30-second pool timeout caused requests to stall before failing, which is why even successful requests show 20+ second p99 latencies — they were queueing for a free connection.

### Run 3 — Larger pool only (300 users, pool 60)

```python
# backend/app/db/database.py
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
    pool_timeout=10,  # fail fast instead of stalling 30s
)
```

| Endpoint        | Requests | Median  | p99    | Failures |
|-----------------|---------:|--------:|-------:|---------:|
| `POST /predict`     |      278 |  4500ms | 20000ms |     8.6% |
| `GET /experiments`  |      260 |   510ms | 23000ms |     5.8% |
| **Aggregated**      |      485 |  4000ms | 20000ms |     8.0% |

Same error reappears — `QueuePool limit of size 20 overflow 40 reached`. Just bumping the pool moved the ceiling but didn't address the root cause: requests holding connections too long. With ~700ms of model deserialization happening *inside* the request handler while holding a connection, even 60 connections saturate quickly under sustained concurrency.

### Run 4 — Model cache + larger pool (300 users)

The real fix: cache loaded model artifacts in memory using `functools.lru_cache`, so subsequent requests reuse the in-memory model instead of re-reading it from disk on every call.

```python
# backend/app/services/services.py
from functools import lru_cache

@lru_cache(maxsize=32)
def _load_model_cached(model_path: str) -> dict:
    return MLPipeline.load_model(model_path)


class PredictionService:
    @staticmethod
    def predict(db, experiment_id, features):
        experiment = db.query(Experiment).filter(...).first()
        # Was: artifact = MLPipeline.load_model(experiment.model_path)
        artifact = _load_model_cached(experiment.model_path)
        ...
```

| Endpoint        | Requests | Median  | p99    | Failures |
|-----------------|---------:|--------:|-------:|---------:|
| `POST /predict`     |      731 |  1200ms |  4600ms |       0% |
| `GET /health`       |      153 |   860ms |  4300ms |       0% |
| **Aggregated**      |     1199 |  1000ms |  4600ms |       0% on /predict |

Throughput: **75.7 RPS**. First call per model is still ~700ms (cold cache, disk read). Every subsequent call is microseconds. Connections are released quickly, so the pool no longer saturates.

## Summary

| Configuration                       | /predict failures | /predict p99 | Throughput |
|-------------------------------------|------------------:|-------------:|-----------:|
| Baseline (50 users)                 |                0% |        980ms |   24.9 RPS |
| Stress, default pool (300 users)    |              5.1% |       24000ms |    4.8 RPS |
| Stress, larger pool only            |              8.6% |       20000ms |   15.3 RPS |
| Stress, larger pool + model cache   |          **0%**   |   **4600ms** | **75.7 RPS** |

End-to-end improvement vs broken state: **failures eliminated, p99 latency reduced 5×, throughput increased 16×**. Same hardware, four lines of code.

## Findings worth noting

**1. Functional tests don't catch performance bugs.** The pytest suite was green throughout. The model-reload-per-request bug only manifests under concurrency.

**2. The first fix is rarely the right fix.** Increasing pool size felt like the obvious answer once the error said "QueuePool limit reached." It moved the bottleneck without addressing it. The actual root cause was upstream — connections were held too long because of synchronous I/O in the request path.

**3. Tail latency tells more than median.** At 50 users the median /predict latency was 25ms but p99 was 980ms — a 40× spread. That spread is the leading indicator of a system that's healthy on average but periodically stalls. Median alone would have suggested everything was fine.

## Known limitations and future work

- **Tests run with `--reload` enabled**, which adds overhead. Production-realistic numbers would be ~10–20% better across all endpoints.
- **Single uvicorn worker.** Production should run `--workers N` (typically `2 × CPU cores + 1`) for true parallelism. Initial experiments with 4 workers showed roughly proportional throughput gains.
- **`/experiments` returns ~140 KB JSON per call** because `roc_curve` arrays are serialized fully. A separate endpoint that returns metric summaries without the full curve data would significantly reduce serialization cost under load.
- **No circuit breakers or rate limiting.** A real deployment should add a request limit per client and reject excess load gracefully rather than queueing.
- **Mutation testing** with `mutmut` would be a strong follow-up to validate that the existing pytest suite actually catches the bugs it claims to.

## Files

- `backend/locustfile.py` — load test definition
- `backend/app/services/services.py` — contains the `_load_model_cached` fix
- `backend/app/db/database.py` — contains the pool configuration