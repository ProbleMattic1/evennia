"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

import time

from evennia.contrib.rpg.traits import TraitHandler
from evennia.objects.objects import DefaultCharacter
from evennia.utils import lazy_property, logger
from evennia.utils.text2html import parse_html
from evennia.utils.utils import make_iter

from typeclasses.crime_record import CrimeRecordHandler
from typeclasses.missions import MissionHandler
from typeclasses.quests import QuestHandler
from world.challenges.challenge_handler import ChallengeHandler
from world.progression import LevelUpEvent, add_xp as rules_add_xp, snapshot as progression_snapshot
from world.progression_rewards import apply_level_up_rewards
from world.web_stream import WEB_STREAM_OPTIONS_KEY, normalize_web_stream_meta

from .objects import ObjectParent


ABILITY_KEYS = ("str", "dex", "con", "int", "wis", "cha")
ABILITY_NAMES = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}

DEFAULT_ABILITY_BASES = {
    "str": 13,
    "dex": 15,
    "con": 14,
    "int": 17,
    "wis": 15,
    "cha": 17,
}

MARCUS_CHARACTER_KEY = "Marcus Killstar"

MARCUS_ABILITY_BASES = {
    "str": 24,
    "dex": 24,
    "con": 24,
    "int": 24,
    "wis": 24,
    "cha": 24,
}

NANOMEGA_REALTY_CHARACTER_KEY = "NanoMegaPlex Real Estate"

NANOMEGA_REALTY_ABILITY_BASES = {
    "str": 10,
    "dex": 12,
    "con": 12,
    "int": 15,
    "wis": 14,
    "cha": 18,
}

NANOMEGA_CONSTRUCTION_CHARACTER_KEY = "NanoMegaPlex Construction"

NANOMEGA_CONSTRUCTION_ABILITY_BASES = {
    "str": 14,
    "dex": 11,
    "con": 13,
    "int": 16,
    "wis": 12,
    "cha": 15,
}

NANOMEGA_ADVERTISING_CHARACTER_KEY = "NanoMegaPlex Advertising Agent"

FRONTIER_REALTY_CHARACTER_KEY = "Frontier Real Estate"
FRONTIER_CONSTRUCTION_CHARACTER_KEY = "Frontier Construction"
FRONTIER_ADVERTISING_CHARACTER_KEY = "Frontier Advertising Agent"
FRONTIER_PROMENADE_GUIDE_CHARACTER_KEY = "Frontier Station Guide"

NANOMEGA_ADVERTISING_ABILITY_BASES = {
    "str": 10,
    "dex": 11,
    "con": 11,
    "int": 15,
    "wis": 13,
    "cha": 18,
}

PROMENADE_GUIDE_CHARACTER_KEY = "Station Guide Kiran"

FRONTIER_PROMENADE_GUIDE_ABILITY_BASES = {
    "str": 10,
    "dex": 12,
    "con": 11,
    "int": 14,
    "wis": 13,
    "cha": 16,
}

PROMENADE_GUIDE_ABILITY_BASES = {
    "str": 10,
    "dex": 12,
    "con": 11,
    "int": 14,
    "wis": 13,
    "cha": 16,
}

PARCEL_COMMUTER_CHARACTER_KEY = "Mira Okonkwo"

PARCEL_COMMUTER_ABILITY_BASES = {
    "str": 10,
    "dex": 11,
    "con": 11,
    "int": 14,
    "wis": 13,
    "cha": 12,
}

LISTINGS_BROKER_CHARACTER_KEY = "Listings Broker Lyra"
HAUL_DISPATCHER_CHARACTER_KEY = "Haul Dispatcher Niko"
REFINERY_ANALYST_CHARACTER_KEY = "Refinery Analyst Oren"
CLAIMS_AGENT_CHARACTER_KEY = "Claims Agent Mina"
CONTRACT_CLERK_CHARACTER_KEY = "Contract Clerk Vale"

STATION_SERVICE_NPC_ABILITY_BASES = {
    "str": 10,
    "dex": 12,
    "con": 12,
    "int": 15,
    "wis": 14,
    "cha": 13,
}

GENERAL_SUPPLY_CLERK_CHARACTER_KEY = "Vesta Kline"

GENERAL_SUPPLY_CLERK_ABILITY_BASES = {
    "str": 10,
    "dex": 12,
    "con": 12,
    "int": 15,
    "wis": 14,
    "cha": 13,
}

CHARACTER_TYPECLASS_PATH = "typeclasses.characters.Character"


def character_key_skips_pointbuy(character_key):
    """Pre-configured NPCs that never use OOC point-buy."""
    return character_key in (
        MARCUS_CHARACTER_KEY,
        NANOMEGA_REALTY_CHARACTER_KEY,
        NANOMEGA_CONSTRUCTION_CHARACTER_KEY,
        NANOMEGA_ADVERTISING_CHARACTER_KEY,
        FRONTIER_REALTY_CHARACTER_KEY,
        FRONTIER_CONSTRUCTION_CHARACTER_KEY,
        FRONTIER_ADVERTISING_CHARACTER_KEY,
        PROMENADE_GUIDE_CHARACTER_KEY,
        FRONTIER_PROMENADE_GUIDE_CHARACTER_KEY,
        PARCEL_COMMUTER_CHARACTER_KEY,
        GENERAL_SUPPLY_CLERK_CHARACTER_KEY,
        LISTINGS_BROKER_CHARACTER_KEY,
        HAUL_DISPATCHER_CHARACTER_KEY,
        REFINERY_ANALYST_CHARACTER_KEY,
        CLAIMS_AGENT_CHARACTER_KEY,
        CONTRACT_CLERK_CHARACTER_KEY,
    )


def ability_bases_for_character_key(character_key, *, rpg_pointbuy_done):
    """
    Base scores when creating missing ability traits.

    Marcus: fixed god-tier. NanoMegaPlex Real Estate: fixed broker spread.
    rpg_pointbuy_done False: 8s until point-buy finishes (normal PCs).
    None (legacy) or True: DEFAULT_ABILITY_BASES for any still-missing trait.
    """
    if character_key == MARCUS_CHARACTER_KEY:
        return MARCUS_ABILITY_BASES
    if character_key == NANOMEGA_REALTY_CHARACTER_KEY:
        return NANOMEGA_REALTY_ABILITY_BASES
    if character_key == NANOMEGA_CONSTRUCTION_CHARACTER_KEY:
        return NANOMEGA_CONSTRUCTION_ABILITY_BASES
    if character_key == NANOMEGA_ADVERTISING_CHARACTER_KEY:
        return NANOMEGA_ADVERTISING_ABILITY_BASES
    if character_key == FRONTIER_REALTY_CHARACTER_KEY:
        return NANOMEGA_REALTY_ABILITY_BASES
    if character_key == FRONTIER_CONSTRUCTION_CHARACTER_KEY:
        return NANOMEGA_CONSTRUCTION_ABILITY_BASES
    if character_key == FRONTIER_ADVERTISING_CHARACTER_KEY:
        return NANOMEGA_ADVERTISING_ABILITY_BASES
    if character_key == PROMENADE_GUIDE_CHARACTER_KEY:
        return PROMENADE_GUIDE_ABILITY_BASES
    if character_key == FRONTIER_PROMENADE_GUIDE_CHARACTER_KEY:
        return FRONTIER_PROMENADE_GUIDE_ABILITY_BASES
    if character_key == PARCEL_COMMUTER_CHARACTER_KEY:
        return PARCEL_COMMUTER_ABILITY_BASES
    if character_key == GENERAL_SUPPLY_CLERK_CHARACTER_KEY:
        return GENERAL_SUPPLY_CLERK_ABILITY_BASES
    if character_key in (
        LISTINGS_BROKER_CHARACTER_KEY,
        HAUL_DISPATCHER_CHARACTER_KEY,
        REFINERY_ANALYST_CHARACTER_KEY,
        CLAIMS_AGENT_CHARACTER_KEY,
        CONTRACT_CLERK_CHARACTER_KEY,
    ):
        return STATION_SERVICE_NPC_ABILITY_BASES
    if rpg_pointbuy_done is False:
        return {k: 8 for k in ABILITY_KEYS}
    return DEFAULT_ABILITY_BASES


class Character(ObjectParent, DefaultCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    """

    WEB_MSG_BUFFER_MAX = 200

    @lazy_property
    def stats(self):
        return TraitHandler(self, db_attribute_key="rpg_stats", db_attribute_category="traits")

    @lazy_property
    def skills(self):
        return TraitHandler(self, db_attribute_key="rpg_skills", db_attribute_category="traits")

    @lazy_property
    def vitals(self):
        return TraitHandler(self, db_attribute_key="rpg_vitals", db_attribute_category="traits")

    @lazy_property
    def missions(self):
        return MissionHandler(self)

    @lazy_property
    def crime_record(self):
        return CrimeRecordHandler(self)

    @lazy_property
    def quests(self):
        return QuestHandler(self)

    @lazy_property
    def challenges(self):
        return ChallengeHandler(self)

    def record_web_stream_text(self, text, meta):
        """
        Append one outbound line to web_msg_buffer. ``text`` matches ``msg`` (str or tuple).
        Called from ServerSession.data_out (portal clients) or from ``msg`` when headless.
        """
        if text is None:
            return
        raw = text[0] if isinstance(text, tuple) else text
        if not isinstance(raw, str) or not raw.strip():
            return
        html = parse_html(raw, strip_ansi=False)

        buf = list(self.attributes.get("web_msg_buffer", default=[]))
        seq = int(self.attributes.get("web_msg_seq", default=0)) + 1
        buf.append({
            "seq": seq,
            "html": str(html),
            "ts": float(time.time()),
            "meta": dict(meta),
        })
        if len(buf) > self.WEB_MSG_BUFFER_MAX:
            buf = buf[-self.WEB_MSG_BUFFER_MAX :]

        self.attributes.add("web_msg_buffer", buf)
        self.attributes.add("web_msg_seq", seq)

    def msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
        """Emit to client(s); tee via data_out when sessions exist, else record here (API/headless)."""
        sessions = make_iter(session) if session else self.sessions.all()
        opts = options
        if opts is not None:
            opts = dict(opts)
            popped = opts.pop(WEB_STREAM_OPTIONS_KEY, None)
        else:
            popped = None
        meta = normalize_web_stream_meta(popped if isinstance(popped, dict) else {})
        kwargs = dict(kwargs)
        kwargs["web_stream_meta"] = meta
        super().msg(text=text, from_obj=from_obj, session=session, options=opts, **kwargs)
        if text is None:
            return
        if sessions:
            return
        self.record_web_stream_text(text, meta)

    def get_web_msg_buffer(self, since_seq=0):
        """
        Return rows: plain dicts with int seq, str html, float ts, dict meta.
        Only includes seq > since_seq when since_seq > 0.
        """
        stored_list = list(self.attributes.get("web_msg_buffer", default=[]))
        cutoff = int(since_seq)

        out = []
        for row in stored_list:
            out.append({
                "seq": int(row["seq"]),
                "html": str(row["html"]),
                "ts": float(row["ts"]),
                "meta": dict(row["meta"]),
            })

        if cutoff:
            return [e for e in out if e["seq"] > cutoff]
        return out

    def at_object_creation(self):
        super().at_object_creation()
        if self.db.credits is None:
            self.db.credits = 1000
        if self.db.morality is None:
            self.db.morality = {"good": 0, "evil": 0, "lawful": 0, "chaotic": 0}
        if self.key in (
            MARCUS_CHARACTER_KEY,
            NANOMEGA_REALTY_CHARACTER_KEY,
            NANOMEGA_CONSTRUCTION_CHARACTER_KEY,
            NANOMEGA_ADVERTISING_CHARACTER_KEY,
            PROMENADE_GUIDE_CHARACTER_KEY,
            PARCEL_COMMUTER_CHARACTER_KEY,
            GENERAL_SUPPLY_CLERK_CHARACTER_KEY,
        ):
            self.db.rpg_pointbuy_done = True
        else:
            self.db.rpg_pointbuy_done = False
        self.db.rpg_level = 1
        self.db.rpg_xp_into_level = 0
        self.ensure_default_rpg_traits()

    def ensure_default_rpg_traits(self):
        """Idempotent: safe to call for old characters that lack traits."""
        done = getattr(self.db, "rpg_pointbuy_done", None)
        bases = ability_bases_for_character_key(self.key, rpg_pointbuy_done=done)
        for key in ABILITY_KEYS:
            if self.stats.get(key):
                continue
            self.stats.add(
                key,
                ABILITY_NAMES[key],
                trait_type="static",
                base=bases[key],
                mod=0,
                mult=1.0,
            )
        if not self.vitals.get("hp"):
            self.vitals.add("hp", "Hit Points", trait_type="gauge", base=10, mod=0, min=0)
        if not self.skills.get("athletics"):
            self.skills.add(
                "athletics",
                "Athletics",
                trait_type="counter",
                base=0,
                mod=0,
                mult=1.0,
                min=0,
                max=None,
            )
        if getattr(self.db, "rpg_level", None) is None:
            self.db.rpg_level = 1
        if getattr(self.db, "rpg_xp_into_level", None) is None:
            self.db.rpg_xp_into_level = 0

    def grant_xp(self, amount: int, *, reason: str = ""):
        """Add XP; may level up. Use this from combat, quests, staff tools, etc."""

        def _on_level_up(ch, ev: LevelUpEvent):
            apply_level_up_rewards(ch, ev)
            ch.msg(f"|yYou reached level {ev.new_level}!|n")

        result = rules_add_xp(self, amount, on_level_up=_on_level_up)
        if amount > 0:
            logger.log_info(
                f"[progression] {self.key} (id={self.id}) gained {amount} XP"
                f"{(' ' + reason) if reason else ''}."
            )
            suffix = f" ({reason})" if reason else ""
            self.msg(f"You gain {amount} XP{suffix}.")
        return result

    def at_pre_puppet(self, account, session=None, **kwargs):
        if not account.check_permstring("Developer"):
            if (
                not character_key_skips_pointbuy(self.key)
                and getattr(self.db, "rpg_pointbuy_done", None) is False
            ):
                raise RuntimeError(
                    "Finish ability point-buy first (OOC): |wpointbuy|n, then |wic|n."
                )
        super().at_pre_puppet(account, session=session, **kwargs)

    def ability_modifier(self, ability_key):
        ability_key = ability_key.lower()
        trait = self.stats.get(ability_key)
        if not trait:
            return 0
        score = int(trait.value)
        return (score - 10) // 2

    def armor_class(self, armor_bonus=0, shield_bonus=0):
        return 10 + self.ability_modifier("dex") + armor_bonus + shield_bonus

    def get_rpg_dashboard_snapshot(self):
        self.ensure_default_rpg_traits()

        def static_payload(trait):
            return {
                "name": trait.name,
                "score": int(trait.value),
                "base": int(trait.base),
                "mod": int(trait.mod),
                "abilityMod": (int(trait.value) - 10) // 2,
            }

        def gauge_payload(trait):
            return {
                "name": trait.name,
                "current": int(trait.value),
                "max": int(trait.max) if trait.max is not None else None,
            }

        abilities = {k: static_payload(self.stats[k]) for k in ABILITY_KEYS if self.stats.get(k)}
        vitals = {}
        if self.vitals.get("hp"):
            vitals["hp"] = gauge_payload(self.vitals.hp)

        prog = progression_snapshot(self)
        return {
            "abilities": abilities,
            "vitals": vitals,
            "armorClass": self.armor_class(),
            "level": prog["level"],
            "xpIntoLevel": prog["xp_into_level"],
            "xpToNext": prog["xp_to_next"],
        }

    def at_post_move(self, source_location, move_type="move", **kwargs):
        super().at_post_move(source_location, move_type=move_type, **kwargs)
        dest = self.location
        if not dest:
            return
        try:
            from world.challenges.challenge_signals import emit
            from world.locator_zones import locator_zone_for_room
            has_mine = dest.tags.has("mining_site", category="mining")
            zone_id = locator_zone_for_room(dest, has_mining_site=has_mine)
            venue_id = getattr(dest.db, "venue_id", None) or None
            emit(self, "room_enter", {
                "room_id": dest.id,
                "zone_id": zone_id,
                "venue_id": venue_id,
            })
        except Exception:
            pass
        # Mirror mission room sync here to consolidate the pipeline
        try:
            self.missions.sync_room(dest)
        except Exception:
            pass
        try:
            self.quests.on_room_enter(dest)
        except Exception:
            pass

    def at_post_puppet(self, **kwargs):
        super().at_post_puppet(**kwargs)
        self.ensure_default_rpg_traits()
        from typeclasses.economy import get_economy

        econ = get_economy(create_missing=False)
        if econ:
            econ.sync_character_balance(self)
            # Daily balance snapshot for challenge predicates
            try:
                from world.challenges.challenge_signals import emit
                balance = econ.get_character_balance(self)
                emit(self, "balance_snapshot", {"balance": balance})
            except Exception:
                pass
