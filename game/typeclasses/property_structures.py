"""
Installed structure/module objects on a PropertyHolding.
"""

from .objects import Object

STRUCTURE_TAG = "property_structure"
STRUCTURE_CATEGORY = "realty"
STRUCTURE_KIND_CATEGORY = "structure_kind"


class PropertyStructure(Object):
    """
    Installed module on a PropertyHolding. blueprint_id drives behavior + upgrades.
    """

    def at_object_creation(self):
        self.tags.add(STRUCTURE_TAG, category=STRUCTURE_CATEGORY)
        self.db.blueprint_id = None
        self.db.slot_weight = 1
        self.db.upgrades = {}
        self.db.condition = 100
        self.locks.add("get:false();drop:false()")

    def apply_blueprint(self, blueprint_id):
        self.db.blueprint_id = blueprint_id
        self.tags.add(blueprint_id, category=STRUCTURE_KIND_CATEGORY)
