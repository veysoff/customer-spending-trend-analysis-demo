"""Demo personas for high-quality test data and presentations.

40 named customer personas showing all ML capabilities:
- 8 Stable/Healthy customers
- 8 At-Risk customers
- 8 Anomaly/High-Risk customers
- 6 Growth customers
- 10 Advanced edge cases (travelers, freelancers, crypto traders, etc.)

Each persona has deterministic, seed-based transaction generation.
"""

from datetime import datetime, timedelta, timezone
import random
import numpy as np
import pandas as pd
from typing import List, Dict


class DemoPersona:
    """Base class for demo personas with UAE localization."""

    # ============================================================================
    # UAE MERCHANT LISTS BY CATEGORY
    # ============================================================================
    _UAE_GROCERY     = ["Carrefour", "LuLu Hypermarket", "Spinneys", "Waitrose UAE", "Al Maya"]
    _UAE_RESTAURANT  = ["Zaatar w Zeit", "Al Mallah", "Tim Hortons UAE", "Paul Bakery", "Shakespeare and Co"]
    _UAE_PHARMACY    = ["Aster Pharmacy", "Boots UAE", "Life Pharmacy", "Bin Sina Pharmacy"]
    _UAE_FUEL        = ["ADNOC", "EPPCO", "Emarat"]
    _UAE_RETAIL      = ["Dubai Mall", "Mall of the Emirates", "H&M UAE", "Zara UAE", "M&S UAE"]
    _UAE_ELECTRONICS = ["Emax", "Sharaf DG", "Apple Store Dubai", "Jumbo Electronics"]
    _UAE_ATM         = ["Emirates NBD ATM", "FAB ATM", "ADCB ATM", "Mashreq ATM"]
    _UAE_HOTEL       = ["Atlantis The Palm", "Marriott UAE", "Hilton Dubai", "Rotana Hotels"]
    _UAE_AIRLINE     = ["Emirates", "Flydubai", "Air Arabia", "Etihad"]
    _UAE_ONLINE      = ["Noon.com", "Amazon.ae", "Namshi", "Carrefour Online"]

    _HOME_COUNTRY    = "AE"
    _EXPAT_TRAVEL    = ["IN", "PH", "GB", "US", "LK", "EG", "JO"]

    # UAE event dates (fixed for 2024 demo data)
    _RAMADAN_START   = datetime(2024, 3, 11, tzinfo=timezone.utc)
    _RAMADAN_END     = datetime(2024, 4, 9, tzinfo=timezone.utc)
    _EID_ALFITR      = datetime(2024, 4, 10, tzinfo=timezone.utc)
    _EID_ALADHA      = datetime(2024, 6, 17, tzinfo=timezone.utc)

    NAME = "Unknown"
    TIER = "unknown"  # stable, at_risk, anomaly, growth
    NARRATIVE = "Unknown customer profile"
    EXPECTED_RISK_SCORE = 0.5  # Expected churn risk 0-1

    def __init__(self, customer_id: str, seed: int = 42):
        self.customer_id = customer_id
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Generate transactions for this persona. Must be implemented by subclasses."""
        raise NotImplementedError

    def _generate_random_merchants(self, n: int) -> List[str]:
        """Generate random merchant names."""
        merchants = [
            "Starbucks", "Whole Foods", "Amazon", "Uber", "Netflix",
            "Target", "Walgreens", "Gas Station", "Restaurant", "Hotel",
            "Apple Store", "Best Buy", "Walmart", "Home Depot", "Nike",
        ]
        return self.rng.choice(merchants, n, replace=True).tolist()

    def _get_mcc_category(self, mcc: str) -> str:
        """Get category from MCC code."""
        mcc_to_category = {
            "5411": "grocery",
            "5412": "grocery",
            "5200": "gas",
            "5211": "home",
            "5311": "retail",
            "5411": "food",
            "5812": "restaurant",
            "7011": "hotel",
            "4111": "taxi",
            "5722": "electronics",
            "5411": "grocery",
        }
        return mcc_to_category.get(mcc, "other")

    def _uae_seasonal_multiplier(self, date: datetime) -> float:
        """Apply UAE seasonal multiplier based on Islamic calendar and local events.

        Ramadan (fasting + Iftar gatherings): +30% spending
        Eid Al Fitr (post-Ramadan): +60% (shopping peak)
        Eid Al Adha (end of pilgrimage): +40%
        Summer months (6-8, when residents travel): -25%
        Normal months: 1.0x
        """
        # Ensure date is timezone-aware for comparison
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        if self._RAMADAN_START <= date <= self._RAMADAN_END:
            return 1.30   # Iftar gatherings, food-related spending

        # Eid Al Fitr (±3 days = major shopping event)
        if abs((date - self._EID_ALFITR).days) <= 3:
            return 1.60

        # Eid Al Adha (±3 days)
        if abs((date - self._EID_ALADHA).days) <= 3:
            return 1.40

        # Summer travel season: domestic spending drops
        if date.month in (6, 7, 8):
            return 0.75

        return 1.0


# ==============================================================================
# TIER 1: Stable/Healthy Customers (Green)
# ==============================================================================


class PersonaStableJohn(DemoPersona):
    """Consistent ~5000/month, normal weekly transactions."""

    NAME = "John_Stable"
    TIER = "stable"
    NARRATIVE = "Consistent spender with predictable pattern - reliable customer"
    EXPECTED_RISK_SCORE = 0.05

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        daily_seed_counter = 0

        while current_date <= end_date:
            # ~3-5 transactions per week (~15/month)
            if self.rng.random() < 0.25:  # ~25% of days have transactions
                n_tx = self.rng.randint(1, 3)  # 1-2 transactions per day
                for _ in range(n_tx):
                    daily_seed_counter += 1
                    seed = self.seed + daily_seed_counter

                    amount = self.rng.normal(320, 50)  # ~$320 ±50
                    amount = max(10, min(1000, amount))  # Clamp between $10-1000

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": amount,
                        "mcc": "5411",
                        "mcc_category": "grocery",
                        "channel": "POS",
                        "merchant": self.rng.choice(["Whole Foods", "Trader Joe's", "Target"]),
                        "country": "US",
                        "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                    })

            current_date += timedelta(days=1)

        return transactions


class PersonaConservativeAlice(DemoPersona):
    """Very stable ~2000/month, monthly bulk purchases."""

    NAME = "Alice_Conservative"
    TIER = "stable"
    NARRATIVE = "Budget-conscious, predictable monthly purchases"
    EXPECTED_RISK_SCORE = 0.02

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            # 1 large transaction per week (~4/month) = ~500 each
            if current_date.day in [1, 8, 15, 22]:  # Weekly on specific days
                amount = self.rng.normal(450, 50)
                amount = max(100, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Walmart",
                    "country": "US",
                    "time_of_day": "morning",
                })

            current_date += timedelta(days=1)

        return transactions


class PersonaPremiumBob(DemoPersona):
    """High value ~15000/month, premium merchants, daily transactions."""

    NAME = "Bob_Premium"
    TIER = "stable"
    NARRATIVE = "Premium customer with high spending and consistent engagement"
    EXPECTED_RISK_SCORE = 0.03

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            # ~25 transactions per month
            if self.rng.random() < 0.8:
                categories = ["restaurant", "hotel", "retail", "electronics"]
                merchants = ["Michelin Restaurant", "5 Star Hotel", "Luxury Retail", "Apple Store"]

                amount = self.rng.normal(600, 150)
                amount = max(200, min(2000, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5812",
                    "mcc_category": self.rng.choice(categories),
                    "channel": "POS",
                    "merchant": self.rng.choice(merchants),
                    "country": "US",
                    "time_of_day": self.rng.choice(["lunch", "dinner", "evening"]),
                })

            current_date += timedelta(days=1)

        return transactions


class PersonaBudgetCarol(DemoPersona):
    """Tight budget ~800/month, bi-weekly small purchases."""

    NAME = "Carol_Budget"
    TIER = "stable"
    NARRATIVE = "Budget-aware customer with sporadic purchases"
    EXPECTED_RISK_SCORE = 0.04

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            # ~8 transactions per month on specific days
            if current_date.day % 14 < 2:
                amount = self.rng.normal(100, 20)
                amount = max(20, min(300, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Dollar General",
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)

        return transactions


class PersonaCyclicalDavid(DemoPersona):
    """Seasonal ~4000/month, high Dec/Jul low Jun/Sep."""

    NAME = "David_Cyclical"
    TIER = "stable"
    NARRATIVE = "Seasonal spender with holiday peaks"
    EXPECTED_RISK_SCORE = 0.03

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            # Seasonal pattern
            month = current_date.month
            if month in [12, 7]:  # December, July peaks
                base_amount = 500
            elif month in [6, 9]:  # June, September lows
                base_amount = 250
            else:
                base_amount = 350

            if self.rng.random() < 0.3:  # ~30% of days
                amount = self.rng.normal(base_amount, base_amount * 0.2)
                amount = max(50, min(1000, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Target",
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon"]),
                })

            current_date += timedelta(days=1)

        return transactions


class PersonaModestEmma(DemoPersona):
    """Consistent middle ~3200/month with slight growth."""

    NAME = "Emma_Modest"
    TIER = "stable"
    NARRATIVE = "Average customer with slight upward spending trend"
    EXPECTED_RISK_SCORE = 0.02

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Slight growth trend (+0.5%/month)
            growth_factor = 1 + (days_elapsed / 365) * 0.06
            base_amount = 250 * growth_factor

            if self.rng.random() < 0.25:
                amount = self.rng.normal(base_amount, 40)
                amount = max(50, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Trader Joe's",
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaDisciplinedFrank(DemoPersona):
    """Highly structured, exactly 2x/week same amount."""

    NAME = "Frank_Disciplined"
    TIER = "stable"
    NARRATIVE = "Most engaged, highly structured spending pattern"
    EXPECTED_RISK_SCORE = 0.01

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            # Exactly Tuesday and Friday
            if current_date.weekday() in [1, 4]:  # Tuesday (1), Friday (4)
                amount = 325 + self.rng.normal(0, 5)  # Very consistent ~$325

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Kroger",
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)

        return transactions


class PersonaIntermittentGrace(DemoPersona):
    """Variable frequency ~2500/month, 1-5 tx/week random."""

    NAME = "Grace_Intermittent"
    TIER = "stable"
    NARRATIVE = "Sporadic user, irregular purchase pattern"
    EXPECTED_RISK_SCORE = 0.06

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            # Random frequency pattern
            if self.rng.random() < 0.2:
                amount = self.rng.normal(280, 60)
                amount = max(50, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Walmart", "Target", "Costco"]),
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })

            current_date += timedelta(days=1)

        return transactions


# ==============================================================================
# TIER 2: At-Risk Customers (Yellow)
# ==============================================================================


class PersonaSilentChurnSarah(DemoPersona):
    """Spending declining 10-15% monthly, 5000 → 2500 over 6 months."""

    NAME = "Sarah_SilentChurn"
    TIER = "at_risk"
    NARRATIVE = "Declining spending trend - silent churn indicator"
    EXPECTED_RISK_SCORE = 0.78

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Linear decline: 5000 → 2500 over 6 months
            decline_factor = 1 - (days_elapsed / 180) * 0.5  # 50% decline in 6 months
            decline_factor = max(0.5, decline_factor)  # Floor at 50%
            base_amount = 300 * decline_factor

            if self.rng.random() < 0.25:
                amount = self.rng.normal(base_amount, 30)
                amount = max(20, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Whole Foods",
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaDecreasingFrequencyMike(DemoPersona):
    """15 tx/month → 5 tx/month over 6 months, amount stable."""

    NAME = "Mike_DecreasingFrequency"
    TIER = "at_risk"
    NARRATIVE = "Transaction frequency declining - behavioral change"
    EXPECTED_RISK_SCORE = 0.65

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Declining frequency: 15→5 per month = 0.5→0.17 per day
            decline_factor = 1 - (days_elapsed / 180) * 0.66  # 66% frequency decline
            decline_factor = max(0.33, decline_factor)

            if self.rng.random() < (0.5 * decline_factor):
                amount = self.rng.normal(320, 50)
                amount = max(100, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Safeway",
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaCategoryShiftLisa(DemoPersona):
    """Stable ~5000/month but shifted from groceries → health/beauty."""

    NAME = "Lisa_CategoryShift"
    TIER = "at_risk"
    NARRATIVE = "Lifestyle change detected - category distribution shift"
    EXPECTED_RISK_SCORE = 0.42

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0
        total_days = (end_date - start_date).days

        while current_date <= end_date:
            # Gradual shift: groceries first half, then health/beauty
            shift_factor = days_elapsed / total_days

            if shift_factor < 0.5:
                # First half: mostly groceries
                category = self.rng.choice(["grocery", "grocery", "grocery", "retail"], 1)[0]
                merchants = ["Whole Foods", "Trader Joe's", "Safeway", "Target"]
                mcc = "5411"
            else:
                # Second half: mostly health/beauty
                category = self.rng.choice(["health", "beauty", "pharmacy", "retail"], 1)[0]
                merchants = ["CVS", "Walgreens", "Sephora", "Sally Beauty"]
                mcc = "5912"

            if self.rng.random() < 0.25:
                amount = self.rng.normal(300, 50)
                amount = max(50, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": mcc,
                    "mcc_category": category,
                    "channel": "POS",
                    "merchant": self.rng.choice(merchants),
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon"]),
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaNegativeTrendTom(DemoPersona):
    """6000 → 3000/month steadily, every transaction smaller."""

    NAME = "Tom_NegativeTrend"
    TIER = "at_risk"
    NARRATIVE = "Steady spending decline over time - churn signal"
    EXPECTED_RISK_SCORE = 0.72

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Linear decline: 6000 → 3000 over full period
            decline_factor = 1 - (days_elapsed / 365) * 0.5
            decline_factor = max(0.5, decline_factor)
            base_amount = 350 * decline_factor

            if self.rng.random() < 0.3:
                amount = self.rng.normal(base_amount, base_amount * 0.15)
                amount = max(50, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Walmart", "Target", "Costco"]),
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon"]),
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaLowEngagementRachel(DemoPersona):
    """~1500/month, only 1-2 tx per week, slowly declining."""

    NAME = "Rachel_LowEngagement"
    TIER = "at_risk"
    NARRATIVE = "Low engagement with slow decline - dormancy risk"
    EXPECTED_RISK_SCORE = 0.55

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Slow decline: -5%/month
            decline_factor = 1 - (days_elapsed / 365) * 0.05
            decline_factor = max(0.8, decline_factor)

            # Very low frequency: 1-2 per week = ~8%/day
            if self.rng.random() < (0.08 * decline_factor):
                amount = self.rng.normal(150, 30)
                amount = max(30, min(400, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Walmart",
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaHighDormancyMark(DemoPersona):
    """Last activity 150+ days ago, previously 3000/month, now inactive."""

    NAME = "Mark_HighDormancy"
    TIER = "at_risk"
    NARRATIVE = "Dormant for 150+ days - high churn risk"
    EXPECTED_RISK_SCORE = 0.92

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0
        dormancy_start_day = 150  # Stop transactions after 150 days

        while current_date <= end_date:
            # Active only first 150 days, then completely silent
            if days_elapsed < dormancy_start_day:
                if self.rng.random() < 0.25:
                    amount = self.rng.normal(300, 50)
                    amount = max(100, min(800, amount))

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": amount,
                        "mcc": "5411",
                        "mcc_category": "grocery",
                        "channel": "POS",
                        "merchant": "Whole Foods",
                        "country": "US",
                        "time_of_day": "afternoon",
                    })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaSupportTicketsNancy(DemoPersona):
    """~4500/month stable BUT 12+ support tickets, increasing."""

    NAME = "Nancy_SupportTickets"
    TIER = "at_risk"
    NARRATIVE = "Frequent support contacts despite spending - satisfaction risk"
    EXPECTED_RISK_SCORE = 0.48

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            # Stable spending pattern
            if self.rng.random() < 0.3:
                amount = self.rng.normal(350, 50)
                amount = max(100, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Walmart", "Target"]),
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)

        return transactions


class PersonaHighUtilizationOscar(DemoPersona):
    """~8500/month, 80% of credit limit, creeping up."""

    NAME = "Oscar_HighUtilization"
    TIER = "at_risk"
    NARRATIVE = "Near credit limit and increasing - credit risk"
    EXPECTED_RISK_SCORE = 0.35

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Slight upward creep: +2%/month
            growth_factor = 1 + (days_elapsed / 365) * 0.02
            base_amount = 400 * growth_factor

            if self.rng.random() < 0.4:
                amount = self.rng.normal(base_amount, base_amount * 0.2)
                amount = max(200, min(1200, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Whole Foods", "Target", "Amazon"]),
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


# ==============================================================================
# TIER 3: Anomaly/High-Risk Customers (Red)
# ==============================================================================


class PersonaSpendingSpikeCharlie(DemoPersona):
    """Normal ~4000/month then suddenly 25000 (1 major spike)."""

    NAME = "Charlie_SpendingSpike"
    TIER = "anomaly"
    NARRATIVE = "Single spending spike detected - suspicious activity"
    EXPECTED_RISK_SCORE = 0.58

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0
        spike_day = 150  # Spike occurs at day 150

        while current_date <= end_date:
            if days_elapsed == spike_day:
                # Single massive spike
                amount = 25000
                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Costco",
                    "country": "US",
                    "time_of_day": "afternoon",
                })
            elif self.rng.random() < 0.25:
                # Normal transactions before/after spike
                amount = self.rng.normal(300, 50)
                amount = max(100, min(700, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Whole Foods",
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaMultipleSpikesDiana(DemoPersona):
    """3-4 major spikes throughout period, erratic pattern."""

    NAME = "Diana_MultipleSpikes"
    TIER = "anomaly"
    NARRATIVE = "Multiple spending spikes - highly volatile"
    EXPECTED_RISK_SCORE = 0.68

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0
        spike_days = [80, 160, 250, 330]  # 4 spikes throughout year

        while current_date <= end_date:
            if days_elapsed in spike_days:
                # Major spikes
                spike_amount = self.rng.normal(18000, 3000)
                spike_amount = max(10000, min(30000, spike_amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": spike_amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Costco", "Target", "Amazon"]),
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon"]),
                })
            elif self.rng.random() < 0.15:
                # Normal transactions between spikes
                amount = self.rng.normal(150, 40)
                amount = max(30, min(400, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Walmart",
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaTimeshiftEric(DemoPersona):
    """Normal amount but time-of-day completely shifted (9am-5pm → 11pm-3am)."""

    NAME = "Eric_Timeshift"
    TIER = "anomaly"
    NARRATIVE = "Unusual time-of-day pattern - behavioral change"
    EXPECTED_RISK_SCORE = 0.45

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Gradual shift from day to night spending
            shift_factor = days_elapsed / 365

            if shift_factor < 0.5:
                # First half: day time (9am-5pm)
                time_choices = ["morning", "afternoon"]
            else:
                # Second half: night time (11pm-3am)
                time_choices = ["evening", "night"]

            if self.rng.random() < 0.3:
                amount = self.rng.normal(300, 50)
                amount = max(100, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": "Whole Foods",
                    "country": "US",
                    "time_of_day": self.rng.choice(time_choices),
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaMerchantJumpingFiona(DemoPersona):
    """~5000/month but rapid category mixing: restaurant → electronics → medical."""

    NAME = "Fiona_MerchantJumping"
    TIER = "anomaly"
    NARRATIVE = "Unusual merchant category combinations"
    EXPECTED_RISK_SCORE = 0.52

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            if self.rng.random() < 0.3:
                # Rapidly cycle through unrelated categories
                category = self.rng.choice([
                    "restaurant", "electronics", "medical", "gas",
                    "hotel", "pharmacy", "retail", "entertainment"
                ])

                category_to_merchant = {
                    "restaurant": ["McDonald's", "Olive Garden", "Chipotle"],
                    "electronics": ["Best Buy", "Apple Store", "Best Buy"],
                    "medical": ["Walgreens", "CVS", "Hospital"],
                    "gas": ["Shell", "Chevron", "BP"],
                    "hotel": ["Marriott", "Hilton", "Airbnb"],
                    "pharmacy": ["CVS", "Walgreens"],
                    "retail": ["Target", "Walmart"],
                    "entertainment": ["Netflix", "Cinema", "Spotify"],
                }

                merchant = self.rng.choice(category_to_merchant.get(category, ["Store"]))
                amount = self.rng.normal(300, 80)
                amount = max(50, min(1000, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5812" if category == "restaurant" else "5411",
                    "mcc_category": category,
                    "channel": "POS",
                    "merchant": merchant,
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })

            current_date += timedelta(days=1)

        return transactions


class PersonaWeekendVsWeekdayGeorge(DemoPersona):
    """~4000/month but ALL weekend transactions (used to be weekday)."""

    NAME = "George_WeekendVsWeekday"
    TIER = "anomaly"
    NARRATIVE = "Complete temporal pattern shift to weekends"
    EXPECTED_RISK_SCORE = 0.38

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            shift_factor = days_elapsed / 365

            if shift_factor < 0.5:
                # First half: weekday transactions
                if current_date.weekday() in [0, 1, 2, 3, 4]:  # Mon-Fri
                    if self.rng.random() < 0.35:
                        amount = self.rng.normal(300, 50)
                        amount = max(100, min(800, amount))

                        transactions.append({
                            "customer_id": self.customer_id,
                            "date": current_date,
                            "amount": amount,
                            "mcc": "5411",
                            "mcc_category": "grocery",
                            "channel": "POS",
                            "merchant": "Whole Foods",
                            "country": "US",
                            "time_of_day": "afternoon",
                        })
            else:
                # Second half: weekend transactions only
                if current_date.weekday() in [5, 6]:  # Sat-Sun
                    if self.rng.random() < 0.5:
                        amount = self.rng.normal(300, 50)
                        amount = max(100, min(800, amount))

                        transactions.append({
                            "customer_id": self.customer_id,
                            "date": current_date,
                            "amount": amount,
                            "mcc": "5411",
                            "mcc_category": "grocery",
                            "channel": "POS",
                            "merchant": "Whole Foods",
                            "country": "US",
                            "time_of_day": self.rng.choice(["morning", "afternoon"]),
                        })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaLargeButRareHelen(DemoPersona):
    """1-2 huge transactions per month (5k-8k) instead of normal distribution."""

    NAME = "Helen_LargeButRare"
    TIER = "anomaly"
    NARRATIVE = "Transaction size distribution completely changed"
    EXPECTED_RISK_SCORE = 0.55

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # 1-2 huge transactions per month = ~3-6% daily
            if self.rng.random() < 0.03:
                # Rare, large transactions
                amount = self.rng.normal(6500, 1000)
                amount = max(4000, min(10000, amount))
            elif self.rng.random() < 0.02:
                # Occasional normal-sized
                amount = self.rng.normal(200, 50)
                amount = max(50, min(500, amount))
            else:
                current_date += timedelta(days=1)
                days_elapsed += 1
                continue

            transactions.append({
                "customer_id": self.customer_id,
                "date": current_date,
                "amount": amount,
                "mcc": "5411",
                "mcc_category": "grocery",
                "channel": "POS",
                "merchant": self.rng.choice(["Costco", "Whole Foods", "Walmart"]),
                "country": "US",
                "time_of_day": self.rng.choice(["morning", "afternoon"]),
            })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaChannelSwitchIvan(DemoPersona):
    """~5000/month stable but switched from 100% POS to 100% Online."""

    NAME = "Ivan_ChannelSwitch"
    TIER = "anomaly"
    NARRATIVE = "Complete channel preference shift detected"
    EXPECTED_RISK_SCORE = 0.42

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            shift_factor = days_elapsed / 365

            if shift_factor < 0.5:
                # First half: 100% POS
                channel = "POS"
                merchant = self.rng.choice(["Whole Foods", "Target", "Walmart"])
            else:
                # Second half: 100% Online
                channel = "ONLINE"
                merchant = self.rng.choice(["Amazon", "Instacart", "eBay"])

            if self.rng.random() < 0.3:
                amount = self.rng.normal(300, 50)
                amount = max(100, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": channel,
                    "merchant": merchant,
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon"]),
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaGeographicAnomalyJulia(DemoPersona):
    """~4500/month but from 10+ countries (fraud risk)."""

    NAME = "Julia_GeographicAnomaly"
    TIER = "anomaly"
    NARRATIVE = "Unusual geographic dispersion - fraud risk"
    EXPECTED_RISK_SCORE = 0.51

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        countries = ["US", "UK", "CA", "DE", "FR", "JP", "BR", "AU", "MX", "IN", "SG"]

        while current_date <= end_date:
            if self.rng.random() < 0.3:
                amount = self.rng.normal(300, 50)
                amount = max(100, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Store", "Market", "Mall"]),
                    "country": self.rng.choice(countries),
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })

            current_date += timedelta(days=1)

        return transactions


# ==============================================================================
# TIER 4: Growth Customers (Green)
# ==============================================================================


class PersonaGrowthTrendKevin(DemoPersona):
    """2000 → 5000/month (+15%/month for 6 months)."""

    NAME = "Kevin_GrowthTrend"
    TIER = "growth"
    NARRATIVE = "Steady spending growth - good engagement signal"
    EXPECTED_RISK_SCORE = 0.08

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Linear growth: 2000 → 5000/month
            growth_factor = 1 + (days_elapsed / 365) * 1.5  # 150% growth
            base_amount = 200 * growth_factor

            if self.rng.random() < 0.25:
                amount = self.rng.normal(base_amount, 40)
                amount = max(50, min(1000, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Whole Foods", "Trader Joe's"]),
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaIncreasingFrequencyLaura(DemoPersona):
    """Stable ~4000/month but transactions increase 5/month → 15/month."""

    NAME = "Laura_IncreasingFrequency"
    TIER = "growth"
    NARRATIVE = "Increasing transaction frequency - rising engagement"
    EXPECTED_RISK_SCORE = 0.03

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Increasing frequency: 5→15/month = 0.167→0.5/day
            growth_factor = 0.167 + (days_elapsed / 365) * 0.333

            if self.rng.random() < growth_factor:
                amount = self.rng.normal(300, 50)
                amount = max(100, min(800, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Target", "Whole Foods"]),
                    "country": "US",
                    "time_of_day": "afternoon",
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaCategoryExpansionMichael(DemoPersona):
    """~4000/month same amount but expanding from 5 → 15 categories."""

    NAME = "Michael_CategoryExpansion"
    TIER = "growth"
    NARRATIVE = "Expanding category usage - cross-sell opportunity"
    EXPECTED_RISK_SCORE = 0.02

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        limited_categories = ["grocery", "grocery", "retail", "retail", "gas"]
        expanded_categories = [
            "grocery", "retail", "gas", "restaurant", "hotel",
            "electronics", "pharmacy", "home", "entertainment", "health",
            "taxi", "airline", "utility", "insurance", "subscription"
        ]

        while current_date <= end_date:
            # Gradual expansion of category choices
            expand_factor = days_elapsed / 365

            if expand_factor < 0.5:
                # First half: limited categories
                categories = limited_categories
            else:
                # Second half: expanded categories
                categories = expanded_categories

            if self.rng.random() < 0.3:
                amount = self.rng.normal(300, 50)
                amount = max(50, min(800, amount))

                category = self.rng.choice(categories)
                category_to_merchant = {
                    "grocery": "Whole Foods",
                    "retail": "Target",
                    "gas": "Shell",
                    "restaurant": "Olive Garden",
                    "hotel": "Marriott",
                    "electronics": "Best Buy",
                    "pharmacy": "CVS",
                    "home": "Home Depot",
                    "entertainment": "Netflix",
                    "health": "Gym",
                    "taxi": "Uber",
                    "airline": "United",
                    "utility": "Power Co",
                    "insurance": "State Farm",
                    "subscription": "Spotify",
                }

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": category,
                    "channel": "POS",
                    "merchant": category_to_merchant.get(category, "Store"),
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaPostLifestyleChangeNina(DemoPersona):
    """3000 → 6000/month with new merchant categories (fine dining, premium retail)."""

    NAME = "Nina_PostLifestyleChange"
    TIER = "growth"
    NARRATIVE = "Positive lifestyle upgrade - high-value growth"
    EXPECTED_RISK_SCORE = 0.04

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Growth and category upgrade: 3000 → 6000/month
            growth_factor = 1 + (days_elapsed / 365) * 1.0  # 100% growth

            if days_elapsed < 180:
                # First half: budget categories
                categories = ["grocery", "retail", "gas", "restaurant"]
                merchants = ["Walmart", "Target", "McDonald's"]
                base_amount = 250
            else:
                # Second half: premium categories
                categories = ["restaurant", "hotel", "electronics", "luxury"]
                merchants = ["Le Bernardin", "5-Star Hotel", "Apple Store", "Saks"]
                base_amount = 400

            base_amount *= growth_factor

            if self.rng.random() < 0.3:
                amount = self.rng.normal(base_amount, base_amount * 0.15)
                amount = max(100, min(1200, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5812" if "restaurant" in categories else "5411",
                    "mcc_category": self.rng.choice(categories),
                    "channel": "POS",
                    "merchant": self.rng.choice(merchants),
                    "country": "US",
                    "time_of_day": self.rng.choice(["afternoon", "evening", "dinner"]),
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaReengagementSuccessOliver(DemoPersona):
    """Dormant 3+ months, now resuming transactions back to previous levels."""

    NAME = "Oliver_ReengagementSuccess"
    TIER = "growth"
    NARRATIVE = "Win-back campaign success - customer re-engagement"
    EXPECTED_RISK_SCORE = 0.28

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0
        dormancy_start = 60  # Dormant days 60-180
        dormancy_end = 180
        recovery_start = 181

        while current_date <= end_date:
            if days_elapsed < dormancy_start:
                # Active period
                if self.rng.random() < 0.25:
                    amount = self.rng.normal(300, 50)
                    amount = max(100, min(800, amount))

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": amount,
                        "mcc": "5411",
                        "mcc_category": "grocery",
                        "channel": "POS",
                        "merchant": "Whole Foods",
                        "country": "US",
                        "time_of_day": "afternoon",
                    })
            elif days_elapsed > recovery_start:
                # Recovery period (re-engagement)
                recovery_factor = (days_elapsed - recovery_start) / (365 - recovery_start)

                if self.rng.random() < (0.25 * recovery_factor):
                    amount = self.rng.normal(300, 50)
                    amount = max(100, min(800, amount))

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": amount,
                        "mcc": "5411",
                        "mcc_category": "grocery",
                        "channel": "POS",
                        "merchant": "Whole Foods",
                        "country": "US",
                        "time_of_day": "afternoon",
                    })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


class PersonaSuperCustomerPatricia(DemoPersona):
    """10000 → 15000/month over time, consistent growth, high value."""

    NAME = "Patricia_SuperCustomer"
    TIER = "growth"
    NARRATIVE = "VIP retention target - premium customer with growth"
    EXPECTED_RISK_SCORE = 0.01

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        days_elapsed = 0

        while current_date <= end_date:
            # Growth: 10000 → 15000/month
            growth_factor = 1 + (days_elapsed / 365) * 0.5  # 50% growth
            base_amount = 600 * growth_factor

            if self.rng.random() < 0.5:
                amount = self.rng.normal(base_amount, base_amount * 0.1)
                amount = max(200, min(2000, amount))

                categories = ["restaurant", "hotel", "retail", "electronics"]
                merchants = ["Michelin", "Luxury Hotel", "Saks", "Apple"]

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5812",
                    "mcc_category": self.rng.choice(categories),
                    "channel": "POS",
                    "merchant": self.rng.choice(merchants),
                    "country": "US",
                    "time_of_day": self.rng.choice(["lunch", "dinner", "evening"]),
                })

            current_date += timedelta(days=1)
            days_elapsed += 1

        return transactions


# ==============================================================================
# TIER 5: Advanced Edge Cases (10 new personas for richer demos)
# ==============================================================================


class PersonaTravelAddict(DemoPersona):
    """International traveler - frequent high-value transactions in different countries."""

    NAME = "Quinn_TravelAddict"
    TIER = "growth"
    NARRATIVE = "Frequent international traveler with hotel/airline spending patterns"
    EXPECTED_RISK_SCORE = 0.15

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        countries = ["US", "UK", "FR", "DE", "JP", "AU", "CA", "MX"]
        merchants = ["Marriott", "Hilton", "United Airlines", "Lufthansa", "AirBnB", "Expedia"]

        while current_date <= end_date:
            # Travel patterns: 2-3 weeks active, 1 week inactive
            week_num = (current_date - start_date).days // 7
            if week_num % 4 != 3:  # Not in the "inactive week"
                if self.rng.random() < 0.4:  # 40% of days
                    n_tx = self.rng.randint(1, 4)
                    for _ in range(n_tx):
                        amount = self.rng.normal(1500, 400) if self.rng.random() < 0.3 else self.rng.normal(250, 100)
                        amount = max(50, min(5000, amount))

                        transactions.append({
                            "customer_id": self.customer_id,
                            "date": current_date,
                            "amount": amount,
                            "mcc": "7011" if amount > 500 else "4111",
                            "mcc_category": "hotel" if amount > 500 else "taxi",
                            "channel": "online",
                            "merchant": self.rng.choice(merchants),
                            "country": self.rng.choice(countries),
                            "time_of_day": self.rng.choice(["morning", "afternoon"]),
                        })
            current_date += timedelta(days=1)
        return transactions


class PersonaRetailRecovery(DemoPersona):
    """Customer who went dormant for 4 months, then came back strong."""

    NAME = "Rebecca_RetailRecovery"
    TIER = "growth"
    NARRATIVE = "Dormant customer who returned with renewed spending after break"
    EXPECTED_RISK_SCORE = 0.25

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        total_days = (end_date - start_date).days
        dormant_start = total_days // 3
        dormant_end = total_days * 2 // 3

        while current_date <= end_date:
            days_elapsed = (current_date - start_date).days

            if days_elapsed < dormant_start or days_elapsed > dormant_end:
                # Active periods (before dormancy or after recovery)
                if self.rng.random() < 0.3:
                    amount = self.rng.normal(400, 80) if days_elapsed > dormant_end else self.rng.normal(300, 70)
                    amount = max(20, min(1200, amount))

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": amount,
                        "mcc": "5311",
                        "mcc_category": "retail",
                        "channel": "POS",
                        "merchant": self.rng.choice(["Target", "H&M", "Forever 21", "Zara"]),
                        "country": "US",
                        "time_of_day": self.rng.choice(["afternoon", "evening"]),
                    })
            # Otherwise: dormant period (no transactions)

            current_date += timedelta(days=1)
        return transactions


class PersonaCryptoTrader(DemoPersona):
    """Highly volatile - cryptocurrency investor with extreme swings."""

    NAME = "Samuel_CryptoTrader"
    TIER = "anomaly"
    NARRATIVE = "Crypto investor - extreme volatility and irregular patterns"
    EXPECTED_RISK_SCORE = 0.65

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            # Random bursts of activity
            if self.rng.random() < 0.15:  # 15% of days very active
                n_tx = self.rng.randint(3, 8)
                for _ in range(n_tx):
                    # Crypto amounts: either very small or very large
                    if self.rng.random() < 0.4:
                        amount = self.rng.uniform(10, 100)
                    else:
                        amount = self.rng.uniform(2000, 10000)

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": amount,
                        "mcc": "6211",  # Securities brokers
                        "mcc_category": "investment",
                        "channel": "online",
                        "merchant": self.rng.choice(["Coinbase", "Kraken", "Binance", "FTX"]),
                        "country": "US",
                        "time_of_day": self.rng.choice(["morning", "afternoon", "evening", "night"]),
                    })
            current_date += timedelta(days=1)
        return transactions


class PersonaGamblerPattern(DemoPersona):
    """Late night casino/gambling activity - high risk pattern."""

    NAME = "Tony_GamblerPattern"
    TIER = "anomaly"
    NARRATIVE = "Frequent late-night casino/gambling transactions - high-risk profile"
    EXPECTED_RISK_SCORE = 0.72

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            # Primarily Thursday-Sunday (weekend heavy)
            day_of_week = current_date.weekday()
            if day_of_week >= 3:  # Thursday-Sunday
                if self.rng.random() < 0.5:
                    amount = self.rng.choice([
                        self.rng.uniform(50, 200),     # Small bets
                        self.rng.uniform(500, 2000),   # Medium bets
                        self.rng.uniform(100, 500),    # Refunds/losses
                    ])

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": amount,
                        "mcc": "7994",  # Casino/gambling
                        "mcc_category": "gambling",
                        "channel": "online",
                        "merchant": self.rng.choice(["Las Vegas Casino", "DraftKings", "FanDuel", "PokerStars"]),
                        "country": "US",
                        "time_of_day": "evening" if self.rng.random() < 0.7 else "night",
                    })
            current_date += timedelta(days=1)
        return transactions


class PersonaDebtPayoff(DemoPersona):
    """Increasing spending over time as debt payments decline - positive trend."""

    NAME = "Ursula_DebtPayoff"
    TIER = "growth"
    NARRATIVE = "Customer paying off debt - spending accelerates as debts cleared"
    EXPECTED_RISK_SCORE = 0.08

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        total_days = (end_date - start_date).days

        while current_date <= end_date:
            days_elapsed = (current_date - start_date).days
            # Accelerating base amount as time progresses (debt clearing)
            progress = days_elapsed / total_days
            base_amount = 300 + (progress * 700)  # $300 -> $1000 over period

            if self.rng.random() < 0.25:
                amount = self.rng.normal(base_amount, base_amount * 0.2)
                amount = max(50, min(2000, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5411",
                    "mcc_category": "grocery",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Whole Foods", "Trader Joe's", "Kroger"]),
                    "country": "US",
                    "time_of_day": "afternoon",
                })
            current_date += timedelta(days=1)
        return transactions


class PersonaSeasonal(DemoPersona):
    """Strong seasonal pattern - high in Q4, low in Q1."""

    NAME = "Victor_Seasonal"
    TIER = "stable"
    NARRATIVE = "Strong seasonal spender - holiday shopping drives high Q4, low Q1"
    EXPECTED_RISK_SCORE = 0.12

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            month = current_date.month
            # Q4 (10-12): High spending, Q1 (1-3): Low spending
            if month in [10, 11, 12]:
                season_multiplier = 2.0
            elif month in [1, 2, 3]:
                season_multiplier = 0.3
            else:
                season_multiplier = 1.0

            if self.rng.random() < 0.25:
                base_amount = 300 * season_multiplier
                amount = self.rng.normal(base_amount, base_amount * 0.3)
                amount = max(20, min(2000, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5311",
                    "mcc_category": "retail",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Target", "Walmart", "Best Buy", "Amazon"]),
                    "country": "US",
                    "time_of_day": self.rng.choice(["afternoon", "evening"]),
                })
            current_date += timedelta(days=1)
        return transactions


class PersonaFreelancer(DemoPersona):
    """Irregular income pattern - feast/famine spending cycles."""

    NAME = "Wendy_Freelancer"
    TIER = "at_risk"
    NARRATIVE = "Freelancer with irregular income - feast/famine spending patterns"
    EXPECTED_RISK_SCORE = 0.45

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        while current_date <= end_date:
            # 2-week feast, 1-week famine cycle
            day_in_cycle = (current_date - start_date).days % 21
            amount = None

            if day_in_cycle < 14:  # Feast period
                if self.rng.random() < 0.35:
                    amount = self.rng.normal(600, 150)
            else:  # Famine period
                if self.rng.random() < 0.05:
                    amount = self.rng.normal(100, 30)

            if amount is not None:
                amount = max(20, min(2000, amount))
                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5812",
                    "mcc_category": "restaurant",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Coffee Shop", "Food Truck", "Restaurant"]),
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })
            current_date += timedelta(days=1)
        return transactions


class PersonaBusinessOwner(DemoPersona):
    """Mixed personal/business spending - high amounts, many categories."""

    NAME = "Xavier_BusinessOwner"
    TIER = "growth"
    NARRATIVE = "Small business owner - mixed personal/business transactions"
    EXPECTED_RISK_SCORE = 0.18

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date

        merchants = [
            ("Office Depot", "5200"), ("AWS", "7379"), ("Restaurant", "5812"),
            ("Fuel", "5541"), ("Hotel", "7011"), ("Airline", "4511"),
            ("Supplies", "5939"), ("Equipment", "7359"), ("Software", "7372"),
        ]

        while current_date <= end_date:
            # Business days are more active
            if current_date.weekday() < 5:  # Weekday
                if self.rng.random() < 0.4:
                    n_tx = self.rng.randint(1, 4)
                    for _ in range(n_tx):
                        idx = self.rng.randint(0, len(merchants))
                        merchant, mcc = merchants[idx]
                        # Business transactions tend higher
                        amount = self.rng.lognormal(6, 1)  # Log-normal for business
                        amount = min(5000, amount)

                        transactions.append({
                            "customer_id": self.customer_id,
                            "date": current_date,
                            "amount": amount,
                            "mcc": mcc,
                            "mcc_category": "business",
                            "channel": "online" if self.rng.random() < 0.6 else "POS",
                            "merchant": merchant,
                            "country": "US",
                            "time_of_day": self.rng.choice(["morning", "afternoon"]),
                        })
            else:  # Weekend - personal spending
                if self.rng.random() < 0.3:
                    amount = self.rng.normal(200, 50)
                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": amount,
                        "mcc": "5812",
                        "mcc_category": "restaurant",
                        "channel": "POS",
                        "merchant": "Restaurant",
                        "country": "US",
                        "time_of_day": self.rng.choice(["evening", "night"]),
                    })
            current_date += timedelta(days=1)
        return transactions


class PersonaStudentRecovery(DemoPersona):
    """Student graduating and finding job - dramatic spending increase."""

    NAME = "Yasmin_StudentRecovery"
    TIER = "growth"
    NARRATIVE = "Recent graduate - spending increases sharply after job placement"
    EXPECTED_RISK_SCORE = 0.10

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        total_days = (end_date - start_date).days
        graduation_day = start_date + timedelta(days=total_days // 2)

        while current_date <= end_date:
            if current_date < graduation_day:
                # Pre-graduation: very low spending
                base_amount = 50
                transaction_prob = 0.10
            else:
                # Post-graduation: increased spending
                days_since_grad = (current_date - graduation_day).days
                base_amount = 50 + (days_since_grad / (total_days - (graduation_day - start_date).days) * 450)
                transaction_prob = 0.35

            if self.rng.random() < transaction_prob:
                amount = self.rng.normal(base_amount, base_amount * 0.3)
                amount = max(10, min(1500, amount))

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": "5812",
                    "mcc_category": "restaurant",
                    "channel": "POS",
                    "merchant": self.rng.choice(["Coffee Shop", "Restaurant", "Bar"]),
                    "country": "US",
                    "time_of_day": self.rng.choice(["afternoon", "evening"]),
                })
            current_date += timedelta(days=1)
        return transactions


class PersonaHealthCrisis(DemoPersona):
    """Medical emergency - sudden spike followed by recovery period."""

    NAME = "Zoe_HealthCrisis"
    TIER = "anomaly"
    NARRATIVE = "Customer with medical emergency - unusual spending spike and recovery"
    EXPECTED_RISK_SCORE = 0.55

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        transactions = []
        current_date = start_date
        crisis_date = start_date + timedelta(days=random.randint(30, 60))
        crisis_recovery_end = crisis_date + timedelta(days=30)

        while current_date <= end_date:
            if current_date < crisis_date:
                # Normal spending
                if self.rng.random() < 0.25:
                    amount = self.rng.normal(250, 50)
            elif current_date < crisis_recovery_end:
                # Crisis period: high pharmacy/hospital spending
                if self.rng.random() < 0.6:
                    amount = self.rng.normal(800, 300)
            else:
                # Recovery: gradually back to normal
                amount = self.rng.normal(200, 50)

            if self.rng.random() < 0.3 or current_date >= crisis_date:
                amount = max(20, min(3000, amount))
                mcc = "5912" if current_date < crisis_recovery_end else "5411"

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": amount,
                    "mcc": mcc,
                    "mcc_category": "pharmacy" if mcc == "5912" else "grocery",
                    "channel": "POS",
                    "merchant": "Pharmacy" if mcc == "5912" else "Grocery",
                    "country": "US",
                    "time_of_day": self.rng.choice(["morning", "afternoon"]),
                })
            current_date += timedelta(days=1)
        return transactions


# ==============================================================================
# UC-1: LIFE EVENT PERSONAS (IDs 41-44)
# ==============================================================================


class PersonaJobLoss(DemoPersona):
    """Customer with sudden income loss — sharp spending collapse."""

    NAME = "Richard_JobLoss"
    TIER = "at_risk"
    NARRATIVE = "Customer with sudden income loss — sharp spending collapse"
    EXPECTED_RISK_SCORE = 0.75

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Months 1-4: Stable, ~5000 AED/mo
        Months 5-8: Collapse to ~800 AED/mo (subsistence), Grocery 85%, no restaurants
        Months 9+: Optional slow recovery
        """
        transactions = []
        current_date = start_date
        month_counter = 0

        while current_date < end_date:
            month_counter += 1

            # Determine spending level and categories by month
            if month_counter <= 4:
                # Stable phase
                daily_budget = self.rng.normal(5000 / 30, 300 / 30)
                grocery_pct = 0.40
                restaurant_pct = 0.20
            elif month_counter <= 8:
                # Crisis phase: collapse to subsistence
                daily_budget = self.rng.normal(800 / 30, 50 / 30)
                grocery_pct = 0.85
                restaurant_pct = 0.00
            else:
                # Slow recovery
                daily_budget = self.rng.normal(1500 / 30, 100 / 30)
                grocery_pct = 0.70
                restaurant_pct = 0.05

            num_txs = self.rng.integers(5, 12)
            for _ in range(num_txs):
                amount = abs(self.rng.normal(daily_budget, daily_budget * 0.3))
                amount = min(amount, 2000.0)  # cap

                rand = self.rng.random()
                if rand < grocery_pct:
                    mcc, category = "5411", "GROCERY"
                    merchant = self.rng.choice(self._UAE_GROCERY)
                elif rand < (grocery_pct + restaurant_pct):
                    mcc, category = "5812", "RESTAURANTS"
                    merchant = self.rng.choice(self._UAE_RESTAURANT)
                else:
                    mcc, category = "5311", "RETAIL"
                    merchant = self.rng.choice(self._UAE_RETAIL)

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": mcc,
                    "mcc_category": category,
                    "channel": "POS",
                    "merchant": merchant,
                    "country": "AE",
                    "time_of_day": self.rng.choice(["morning", "afternoon"]),
                })
                current_date += timedelta(hours=self.rng.integers(4, 12))

            # Move to next month
            current_date = current_date.replace(day=1) + timedelta(days=32)
            current_date = current_date.replace(day=1)

        return transactions


class PersonaBonus(DemoPersona):
    """Bonus spender with predictable seasonal peaks."""

    NAME = "Victoria_BonusSpender"
    TIER = "growth"
    NARRATIVE = "Bonus spender with predictable seasonal peaks"
    EXPECTED_RISK_SCORE = 0.08

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Baseline: 3500 AED/mo
        Months 6, 12: Spike to 12000 AED (bonus months)
        """
        transactions = []
        current_date = start_date
        month_counter = 0

        while current_date < end_date:
            month_counter += 1

            # Determine if bonus month
            is_bonus = (month_counter % 6 == 0)  # Months 6, 12, 18, ...
            daily_budget = (12000 / 30) if is_bonus else (3500 / 30)

            num_txs = self.rng.integers(8, 15)
            for _ in range(num_txs):
                amount = abs(self.rng.normal(daily_budget, daily_budget * 0.4))
                amount = min(amount, 3000.0)

                if is_bonus:
                    # Luxury categories during bonus
                    rand = self.rng.random()
                    if rand < 0.4:
                        mcc, category = "5812", "RESTAURANTS"
                        merchant = self.rng.choice(self._UAE_RESTAURANT)
                    elif rand < 0.7:
                        mcc, category = "5311", "RETAIL"
                        merchant = self.rng.choice(self._UAE_RETAIL)
                    else:
                        mcc, category = "7011", "ACCOMMODATION"
                        merchant = self.rng.choice(self._UAE_HOTEL)
                else:
                    # Normal categories
                    rand = self.rng.random()
                    if rand < 0.5:
                        mcc, category = "5411", "GROCERY"
                        merchant = self.rng.choice(self._UAE_GROCERY)
                    else:
                        mcc, category = "5812", "RESTAURANTS"
                        merchant = self.rng.choice(self._UAE_RESTAURANT)

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": mcc,
                    "mcc_category": category,
                    "channel": self.rng.choice(["POS", "ONLINE"]),
                    "merchant": merchant,
                    "country": "AE",
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })
                current_date += timedelta(hours=self.rng.integers(6, 18))

            # Move to next month
            current_date = current_date.replace(day=1) + timedelta(days=32)
            current_date = current_date.replace(day=1)

        return transactions


class PersonaRetirement(DemoPersona):
    """Retiree with fixed low spending and consistent patterns."""

    NAME = "Walter_Retired"
    TIER = "stable"
    NARRATIVE = "Retiree with fixed low spending and consistent patterns"
    EXPECTED_RISK_SCORE = 0.02

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Baseline: ~2000 AED/mo, very consistent.
        70% Grocery, 20% Pharmacy, 10% Gas (visiting grandkids)
        """
        transactions = []
        current_date = start_date

        while current_date < end_date:
            # Very consistent daily spending
            num_txs = self.rng.integers(3, 6)
            for _ in range(num_txs):
                rand = self.rng.random()
                if rand < 0.70:
                    amount = self.rng.uniform(150, 400)
                    mcc, category = "5411", "GROCERY"
                    merchant = self.rng.choice(self._UAE_GROCERY)
                elif rand < 0.90:
                    amount = self.rng.uniform(50, 200)
                    mcc, category = "5912", "PHARMACY"
                    merchant = self.rng.choice(self._UAE_PHARMACY)
                else:
                    amount = self.rng.uniform(100, 300)
                    mcc, category = "5541", "GAS_STATION"
                    merchant = self.rng.choice(self._UAE_FUEL)

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": mcc,
                    "mcc_category": category,
                    "channel": "POS",
                    "merchant": merchant,
                    "country": "AE",
                    "time_of_day": self.rng.choice(["morning", "afternoon"]),
                })
                current_date += timedelta(hours=self.rng.integers(8, 16))

        return transactions


class PersonaWedding(DemoPersona):
    """Customer with major life event (wedding) — spending spike + permanent category shift."""

    NAME = "Alexandra_Wedding"
    TIER = "anomaly"
    NARRATIVE = "Customer with major life event (wedding) — spending spike + permanent category shift"
    EXPECTED_RISK_SCORE = 0.45

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Months 1-2: Normal (~3000 AED/mo)
        Months 3-4: Wedding spike (furniture, decor, catering) — 15000 AED/mo
        Months 5+: Return to normal but category shifts (more grocery, less entertainment)
        """
        transactions = []
        current_date = start_date
        month_counter = 0

        while current_date < end_date:
            month_counter += 1

            if month_counter <= 2:
                # Pre-wedding: normal
                daily_budget = 3000 / 30
                is_wedding = False
            elif month_counter <= 4:
                # Wedding months: spike
                daily_budget = 15000 / 30
                is_wedding = True
            else:
                # Post-wedding: normal but different categories
                daily_budget = 3500 / 30
                is_wedding = False

            num_txs = self.rng.integers(6, 12)
            for _ in range(num_txs):
                amount = abs(self.rng.normal(daily_budget, daily_budget * 0.35))
                amount = min(amount, 4000.0)

                if is_wedding:
                    # Wedding categories
                    rand = self.rng.random()
                    if rand < 0.4:
                        mcc, category = "5200", "HOME"
                        merchant = self.rng.choice(self._UAE_RETAIL)
                    elif rand < 0.8:
                        mcc, category = "5812", "RESTAURANTS"
                        merchant = self.rng.choice(self._UAE_RESTAURANT)
                    else:
                        mcc, category = "7011", "ACCOMMODATION"
                        merchant = self.rng.choice(self._UAE_HOTEL)
                else:
                    # Post-wedding: more household-oriented
                    rand = self.rng.random()
                    if rand < 0.50:
                        mcc, category = "5411", "GROCERY"
                        merchant = self.rng.choice(self._UAE_GROCERY)
                    elif rand < 0.75:
                        mcc, category = "5812", "RESTAURANTS"
                        merchant = self.rng.choice(self._UAE_RESTAURANT)
                    else:
                        mcc, category = "5912", "PHARMACY"
                        merchant = self.rng.choice(self._UAE_PHARMACY)

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": mcc,
                    "mcc_category": category,
                    "channel": self.rng.choice(["POS", "ONLINE"]),
                    "merchant": merchant,
                    "country": "AE",
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })
                current_date += timedelta(hours=self.rng.integers(6, 14))

            # Move to next month
            current_date = current_date.replace(day=1) + timedelta(days=32)
            current_date = current_date.replace(day=1)

        return transactions


# ==============================================================================
# UC-2: CHURN MECHANISM PERSONAS (IDs 45-47)
# ==============================================================================


class PersonaBudgetConstraint(DemoPersona):
    """Maxed-out credit — hidden churn signal despite active transactions."""

    NAME = "Marcus_CreditMaxed"
    TIER = "at_risk"
    NARRATIVE = "Maxed-out credit — hidden churn signal despite active transactions"
    EXPECTED_RISK_SCORE = 0.80

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """High utilization 85-99% throughout.
        Frequent small transactions (min amounts, ~150 AED).
        Max payment delay: 15-25 days.
        Very low campaigns_opened (0-2).
        """
        transactions = []
        current_date = start_date

        while current_date < end_date:
            # Frequent small txs throughout the day
            num_txs = self.rng.integers(15, 25)
            for _ in range(num_txs):
                amount = self.rng.uniform(100, 250)  # Small transactions

                rand = self.rng.random()
                if rand < 0.6:
                    mcc, category = "5411", "GROCERY"
                    merchant = self.rng.choice(self._UAE_GROCERY)
                elif rand < 0.85:
                    mcc, category = "5812", "RESTAURANTS"
                    merchant = self.rng.choice(self._UAE_RESTAURANT)
                else:
                    mcc, category = "5311", "RETAIL"
                    merchant = self.rng.choice(self._UAE_RETAIL)

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": mcc,
                    "mcc_category": category,
                    "channel": "POS",
                    "merchant": merchant,
                    "country": "AE",
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })
                current_date += timedelta(hours=self.rng.integers(1, 4))

        return transactions


class PersonaSilentDisengagement(DemoPersona):
    """Silent disengagement — low activity masks churn risk."""

    NAME = "Emma_Disengaged"
    TIER = "at_risk"
    NARRATIVE = "Silent disengagement — low activity masks churn risk"
    EXPECTED_RISK_SCORE = 0.68

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Spending stable (~4000 AED/mo) — no decline signal.
        Dormancy 75+ days — long gaps between transactions.
        campaigns_opened: 0 (completely ignores marketing).
        Transaction frequency: 8-12/mo (half normal).
        """
        transactions = []
        current_date = start_date

        while current_date < end_date:
            # Very sparse — only 1-2 txs per week
            num_txs = self.rng.integers(1, 2)
            for _ in range(num_txs):
                amount = self.rng.uniform(300, 600)

                rand = self.rng.random()
                if rand < 0.50:
                    mcc, category = "5411", "GROCERY"
                    merchant = self.rng.choice(self._UAE_GROCERY)
                elif rand < 0.75:
                    mcc, category = "5812", "RESTAURANTS"
                    merchant = self.rng.choice(self._UAE_RESTAURANT)
                else:
                    mcc, category = "5311", "RETAIL"
                    merchant = self.rng.choice(self._UAE_RETAIL)

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": mcc,
                    "mcc_category": category,
                    "channel": "POS",
                    "merchant": merchant,
                    "country": "AE",
                    "time_of_day": self.rng.choice(["morning", "afternoon"]),
                })

            # Long gap before next transaction (dormancy)
            current_date += timedelta(days=self.rng.integers(8, 15))

        return transactions


class PersonaSubscriptionChurn(DemoPersona):
    """Subscription churn — recurring charges stop, overall spending follows."""

    NAME = "Isaac_SubscriptionFatigue"
    TIER = "at_risk"
    NARRATIVE = "Subscription churn — recurring charges stop, overall spending follows"
    EXPECTED_RISK_SCORE = 0.62

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Months 1-3: Regular spending including subscriptions (Netflix, Spotify, etc.)
        Months 4+: Subscription txs disappear, spending drops 30%
        """
        transactions = []
        current_date = start_date
        month_counter = 0

        while current_date < end_date:
            month_counter += 1
            has_subscriptions = (month_counter <= 3)

            if has_subscriptions:
                daily_budget = 4000 / 30
            else:
                daily_budget = (4000 * 0.70) / 30

            num_txs = self.rng.integers(8, 14)
            for _ in range(num_txs):
                amount = abs(self.rng.normal(daily_budget, daily_budget * 0.3))
                amount = min(amount, 2000.0)

                if has_subscriptions and self.rng.random() < 0.15:
                    # Subscription transaction
                    mcc, category = "7372", "DIGITAL_SERVICES"
                    merchant = self.rng.choice(["Netflix", "Spotify", "Adobe Cloud", "Dropbox"])
                    channel = "ONLINE"
                else:
                    # Regular POS
                    rand = self.rng.random()
                    if rand < 0.50:
                        mcc, category = "5411", "GROCERY"
                        merchant = self.rng.choice(self._UAE_GROCERY)
                    else:
                        mcc, category = "5812", "RESTAURANTS"
                        merchant = self.rng.choice(self._UAE_RESTAURANT)
                    channel = "POS"

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": mcc,
                    "mcc_category": category,
                    "channel": channel,
                    "merchant": merchant,
                    "country": "AE",
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })
                current_date += timedelta(hours=self.rng.integers(4, 12))

            # Move to next month
            current_date = current_date.replace(day=1) + timedelta(days=32)
            current_date = current_date.replace(day=1)

        return transactions


# ==============================================================================
# UC-3: FRAUD COMBINATION PERSONAS (IDs 48-55)
# ==============================================================================


class PersonaAccountTakeover(DemoPersona):
    """Account takeover — multiple signals simultaneously."""

    NAME = "James_Hacked"
    TIER = "anomaly"
    NARRATIVE = "Account takeover — multiple signals simultaneously"
    EXPECTED_RISK_SCORE = 0.85

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Months 1-3: Normal spending, country=AE, channels=POS+ONLINE, times=normal
        Month 4 onwards: Sudden changes — Geo: 100% foreign (NG, CN)
        Channel: 100% ONLINE, Time: 80% night (02:00-05:00), Velocity: 3x normal
        """
        transactions = []
        current_date = start_date
        month_counter = 0

        while current_date < end_date:
            month_counter += 1
            is_compromised = (month_counter > 3)

            if is_compromised:
                # 3x velocity: 40 txs/mo → 120 txs/mo
                num_txs = self.rng.integers(30, 40)
                normal_amount = 500.0
            else:
                num_txs = self.rng.integers(8, 15)
                normal_amount = 250.0

            for _ in range(num_txs):
                if is_compromised:
                    # Foreign countries, high risk MCCs
                    country = self.rng.choice(["NG", "CN", "RU", "UA"])
                    amount = self.rng.uniform(normal_amount * 2, normal_amount * 4)
                    hour = self.rng.integers(2, 6) if self.rng.random() < 0.80 else self.rng.integers(0, 24)
                    channel = "ONLINE"
                    mcc, category = "7999", "ENTERTAINMENT"
                else:
                    # Normal: UAE, reasonable amounts, POS/ONLINE mix
                    country = "AE"
                    amount = self.rng.uniform(100, 500)
                    hour = self.rng.integers(8, 20)
                    channel = self.rng.choice(["POS", "ONLINE"])
                    rand = self.rng.random()
                    if rand < 0.50:
                        mcc, category = "5411", "GROCERY"
                    else:
                        mcc, category = "5812", "RESTAURANTS"

                time_str = f"{hour:02d}:00"
                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": mcc,
                    "mcc_category": category,
                    "channel": channel,
                    "merchant": "Foreign Merchant" if is_compromised else self.rng.choice(self._UAE_GROCERY),
                    "country": country,
                    "time_of_day": time_str,
                })
                current_date += timedelta(minutes=self.rng.integers(10, 60))

        return transactions


class PersonaMicroLending(DemoPersona):
    """Structuring/smurfing pattern — micro-txs → large cash-out cycle."""

    NAME = "Paul_Smurfer"
    TIER = "anomaly"
    NARRATIVE = "Structuring/smurfing pattern — micro-txs → large cash-out cycle"
    EXPECTED_RISK_SCORE = 0.80

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Days 1-10 each month: Burst of 100+ micro-txs (8-18 AED) within 12 hours.
        Days 11-30: Single large withdrawal (~2500 AED) at ATM.
        Pattern repeats.
        """
        transactions = []
        current_date = start_date
        day_in_month = 1

        while current_date < end_date:
            if day_in_month <= 10:
                # Micro-txs burst
                num_txs = self.rng.integers(30, 50)
                for _ in range(num_txs):
                    amount = self.rng.uniform(8, 18)
                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": round(amount, 2),
                        "mcc": "5411",
                        "mcc_category": "GROCERY",
                        "channel": "POS",
                        "merchant": self.rng.choice(self._UAE_GROCERY),
                        "country": "AE",
                        "time_of_day": self.rng.choice(["morning", "afternoon"]),
                    })
                    current_date += timedelta(minutes=self.rng.integers(3, 12))
            else:
                # Large ATM withdrawal
                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(self.rng.uniform(2000, 3000), 2),
                    "mcc": "0000",  # ATM
                    "mcc_category": "ATM_WITHDRAWAL",
                    "channel": "ATM",
                    "merchant": self.rng.choice(self._UAE_ATM),
                    "country": "AE",
                    "time_of_day": self.rng.choice(["morning", "afternoon"]),
                })
                current_date += timedelta(days=1)

            day_in_month += 1
            if day_in_month > 30:
                day_in_month = 1

        return transactions


class PersonaHolidayFraud(DemoPersona):
    """Holiday shopping season exploited for fraud."""

    NAME = "Susan_HolidayFraudster"
    TIER = "anomaly"
    NARRATIVE = "Holiday shopping season exploited for fraud"
    EXPECTED_RISK_SCORE = 0.70

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Months 1-11: Normal customer.
        December: Legitimate spike (1-15) + fraudulent overlay (16-31)
        """
        transactions = []
        current_date = start_date

        while current_date < end_date:
            month = current_date.month
            day = current_date.day

            if month != 12:
                # Normal month
                num_txs = self.rng.integers(5, 10)
                for _ in range(num_txs):
                    amount = self.rng.uniform(200, 600)
                    rand = self.rng.random()
                    if rand < 0.50:
                        mcc, category = "5411", "GROCERY"
                        merchant = self.rng.choice(self._UAE_GROCERY)
                    else:
                        mcc, category = "5812", "RESTAURANTS"
                        merchant = self.rng.choice(self._UAE_RESTAURANT)

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": round(amount, 2),
                        "mcc": mcc,
                        "mcc_category": category,
                        "channel": "POS",
                        "merchant": merchant,
                        "country": "AE",
                        "time_of_day": self.rng.choice(["morning", "afternoon"]),
                    })
                    current_date += timedelta(hours=self.rng.integers(6, 18))

            elif day <= 15:
                # Legitimate holiday shopping
                num_txs = self.rng.integers(5, 8)
                for _ in range(num_txs):
                    amount = self.rng.uniform(500, 1500)
                    rand = self.rng.random()
                    if rand < 0.4:
                        mcc, category = "5311", "RETAIL"
                        merchant = self.rng.choice(self._UAE_RETAIL)
                    elif rand < 0.8:
                        mcc, category = "5812", "RESTAURANTS"
                        merchant = self.rng.choice(self._UAE_RESTAURANT)
                    else:
                        mcc, category = "7011", "ACCOMMODATION"
                        merchant = self.rng.choice(self._UAE_HOTEL)

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": round(amount, 2),
                        "mcc": mcc,
                        "mcc_category": category,
                        "channel": self.rng.choice(["POS", "ONLINE"]),
                        "merchant": merchant,
                        "country": "AE",
                        "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                    })
                    current_date += timedelta(hours=self.rng.integers(6, 14))

            else:
                # Fraudulent overlay: micro-txs + high-risk MCCs + geo jumps
                num_txs = self.rng.integers(15, 25)
                for _ in range(num_txs):
                    rand = self.rng.random()
                    if rand < 0.40:
                        # Micro-txs
                        amount = self.rng.uniform(5, 20)
                        country = "AE"
                    else:
                        # Geo-jumps
                        amount = self.rng.uniform(200, 800)
                        country = self.rng.choice(["NG", "CN"])

                    if self.rng.random() < 0.60:
                        # High-risk MCCs
                        mcc, category = "7994", "GAMBLING"
                    else:
                        mcc, category = "5411", "GROCERY"

                    hour = self.rng.integers(2, 6) if self.rng.random() < 0.40 else self.rng.integers(0, 24)
                    time_str = f"{hour:02d}:00"

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": round(amount, 2),
                        "mcc": mcc,
                        "mcc_category": category,
                        "channel": "ONLINE" if country != "AE" else "POS",
                        "merchant": "Fraud Merchant" if country != "AE" else self.rng.choice(self._UAE_GROCERY),
                        "country": country,
                        "time_of_day": time_str,
                    })
                    current_date += timedelta(minutes=self.rng.integers(5, 30))

        return transactions


class PersonaPaymentFraud(DemoPersona):
    """Bill-payment fraud — rapid transactions to utility sites."""

    NAME = "Robert_BillPaymentFraud"
    TIER = "anomaly"
    NARRATIVE = "Bill-payment fraud — rapid transactions to utility sites"
    EXPECTED_RISK_SCORE = 0.75

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Months 1-2: Normal, 1000-2000 AED/mo to bill merchants.
        Months 3-4: Burst of 20-30 txs to same merchant in single day, amounts 1-500 AED
        """
        transactions = []
        current_date = start_date
        month_counter = 0

        while current_date < end_date:
            month_counter += 1
            is_fraud_month = (3 <= month_counter <= 4)

            if is_fraud_month:
                # Burst month: 20-30 rapid txs
                num_txs = self.rng.integers(20, 30)
                for i in range(num_txs):
                    amount = self.rng.uniform(1, 500)
                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": round(amount, 2),
                        "mcc": "4900",  # Utility
                        "mcc_category": "UTILITY",
                        "channel": "ONLINE",
                        "merchant": "Bill Payment Site",
                        "country": "AE",
                        "time_of_day": f"{9 + (i % 8):02d}:00",
                    })
                    current_date += timedelta(minutes=self.rng.integers(2, 15))
            else:
                # Normal month: 1-2 regular bill txs
                num_txs = self.rng.integers(1, 3)
                for _ in range(num_txs):
                    amount = self.rng.uniform(500, 1500)
                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": round(amount, 2),
                        "mcc": self.rng.choice(["4900", "6300", "4814"]),
                        "mcc_category": self.rng.choice(["UTILITY", "INSURANCE", "TELECOM"]),
                        "channel": "ONLINE",
                        "merchant": self.rng.choice(["DEWA", "Etisalat", "Emirates Insurance"]),
                        "country": "AE",
                        "time_of_day": self.rng.choice(["morning", "afternoon"]),
                    })
                    current_date += timedelta(days=self.rng.integers(5, 15))

            # Move to next month
            current_date = current_date.replace(day=1) + timedelta(days=32)
            current_date = current_date.replace(day=1)

        return transactions


class PersonaMultiCountrySmurf(DemoPersona):
    """International mule account — constant geo-jumping."""

    NAME = "Yuki_GlobalMule"
    TIER = "anomaly"
    NARRATIVE = "International mule account — constant geo-jumping"
    EXPECTED_RISK_SCORE = 0.88

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Every transaction from different country.
        Countries: 20+ rotation (AE, GB, US, DE, IN, PH, KE, ZA, BR, MX, etc.)
        Amounts: 100-5000 AED. Times: Random all hours.
        """
        transactions = []
        current_date = start_date
        countries = ["AE", "GB", "US", "DE", "IN", "PH", "KE", "ZA", "BR", "MX",
                     "FR", "IT", "ES", "NL", "BE", "SE", "NO", "DK", "PL", "RU"]
        country_idx = 0

        while current_date < end_date:
            num_txs = self.rng.integers(8, 15)
            for _ in range(num_txs):
                amount = self.rng.uniform(100, 5000)
                country = countries[country_idx % len(countries)]
                country_idx += 1

                hour = self.rng.integers(0, 24)
                time_str = f"{hour:02d}:00"

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": self.rng.choice(["5411", "5812", "7011"]),
                    "mcc_category": self.rng.choice(["GROCERY", "RESTAURANTS", "ACCOMMODATION"]),
                    "channel": "ONLINE",
                    "merchant": "International Merchant",
                    "country": country,
                    "time_of_day": time_str,
                })
                current_date += timedelta(hours=self.rng.integers(2, 6))

        return transactions


class PersonaLateNightSyndrome(DemoPersona):
    """Night-time cyber fraud — high-risk timing + channels."""

    NAME = "David_NightCyber"
    TIER = "anomaly"
    NARRATIVE = "Night-time cyber fraud — high-risk timing + channels"
    EXPECTED_RISK_SCORE = 0.78

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """95% of transactions between 02:00-05:00 (night).
        Only ONLINE channel. Only high-risk MCC categories.
        MCC drift: every month new weird category.
        """
        transactions = []
        current_date = start_date
        month_counter = 0
        high_risk_categories = ["CASINO", "SUBSCRIPTION", "CRYPTO", "PAWN_SHOP", "GAMBLING"]

        while current_date < end_date:
            month_counter += 1
            chosen_category = high_risk_categories[month_counter % len(high_risk_categories)]

            num_txs = self.rng.integers(8, 15)
            for _ in range(num_txs):
                amount = self.rng.uniform(100, 1000)

                if self.rng.random() < 0.95:
                    hour = self.rng.integers(2, 6)
                else:
                    hour = self.rng.integers(0, 24)

                time_str = f"{hour:02d}:00"

                # Map category to MCC
                mcc_map = {
                    "CASINO": "7994",
                    "SUBSCRIPTION": "7372",
                    "CRYPTO": "9999",
                    "PAWN_SHOP": "5932",
                    "GAMBLING": "7994",
                }
                mcc = mcc_map.get(chosen_category, "7999")

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": mcc,
                    "mcc_category": chosen_category,
                    "channel": "ONLINE",
                    "merchant": f"{chosen_category} Provider",
                    "country": "AE",
                    "time_of_day": time_str,
                })
                current_date += timedelta(hours=self.rng.integers(1, 4))

        return transactions


class PersonaCategoryWhitelabeling(DemoPersona):
    """Merchant category fraud — label misrepresentation."""

    NAME = "Olivia_MerchantFraud"
    TIER = "anomaly"
    NARRATIVE = "Merchant category fraud — label misrepresentation"
    EXPECTED_RISK_SCORE = 0.72

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Months 1-2: Normal customer, Grocery + Restaurants.
        Months 3+: Category mapping becomes wrong on purpose.
        MCC 5411 labeled as CASINO, MCC 5812 labeled as CRYPTO, etc.
        """
        transactions = []
        current_date = start_date
        month_counter = 0

        while current_date < end_date:
            month_counter += 1
            is_fraud = (month_counter > 2)

            num_txs = self.rng.integers(6, 12)
            for _ in range(num_txs):
                amount = self.rng.uniform(150, 600)

                if is_fraud:
                    # Wrong labels
                    if self.rng.random() < 0.50:
                        mcc = "5411"  # Actually grocery
                        category = "CASINO"  # But labeled as casino
                        merchant = "Carrefour"
                    else:
                        mcc = "5812"  # Actually restaurant
                        category = "CRYPTO"  # But labeled as crypto
                        merchant = self.rng.choice(self._UAE_RESTAURANT)
                else:
                    # Normal
                    if self.rng.random() < 0.50:
                        mcc = "5411"
                        category = "GROCERY"
                        merchant = self.rng.choice(self._UAE_GROCERY)
                    else:
                        mcc = "5812"
                        category = "RESTAURANTS"
                        merchant = self.rng.choice(self._UAE_RESTAURANT)

                transactions.append({
                    "customer_id": self.customer_id,
                    "date": current_date,
                    "amount": round(amount, 2),
                    "mcc": mcc,
                    "mcc_category": category,
                    "channel": "POS",
                    "merchant": merchant,
                    "country": "AE",
                    "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                })
                current_date += timedelta(hours=self.rng.integers(4, 12))

        return transactions


class PersonaRecoveryArc(DemoPersona):
    """Fraud detected and recovered — account remediation."""

    NAME = "Thomas_FraudRecovery"
    TIER = "growth"
    NARRATIVE = "Fraud detected and recovered — account remediation"
    EXPECTED_RISK_SCORE = 0.40

    def generate_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Months 1-2: Normal.
        Months 3-4: Clear fraud (geo jump + micro-txs + high velocity + night).
        Months 5-6: Signals gradually disappear (recovered).
        """
        transactions = []
        current_date = start_date
        month_counter = 0

        while current_date < end_date:
            month_counter += 1

            if month_counter <= 2:
                # Normal phase
                num_txs = self.rng.integers(6, 12)
                for _ in range(num_txs):
                    amount = self.rng.uniform(200, 700)
                    rand = self.rng.random()
                    if rand < 0.50:
                        mcc, category = "5411", "GROCERY"
                        merchant = self.rng.choice(self._UAE_GROCERY)
                    else:
                        mcc, category = "5812", "RESTAURANTS"
                        merchant = self.rng.choice(self._UAE_RESTAURANT)

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": round(amount, 2),
                        "mcc": mcc,
                        "mcc_category": category,
                        "channel": "POS",
                        "merchant": merchant,
                        "country": "AE",
                        "time_of_day": self.rng.choice(["morning", "afternoon"]),
                    })
                    current_date += timedelta(hours=self.rng.integers(6, 14))

            elif month_counter <= 4:
                # Fraud phase
                num_txs = self.rng.integers(25, 35)
                for _ in range(num_txs):
                    amount = self.rng.uniform(100, 1000)
                    country = self.rng.choice(["NG", "CN", "AE", "AE"])  # Mostly foreign
                    hour = self.rng.integers(2, 6) if self.rng.random() < 0.70 else self.rng.integers(0, 24)
                    time_str = f"{hour:02d}:00"

                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": round(amount, 2),
                        "mcc": "7999",
                        "mcc_category": "ENTERTAINMENT",
                        "channel": "ONLINE",
                        "merchant": "Fraud Merchant",
                        "country": country,
                        "time_of_day": time_str,
                    })
                    current_date += timedelta(minutes=self.rng.integers(10, 40))

            else:
                # Recovery phase: fraud signals gradually disappear
                pct_normal = min(1.0, (month_counter - 4) / 2.0)  # 0-100% normal by month 6
                num_txs = self.rng.integers(8, 14)
                for _ in range(num_txs):
                    if self.rng.random() < pct_normal:
                        # Legitimate
                        amount = self.rng.uniform(200, 700)
                        country = "AE"
                        hour = self.rng.integers(8, 20)
                        rand = self.rng.random()
                        if rand < 0.50:
                            mcc, category = "5411", "GROCERY"
                            merchant = self.rng.choice(self._UAE_GROCERY)
                        else:
                            mcc, category = "5812", "RESTAURANTS"
                            merchant = self.rng.choice(self._UAE_RESTAURANT)
                    else:
                        # Remaining fraud signals
                        amount = self.rng.uniform(100, 600)
                        country = self.rng.choice(["NG", "AE", "AE", "AE"])
                        hour = self.rng.integers(2, 6) if self.rng.random() < 0.40 else self.rng.integers(8, 20)
                        mcc, category = "7999", "ENTERTAINMENT"
                        merchant = "Suspicious Merchant"

                    time_str = f"{hour:02d}:00"
                    transactions.append({
                        "customer_id": self.customer_id,
                        "date": current_date,
                        "amount": round(amount, 2),
                        "mcc": mcc,
                        "mcc_category": category,
                        "channel": "POS" if country == "AE" else "ONLINE",
                        "merchant": merchant,
                        "country": country,
                        "time_of_day": time_str,
                    })
                    current_date += timedelta(hours=self.rng.integers(4, 12))

        return transactions


# ==============================================================================
# REGISTRY: Map persona numbers to classes
# ==============================================================================

DEMO_PERSONAS_REGISTRY = {
    # Stable (8)
    1: PersonaStableJohn,
    2: PersonaConservativeAlice,
    3: PersonaPremiumBob,
    4: PersonaBudgetCarol,
    5: PersonaCyclicalDavid,
    6: PersonaModestEmma,
    7: PersonaDisciplinedFrank,
    8: PersonaIntermittentGrace,
    # At-risk (8)
    9: PersonaSilentChurnSarah,
    10: PersonaDecreasingFrequencyMike,
    11: PersonaCategoryShiftLisa,
    12: PersonaNegativeTrendTom,
    13: PersonaLowEngagementRachel,
    14: PersonaHighDormancyMark,
    15: PersonaSupportTicketsNancy,
    16: PersonaHighUtilizationOscar,
    # Anomalies (8)
    17: PersonaSpendingSpikeCharlie,
    18: PersonaMultipleSpikesDiana,
    19: PersonaTimeshiftEric,
    20: PersonaMerchantJumpingFiona,
    21: PersonaWeekendVsWeekdayGeorge,
    22: PersonaLargeButRareHelen,
    23: PersonaChannelSwitchIvan,
    24: PersonaGeographicAnomalyJulia,
    # Growth (6)
    25: PersonaGrowthTrendKevin,
    26: PersonaIncreasingFrequencyLaura,
    27: PersonaCategoryExpansionMichael,
    28: PersonaPostLifestyleChangeNina,
    29: PersonaReengagementSuccessOliver,
    30: PersonaSuperCustomerPatricia,
    # Advanced Edge Cases (10)
    31: PersonaTravelAddict,
    32: PersonaRetailRecovery,
    33: PersonaCryptoTrader,
    34: PersonaGamblerPattern,
    35: PersonaDebtPayoff,
    36: PersonaSeasonal,
    37: PersonaFreelancer,
    38: PersonaBusinessOwner,
    39: PersonaStudentRecovery,
    40: PersonaHealthCrisis,
    # UC-1: Life Events (4)
    41: PersonaJobLoss,
    42: PersonaBonus,
    43: PersonaRetirement,
    44: PersonaWedding,
    # UC-2: Churn Mechanisms (3)
    45: PersonaBudgetConstraint,
    46: PersonaSilentDisengagement,
    47: PersonaSubscriptionChurn,
    # UC-3: Fraud Combinations (8)
    48: PersonaAccountTakeover,
    49: PersonaMicroLending,
    50: PersonaHolidayFraud,
    51: PersonaPaymentFraud,
    52: PersonaMultiCountrySmurf,
    53: PersonaLateNightSyndrome,
    54: PersonaCategoryWhitelabeling,
    55: PersonaRecoveryArc,
}
