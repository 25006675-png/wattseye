"""Ranker: score cards, decide which surface.

score = impact_rm_monthly × confidence × novelty × dismiss_decay × severity_boost

Top N cards (default 2) get surfaced=True. The rest stay in the list but
render as secondary tiles in the UI.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .situations import Card, HomeSnapshot


SEVERITY_BOOST = {"low": 0.8, "medium": 1.0, "high": 1.3}
DISMISS_DECAY_DAYS = 7              # full suppression for 7 days after dismiss
NOVELTY_REPEAT_DAYS = 3             # already-shown <3 days ago = reduced novelty
DEFAULT_SURFACE_COUNT = 2


def _novelty(card_key: str, snap: HomeSnapshot) -> float:
    last_shown = snap.recently_shown.get(card_key)
    if last_shown is None:
        return 1.0
    age_days = (snap.timestamp - last_shown).total_seconds() / 86400
    if age_days >= NOVELTY_REPEAT_DAYS:
        return 1.0
    return 0.4 + 0.6 * (age_days / NOVELTY_REPEAT_DAYS)


def _dismiss_decay(card_key: str, snap: HomeSnapshot) -> float:
    last_dismissed = snap.dismissed_archetypes.get(card_key)
    if last_dismissed is None:
        return 1.0
    age_days = (snap.timestamp - last_dismissed).total_seconds() / 86400
    if age_days >= DISMISS_DECAY_DAYS:
        return 1.0
    return age_days / DISMISS_DECAY_DAYS  # linear ramp back to 1.0


def rank(cards: list[Card], snap: HomeSnapshot, surface_count: int = DEFAULT_SURFACE_COUNT) -> list[Card]:
    """Compute score, sort, mark top N as surfaced. Mutates cards in place + returns sorted list."""
    for c in cards:
        nov = _novelty(c.archetype_key, snap)
        dec = _dismiss_decay(c.archetype_key, snap)
        sev = SEVERITY_BOOST.get(c.severity, 1.0)
        # Use sqrt of RM so a RM 100 card doesn't crush a RM 9 card 11x over
        impact_factor = max(c.impact_rm_monthly, 0.5) ** 0.5
        c.score = round(impact_factor * c.confidence * nov * dec * sev, 3)

    cards.sort(key=lambda x: x.score, reverse=True)
    for i, c in enumerate(cards, start=1):
        c.rank = i
        c.surfaced = i <= surface_count
    return cards
