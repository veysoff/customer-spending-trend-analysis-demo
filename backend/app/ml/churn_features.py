"""Feature engineering for churn prediction (UC-2 Phase 5B)."""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..db.models import Customer, Transaction


class ChurnFeatureEngineer:
    """Engineer features for churn prediction from customer and transaction data."""

    @staticmethod
    def engineer_churn_features(customer_id: str, db: Session) -> Dict[str, float]:
        """Calculate all 15 churn prediction features for a customer.

        Args:
            customer_id: Customer ID to calculate features for
            db: Database session

        Returns:
            Dictionary with all 15 features:
            - 7 UC-1 trends (trend_slope, spending_volatility, category_entropy,
              transaction_count_trend, pos_ratio, online_ratio, avg_transaction_amount)
            - 8 UC-2 credit metrics (utilization_ratio, dormancy_days,
              payment_delay_score, support_sentiment_score, campaign_engagement_score,
              account_age_months, balance_to_spending_ratio, inactive_months_count)
        """
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        features = {}

        # UC-1 Features (7 trends)
        features["trend_slope"] = ChurnFeatureEngineer._calculate_trend_slope(customer_id, db)
        features["spending_volatility"] = ChurnFeatureEngineer._calculate_spending_volatility(customer_id, db)
        features["category_entropy"] = ChurnFeatureEngineer._calculate_category_entropy(customer_id, db)
        features["transaction_count_trend"] = ChurnFeatureEngineer._calculate_transaction_count_trend(customer_id, db)
        features["pos_ratio"] = ChurnFeatureEngineer._calculate_pos_ratio(customer_id, db)
        features["online_ratio"] = ChurnFeatureEngineer._calculate_online_ratio(customer_id, db)
        features["avg_transaction_amount"] = ChurnFeatureEngineer._calculate_avg_transaction_amount(customer_id, db)

        # UC-2 Features (8 credit metrics)
        features["utilization_ratio"] = ChurnFeatureEngineer.calculate_utilization_ratio(customer)
        features["dormancy_days"] = ChurnFeatureEngineer.calculate_dormancy(customer)
        features["payment_delay_score"] = ChurnFeatureEngineer.calculate_payment_delay_score(customer)
        features["support_sentiment_score"] = ChurnFeatureEngineer.calculate_support_sentiment(customer)
        features["campaign_engagement_score"] = ChurnFeatureEngineer.calculate_engagement_score(customer)
        features["account_age_months"] = ChurnFeatureEngineer.calculate_account_age_months(customer)
        features["balance_to_spending_ratio"] = ChurnFeatureEngineer.calculate_balance_to_spending_ratio(customer, db)
        features["inactive_months_count"] = ChurnFeatureEngineer.calculate_inactive_months_count(customer, db)

        return features

    @staticmethod
    def engineer_churn_features_bulk(customers: List, db: Session) -> Dict[str, Dict[str, float]]:
        """Bulk feature engineering: single DB query for all transactions, then distribute.

        Optimizes for batch processing by loading all transactions once instead of
        making N separate queries for N customers. Reduces DB roundtrips from ~105 to 1.

        Args:
            customers: List of Customer ORM objects to calculate features for
            db: Database session

        Returns:
            Dictionary mapping customer_id → features_dict (same format as engineer_churn_features)
        """
        import logging
        logger = logging.getLogger(__name__)

        customer_ids = [c.id for c in customers]
        if not customer_ids:
            return {}

        # OPTIMIZATION: Single DB query for all transactions for all customers
        rows = db.query(Transaction).filter(
            Transaction.customer_id.in_(customer_ids)
        ).all()

        # Group transactions by customer_id into lists for DataFrame building
        tx_map: Dict[str, List] = {cid: [] for cid in customer_ids}
        for tx in rows:
            if tx.customer_id in tx_map:
                tx_map[tx.customer_id].append({
                    "date": tx.date,
                    "amount": tx.amount,
                    "mcc_category": tx.mcc_category,
                    "channel": tx.channel,
                })

        # Calculate features for each customer using pre-loaded transaction data
        results = {}
        for customer in customers:
            cid = customer.id
            try:
                # Build DataFrame from pre-loaded transactions
                df = pd.DataFrame(tx_map.get(cid, []))

                # Calculate features without additional DB queries (except for non-transaction data)
                features = {}

                # UC-1 Features (7 trends) - calculated from pre-loaded df
                features["trend_slope"] = ChurnFeatureEngineer._calculate_trend_slope_from_df(df)
                features["spending_volatility"] = ChurnFeatureEngineer._calculate_spending_volatility_from_df(df)
                features["category_entropy"] = ChurnFeatureEngineer._calculate_category_entropy_from_df(df)
                features["transaction_count_trend"] = ChurnFeatureEngineer._calculate_transaction_count_trend_from_df(df)
                features["pos_ratio"] = ChurnFeatureEngineer._calculate_pos_ratio_from_df(df)
                features["online_ratio"] = ChurnFeatureEngineer._calculate_online_ratio_from_df(df)
                features["avg_transaction_amount"] = ChurnFeatureEngineer._calculate_avg_transaction_amount_from_df(df)

                # UC-2 Features (8 credit metrics) - these don't need DB queries (come from Customer record)
                features["utilization_ratio"] = ChurnFeatureEngineer.calculate_utilization_ratio(customer)
                features["dormancy_days"] = ChurnFeatureEngineer.calculate_dormancy(customer)
                features["payment_delay_score"] = ChurnFeatureEngineer.calculate_payment_delay_score(customer)
                features["support_sentiment_score"] = ChurnFeatureEngineer.calculate_support_sentiment(customer)
                features["campaign_engagement_score"] = ChurnFeatureEngineer.calculate_engagement_score(customer)
                features["account_age_months"] = ChurnFeatureEngineer.calculate_account_age_months(customer)
                features["balance_to_spending_ratio"] = ChurnFeatureEngineer.calculate_balance_to_spending_ratio(customer, db)
                features["inactive_months_count"] = ChurnFeatureEngineer.calculate_inactive_months_count(customer, db)

                results[cid] = features

            except Exception as e:
                logger.warning(f"Feature engineering failed for customer {cid}: {e}")

        return results

    # ========== DATAFRAME-BASED FEATURE HELPERS (for bulk loading) ==========
    # These are fast versions of the trend calculation methods that work with pre-loaded DataFrames

    @staticmethod
    def _calculate_trend_slope_from_df(df: pd.DataFrame) -> float:
        """Calculate trend slope from pre-loaded transaction DataFrame."""
        if df.empty or len(df) < 2:
            return 0.0

        df_copy = df.copy()
        df_copy["date"] = pd.to_datetime(df_copy["date"], errors="coerce")

        # Filter out NULL dates/amounts
        df_copy = df_copy.dropna(subset=["date", "amount"])

        if len(df_copy) < 2:
            return 0.0

        # Group by month and sum amounts
        df_copy["month"] = df_copy["date"].dt.strftime("%Y-%m")
        monthly_spending = df_copy.groupby("month")["amount"].sum()

        if len(monthly_spending) < 2:
            return 0.0

        x = np.arange(len(monthly_spending))
        y = np.array(monthly_spending.values)
        slope = np.polyfit(x, y, 1)[0]
        return float(slope)

    @staticmethod
    def _calculate_spending_volatility_from_df(df: pd.DataFrame) -> float:
        """Calculate spending volatility from pre-loaded transaction DataFrame."""
        if df.empty or len(df) < 2:
            return 0.0

        amounts = df["amount"].dropna()

        if len(amounts) < 2:
            return 0.0

        mean = amounts.mean()
        if mean == 0:
            return 0.0

        volatility = amounts.std() / mean
        return float(min(volatility, 10.0))

    @staticmethod
    def _calculate_category_entropy_from_df(df: pd.DataFrame) -> float:
        """Calculate category diversity from pre-loaded transaction DataFrame."""
        if df.empty:
            return 0.0

        # Count transactions by category (skip NULL categories)
        category_counts = df["mcc_category"].dropna().value_counts()

        if len(category_counts) == 0:
            return 0.0

        # Calculate Shannon entropy
        total = category_counts.sum()
        if total == 0:
            return 0.0

        entropy = 0.0
        for count in category_counts.values:
            if count > 0:
                prob = count / total
                entropy -= prob * np.log2(prob)

        return float(entropy)

    @staticmethod
    def _calculate_transaction_count_trend_from_df(df: pd.DataFrame) -> float:
        """Calculate transaction frequency trend from pre-loaded transaction DataFrame."""
        if df.empty or len(df) < 2:
            return 0.0

        df_copy = df.copy()
        df_copy["date"] = pd.to_datetime(df_copy["date"], errors="coerce")
        df_copy = df_copy.dropna(subset=["date"])

        if len(df_copy) < 2:
            return 0.0

        # Group by month and count
        df_copy["month"] = df_copy["date"].dt.strftime("%Y-%m")
        monthly_counts = df_copy.groupby("month").size()

        if len(monthly_counts) < 2:
            return 0.0

        x = np.arange(len(monthly_counts))
        y = np.array(monthly_counts.values)
        trend = np.polyfit(x, y, 1)[0]
        result = float(trend)
        return result if np.isfinite(result) else 0.0

    @staticmethod
    def _calculate_pos_ratio_from_df(df: pd.DataFrame) -> float:
        """Calculate POS transaction ratio from pre-loaded transaction DataFrame."""
        if df.empty:
            return 0.0

        total = len(df)
        pos_count = (df["channel"] == "POS").sum()

        return float(pos_count / total) if total > 0 else 0.0

    @staticmethod
    def _calculate_online_ratio_from_df(df: pd.DataFrame) -> float:
        """Calculate ONLINE transaction ratio from pre-loaded transaction DataFrame."""
        if df.empty:
            return 0.0

        total = len(df)
        online_count = (df["channel"] == "ONLINE").sum()

        return float(online_count / total) if total > 0 else 0.0

    @staticmethod
    def _calculate_avg_transaction_amount_from_df(df: pd.DataFrame) -> float:
        """Calculate average transaction amount from pre-loaded transaction DataFrame."""
        if df.empty:
            return 0.0

        avg_amount = df["amount"].mean()
        return float(avg_amount) if pd.notna(avg_amount) else 0.0

    # ========== UC-2 FEATURE METHODS (8 CHURN-SPECIFIC) ==========

    @staticmethod
    def calculate_utilization_ratio(customer: Customer) -> float:
        """Calculate credit utilization ratio (current_balance / credit_limit).

        Range: 0.0 to 1.0+
        - High utilization (>0.8) indicates high debt/activity
        - Low utilization (<0.2) indicates inactive account
        """
        # Safe NULL checks for both values
        if not customer.credit_limit or customer.credit_limit == 0:
            return 0.0

        balance = customer.current_balance if customer.current_balance is not None else 0.0
        if balance == 0:
            return 0.0

        utilization = balance / customer.credit_limit
        return min(utilization, 2.0)  # Cap at 2.0

    @staticmethod
    def calculate_dormancy(customer: Customer) -> float:
        """Calculate days since last transaction (timezone-aware).

        Metric of inactivity/dormancy:
        - 0-30 days: Active
        - 30-60 days: Moderately active
        - 60-180 days: Inactive warning
        - 180+ days: Churned/dormant
        """
        if not customer.last_transaction_date:
            return 365  # No transactions = very dormant

        last_transaction = customer.last_transaction_date
        now = datetime.now(timezone.utc)

        # Ensure last_transaction is timezone-aware for comparison
        if last_transaction.tzinfo is None:
            last_transaction = last_transaction.replace(tzinfo=timezone.utc)

        days_since = (now - last_transaction).days
        return float(max(0, days_since))

    @staticmethod
    def calculate_payment_delay_score(customer: Customer) -> float:
        """Calculate payment behavior risk score (0.0 to 1.0).

        Weighted combination:
        - max_payment_delay_days (weight 0.6): 60+ days = full risk
        - total_late_payments (weight 0.4): 5+ payments = full risk
        """
        # Normalize delay days to 0.0-1.0 (60 days = max risk)
        max_delay_normalized = 0.0
        if customer.max_payment_delay_days:
            max_delay_normalized = min(customer.max_payment_delay_days / 60.0, 1.0)

        # Normalize late payments to 0.0-1.0 (5 payments = max risk)
        late_payments_normalized = 0.0
        if customer.total_late_payments:
            late_payments_normalized = min(customer.total_late_payments / 5.0, 1.0)

        # Weighted combination
        score = (max_delay_normalized * 0.6) + (late_payments_normalized * 0.4)
        return float(min(score, 1.0))

    @staticmethod
    def calculate_support_sentiment(customer: Customer) -> float:
        """Calculate customer support satisfaction score (0.0 to 1.0).

        Lower score = higher issues:
        - support_tickets_count: Each ticket -0.1 (max -0.5)
        - complaint_severity: HIGH -0.3, MEDIUM -0.15, LOW -0.05
        """
        score = 1.0

        # Support tickets reduce score
        if customer.support_tickets_count:
            tickets_penalty = min(customer.support_tickets_count * 0.1, 0.5)
            score -= tickets_penalty

        # Complaint severity reduces score
        if customer.complaint_severity:
            severity_penalty = {
                "HIGH": 0.3,
                "MEDIUM": 0.15,
                "LOW": 0.05,
            }.get(customer.complaint_severity, 0.0)
            score -= severity_penalty

        return max(score, 0.0)

    @staticmethod
    def calculate_engagement_score(customer: Customer) -> float:
        """Calculate marketing engagement score (0.0 to 1.0).

        Based on campaign interaction:
        - campaigns_opened: Number of emails opened
        - campaigns_clicked: Number of links clicked
        - Score: (opened + clicked*1.5) / max_engagement_cap
        """
        max_engagement = 20.0

        opened = customer.campaigns_opened or 0
        clicked = customer.campaigns_clicked or 0

        engagement = opened + (clicked * 1.5)
        score = min(engagement / max_engagement, 1.0)

        return score

    @staticmethod
    def calculate_account_age_months(customer: Customer) -> float:
        """Calculate account age in months.

        Older accounts (established customers) are lower risk.
        """
        if not customer.created_at:
            return 0.0

        created = customer.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - created).days
        if age_days < 0:
            age_days = 0  # created_at in future → treat as new account
        age_months = age_days / 30.44
        return float(age_months)

    @staticmethod
    def calculate_balance_to_spending_ratio(customer: Customer, db: Session) -> float:
        """Calculate ratio of current balance to average monthly spending.

        - Low ratio: Customer is actively spending (healthy)
        - High ratio: Customer has high balance, not spending (potential churn)
        """
        if not customer.id:
            return 0.0

        # Get average monthly spending from transactions (precise calculation)
        now = datetime.now(timezone.utc)
        six_months_ago = now - timedelta(days=180)

        recent_transactions = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.customer_id == customer.id,
                Transaction.date >= six_months_ago
            )
        ).scalar()

        if not recent_transactions or recent_transactions == 0:
            # No spending in 6 months = high churn signal → return max ratio
            return 10.0

        # Calculate exact number of days and convert to months (more accurate)
        days_elapsed = (now - six_months_ago).days
        if days_elapsed <= 0:
            days_elapsed = 1  # Avoid division by zero

        months_elapsed = days_elapsed / 30.44  # Average days per month
        monthly_spending = recent_transactions / months_elapsed

        if monthly_spending == 0:
            return 0.0

        ratio = customer.current_balance / monthly_spending
        return min(ratio, 10.0)  # Cap at 10

    @staticmethod
    def calculate_inactive_months_count(customer: Customer, db: Session) -> float:
        """Calculate how many of the last 6 months had no transactions.

        0-6 months inactive:
        - 0 months: Fully active
        - 3 months: Partially active
        - 6 months: Completely inactive
        """
        if not customer.id:
            return 0.0

        inactive_months = 0

        now = datetime.now(timezone.utc)
        for months_back in range(6):
            # months_back=0 → current month (now-30d to now)
            # months_back=1 → previous month (now-60d to now-30d), etc.
            month_end = now - timedelta(days=30 * months_back)
            month_start = now - timedelta(days=30 * (months_back + 1))

            transactions_in_month = (
                db.query(func.count(Transaction.id))
                .filter(
                    and_(
                        Transaction.customer_id == customer.id,
                        Transaction.date >= month_start,
                        Transaction.date <= month_end,
                    )
                )
                .scalar()
            )

            if transactions_in_month == 0:
                inactive_months += 1

        return float(inactive_months)

    # ========== UC-1 FEATURE METHODS (7 TRENDS) ==========

    @staticmethod
    def _calculate_trend_slope(customer_id: str, db: Session) -> float:
        """Calculate trend slope (monthly spending trend).

        Positive slope: Increasing spending (healthy)
        Negative slope: Decreasing spending (churn signal)
        """
        transactions = db.query(Transaction).filter(
            Transaction.customer_id == customer_id
        ).order_by(Transaction.date).all()

        if len(transactions) < 2:
            return 0.0

        # Group by month and sum amounts (safe NULL handling)
        monthly_spending = {}
        for txn in transactions:
            # Skip transactions with NULL date or NULL amount
            if txn.date is None or txn.amount is None:
                continue

            month_key = txn.date.strftime("%Y-%m")
            monthly_spending[month_key] = monthly_spending.get(month_key, 0) + txn.amount

        if len(monthly_spending) < 2:
            return 0.0

        # Calculate linear regression slope
        months = sorted(monthly_spending.keys())
        amounts = [monthly_spending[m] for m in months]
        x = np.arange(len(amounts))
        y = np.array(amounts)

        slope = np.polyfit(x, y, 1)[0]
        return float(slope)

    @staticmethod
    def _calculate_spending_volatility(customer_id: str, db: Session) -> float:
        """Calculate spending volatility (coefficient of variation).

        Low volatility: Consistent spender (stable)
        High volatility: Erratic spending (unstable)
        """
        transactions = db.query(Transaction).filter(
            Transaction.customer_id == customer_id
        ).all()

        if len(transactions) < 2:
            return 0.0

        # Filter out NULL amounts (avoid numpy crash)
        amounts = [t.amount for t in transactions if t.amount is not None]

        if len(amounts) < 2:
            return 0.0

        mean = np.mean(amounts)

        if mean == 0:
            return 0.0

        volatility = np.std(amounts) / mean
        return float(min(volatility, 10.0))

    @staticmethod
    def _calculate_category_entropy(customer_id: str, db: Session) -> float:
        """Calculate category diversity (Shannon entropy).

        High entropy: Diverse spending (healthy)
        Low entropy: Concentrated spending (risky)
        """
        transactions = db.query(Transaction).filter(
            Transaction.customer_id == customer_id
        ).all()

        if len(transactions) == 0:
            return 0.0

        # Count transactions by category (skip NULL categories)
        category_counts = {}
        for t in transactions:
            cat = t.mcc_category

            # Skip NULL categories (not a valid category)
            if cat is None:
                continue

            category_counts[cat] = category_counts.get(cat, 0) + 1

        # If no valid categories, return 0
        if len(category_counts) == 0:
            return 0.0

        # Calculate Shannon entropy
        total = sum(category_counts.values())  # Count only valid transactions
        if total == 0:
            return 0.0

        entropy = 0.0
        for count in category_counts.values():
            if count > 0:
                prob = count / total
                entropy -= prob * np.log2(prob)

        return float(entropy)

    @staticmethod
    def _calculate_transaction_count_trend(customer_id: str, db: Session) -> float:
        """Calculate transaction frequency trend.

        Increasing: More transactions over time (healthy)
        Decreasing: Fewer transactions (churn signal)
        """
        transactions = db.query(Transaction).filter(
            Transaction.customer_id == customer_id
        ).order_by(Transaction.date).all()

        if len(transactions) < 2:
            return 0.0

        # Group by month and count
        monthly_counts = {}
        for txn in transactions:
            # Skip transactions with NULL date (Issue #16 fix)
            if txn.date is None:
                continue

            month_key = txn.date.strftime("%Y-%m")
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1

        if len(monthly_counts) < 2:
            return 0.0

        months = sorted(monthly_counts.keys())
        counts = [monthly_counts[m] for m in months]
        x = np.arange(len(counts))
        y = np.array(counts)

        trend = np.polyfit(x, y, 1)[0]
        result = float(trend)
        return result if np.isfinite(result) else 0.0

    @staticmethod
    def _calculate_pos_ratio(customer_id: str, db: Session) -> float:
        """Calculate POS (in-store) transaction ratio.

        Range: 0.0 to 1.0
        Optimized: single query with conditional aggregation (no N+1).
        """
        result = db.query(
            func.count(Transaction.id).label("total"),
            func.sum(func.cast(Transaction.channel == "POS", db.Integer)).label("pos_count")
        ).filter(
            Transaction.customer_id == customer_id
        ).first()

        if not result or result.total == 0:
            return 0.0

        return float(result.pos_count / result.total) if result.total > 0 else 0.0

    @staticmethod
    def _calculate_online_ratio(customer_id: str, db: Session) -> float:
        """Calculate ONLINE transaction ratio.

        Range: 0.0 to 1.0
        Optimized: single query with conditional aggregation (no N+1).
        """
        result = db.query(
            func.count(Transaction.id).label("total"),
            func.sum(func.cast(Transaction.channel == "ONLINE", db.Integer)).label("online_count")
        ).filter(
            Transaction.customer_id == customer_id
        ).first()

        if not result or result.total == 0:
            return 0.0

        return float(result.online_count / result.total) if result.total > 0 else 0.0

    @staticmethod
    def _calculate_avg_transaction_amount(customer_id: str, db: Session) -> float:
        """Calculate average transaction amount.

        Range: $0 to $10,000+
        """
        avg_amount = db.query(func.avg(Transaction.amount)).filter(
            Transaction.customer_id == customer_id
        ).scalar()

        return float(avg_amount) if avg_amount else 0.0
