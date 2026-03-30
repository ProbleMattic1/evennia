# GM workflow: station NPCs and puppeting

## Purpose

Station service characters (brokers, dispatchers, clerks) are normal `Character`
objects with `db.is_npc = True`, owned by the service account. Players interact
via `station/*` when the matching NPC is in the room. Room echoes and desk
ambience attribute visible lines to those objects when possible.

## When to puppet an NPC

- Live roleplay: tours, inspections, disputes, bespoke dialogue beyond scripted handlers.
- Temporary scenes: use a staff account with `Developer` (or equivalent) so
  `at_pre_puppet` point-buy rules do not block NPC characters that are already
  bootstrapped with `db.rpg_pointbuy_done = True`.

## Safe procedure

1. Use `@ic <npc>` (or your game’s equivalent) to puppet the target NPC.
2. Stay in-character for public channels and room output; use `say` / `emote`
   as usual. NPC cmdsets (e.g. promenade guide) apply while puppeted.
3. When finished, **unpuppet** (`@ooc` / unpuppet command) so the NPC is not
   left tied to a staff session. Avoid leaving service NPCs puppeted overnight.
4. Do **not** reparent or delete NPC objects during a scene without a rollback plan.

## Locks and accounts

- NPCs must remain on the designated service account with correct `puppet:` locks.
- Do not grant player accounts puppet rights over service NPCs.

## Coordination with automation

- Interval scripts (mining, haulers, economy) remain authoritative for mechanics.
- GM puppeting is for **presentation and RP**; do not rely on a puppeted NPC
  for ticks or payouts.

## Web vs telnet

- Web `play_interact` uses the character resolved for web APIs, not necessarily
  a live telnet puppet. Room echoes from web exclude the acting character from
  the public line while still sending private dialogue to `char.msg`.
