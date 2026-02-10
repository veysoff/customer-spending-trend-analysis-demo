"""Customer persona generators with deterministic transaction generation."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np
import uuid


class PersonaGenerator(ABC):
    """Base class for customer persona transaction generation."""

    NAME: str = "ABSTRACT"
    PERSONA_ID: int = 0
    NARRATIVE: str = ""
    EXPECTED_RISK_SCORE: float = 0.5

    def __init__(self, customer_id: int, start_date: datetime, end_date: datetime):
        """Initialize persona generator."""
        self.customer_id = customer_id
        self.start_date = start_date
        self.end_date = end_date
        self.rng = np.random.Generator(np.random.PCG64(seed=customer_id))

    def generate_transactions(self) -> List[Dict[str, Any]]:
        """Generate all transactions for this persona over the period."""
        transactions = []
        current_month = self.start_date.replace(day=1)

        while current_month <= self.end_date:
            # 1. Calculate base monthly budget
            monthly_budget = self._calculate_monthly_budget(current_month)

            # 2. Apply seasonality factor
            seasonal_factor = self._get_seasonality(current_month)
            adjusted_budget = monthly_budget * seasonal_factor

            # 3. Determine transaction count for this month
            tx_count = self._get_transaction_count(current_month)

            # 4. Generate individual transactions
            for _ in range(tx_count):
                date = self._get_random_date_in_month(current_month)
                amount = self._get_transaction_amount(adjusted_budget)
                mcc, mcc_category = self._get_mcc_category(current_month)
                channel = self._get_channel(current_month)
                time_of_day = self._get_time_of_day(current_month)

                transactions.append({
                    'id': str(uuid.uuid4()),
                    'customer_id': str(self.customer_id),
                    'date': date,
                    'amount': round(amount, 2),
                    'mcc': mcc,
                    'mcc_category': mcc_category,
                    'channel': channel,
                    'merchant': f"{self.NAME}_Merchant_{self.rng.integers(1000, 9999)}",
                    'country': self._get_country(current_month),
                    'time_of_day': time_of_day,
                })

            # Move to next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)

        return transactions

    @abstractmethod
    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Return base monthly spending for this month."""
        pass

    @abstractmethod
    def _get_seasonality(self, month: datetime) -> float:
        """Return seasonality factor (1.0 = no seasonality)."""
        pass

    @abstractmethod
    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Return MCC category probabilities for this month."""
        pass

    def _get_transaction_count(self, month: datetime) -> int:
        return self.rng.integers(25, 31)

    def _get_random_date_in_month(self, month: datetime) -> datetime:
        day = self.rng.integers(1, 29)
        return month.replace(day=min(day, 28))

    def _get_transaction_amount(self, monthly_budget: float) -> float:
        amount = self.rng.lognormal(mean=np.log(50), sigma=0.5)
        return min(amount, monthly_budget * 0.5)

    def _get_mcc_category(self, month: datetime) -> tuple:
        """Select MCC and category based on persona distribution."""
        mcc_dist = self._get_mcc_distribution(month)
        categories = list(mcc_dist.keys())
        probabilities = list(mcc_dist.values())

        category = self.rng.choice(categories, p=probabilities)

        # Map category to MCC code
        mcc_map = {
            'Groceries': '5411',
            'Restaurants': '5812',
            'Transport': '4121',
            'Entertainment': '7922',
            'Shopping': '5399',
            'Home': '5200',
            'Kids': '5945',
            'Travel': '4511',
            'Utilities': '4900',
            'Alcohol': '5921',
            'Gambling': '7995',
            'Crypto': '6211',
            'Tech': '5734',
            'Other': '9999',
        }

        mcc = mcc_map.get(category, '9999')
        return mcc, category

    def _get_channel(self, month: datetime) -> str:
        """Return transaction channel."""
        channels = ['POS', 'Online', 'ATM', 'Mobile']
        return self.rng.choice(channels)

    def _get_time_of_day(self, month: datetime) -> str:
        """Return time of day for transaction."""
        return self.rng.choice(['morning', 'afternoon', 'evening', 'night'])

    def _get_country(self, month: datetime) -> str:
        """Return transaction country."""
        return 'DE'  # Germany (can be overridden)


class StableJohn(PersonaGenerator):
    """STABLE_John: Baseline predictable customer with linear growth."""

    NAME = "STABLE_John"
    PERSONA_ID = 1
    NARRATIVE = "Middle-aged professional, stable income, consistent spending"
    EXPECTED_RISK_SCORE = 0.15

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Linear growth: 3000 + 0.2% per month."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)
        growth = 1.0 + (0.002 * months_since_start)  # +0.2% per month
        return 3000 * growth

    def _get_seasonality(self, month: datetime) -> float:
        """Strong seasonality: Dec +20%, Aug -10%."""
        seasonality_map = {
            1: 0.95, 2: 0.95, 3: 0.98, 4: 1.0, 5: 1.0, 6: 0.98,
            7: 0.95, 8: 0.90, 9: 0.98, 10: 1.0, 11: 1.05, 12: 1.20,
        }
        return seasonality_map.get(month.month, 1.0)

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Stable distribution: Groceries 35%, Restaurants 25%, Transport 20%, Other 20%."""
        return {
            'Groceries': 0.35,
            'Restaurants': 0.25,
            'Transport': 0.20,
            'Other': 0.20,
        }


class ChurnSarah(PersonaGenerator):
    """CHURN_Sarah: Silent churn with gradual spending decline and category shift."""

    NAME = "CHURN_Sarah"
    PERSONA_ID = 2
    NARRATIVE = "Young professional, gradually reduces spending, switches to subsistence"
    EXPECTED_RISK_SCORE = 0.75

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Phase 1 (1-12): 3500. Phase 2 (13-18): decay 8%/mo. Phase 3 (19-24): plateau at 1800."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 12:
            return 3500  # Phase 1: Normal
        elif months_since_start < 18:
            decay_months = months_since_start - 12
            return 3500 * ((1 - 0.08) ** decay_months)  # Phase 2: Decay
        else:
            return 1800  # Phase 3: Churn plateau

    def _get_seasonality(self, month: datetime) -> float:
        """Weak seasonality in phase 1, flat in phases 2-3."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 12:
            seasonality_map = {1: 0.9, 2: 0.9, 3: 0.95, 4: 1.0, 5: 1.0, 6: 0.95,
                            7: 0.95, 8: 0.95, 9: 0.98, 10: 1.0, 11: 1.1, 12: 1.15}
            return seasonality_map.get(month.month, 1.0)
        else:
            return 1.0  # No seasonality in decay phases

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Shift from restaurants/shopping to groceries only."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 12:
            return {'Restaurants': 0.40, 'Shopping': 0.30, 'Transport': 0.20, 'Groceries': 0.10}
        elif months_since_start < 18:
            # Linear transition over 6 months
            progress = (months_since_start - 12) / 6.0
            return {
                'Groceries': 0.10 + (0.90 * progress),
                'Restaurants': 0.40 * (1 - progress),
                'Shopping': 0.30 * (1 - progress),
                'Transport': 0.20 * (1 - progress),
            }
        else:
            return {'Groceries': 1.0}  # 100% groceries (subsistence)


class StressAlex(PersonaGenerator):
    """STRESS_Alex: High volatility with sudden behavior shift."""

    NAME = "STRESS_Alex"
    PERSONA_ID = 3
    NARRATIVE = "Business owner under stress, high volatility, shifts to single category"
    EXPECTED_RISK_SCORE = 0.60

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Phase 1 (1-8): 4000. Phase 2 (9+): 3200 with high variance."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 8:
            base = 4000
        else:
            base = 3200

        # Add random noise (40% variance)
        noise = self.rng.normal(1.0, 0.40)
        return max(base * noise, 100)  # Ensure positive

    def _get_seasonality(self, month: datetime) -> float:
        """No seasonality (stress-driven, not calendar-driven)."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Shift to groceries + alcohol (coping behavior)."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 9:
            return {'Restaurants': 0.35, 'Shopping': 0.30, 'Groceries': 0.20, 'Other': 0.15}
        else:
            return {'Groceries': 0.60, 'Alcohol': 0.30, 'Other': 0.10}

    def _get_time_of_day(self, month: datetime) -> str:
        """Shift to late-night transactions in stress phase."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 9:
            return self.rng.choice(['morning', 'afternoon', 'evening'])
        else:
            # Heavy night-time concentration
            return self.rng.choice(['evening', 'night'], p=[0.3, 0.7])


class ShifterElena(PersonaGenerator):
    """SHIFTER_Elena: Positive lifestyle change with permanent category shift."""

    NAME = "SHIFTER_Elena"
    PERSONA_ID = 4
    NARRATIVE = "Life event (marriage/kids/house), permanent category shift"
    EXPECTED_RISK_SCORE = 0.20

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Phase 1 (1-6): 2800. Phase 2 (7+): 3800."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 6:
            return 2800
        else:
            return 3800  # +35% increase

    def _get_seasonality(self, month: datetime) -> float:
        """Strong family-oriented seasonality."""
        seasonality_map = {
            1: 1.0, 2: 1.0, 3: 0.95, 4: 0.95, 5: 1.0, 6: 0.95,
            7: 1.0, 8: 0.90, 9: 1.05, 10: 1.05, 11: 1.1, 12: 1.2,  # School & holidays
        }
        return seasonality_map.get(month.month, 1.0)

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Shift from entertainment to home/kids."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 7:
            return {'Restaurants': 0.45, 'Entertainment': 0.30, 'Transport': 0.15, 'Other': 0.10}
        else:
            return {'Home': 0.40, 'Kids': 0.25, 'Groceries': 0.20, 'Transport': 0.15}


class AnomalyMark(PersonaGenerator):
    """ANOMALY_Mark: Risky behavioral anomalies with gambling and late-night spikes."""

    NAME = "ANOMALY_Mark"
    PERSONA_ID = 5
    NARRATIVE = "High-risk customer, irregular transactions, gambling, late-night spikes"
    EXPECTED_RISK_SCORE = 0.85

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Phase 1 (1-12): 2500. Phase 2 (13+): erratic 2000-4000."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 12:
            return 2500
        else:
            # Extremely volatile
            return self.rng.uniform(2000, 4000)

    def _get_seasonality(self, month: datetime) -> float:
        """No seasonality."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Shift to gambling, crypto, risky merchants."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 12:
            return {'Groceries': 0.30, 'Restaurants': 0.30, 'Transport': 0.25, 'Other': 0.15}
        else:
            return {
                'Gambling': 0.30,
                'Crypto': 0.20,
                'Groceries': 0.25,
                'Restaurants': 0.15,
                'Other': 0.10,
            }

    def _get_time_of_day(self, month: datetime) -> str:
        """Heavy night-time concentration in anomaly phase."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 12:
            return self.rng.choice(['morning', 'afternoon', 'evening', 'night'], p=[0.3, 0.3, 0.25, 0.15])
        else:
            return self.rng.choice(['evening', 'night'], p=[0.2, 0.8])


class SeasonalWinter(PersonaGenerator):
    """SEASONAL_Winter: Winter-heavy spender with inverted seasonality."""

    NAME = "SEASONAL_Winter"
    PERSONA_ID = 6
    NARRATIVE = "Retiree, seasonal spending pattern, winter travel, summer home"
    EXPECTED_RISK_SCORE = 0.25

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Base monthly budget."""
        return 2200

    def _get_seasonality(self, month: datetime) -> float:
        """Inverted seasonality: winter high, summer low."""
        seasonality_map = {
            1: 1.50, 2: 1.40, 3: 1.30, 4: 0.80, 5: 0.75, 6: 0.80,
            7: 0.75, 8: 0.75, 9: 0.90, 10: 0.90, 11: 0.95, 12: 1.50,
        }
        return seasonality_map.get(month.month, 1.0)

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Travel-heavy, utilities, restaurants."""
        return {'Travel': 0.40, 'Utilities': 0.15, 'Restaurants': 0.20, 'Other': 0.25}


class GrowthTech(PersonaGenerator):
    """GROWTH_Tech: Young tech worker with consistent salary growth."""

    NAME = "GROWTH_Tech"
    PERSONA_ID = 7
    NARRATIVE = "Young tech worker, consistent salary growth, increasing spending"
    EXPECTED_RISK_SCORE = 0.10

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Exponential growth: +2% per month."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)
        return 2000 * ((1.02) ** months_since_start)

    def _get_seasonality(self, month: datetime) -> float:
        """No seasonality."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Tech-heavy."""
        return {'Tech': 0.40, 'Restaurants': 0.30, 'Travel': 0.20, 'Other': 0.10}


class RiskCrypto(PersonaGenerator):
    """RISK_Crypto: Young crypto trader with extreme volatility."""

    NAME = "RISK_Crypto"
    PERSONA_ID = 8
    NARRATIVE = "Young crypto trader, extreme volatility, high-risk transactions"
    EXPECTED_RISK_SCORE = 0.70

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Highly variable monthly budget."""
        return self.rng.uniform(2000, 8000)

    def _get_seasonality(self, month: datetime) -> float:
        """No seasonality."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Crypto-heavy."""
        return {'Crypto': 0.50, 'Restaurants': 0.20, 'Gambling': 0.15, 'Other': 0.15}


class LuxuryPremium(PersonaGenerator):
    """LUXURY_Premium: Executive with consistent high-value spending."""

    NAME = "LUXURY_Premium"
    PERSONA_ID = 9
    NARRATIVE = "Executive, luxury lifestyle, consistent high-value spending"
    EXPECTED_RISK_SCORE = 0.08

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """High stable budget."""
        return 8000

    def _get_seasonality(self, month: datetime) -> float:
        """Slight summer/winter adjustment."""
        seasonality_map = {
            1: 1.0, 2: 1.0, 3: 1.0, 4: 0.95, 5: 1.0, 6: 1.05,
            7: 1.15, 8: 1.15, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.10,
        }
        return seasonality_map.get(month.month, 1.0)

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Premium spending."""
        return {'Restaurants': 0.50, 'Travel': 0.25, 'Shopping': 0.15, 'Other': 0.10}


class BudgetSaver(PersonaGenerator):
    """BUDGET_Saver: Conservative spender with minimal essential purchases."""

    NAME = "BUDGET_Saver"
    PERSONA_ID = 10
    NARRATIVE = "Conservative spender, minimal spending, essential purchases only"
    EXPECTED_RISK_SCORE = 0.08

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Very low budget."""
        return 1000

    def _get_seasonality(self, month: datetime) -> float:
        """Slight winter heating adjustment."""
        seasonality_map = {
            1: 1.05, 2: 1.05, 3: 1.0, 4: 1.0, 5: 1.0, 6: 0.95,
            7: 0.95, 8: 0.95, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.05,
        }
        return seasonality_map.get(month.month, 1.0)

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Essential only."""
        return {'Groceries': 0.70, 'Utilities': 0.15, 'Transport': 0.10, 'Other': 0.05}
