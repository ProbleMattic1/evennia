from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StationServiceResult:
    private: str
    """Full ANSI/text for the caller only."""
    room_echo_template: str | None = None
    """
    Optional one-line template for others in the room, e.g.
    "{player} accepts a work order from {npc}."
    """


def as_result(maybe) -> StationServiceResult:
    """Allow handlers to return str (legacy) or StationServiceResult."""
    if isinstance(maybe, StationServiceResult):
        return maybe
    return StationServiceResult(private=str(maybe))
