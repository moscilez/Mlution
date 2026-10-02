"""Deterministic synthetic telecom churn dataset used for the built-in demo."""
from pathlib import Path

import numpy as np
import pandas as pd

N_ROWS = 1500
TARGET = "churn"


def generate_demo_dataframe() -> pd.DataFrame:
    rng = np.random.RandomState(42)
    n = N_ROWS

    customer_id = [f"CUST-{i:06d}" for i in range(1, n + 1)]
    tenure_months = rng.randint(1, 73, n)
    monthly_charges = np.round(rng.uniform(20, 120, n), 2)
    total_charges = np.round(tenure_months * monthly_charges * rng.uniform(0.92, 1.08, n), 2)
    contract_type = rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.55, 0.25, 0.20])
    payment_method = rng.choice(
        ["Electronic check", "Mailed check", "Bank transfer", "Credit card"], n
    )
    num_support_calls = np.clip(rng.poisson(1.2, n), 0, 8)
    is_premium = rng.choice(["Yes", "No"], n, p=[0.3, 0.7])
    avg_monthly_gb = np.round(np.clip(rng.normal(45, 20, n), 1, None), 1)
    has_streaming = rng.choice(["Yes", "No"], n, p=[0.5, 0.5])

    z = (
        -1.2
        + 0.45 * num_support_calls
        + 1.0 * (contract_type == "Month-to-month")
        + 0.012 * (monthly_charges - 70)
        - 0.03 * tenure_months
        + rng.normal(0, 0.6, n)
    )
    p = 1.0 / (1.0 + np.exp(-z))
    churn = (p > 0.5).astype(int)
    flip = rng.rand(n) < 0.03
    churn = np.where(flip, 1 - churn, churn)

    df = pd.DataFrame(
        {
            "customer_id": customer_id,
            "tenure_months": tenure_months,
            "monthly_charges": monthly_charges,
            "total_charges": total_charges,
            "contract_type": contract_type,
            "payment_method": payment_method,
            "num_support_calls": num_support_calls,
            "is_premium": is_premium,
            "avg_monthly_gb": avg_monthly_gb,
            "has_streaming": has_streaming,
            TARGET: churn,
        }
    )

    # Inject realistic data-quality issues: ~1.5% missing, ~0.5% exact duplicates.
    for col in ("total_charges", "avg_monthly_gb"):
        idx = rng.choice(n, size=int(n * 0.015), replace=False)
        df.loc[idx, col] = np.nan
    dup = df.sample(n=max(1, int(n * 0.005)), random_state=42)
    df = pd.concat([df, dup], ignore_index=True)
    return df


def generate_demo_csv(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = generate_demo_dataframe()
    df.to_csv(path, index=False)
    return path
