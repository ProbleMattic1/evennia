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
