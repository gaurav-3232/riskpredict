"""
Locust load test for RiskPredict.

Targets experiment_id=9 (random_forest on the loan default dataset, 11 features).

Run interactively (web UI on :8089):
    locust -f locustfile.py --host http://localhost:8001

Run headless (no UI, fixed duration):
    locust -f locustfile.py --host http://localhost:8001 \
        --users 50 --spawn-rate 10 --run-time 60s --headless
"""
import random
from locust import HttpUser, task, between, events

EXPERIMENT_ID = 9


def random_features() -> dict:
    """Generate inputs roughly in-distribution for experiment 9 (loan dataset)."""
    return {
        "person_age": random.randint(20, 65),
        "person_income": random.randint(20000, 150000),
        "person_emp_length": round(random.uniform(0, 20), 1),
        "loan_amnt": random.randint(1000, 35000),
        "loan_int_rate": round(random.uniform(5.0, 23.0), 2),
        "loan_percent_income": round(random.uniform(0.0, 0.8), 3),
        "cb_person_cred_hist_length": random.randint(2, 30),
        "person_home_ownership": random.choice(["RENT", "OWN", "MORTGAGE", "OTHER"]),
        "loan_intent": random.choice(
            ["EDUCATION", "MEDICAL", "VENTURE", "PERSONAL",
             "DEBTCONSOLIDATION", "HOMEIMPROVEMENT"]
        ),
        "loan_grade": random.choice(["A", "B", "C", "D", "E", "F", "G"]),
        "cb_person_default_on_file": random.choice(["Y", "N"]),
    }


class RiskPredictUser(HttpUser):
    """Simulates one user of the RiskPredict API."""

    wait_time = between(1, 3)

    @task(1)
    def health(self):
        with self.client.get("/health", name="GET /health", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"unexpected {r.status_code}")

    @task(5)
    def predict(self):
        payload = {"experiment_id": EXPERIMENT_ID, "features": random_features()}
        with self.client.post(
            "/predict", json=payload, name="POST /predict", catch_response=True
        ) as r:
            if r.status_code != 200:
                r.failure(f"status={r.status_code} body={r.text[:200]}")
            elif "prediction" not in r.json():
                r.failure("missing 'prediction' key in response")

    @task(2)
    def list_experiments(self):
        with self.client.get(
            "/experiments", name="GET /experiments", catch_response=True
        ) as r:
            if r.status_code != 200:
                r.failure(f"unexpected {r.status_code}")


@events.quitting.add_listener
def _print_summary(environment, **kwargs):
    stats = environment.stats.total
    print("\n" + "=" * 70)
    print("LOCUST SUMMARY")
    print("=" * 70)
    print(f"Total requests       : {stats.num_requests}")
    print(f"Total failures       : {stats.num_failures} "
          f"({100*stats.fail_ratio:.2f}%)")
    print(f"Requests per second  : {stats.total_rps:.2f}")
    print(f"Median latency  (ms) : {stats.median_response_time}")
    print(f"p95 latency     (ms) : {stats.get_response_time_percentile(0.95):.0f}")
    print(f"p99 latency     (ms) : {stats.get_response_time_percentile(0.99):.0f}")
    print(f"Max latency     (ms) : {stats.max_response_time:.0f}")
    print("=" * 70)