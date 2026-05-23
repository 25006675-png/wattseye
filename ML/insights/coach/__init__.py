"""WattsEye Coach engine: correlator -> quantifier -> templates -> ranker.

See plan/03_MACHINE_LEARNING.md and recommendation.md for the design rationale.
"""

from .situations import Situation, Card, HomeSnapshot, Evidence
from .coach_engine import generate_cards

__all__ = ["Situation", "Card", "HomeSnapshot", "Evidence", "generate_cards"]
