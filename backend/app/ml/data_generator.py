import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import uuid
from typing import Tuple, List

class SyntheticDataGenerator:
    """Generate realistic synthetic banking transaction data."""

    MCC_CATEGORIES = {
        "5411": "GROCERY",
        "5422": "PHARMACY",
        "5812": "RESTAURANTS",
        "4511": "AIRLINES",
        "7011": "ACCOMMODATION",
        "5961": "DIRECT_MARKETING",
        "5733": "ELECTRONICS",
        "5944": "BOOKSTORES",
        "5200": "BUILDING_SUPPLIES",
        "4213": "LOGISTICS",
    }

    CHANNELS = ["POS", "ONLINE", "ATM", "MOBILE"]
    MERCHANTS = ["Tesco", "Sainsbury's", "Amazon", "Netflix", "Uber", "Starbucks",
                 "McDonald's", "Boots", "John Lewis", "Argos", "Next", "M&S"]
    COUNTRIES = ["GB", "US", "FR", "DE", "ES"]

    def __init__(self, n_customers: int = 1000, n_months: int = 12, seed: int = 42):
        self.n_customers = n_customers
        self.n_months = n_months
        self.seed = seed
        # Use a local random generator to avoid affecting global numpy state
        self.rng = np.random.default_rng(seed)

    def _get_pattern_type(self, customer_idx: int) -> str:
        """Assign behavior pattern to customer."""
        ratio = customer_idx / self.n_customers
        if ratio < 0.40:
            return "normal"
        elif ratio < 0.70:
            return "silent_churn"
        else:
            return "lifestyle_shift"

    def _generate_monthly_spending(self, pattern: str, month: int) -> float:
        """Generate monthly spending based on pattern."""
        base = self.rng.normal(5000, 500)

        # Seasonal adjustment
        if month == 12:  # December
            seasonal = base * 1.15
        elif month == 8:  # August
            seasonal = base * 0.80
        else:
            seasonal = base

        if pattern == "normal":
            return seasonal
        elif pattern == "silent_churn":
            # 10% monthly decline starting month 4
            if month >= 4:
                decline_factor = (0.9 ** (month - 3))
                return seasonal * decline_factor
            return seasonal
        else:  # lifestyle_shift
            return seasonal

    def _generate_daily_transactions(self, monthly_spending: float, month: int,
                                     pattern: str) -> List[Tuple]:
        """Generate daily transactions for a month."""
        transactions = []
        days_in_month = 28 if month == 2 else 30 if month in [4, 6, 9, 11] else 31

        # Transaction frequency varies
        if pattern == "silent_churn":
            n_transactions = max(int(self.rng.normal(25, 5)), 10)
        else:
            n_transactions = int(self.rng.normal(30, 5))

        for _ in range(n_transactions):
            day = self.rng.integers(1, days_in_month + 1)
            hour = self.rng.integers(0, 24)
            minute = self.rng.integers(0, 60)

            amount = self.rng.lognormal(np.log(50), 0.5)  # Lognormal distribution
            amount = min(amount, monthly_spending)

            mcc = self.rng.choice(list(self.MCC_CATEGORIES.keys()))
            channel = self.rng.choice(self.CHANNELS)
            merchant = self.rng.choice(self.MERCHANTS)
            country = self.rng.choice(self.COUNTRIES)

            transactions.append((
                day, hour, minute, amount, mcc, channel, merchant, country
            ))

        return transactions

    def _shift_categories(self, mcc_list: List[str]) -> List[str]:
        """Shift category distribution for lifestyle shift."""
        # Increase GROCERY, decrease RESTAURANTS and AIRLINES
        adjusted = []
        for mcc in mcc_list:
            if self.rng.random() < 0.3:  # 30% chance to change
                if mcc in ["5812", "4511"]:  # RESTAURANTS, AIRLINES
                    adjusted.append("5411")  # Switch to GROCERY
                else:
                    adjusted.append(mcc)
            else:
                adjusted.append(mcc)
        return adjusted

    def generate(self) -> pd.DataFrame:
        """Generate complete synthetic dataset."""
        records = []

        for cust_idx in range(self.n_customers):
            customer_id = f"customer_{cust_idx:06d}"
            pattern = self._get_pattern_type(cust_idx)

            # Track transactions for lifestyle shift category change
            month_mccs = {m: [] for m in range(1, self.n_months + 1)}

            for month in range(1, self.n_months + 1):
                monthly_spending = self._generate_monthly_spending(pattern, month)
                transactions = self._generate_daily_transactions(
                    monthly_spending, month, pattern
                )

                for day, hour, minute, amount, mcc, channel, merchant, country in transactions:
                    # Apply category shift for lifestyle_shift pattern
                    if pattern == "lifestyle_shift" and month >= 7:
                        if np.random.random() < 0.4:  # 40% category shift
                            mcc = "5411"  # Force GROCERY

                    date_obj = datetime(2023, month, day, hour, minute)

                    records.append({
                        "transaction_id": str(uuid.uuid4()),
                        "customer_id": customer_id,
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "amount": round(amount, 2),
                        "mcc": mcc,
                        "mcc_category": self.MCC_CATEGORIES[mcc],
                        "channel": channel,
                        "merchant": merchant,
                        "country": country,
                        "time_of_day": date_obj.strftime("%H:%M"),
                        "pattern": pattern,
                    })

                    month_mccs[month].append(mcc)

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values(["customer_id", "date"]).reset_index(drop=True)

    def _generate_churn_metrics(self, churn_pattern: str) -> dict:
        """Generate credit and churn-related metrics based on pattern.

        Patterns:
        - "stable": no churn, low dormancy (0-30 days), active customer
        - "churning": churned, high dormancy (90-180 days), declining engagement
        - "at_risk": no churn yet, medium dormancy (30-60 days), warning signs
        - "churned": churned, very high dormancy (180+ days), inactive for long time
        """
        if churn_pattern == "stable":
            return {
                "credit_limit": self.rng.uniform(8000, 25000),
                "current_balance": self.rng.uniform(1000, 5000),
                "annual_income": self.rng.uniform(30000, 120000),
                "is_churned": 0,
                "support_tickets_count": int(self.rng.poisson(1)),
                "complaint_severity": "LOW",
                "campaigns_opened": int(self.rng.integers(3, 10)),
                "campaigns_clicked": int(self.rng.integers(1, 5)),
                "max_payment_delay_days": int(self.rng.integers(0, 5)),
                "total_late_payments": 0,
            }
        elif churn_pattern == "churning":
            return {
                "credit_limit": self.rng.uniform(5000, 15000),
                "current_balance": self.rng.uniform(8000, 15000),
                "annual_income": self.rng.uniform(25000, 80000),
                "is_churned": 1,
                "support_tickets_count": int(self.rng.poisson(5)),
                "complaint_severity": "HIGH",
                "campaigns_opened": int(self.rng.integers(0, 3)),
                "campaigns_clicked": int(self.rng.integers(0, 1)),
                "max_payment_delay_days": int(self.rng.integers(10, 30)),
                "total_late_payments": int(self.rng.integers(1, 5)),
            }
        elif churn_pattern == "at_risk":
            return {
                "credit_limit": self.rng.uniform(10000, 30000),
                "current_balance": self.rng.uniform(2000, 8000),
                "annual_income": self.rng.uniform(40000, 150000),
                "is_churned": 0,
                "support_tickets_count": int(self.rng.poisson(3)),
                "complaint_severity": "MEDIUM",
                "campaigns_opened": int(self.rng.integers(2, 7)),
                "campaigns_clicked": int(self.rng.integers(0, 3)),
                "max_payment_delay_days": int(self.rng.integers(5, 15)),
                "total_late_payments": 0,
            }
        else:  # churned
            return {
                "credit_limit": self.rng.uniform(3000, 10000),
                "current_balance": self.rng.uniform(5000, 9000),
                "annual_income": self.rng.uniform(20000, 60000),
                "is_churned": 1,
                "support_tickets_count": int(self.rng.poisson(2)),
                "complaint_severity": "MEDIUM",
                "campaigns_opened": int(self.rng.integers(0, 2)),
                "campaigns_clicked": 0,
                "max_payment_delay_days": 0,
                "total_late_payments": 0,
            }

    def _get_churn_pattern(self, customer_idx: int) -> str:
        """Assign churn pattern to customer based on distribution.

        Distribution:
        - 40% stable (no churn)
        - 30% churning (churned)
        - 20% at_risk (no churn but at risk)
        - 10% churned (long-term inactive)
        """
        ratio = customer_idx / self.n_customers
        if ratio < 0.40:
            return "stable"
        elif ratio < 0.70:
            return "churning"
        elif ratio < 0.90:
            return "at_risk"
        else:
            return "churned"

    def save_to_db(self, db_session, batch_size: int = 1000):
        """Save generated data to database in batches.

        Args:
            db_session: SQLAlchemy session
            batch_size: Number of records to insert per batch

        Note: Requires db_session to have Transaction and Customer models imported.
        """
        from sqlalchemy.orm import Session
        from ..db.models import Customer, Transaction
        from datetime import datetime, timezone

        # Generate data
        df = self.generate()

        # Extract unique customers and insert with churn metrics
        customers_df = df[["customer_id", "pattern"]].drop_duplicates()
        customers_to_insert = []

        for idx, (_, row) in enumerate(customers_df.iterrows()):
            customer_transactions = df[df["customer_id"] == row["customer_id"]]

            # Get churn pattern and metrics
            churn_pattern = self._get_churn_pattern(idx)
            churn_metrics = self._generate_churn_metrics(churn_pattern)

            customer = Customer(
                id=row["customer_id"],
                pattern=row["pattern"],
                first_transaction_date=customer_transactions["date"].min(),
                last_transaction_date=customer_transactions["date"].max(),
                # Add churn-related fields
                credit_limit=churn_metrics["credit_limit"],
                current_balance=churn_metrics["current_balance"],
                annual_income=churn_metrics["annual_income"],
                is_churned=churn_metrics["is_churned"],
                support_tickets_count=churn_metrics["support_tickets_count"],
                complaint_severity=churn_metrics["complaint_severity"],
                campaigns_opened=churn_metrics["campaigns_opened"],
                campaigns_clicked=churn_metrics["campaigns_clicked"],
                max_payment_delay_days=churn_metrics["max_payment_delay_days"],
                total_late_payments=churn_metrics["total_late_payments"],
            )
            customers_to_insert.append(customer)

        db_session.bulk_save_objects(customers_to_insert)
        db_session.commit()

        # Insert transactions in batches
        transactions_batch = []
        for _, row in df.iterrows():
            transaction_dict = {
                "id": row["transaction_id"],
                "customer_id": row["customer_id"],
                "date": row["date"],
                "amount": row["amount"],
                "mcc": row["mcc"],
                "mcc_category": row["mcc_category"],
                "channel": row["channel"],
                "merchant": row["merchant"],
                "country": row["country"],
                "time_of_day": row["time_of_day"],
            }
            transactions_batch.append(transaction_dict)

            if len(transactions_batch) >= batch_size:
                db_session.bulk_insert_mappings(Transaction, transactions_batch)
                db_session.commit()
                transactions_batch = []

        # Insert remaining
        if transactions_batch:
            db_session.bulk_insert_mappings(Transaction, transactions_batch)
            db_session.commit()
