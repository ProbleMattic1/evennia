from evennia.objects.objects import DefaultObject

from .economy import get_economy
from .objects import ObjectParent


class CentralBank(ObjectParent, DefaultObject):
    """
    In-world representation of the central reserve.
    The actual money lives in EconomyEngine.
    """

    def at_object_creation(self):
        self.db.bank_id = "alpha-prime"
        self.db.treasury_account = "treasury:alpha-prime"
        self.db.desc = (
            "Alpha Prime is the sovereign financial authority for the sector. "
            "Its reserve systems track taxation, treasury balances, and state capital flows."
        )

    def get_treasury_balance(self):
        econ = get_economy(create_missing=True)
        return econ.get_balance(self.db.treasury_account)
