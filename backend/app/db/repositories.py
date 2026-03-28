"""Repository pattern for data access abstraction."""

from typing import List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .models import Customer, Transaction, CustomerRiskProfile


class CustomerRepository:
    """Repository for customer-related data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy session
        """
        self.db = db

    def get_by_id(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID.

        Args:
            customer_id: Customer identifier (e.g., 'customer_000001')

        Returns:
            Customer object or None if not found
        """
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def get_all(self, limit: int = None) -> List[Customer]:
        """Get all customers.

        Args:
            limit: Maximum number of customers to return

        Returns:
            List of Customer objects
        """
        query = self.db.query(Customer)
        if limit:
            query = query.limit(limit)
        return query.all()

    def get_all_at_risk(self, threshold: float = 0.6, limit: int = 10) -> List[Customer]:
        """Get customers with high churn risk.

        Args:
            threshold: Minimum risk score (0.0-1.0)
            limit: Maximum number of customers to return

        Returns:
            List of Customer objects ordered by risk score (descending)
        """
        # Join with risk profiles and filter by threshold
        customers = (
            self.db.query(Customer)
            .join(CustomerRiskProfile)
            .filter(CustomerRiskProfile.churn_risk >= threshold)
            .order_by(desc(CustomerRiskProfile.churn_risk))
            .limit(limit)
            .all()
        )
        return customers

    def get_customer_with_transactions(
        self, customer_id: str
    ) -> Tuple[Optional[Customer], List[Transaction]]:
        """Get customer profile with all transactions.

        Args:
            customer_id: Customer identifier

        Returns:
            Tuple of (Customer object, list of Transaction objects)
        """
        customer = self.get_by_id(customer_id)
        if not customer:
            return None, []

        transactions = (
            self.db.query(Transaction)
            .filter(Transaction.customer_id == customer_id)
            .order_by(Transaction.date)
            .all()
        )

        return customer, transactions

    def get_customer_count(self) -> int:
        """Get total number of customers.

        Returns:
            Number of customers in database
        """
        return self.db.query(Customer).count()

    def get_customers_by_pattern(self, pattern: str) -> List[Customer]:
        """Get customers by behavior pattern.

        Args:
            pattern: Behavior pattern ('normal', 'silent_churn', 'lifestyle_shift')

        Returns:
            List of Customer objects with matching pattern
        """
        return self.db.query(Customer).filter(Customer.pattern == pattern).all()


class TransactionRepository:
    """Repository for transaction-related data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy session
        """
        self.db = db

    def get_by_customer_id(self, customer_id: str) -> List[Transaction]:
        """Get all transactions for a customer.

        Args:
            customer_id: Customer identifier

        Returns:
            List of Transaction objects ordered by date
        """
        return (
            self.db.query(Transaction)
            .filter(Transaction.customer_id == customer_id)
            .order_by(Transaction.date)
            .all()
        )

    def get_by_date_range(
        self, customer_id: str, start_date: datetime, end_date: datetime
    ) -> List[Transaction]:
        """Get transactions for customer within date range.

        Args:
            customer_id: Customer identifier
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of Transaction objects ordered by date
        """
        return (
            self.db.query(Transaction)
            .filter(
                Transaction.customer_id == customer_id,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
            )
            .order_by(Transaction.date)
            .all()
        )

    def get_by_mcc_category(self, customer_id: str, category: str) -> List[Transaction]:
        """Get transactions for customer in specific MCC category.

        Args:
            customer_id: Customer identifier
            category: MCC category (e.g., 'GROCERY', 'RESTAURANTS')

        Returns:
            List of Transaction objects
        """
        return (
            self.db.query(Transaction)
            .filter(
                Transaction.customer_id == customer_id,
                Transaction.mcc_category == category,
            )
            .all()
        )

    def get_by_channel(self, customer_id: str, channel: str) -> List[Transaction]:
        """Get transactions for customer in specific channel.

        Args:
            customer_id: Customer identifier
            channel: Channel (e.g., 'POS', 'ONLINE', 'ATM', 'MOBILE')

        Returns:
            List of Transaction objects
        """
        return (
            self.db.query(Transaction)
            .filter(
                Transaction.customer_id == customer_id,
                Transaction.channel == channel,
            )
            .all()
        )

    def get_transaction_count(self, customer_id: str) -> int:
        """Get number of transactions for customer.

        Args:
            customer_id: Customer identifier

        Returns:
            Number of transactions
        """
        return (
            self.db.query(Transaction)
            .filter(Transaction.customer_id == customer_id)
            .count()
        )

    def get_total_spending(self, customer_id: str) -> float:
        """Get total spending for customer.

        Args:
            customer_id: Customer identifier

        Returns:
            Sum of all transaction amounts
        """
        result = (
            self.db.query(Transaction)
            .filter(Transaction.customer_id == customer_id)
            .with_entities(Transaction.amount)
        )
        total = sum(t[0] for t in result.all())
        return total


class RiskProfileRepository:
    """Repository for customer risk profile management."""

    def __init__(self, db: Session):
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy session
        """
        self.db = db

    def get_by_customer_id(self, customer_id: str) -> Optional[CustomerRiskProfile]:
        """Get risk profile for customer.

        Args:
            customer_id: Customer identifier

        Returns:
            CustomerRiskProfile object or None if not found
        """
        return (
            self.db.query(CustomerRiskProfile)
            .filter(CustomerRiskProfile.customer_id == customer_id)
            .first()
        )

    def create_or_update(
        self,
        customer_id: str,
        churn_risk: float,
        risk_category: str,
        primary_signal: str = None,
        recommended_action: str = None,
    ) -> CustomerRiskProfile:
        """Create or update risk profile for customer.

        Args:
            customer_id: Customer identifier
            churn_risk: Risk score (0.0-1.0)
            risk_category: Risk category ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
            primary_signal: Primary risk signal
            recommended_action: Recommended action for customer

        Returns:
            Created or updated CustomerRiskProfile object
        """
        profile = self.get_by_customer_id(customer_id)

        if profile:
            profile.churn_risk = churn_risk
            profile.risk_category = risk_category
            profile.primary_signal = primary_signal
            profile.recommended_action = recommended_action
            profile.last_updated = datetime.now(timezone.utc)
        else:
            profile = CustomerRiskProfile(
                customer_id=customer_id,
                churn_risk=churn_risk,
                risk_category=risk_category,
                primary_signal=primary_signal,
                recommended_action=recommended_action,
            )
            self.db.add(profile)

        self.db.commit()
        return profile

    def get_high_risk_customers(self, limit: int = 10) -> List[CustomerRiskProfile]:
        """Get customers with highest churn risk.

        Args:
            limit: Maximum number of customers to return

        Returns:
            List of CustomerRiskProfile objects ordered by risk (descending)
        """
        return (
            self.db.query(CustomerRiskProfile)
            .order_by(desc(CustomerRiskProfile.churn_risk))
            .limit(limit)
            .all()
        )
