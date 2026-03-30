"""
Property claim deeds — three concrete kinds (residential / commercial / industrial).

Shared umbrella tag ``property_claim`` (realty) for nav and APIs; kind via
``property_kind`` category on the object.
"""

from .objects import Object

PROPERTY_CLAIM_TAG = "property_claim"
PROPERTY_CLAIM_CATEGORY = "realty"
PROPERTY_KIND_CATEGORY = "property_kind"


class PropertyClaim(Object):
    """Shared fields for all property deeds. Subclasses are spawned at sale time."""

    def at_object_creation(self):
        self.db.lot_ref  = None
        self.db.lot_key  = None
        self.db.lot_tier = 1
        self.tags.add(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY)
        self.locks.add("get:true();drop:true();give:true()")

    def at_post_move(self, source_location, move_type="move", **kwargs):
        super().at_post_move(source_location, move_type=move_type, **kwargs)
        from typeclasses.property_title_sync import sync_property_title_from_deed_location

        sync_property_title_from_deed_location(self)

    def at_pre_give(self, giver, getter, **kwargs):
        from typeclasses.characters import (
            CHARACTER_TYPECLASS_PATH,
            NANOMEGA_REALTY_CHARACTER_KEY,
        )
        from typeclasses.property_transfer_fee import (
            PROPERTY_DEED_TRANSFER_FEE_CR,
            charge_property_deed_give_fee,
        )

        if getter.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            # The NanoMegaPlex Real Estate broker issues charter grants at no fee.
            if giver.key == NANOMEGA_REALTY_CHARACTER_KEY:
                return super().at_pre_give(giver, getter, **kwargs)
            if not charge_property_deed_give_fee(giver, PROPERTY_DEED_TRANSFER_FEE_CR):
                giver.msg(
                    f"You need {PROPERTY_DEED_TRANSFER_FEE_CR:,} cr to transfer this deed to another character."
                )
                return False
        return super().at_pre_give(giver, getter, **kwargs)

    def at_give(self, giver, getter, **kwargs):
        super().at_give(giver, getter, **kwargs)
        from typeclasses.property_title_sync import sync_property_title_from_deed_location

        sync_property_title_from_deed_location(self)


class ResidentialPropertyClaim(PropertyClaim):
    """Residential parcel deed — future structures attach here."""

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("residential", category=PROPERTY_KIND_CATEGORY)


class CommercialPropertyClaim(PropertyClaim):
    """Commercial parcel deed."""

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("commercial", category=PROPERTY_KIND_CATEGORY)


class IndustrialPropertyClaim(PropertyClaim):
    """Industrial parcel deed."""

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("industrial", category=PROPERTY_KIND_CATEGORY)


CLAIM_TYPECLASS_BY_ZONE = {
    "residential": "typeclasses.property_claims.ResidentialPropertyClaim",
    "commercial":  "typeclasses.property_claims.CommercialPropertyClaim",
    "industrial":  "typeclasses.property_claims.IndustrialPropertyClaim",
}

CLAIM_TITLE_PREFIX_BY_ZONE = {
    "residential": "Residential claim",
    "commercial":  "Commercial claim",
    "industrial":  "Industrial claim",
}


def get_property_claim_kind(obj):
    """
    Return parcel kind from ``property_kind`` tags: residential | commercial | industrial.
    Used by web UI and any system that branches on deed type.
    """
    for z in ("residential", "commercial", "industrial"):
        if obj.tags.has(z, category=PROPERTY_KIND_CATEGORY):
            return z
    return "residential"
