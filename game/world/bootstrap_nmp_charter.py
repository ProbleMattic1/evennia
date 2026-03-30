"""
Bootstrap NanoMegaPlex charter property lots and grant them to the
NanoMegaPlex Real Estate broker.

Charter lots are hand-authored, tier 3 (Prime), and span five prestige districts
inside the NanoMegaPlex.  Each is claimed immediately by the broker so it never
surfaces on the primary sovereign exchange.  Operators release lots to founders
and sponsors via `grantcharter` / secondary listing rather than the standard
purchase flow.

Safe to call on every server start (idempotent).
"""

from evennia import create_object, search_object

from typeclasses.property_claim_market import grant_primary_property_deed
from typeclasses.property_lots import PropertyLot
from world.venue_resolve import get_realty_broker_for_venue
from world.venues import apply_venue_metadata, get_venue


# ---------------------------------------------------------------------------
# District metadata (stored on lot.db for UI / mission hooks later)
# ---------------------------------------------------------------------------

DISTRICTS = {
    "crown_atrium": {
        "label": "Crown Atrium",
        "desc_flavor": (
            "the glass-ceilinged residential summit of the NanoMegaPlex — "
            "panoramic station views, whisper-climate control, and direct "
            "promenade lift access"
        ),
    },
    "sovereign_terrace": {
        "label": "Sovereign Terrace",
        "desc_flavor": (
            "the premier ground-level commercial front of the NanoMegaPlex — "
            "flagship storefronts with full-width holographic frontage and "
            "sovereign lease protection"
        ),
    },
    "meridian_heights": {
        "label": "Meridian Heights",
        "desc_flavor": (
            "a sought-after mid-plex luxury residential tier — wide private "
            "corridors, customised atrium access, and views over the civic core"
        ),
    },
    "apex_row": {
        "label": "Apex Row",
        "desc_flavor": (
            "the highest-traffic commercial strip in the NanoMegaPlex — "
            "corner anchors, prime footfall, and integrated broadcast kiosks"
        ),
    },
    "coreward_industrial": {
        "label": "Coreward Industrial",
        "desc_flavor": (
            "the inner-ring premium fab district — direct conduit to the "
            "processing plant, reinforced power routing, and sovereign "
            "industrial lease protections"
        ),
    },
}


# ---------------------------------------------------------------------------
# Charter lot catalogue
# ---------------------------------------------------------------------------
# Fields:
#   lot_key     — stable unique object key (never change after first boot)
#   tier        — always 3 (Prime) for charter stock
#   zone        — residential | commercial | industrial
#   size_units  — footprint; charter lots exceed the procedural jackpot max (6)
#   district_id — key into DISTRICTS above
#   desc        — flavour text appended to the standard parcel description
# ---------------------------------------------------------------------------

NMP_CHARTER_CATALOGUE = [
    # --- Crown Atrium (residential sky stacks) ---
    {
        "lot_key": "Crown Atrium Penthouse I",
        "tier": 3, "zone": "residential", "size_units": 10,
        "district_id": "crown_atrium",
        "desc": (
            "The largest residential charter parcel at the crown of the NanoMegaPlex. "
            "Full-height observation ports, private lift lobby, and direct link to the "
            "Sovereign Terrace below.  First-tier charter offering."
        ),
    },
    {
        "lot_key": "Crown Atrium Penthouse II",
        "tier": 3, "zone": "residential", "size_units": 10,
        "district_id": "crown_atrium",
        "desc": (
            "Mirror parcel to Penthouse I; identical footprint on the opposing arc of "
            "the atrium crown.  Natural light cycle synchronised to station time."
        ),
    },
    {
        "lot_key": "Crown Atrium Penthouse III",
        "tier": 3, "zone": "residential", "size_units": 8,
        "district_id": "crown_atrium",
        "desc": (
            "Compact crown parcel with the same atrium views as the flagship pair. "
            "Preferred by operators who want Crown Atrium prestige in a focused footprint."
        ),
    },
    {
        "lot_key": "Crown Atrium Sky Suite Alpha",
        "tier": 3, "zone": "residential", "size_units": 7,
        "district_id": "crown_atrium",
        "desc": (
            "Sub-atrium sky suite; private mezzanine above the main promenade bustle. "
            "Ideal for a principal residence or private receiving floor."
        ),
    },
    {
        "lot_key": "Crown Atrium Sky Suite Beta",
        "tier": 3, "zone": "residential", "size_units": 7,
        "district_id": "crown_atrium",
        "desc": (
            "Paired with Sky Suite Alpha on the same atrium ring.  "
            "Combined acquisition grants the full upper arc of Crown Atrium."
        ),
    },
    # --- Sovereign Terrace (commercial flagship) ---
    {
        "lot_key": "Sovereign Terrace Flagship I",
        "tier": 3, "zone": "commercial", "size_units": 10,
        "district_id": "sovereign_terrace",
        "desc": (
            "The single largest commercial charter parcel in the NanoMegaPlex. "
            "Corner position with dual street frontage, full-width holographic "
            "signage mounts, and sovereign lease protection for the term."
        ),
    },
    {
        "lot_key": "Sovereign Terrace Flagship II",
        "tier": 3, "zone": "commercial", "size_units": 10,
        "district_id": "sovereign_terrace",
        "desc": (
            "Second flagship commercial anchor on Sovereign Terrace.  "
            "Symmetrically positioned opposite Flagship I; joint operators can "
            "brand across the full terrace frontage."
        ),
    },
    {
        "lot_key": "Sovereign Terrace Grand Arcade",
        "tier": 3, "zone": "commercial", "size_units": 9,
        "district_id": "sovereign_terrace",
        "desc": (
            "Deep-run arcade parcel spanning from Sovereign Terrace into the inner "
            "promenade.  High dwell time, covered concourse, integrated vendor rail."
        ),
    },
    {
        "lot_key": "Sovereign Terrace Exchange Court",
        "tier": 3, "zone": "commercial", "size_units": 7,
        "district_id": "sovereign_terrace",
        "desc": (
            "Mid-terrace courtyard commercial unit — open floor plan, market-stall "
            "capacity, and direct sightlines to the main promenade lifts."
        ),
    },
    {
        "lot_key": "Sovereign Terrace Concourse End",
        "tier": 3, "zone": "commercial", "size_units": 7,
        "district_id": "sovereign_terrace",
        "desc": (
            "Terminal-end commercial berth on Sovereign Terrace; highest foot-traffic "
            "exit point before the spoke corridors.  Premium impulse location."
        ),
    },
    # --- Meridian Heights (residential mid-plex) ---
    {
        "lot_key": "Meridian Heights Residence I",
        "tier": 3, "zone": "residential", "size_units": 8,
        "district_id": "meridian_heights",
        "desc": (
            "Flagship residential unit in Meridian Heights.  Wide private corridor "
            "approach, layered sound dampening, and a dedicated civic-core view panel."
        ),
    },
    {
        "lot_key": "Meridian Heights Residence II",
        "tier": 3, "zone": "residential", "size_units": 8,
        "district_id": "meridian_heights",
        "desc": (
            "Second premier residence in the Heights tier.  Identical spec to "
            "Residence I; mirrored layout on the opposing corridor arc."
        ),
    },
    {
        "lot_key": "Meridian Heights Residence III",
        "tier": 3, "zone": "residential", "size_units": 6,
        "district_id": "meridian_heights",
        "desc": (
            "Focused mid-plex residence — tighter footprint, same Meridian Heights "
            "address prestige, and access to the shared atrium mezzanine."
        ),
    },
    {
        "lot_key": "Meridian Heights Residence IV",
        "tier": 3, "zone": "residential", "size_units": 6,
        "district_id": "meridian_heights",
        "desc": (
            "Fourth numbered residence on the Heights corridor.  "
            "Lower numbering carries historical cachet for early-access holders."
        ),
    },
    # --- Apex Row (commercial premium strip) ---
    {
        "lot_key": "Apex Row Corner Anchor",
        "tier": 3, "zone": "commercial", "size_units": 9,
        "district_id": "apex_row",
        "desc": (
            "The corner anchor of Apex Row — the highest single-unit foot-traffic "
            "position in the commercial strip.  Broadcast kiosk mounts included."
        ),
    },
    {
        "lot_key": "Apex Row Shopfront I",
        "tier": 3, "zone": "commercial", "size_units": 7,
        "district_id": "apex_row",
        "desc": (
            "Prime mid-strip shopfront on Apex Row.  Full holographic frontage and "
            "automated stock-display rail along the entire facade width."
        ),
    },
    {
        "lot_key": "Apex Row Shopfront II",
        "tier": 3, "zone": "commercial", "size_units": 7,
        "district_id": "apex_row",
        "desc": (
            "Adjacent to Shopfront I; combined acquisition secures a double-width "
            "frontage mid-row — the largest continuous commercial face on Apex Row."
        ),
    },
    {
        "lot_key": "Apex Row Inner Arcade",
        "tier": 3, "zone": "commercial", "size_units": 6,
        "district_id": "apex_row",
        "desc": (
            "Recessed arcade unit behind the Apex Row primary frontage.  "
            "Sheltered high-dwell environment; popular for specialty vendors."
        ),
    },
    # --- Coreward Industrial (premium fab / manufacturing) ---
    {
        "lot_key": "Coreward Fab Station I",
        "tier": 3, "zone": "industrial", "size_units": 9,
        "district_id": "coreward_industrial",
        "desc": (
            "Premier inner-ring industrial parcel with a direct conduit to the "
            "Aurnom Ore Processing Plant.  Reinforced power routing and sovereign "
            "output quotas make this the most productive industrial site in the plex."
        ),
    },
    {
        "lot_key": "Coreward Fab Station II",
        "tier": 3, "zone": "industrial", "size_units": 9,
        "district_id": "coreward_industrial",
        "desc": (
            "Second coreward fab station, parallel conduit to Station I.  "
            "Operators running both units benefit from shared intake rail discounts."
        ),
    },
    {
        "lot_key": "Coreward Processing Bay Omega",
        "tier": 3, "zone": "industrial", "size_units": 10,
        "district_id": "coreward_industrial",
        "desc": (
            "The largest industrial charter parcel in the NanoMegaPlex. "
            "Omega Bay occupies the coreward end-cap with triple-width "
            "intake, heavy equipment mounts, and a dedicated ore-hopper spur. "
            "The single most productive industrial footprint available."
        ),
    },
]


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def _ensure_charter_lot(spec, office_room, venue_id):
    """
    Idempotent: return existing lot if key matches, else create fresh.
    Always updates mutable fields (tier, zone, size_units, district, desc).
    """
    for obj in office_room.contents:
        if obj.key == spec["lot_key"] and obj.tags.has("property_lot", category="realty"):
            _apply_spec_fields(obj, spec, venue_id)
            return obj, False

    lot = create_object(
        PropertyLot,
        key=spec["lot_key"],
        location=office_room,
        home=office_room,
    )
    _apply_spec_fields(lot, spec, venue_id)
    return lot, True


def _apply_spec_fields(lot, spec, venue_id):
    district_id = spec.get("district_id", "")
    district = DISTRICTS.get(district_id, {})

    lot.db.lot_tier = spec["tier"]
    lot.db.zone = spec["zone"]
    lot.db.size_units = spec["size_units"]
    lot.db.venue_id = venue_id
    lot.db.district_id = district_id
    lot.db.district_label = district.get("label", "")

    flavor = district.get("desc_flavor", "")
    custom = spec.get("desc", "")
    lot.db.desc = (
        f"Charter parcel in {district.get('label', 'NanoMegaPlex')} — {flavor}.\n\n"
        f"{custom}"
    ).strip()


def bootstrap_nmp_charter():
    """
    Create/update all charter lots and grant deeds to the NanoMegaPlex Real
    Estate broker.  Lots already claimed by the broker are skipped gracefully.
    """
    venue_id = "nanomega_core"
    vspec = get_venue(venue_id)
    office_key = vspec["realty"]["office_key"]

    found = search_object(office_key)
    if not found:
        print(f"[nmp-charter] Real Estate Office '{office_key}' not found; skipping.")
        return

    office = found[0]
    apply_venue_metadata(office, venue_id)

    broker = get_realty_broker_for_venue(venue_id)
    if not broker:
        print("[nmp-charter] NanoMegaPlex Real Estate broker not found; skipping.")
        return

    created = 0
    granted = 0
    skipped = 0

    for spec in NMP_CHARTER_CATALOGUE:
        lot, is_new = _ensure_charter_lot(spec, office, venue_id)

        ok, msg, _claim = grant_primary_property_deed(lot, broker)
        if is_new and ok:
            created += 1
            granted += 1
        elif ok and "already granted" in msg:
            skipped += 1
        elif ok:
            granted += 1
        else:
            print(f"[nmp-charter] Could not grant '{spec['lot_key']}': {msg}")

    print(
        f"[nmp-charter] Done — {created} lots created, "
        f"{granted} deeds granted, {skipped} already held by broker."
    )
