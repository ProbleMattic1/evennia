"""
Visitable shell rooms for PropertyHolding (RPG place layer).

Authority stays on PropertyLot + PropertyHolding; rooms are lazy-created surfaces.
"""

from evennia import create_object, search_object

from typeclasses.property_lot_registry import infer_lot_venue_id


def open_property_shell(holding):
    """
    Promote place from void to shell so resolve_property_root_room can create the interior.
    """
    st = dict(holding.db.place_state or {})
    if st.get("mode") == "void":
        st["mode"] = "shell"
    st.setdefault("root_room_id", None)
    st.setdefault("exit_from_hub_id", None)
    holding.db.place_state = st


def resolve_property_root_room(holding):
    """
    Return the visitable root room for this holding. Create on first demand
    if holding.db.place_state['mode'] != 'void'.
    """
    st = dict(holding.db.place_state or {})
    rid = st.get("root_room_id")
    if rid:
        found = search_object("#" + str(rid))
        if found:
            room = found[0]
            if hasattr(room, "contents") and getattr(room.db, "holding_ref", None) == holding:
                lot = getattr(holding.db, "lot_ref", None)
                if lot:
                    vid = infer_lot_venue_id(lot)
                    if not getattr(room.db, "venue_id", None):
                        room.db.venue_id = vid
                    room.tags.add(f"locator_venue:{vid}", category="locator")
                return room
        st["root_room_id"] = None
        holding.db.place_state = st

    mode = st.get("mode") or "void"
    if mode == "void":
        return None

    room = create_object(
        "typeclasses.rooms.Room",
        key=f"{holding.key} — interior",
    )
    room.db.desc = (
        "Your titled parcel. Development defines what stands here."
    )
    room.tags.add("property_place", category="realty")
    room.tags.add(f"holding_{holding.id}", category="property_place")
    room.db.holding_ref = holding
    lot = getattr(holding.db, "lot_ref", None)
    if lot:
        vid = infer_lot_venue_id(lot)
        room.db.venue_id = vid
        room.tags.add(f"locator_venue:{vid}", category="locator")
    st["root_room_id"] = room.id
    holding.db.place_state = st
    try:
        from web.ui.world_graph import invalidate_world_graph_cache

        invalidate_world_graph_cache()
    except Exception:
        pass
    return room


def ensure_district_exit(holding, district_room, exit_key="my property", aliases=None):
    """
    Idempotent exit from a district room into the property root room.
    """
    aliases = aliases or ["parcel", "holding"]
    root = resolve_property_root_room(holding)
    if not root or not district_room:
        return None
    for ex in district_room.exits:
        if ex.key == exit_key and getattr(ex, "destination", None) == root:
            return ex
    return create_object(
        "typeclasses.exits.Exit",
        key=exit_key,
        aliases=aliases,
        location=district_room,
        destination=root,
    )
