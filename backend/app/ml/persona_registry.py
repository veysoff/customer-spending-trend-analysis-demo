"""
Persona Registry for Phase 4: Fine-Grained Synthetic Profiles

This module provides a registry and utility functions for managing all 22 personas.
Extended from 10 core personas to include 12 edge case personas for comprehensive
test data generation covering extreme spending, temporal anomalies, behavioral
patterns, fraud indicators, and lifecycle stages.
"""

from typing import Dict, Type, List, Optional

from .persona_generators import (
    StableJohn,
    ChurnSarah,
    StressAlex,
    ShifterElena,
    AnomalyMark,
    SeasonalWinter,
    GrowthTech,
    RiskCrypto,
    LuxuryPremium,
    BudgetSaver,
    ExtremeSpender,
    SubsistenceMinimal,
    DormantRevival,
    DeclineRecovery,
    BurstFraud,
    VolatilityCyclic,
    CategorySwitcher,
    PerfectRoutine,
    MultiCountry,
    MuleAccount,
    SplitterSmurfer,
    NighttimeOnly,
    PersonaGenerator,
)


# Registry mapping persona IDs to generator classes
PERSONA_REGISTRY: Dict[int, Type[PersonaGenerator]] = {
    # Original 10 personas (core patterns)
    1: StableJohn,
    2: ChurnSarah,
    3: StressAlex,
    4: ShifterElena,
    5: AnomalyMark,
    6: SeasonalWinter,
    7: GrowthTech,
    8: RiskCrypto,
    9: LuxuryPremium,
    10: BudgetSaver,
    # Extended 12 edge case personas
    11: ExtremeSpender,
    12: SubsistenceMinimal,
    13: DormantRevival,
    14: DeclineRecovery,
    15: BurstFraud,
    16: VolatilityCyclic,
    17: CategorySwitcher,
    18: PerfectRoutine,
    19: MultiCountry,
    20: MuleAccount,
    21: SplitterSmurfer,
    22: NighttimeOnly,
}


def get_persona_class(persona_id: int) -> Optional[Type[PersonaGenerator]]:
    """
    Get persona generator class by ID.

    Args:
        persona_id: Persona ID (1-22)

    Returns:
        PersonaGenerator subclass or None if not found
    """
    return PERSONA_REGISTRY.get(persona_id)


def list_personas() -> List[Dict[str, any]]:
    """
    List all available personas with their metadata.

    Returns:
        List of persona dictionaries with id, name, narrative, and expected_risk
    """
    return [
        {
            'id': persona_id,
            'name': persona_class.NAME,
            'narrative': persona_class.NARRATIVE,
            'expected_risk_score': persona_class.EXPECTED_RISK_SCORE,
        }
        for persona_id, persona_class in sorted(PERSONA_REGISTRY.items())
    ]


def get_all_persona_classes() -> Dict[int, Type[PersonaGenerator]]:
    """
    Get all persona generator classes.

    Returns:
        Dictionary mapping persona IDs to generator classes
    """
    return PERSONA_REGISTRY.copy()
