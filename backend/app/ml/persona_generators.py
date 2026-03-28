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


class ExtremeSpender(PersonaGenerator):
    """EXTREME_Spender: Wealthy customer with very high monthly spending (>$10k)."""

    NAME = "EXTREME_Spender"
    PERSONA_ID = 11
    NARRATIVE = "High net worth individual with luxury spending habits"
    EXPECTED_RISK_SCORE = 0.05

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Very high monthly budget with slight growth."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)
        return 10000 + (50 * months_since_start)

    def _get_seasonality(self, month: datetime) -> float:
        """Seasonal travel and holidays."""
        seasonality_map = {1: 1.2, 2: 0.9, 3: 1.0, 4: 0.95, 5: 1.05, 6: 1.1,
                          7: 1.25, 8: 1.2, 9: 1.0, 10: 0.95, 11: 1.15, 12: 1.3}
        return seasonality_map.get(month.month, 1.0)

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Premium shopping and travel."""
        return {'Shopping': 0.40, 'Travel': 0.30, 'Restaurants': 0.20, 'Entertainment': 0.10}

    def _get_transaction_amount(self, monthly_budget: float) -> float:
        """Higher amounts for premium customer."""
        amount = self.rng.lognormal(mean=np.log(300), sigma=0.6)
        return min(amount, monthly_budget * 0.3)


class SubsistenceMinimal(PersonaGenerator):
    """SUBSISTENCE_Minimal: Very low monthly spending (<$100) from dormant/minimal account."""

    NAME = "SUBSISTENCE_Minimal"
    PERSONA_ID = 12
    NARRATIVE = "Minimal spending, likely student or unemployed, essential purchases only"
    EXPECTED_RISK_SCORE = 0.45

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Very minimal budget."""
        return self.rng.uniform(50, 150)

    def _get_seasonality(self, month: datetime) -> float:
        """No seasonality."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Only essentials."""
        return {'Groceries': 0.80, 'Transport': 0.15, 'Utilities': 0.05}

    def _get_transaction_count(self, month: datetime) -> int:
        """Very few transactions."""
        return self.rng.integers(3, 8)


class DormantRevival(PersonaGenerator):
    """DORMANT_Revival: Account inactive 8 months, then gradual reactivation."""

    NAME = "DORMANT_Revival"
    PERSONA_ID = 13
    NARRATIVE = "Dormant account reactivated, customer returning after 8-month absence"
    EXPECTED_RISK_SCORE = 0.55

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Zero for 8 months, then gradual ramp-up."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 8:
            return 0  # Dormant period
        else:
            # Gradual ramp-up over 4 months (months 8-12), starting with small base
            ramp_months = min(months_since_start - 8, 4)
            # Start with minimum of $500 (month 8), ramp to $3000 (month 12)
            return 500 + ((ramp_months / 4.0) * 2500)

    def _get_seasonality(self, month: datetime) -> float:
        """No seasonality."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Start with essentials, diversify as activity returns."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 8:
            return {'Groceries': 0.9, 'Other': 0.1}  # Only essentials when reactivating
        else:
            # Gradually diversify
            progress = min((months_since_start - 8) / 8.0, 1.0)
            return {
                'Groceries': 0.4 + (0.5 * (1 - progress)),
                'Restaurants': 0.2 * progress,
                'Transport': 0.2 * progress,
                'Entertainment': 0.1 * progress,
                'Other': 0.1,
            }

    def _get_transaction_count(self, month: datetime) -> int:
        """Few txns initially, increasing."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)
        if months_since_start < 8:
            return 0  # Dormant
        else:
            ramp = min((months_since_start - 8) / 8.0, 1.0)
            return int(ramp * 25 + 5)


class DeclineRecovery(PersonaGenerator):
    """DECLINE_Recovery: Sharp decline followed by V-shaped recovery."""

    NAME = "DECLINE_Recovery"
    PERSONA_ID = 14
    NARRATIVE = "Temporary life crisis (month 7-12) followed by strong recovery"
    EXPECTED_RISK_SCORE = 0.40

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """V-shaped pattern."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 6:
            return 3500  # Normal
        elif months_since_start < 12:
            # Decline phase
            decline_progress = (months_since_start - 6) / 6.0
            return 3500 * (1 - 0.55 * decline_progress)  # Down to ~1575
        else:
            # Recovery phase
            recovery_progress = min((months_since_start - 12) / 12.0, 1.0)
            low_point = 1575
            return low_point + (4200 - low_point) * recovery_progress  # Up to $4200

    def _get_seasonality(self, month: datetime) -> float:
        """Light seasonality."""
        seasonality_map = {1: 0.95, 2: 0.95, 3: 1.0, 4: 1.0, 5: 1.0, 6: 0.98,
                          7: 0.98, 8: 0.98, 9: 1.0, 10: 1.0, 11: 1.05, 12: 1.1}
        return seasonality_map.get(month.month, 1.0)

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Shift to essentials during crisis."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 6:
            return {'Restaurants': 0.40, 'Shopping': 0.30, 'Entertainment': 0.20, 'Groceries': 0.10}
        elif months_since_start < 12:
            # Crisis: shift to essentials
            return {'Groceries': 0.70, 'Transport': 0.15, 'Utilities': 0.15}
        else:
            # Recovery: gradual return to normal
            recovery_progress = min((months_since_start - 12) / 12.0, 1.0)
            crisis_factor = 1.0 - recovery_progress

            # Ensure probabilities sum to 1.0
            distribution = {
                'Restaurants': 0.35 * recovery_progress,
                'Shopping': 0.25 * recovery_progress,
                'Entertainment': 0.15 * recovery_progress,
                'Groceries': 0.15 + 0.55 * crisis_factor,
                'Transport': 0.10 * crisis_factor,
            }
            total = sum(distribution.values())
            return {k: v / total for k, v in distribution.items()}


class BurstFraud(PersonaGenerator):
    """BURST_Fraud: Suspicious rapid transaction clusters."""

    NAME = "BURST_Fraud"
    PERSONA_ID = 15
    NARRATIVE = "Suspicious rapid transaction sequences, potential fraud pattern"
    EXPECTED_RISK_SCORE = 0.85

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Normal baseline."""
        return 3000

    def _get_seasonality(self, month: datetime) -> float:
        """No seasonality."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Various categories."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 12:
            # Normal behavior first half
            return {'Groceries': 0.30, 'Restaurants': 0.25, 'Shopping': 0.25, 'Entertainment': 0.20}
        else:
            # Fraud phase: casino/gambling (normalize probabilities)
            return {'Gambling': 0.50, 'ATM': 0.30, 'Shopping': 0.15, 'Other': 0.05}

    def _get_transaction_count(self, month: datetime) -> int:
        """Normal until month 12, then burst clusters."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 12:
            return self.rng.integers(20, 30)
        else:
            # Burst phase: 5-10 txns per cluster
            return self.rng.integers(40, 60)

    def _get_random_date_in_month(self, month: datetime) -> datetime:
        """Create temporal clusters in fraud phase."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 12:
            # Normal distribution
            day = self.rng.integers(1, 29)
        else:
            # Clustered - same day clusters for fraud bursts
            day = self.rng.integers(1, 29)

        return month.replace(day=min(day, 28))

    def _get_transaction_amount(self, monthly_budget: float) -> float:
        """Larger amounts for fraud phase."""
        amount = self.rng.lognormal(mean=np.log(50), sigma=0.5)
        return min(amount, monthly_budget * 0.4)


class VolatilityCyclic(PersonaGenerator):
    """VOLATILITY_Cyclic: Extreme quarterly boom-bust cycles."""

    NAME = "VOLATILITY_Cyclic"
    PERSONA_ID = 16
    NARRATIVE = "Seasonal business owner with extreme quarterly cycles"
    EXPECTED_RISK_SCORE = 0.40

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Quarterly cycle."""
        quarter = (month.month - 1) // 3

        if quarter == 0:  # Q1: Boom
            return 8000
        elif quarter == 1:  # Q2: Decline
            return 2000
        elif quarter == 2:  # Q3: Recovery
            return 6000
        else:  # Q4: Peak
            return 9000

    def _get_seasonality(self, month: datetime) -> float:
        """No additional seasonality, quarterly cycle is primary."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Shift based on cycle."""
        quarter = (month.month - 1) // 3

        if quarter in [0, 3]:  # Boom phases
            return {'Shopping': 0.40, 'Restaurants': 0.30, 'Entertainment': 0.20, 'Travel': 0.10}
        else:  # Decline phases
            return {'Groceries': 0.50, 'Transport': 0.30, 'Utilities': 0.20}


class CategorySwitcher(PersonaGenerator):
    """CATEGORY_Switcher: Complete lifestyle change with category shift."""

    NAME = "CATEGORY_Switcher"
    PERSONA_ID = 17
    NARRATIVE = "Major lifestyle change (job relocation, family status), MCC distribution completely shifts"
    EXPECTED_RISK_SCORE = 0.50

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Stable amount, categories change."""
        return 3000

    def _get_seasonality(self, month: datetime) -> float:
        """Light seasonality."""
        seasonality_map = {1: 0.95, 2: 0.95, 3: 1.0, 4: 1.0, 5: 1.0, 6: 0.98,
                          7: 0.98, 8: 0.98, 9: 1.0, 10: 1.0, 11: 1.05, 12: 1.1}
        return seasonality_map.get(month.month, 1.0)

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Major shift at month 7."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 7:
            # Urban: restaurants heavy
            return {'Restaurants': 0.50, 'Entertainment': 0.25, 'Transport': 0.15, 'Groceries': 0.10}
        else:
            # Rural/family: groceries heavy
            return {'Groceries': 0.70, 'Utilities': 0.15, 'Kids': 0.10, 'Transport': 0.05}


class PerfectRoutine(PersonaGenerator):
    """PERFECT_Routine: Extremely deterministic spending with same amounts/times."""

    NAME = "PERFECT_Routine"
    PERSONA_ID = 18
    NARRATIVE = "Extremely regular person with near-identical daily purchases"
    EXPECTED_RISK_SCORE = 0.08

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Fixed budget."""
        return 3000  # Exactly $3000/month

    def _get_seasonality(self, month: datetime) -> float:
        """No seasonality."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Fixed distribution."""
        return {'Groceries': 0.35, 'Restaurants': 0.25, 'Transport': 0.20, 'Utilities': 0.20}

    def _get_transaction_count(self, month: datetime) -> int:
        """Exactly 22 transactions per month."""
        return 22

    def _get_random_date_in_month(self, month: datetime) -> datetime:
        """Specific days: Mon-Fri for work, Wed for groceries, Fri for gas, last day for utilities."""
        # Simplified: spread evenly across Mon-Fri
        weekday = self.rng.integers(0, 5)  # Mon=0 to Fri=4
        day = 1 + (self.rng.integers(0, 4) * 7) + weekday  # Spread across weeks
        return month.replace(day=min(day, 28))

    def _get_transaction_amount(self, monthly_budget: float) -> float:
        """Very consistent amounts."""
        # 5 merchants with fixed amounts
        base_amounts = [4.50, 12.00, 80, 50, 150]
        amount = self.rng.choice(base_amounts)
        # Add tiny variance (±0.5)
        return amount + self.rng.uniform(-0.5, 0.5)

    def _get_time_of_day(self, month: datetime) -> str:
        """Specific times."""
        return self.rng.choice(['morning', 'afternoon', 'evening'], p=[0.3, 0.5, 0.2])


class MultiCountry(PersonaGenerator):
    """MULTI_Country: Frequent international traveler with multi-country transactions."""

    NAME = "MULTI_Country"
    PERSONA_ID = 19
    NARRATIVE = "Frequent international traveler with transactions across multiple countries"
    EXPECTED_RISK_SCORE = 0.25

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Normal budget."""
        return 3500

    def _get_seasonality(self, month: datetime) -> float:
        """Slight summer travel increase."""
        seasonality_map = {1: 0.95, 2: 0.95, 3: 1.0, 4: 1.05, 5: 1.1, 6: 1.15,
                          7: 1.25, 8: 1.2, 9: 1.05, 10: 1.0, 11: 0.95, 12: 1.0}
        return seasonality_map.get(month.month, 1.0)

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Travel-heavy distribution."""
        return {'Restaurants': 0.30, 'Travel': 0.30, 'Shopping': 0.20, 'Entertainment': 0.20}

    def _get_country(self, month: datetime) -> str:
        """Rotate through multiple countries."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)
        countries = ['GB', 'US', 'FR', 'DE', 'ES']
        # Shift countries monthly with 40% GB baseline
        if self.rng.random() < 0.4:
            return 'GB'
        return self.rng.choice(countries)


class MuleAccount(PersonaGenerator):
    """MULE_Account: Money laundering simulation with rapid deposits/withdrawals."""

    NAME = "MULE_Account"
    PERSONA_ID = 20
    NARRATIVE = "Suspicious money movement pattern, potential money mule account"
    EXPECTED_RISK_SCORE = 0.90

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Cycles of large amounts."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 6:
            return 500  # Minimal activity initially
        else:
            # Large cycles
            return 5000

    def _get_seasonality(self, month: datetime) -> float:
        """No seasonality."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Wire transfers and ATM dominant."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 6:
            return {'Groceries': 0.5, 'Transport': 0.5}
        else:
            return {'Other': 0.80, 'ATM': 0.20}  # Ambiguous categories for transfers

    def _get_transaction_count(self, month: datetime) -> int:
        """2-3 large clusters per month."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 6:
            return self.rng.integers(5, 8)
        else:
            return self.rng.integers(8, 12)  # Few large txns

    def _get_transaction_amount(self, monthly_budget: float) -> float:
        """Very large, fixed amounts."""
        months_since_start = (month := datetime(2024, 1, 1)).year  # Dummy

        if months_since_start < 6:
            return self.rng.uniform(50, 100)
        else:
            # Large fixed amounts ($4500-5000)
            return self.rng.uniform(4500, 5000)


class SplitterSmurfer(PersonaGenerator):
    """SPLITTER_Smurfer: Transaction splitting to avoid detection."""

    NAME = "SPLITTER_Smurfer"
    PERSONA_ID = 21
    NARRATIVE = "Breaking large transactions into smaller amounts, potential structuring"
    EXPECTED_RISK_SCORE = 0.85

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Normal baseline that gets split."""
        return 3000

    def _get_seasonality(self, month: datetime) -> float:
        """No seasonality."""
        return 1.0

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Shifting from normal to repetitive same-category."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 6:
            return {'Groceries': 0.30, 'Shopping': 0.30, 'Restaurants': 0.25, 'Entertainment': 0.15}
        else:
            # Same merchant/category repeated
            return {'Shopping': 0.95, 'Other': 0.05}

    def _get_transaction_count(self, month: datetime) -> int:
        """Normal until splitting starts."""
        months_since_start = (month.year - self.start_date.year) * 12 + (month.month - self.start_date.month)

        if months_since_start < 6:
            return self.rng.integers(25, 30)
        else:
            # Many small transactions (splitting)
            return self.rng.integers(80, 120)

    def _get_transaction_amount(self, monthly_budget: float) -> float:
        """Smaller amounts when splitting."""
        months_since_start = (month := datetime(2024, 1, 1)).year  # Dummy

        if months_since_start < 6:
            amount = self.rng.lognormal(mean=np.log(100), sigma=0.5)
        else:
            # Consistently smaller: $500 split into 10 × $50 txns
            amount = self.rng.uniform(400, 600)

        return min(amount, monthly_budget * 0.3)


class NighttimeOnly(PersonaGenerator):
    """NIGHTTIME_Only: All transactions only at night (23:00-06:00)."""

    NAME = "NIGHTTIME_Only"
    PERSONA_ID = 22
    NARRATIVE = "Extreme temporal skew, all transactions only at night, potential shift work or concerning"
    EXPECTED_RISK_SCORE = 0.65

    def _calculate_monthly_budget(self, month: datetime) -> float:
        """Normal spending amount."""
        return 2500

    def _get_seasonality(self, month: datetime) -> float:
        """Summer increase (more outdoor nightlife)."""
        seasonality_map = {1: 0.95, 2: 0.95, 3: 1.0, 4: 1.05, 5: 1.1, 6: 1.15,
                          7: 1.25, 8: 1.2, 9: 1.05, 10: 0.98, 11: 0.95, 12: 0.95}
        return seasonality_map.get(month.month, 1.0)

    def _get_mcc_distribution(self, month: datetime) -> Dict[str, float]:
        """Night-oriented spending."""
        return {'Restaurants': 0.30, 'Entertainment': 0.30, 'ATM': 0.25, 'Shopping': 0.15}

    def _get_random_date_in_month(self, month: datetime) -> datetime:
        """Nighttime only + concentrated on weekends."""
        # Slightly bias towards Wed-Sat (nights out)
        if self.rng.random() < 0.6:
            # Weekend nights
            weekday = self.rng.integers(2, 6)  # Wed-Sat
        else:
            # Any weekday
            weekday = self.rng.integers(0, 7)

        day = 1 + (self.rng.integers(0, 4) * 7) + weekday
        day = min(day, 28)

        return month.replace(day=day)

    def _get_time_of_day(self, month: datetime) -> str:
        """Always night."""
        return self.rng.choice(['evening', 'night'], p=[0.3, 0.7])
