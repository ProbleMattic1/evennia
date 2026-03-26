"""
Pure combat outcomes for property raids (extension point for deep RPG).
"""


def property_raid_outcome(holding, attacker_strength: int, defender_strength: int) -> dict:
    """
    Returns {damage_to_structures, credits_lost, morale_delta}.
    Wire to a combat command when a 'raid' action targets a property place.
    """
    _ = (holding, attacker_strength, defender_strength)
    return {
        "damage_to_structures": 0,
        "credits_lost": 0,
        "morale_delta": -5,
    }
