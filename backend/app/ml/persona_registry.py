"""
Persona Registry for Phase 4: Fine-Grained Synthetic Profiles

This module provides a registry and utility functions for managing all 10 personas.
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
    PersonaGenerator,
)


# Registry mapping persona IDs to generator classes
PERSONA_REGISTRY: Dict[int, Type[PersonaGenerator]] = {
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
}


def get_persona_class(persona_id: int) -> Optional[Type[PersonaGenerator]]:
    """
    Get persona generator class by ID.

    Args:
        persona_id: Persona ID (1-10)

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
