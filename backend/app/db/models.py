"""SQLAlchemy ORM models for banking data."""

from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Customer(Base):
    """Customer profile with behavioral pattern."""

    __tablename__ = "customers"

    id = Column(String(50), primary_key=True, index=True)
    pattern = Column(String(20), nullable=False)  # normal, silent_churn, lifestyle_shift
    first_transaction_date = Column(DateTime, nullable=True)
    last_transaction_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_customer_pattern", "pattern"),
    )

    def __repr__(self):
        return f"<Customer(id={self.id}, pattern={self.pattern})>"


class Transaction(Base):
    """Individual banking transaction."""

    __tablename__ = "transactions"

    id = Column(String(50), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    mcc = Column(String(10), nullable=False)
    mcc_category = Column(String(50), nullable=False, index=True)
    channel = Column(String(20), nullable=False)
    merchant = Column(String(100), nullable=False)
    country = Column(String(2), nullable=False)
    time_of_day = Column(String(5), nullable=False)

    # Composite index for customer time series queries
    __table_args__ = (
        Index("idx_customer_date", "customer_id", "date"),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, customer_id={self.customer_id}, amount={self.amount})>"


class CustomerRiskProfile(Base):
    """ML-generated risk profile for customer."""

    __tablename__ = "customer_risk_profiles"

    customer_id = Column(String(50), ForeignKey("customers.id"), primary_key=True, index=True)
    churn_risk = Column(Float, default=0.0)  # 0.0-1.0 probability
    risk_category = Column(String(20), default="LOW")  # LOW, MEDIUM, HIGH, CRITICAL
    primary_signal = Column(String(200), nullable=True)
    recommended_action = Column(String(500), nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CustomerRiskProfile(customer_id={self.customer_id}, risk={self.risk_category})>"
