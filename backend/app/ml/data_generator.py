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

    def save_to_db(self, db_session, batch_size: int = 1000):
        """Save generated data to database in batches.

        Args:
            db_session: SQLAlchemy session
            batch_size: Number of records to insert per batch

        Note: Requires db_session to have Transaction and Customer models imported.
        """
        from sqlalchemy.orm import Session
        from ..db.models import Customer, Transaction

        # Generate data
        df = self.generate()

        # Extract unique customers and insert
        customers_df = df[["customer_id", "pattern"]].drop_duplicates()
        customers_to_insert = []

        for _, row in customers_df.iterrows():
            customer_transactions = df[df["customer_id"] == row["customer_id"]]
            customer = Customer(
                id=row["customer_id"],
                pattern=row["pattern"],
                first_transaction_date=customer_transactions["date"].min(),
                last_transaction_date=customer_transactions["date"].max(),
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
