"""
Parse optional feedrefinery source keywords (shared plant bay vs personal silo).

Used by ``commands.refining.CmdFeedRefinery``. Kept here for small, import-light tests.
"""


def parse_feedrefinery_source(main: str) -> tuple[str, str]:
    """
    Returns (mode, rest) where mode is ``auto``, ``shared``, or ``silo``.

    ``rest`` is the remainder of the argument string after the keyword, lowercased
    and stripped (same as legacy ``feedrefinery`` parsing).
    """
    raw = (main or "").strip()
    s = raw.lower()
    for prefix in ("shared ", "plant ", "bay "):
        if s.startswith(prefix):
            return "shared", raw[len(prefix) :].strip().lower()
    for prefix in ("personal ", "silo ", "mine "):
        if s.startswith(prefix):
            return "silo", raw[len(prefix) :].strip().lower()
    return "auto", s
