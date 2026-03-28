"""SQLAlchemy ORM models for banking data."""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime, timezone


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Customer(Base):
    """Customer profile with behavioral pattern and persona metadata."""

    __tablename__ = "customers"

    id = Column(String(50), primary_key=True, index=True)
    pattern = Column(String(20), nullable=False)  # normal, silent_churn, lifestyle_shift
    first_transaction_date = Column(DateTime, nullable=True)
    last_transaction_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Persona metadata (nullable for backward compatibility)
    persona_id = Column(Integer, nullable=True)
    persona_name = Column(String(50), nullable=True)
    persona_tier = Column(String(20), nullable=True)  # stable, at_risk, anomaly, growth
    persona_seed = Column(Integer, nullable=True)
    narrative = Column(String(1000), nullable=True)
    expected_risk_score = Column(Float, nullable=True)
    generation_timestamp = Column(DateTime, nullable=True)

    # Credit/Account Management (UC-2 Phase 5)
    credit_limit = Column(Float, nullable=True, default=5000.0)
    current_balance = Column(Float, nullable=True, default=0.0)
    annual_income = Column(Float, nullable=True)

    # Churn Training Label
    is_churned = Column(Integer, nullable=True, default=0)  # 0/1 binary label

    # Support/Customer Service
    support_tickets_count = Column(Integer, nullable=True, default=0)
    complaint_severity = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH

    # Marketing Engagement
    campaigns_opened = Column(Integer, nullable=True, default=0)
    campaigns_clicked = Column(Integer, nullable=True, default=0)

    # Payment Behavior
    max_payment_delay_days = Column(Integer, nullable=True, default=0)
    total_late_payments = Column(Integer, nullable=True, default=0)

    # Computed Fields
    days_since_last_transaction = Column(Integer, nullable=True)
    churn_risk_score = Column(Float, nullable=True)
    risk_category = Column(String(50), nullable=True)  # STABLE, MEDIUM, HIGH, CRITICAL
    primary_signal = Column(String(255), nullable=True)  # Main churn indicator
    recommended_action = Column(String(255), nullable=True)  # Suggested action
    churn_prediction_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Relationship for eager loading
    transactions = relationship("Transaction", back_populates="customer", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("idx_customer_pattern", "pattern"),
        Index("idx_customer_persona_id", "persona_id"),
        Index("idx_customer_persona_name", "persona_name"),
    )

    def __repr__(self):
        persona_info = f", persona={self.persona_name}" if self.persona_name else ""
        return f"<Customer(id={self.id}, pattern={self.pattern}{persona_info})>"


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

    # Relationship for back reference
    customer = relationship("Customer", back_populates="transactions")

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
    calculated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<CustomerRiskProfile(customer_id={self.customer_id}, risk={self.risk_category})>"


class AIInterpretation(Base):
    """Cached AI-generated narratives for customers (Phase 5E)."""

    __tablename__ = "ai_interpretations"

    customer_id = Column(String(50), ForeignKey("customers.id"), primary_key=True, index=True)
    summary = Column(String(20), nullable=False)  # HEALTHY, MEDIUM, WARNING, CRITICAL
    summary_icon = Column(String(10), nullable=True)  # Emoji icon (🟢 🟡 🔴)
    risk_category = Column(String(50), nullable=True)  # Risk category name
    key_findings = Column(String(2000), nullable=True)  # JSON array
    business_advice = Column(String(1000), nullable=True)
    technical_evidence = Column(String(2000), nullable=True)  # JSON
    confidence_score = Column(Float, default=0.0)
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Cache TTL

    def __repr__(self):
        return f"<AIInterpretation(customer_id={self.customer_id}, summary={self.summary})>"
