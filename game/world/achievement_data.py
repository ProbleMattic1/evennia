"""
Achievement definitions for ``evennia.contrib.game_systems.achievements``.

Loaded via ``settings.ACHIEVEMENT_CONTRIB_MODULES``.
"""

ACHIEVE_VETERAN_SPACER = {
    "key": "veteran_spacer",
    "name": "Veteran Spacer",
    "desc": "Gain five character levels through experience.",
    "category": "progression",
    "tracking": "character_level",
    "count": 5,
}

ACHIEVE_FIRST_LIGHT = {
    "key": "first_light",
    "name": "First Light",
    "desc": "Reach character level 2.",
    "category": "progression",
    "tracking": "milestone_level_2",
    "count": 1,
}

ACHIEVE_FIRST_MISSION = {
    "key": "first_mission",
    "name": "First Contract",
    "desc": "Complete any mission.",
    "category": "missions",
    "tracking": "mission_completed",
    "count": 1,
}

ACHIEVE_MISSION_VETERAN = {
    "key": "mission_veteran",
    "name": "Veteran Operator",
    "desc": "Complete ten missions.",
    "category": "missions",
    "tracking": "mission_completed",
    "count": 10,
}

ACHIEVE_FIRST_QUEST = {
    "key": "first_quest",
    "name": "First Thread",
    "desc": "Complete any quest.",
    "category": "quests",
    "tracking": "quest_completed",
    "count": 1,
}

ACHIEVE_STORY_RUNNER = {
    "key": "story_runner",
    "name": "Story Runner",
    "desc": "Complete five quests.",
    "category": "quests",
    "tracking": "quest_completed",
    "count": 5,
}

ACHIEVE_FIRST_PURCHASE = {
    "key": "first_purchase",
    "name": "Open Wallet",
    "desc": "Buy something from a merchant kiosk.",
    "category": "economy",
    "tracking": "catalog_purchase",
    "count": 1,
}

ACHIEVE_FIRST_CLAIM = {
    "key": "first_claim",
    "name": "Staked Ground",
    "desc": "File your first mining claim on a deposit.",
    "category": "mining",
    "tracking": "mining_site_claimed",
    "count": 1,
}
