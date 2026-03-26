"""
Credits charged to the giver when transferring a property deed to another character.
"""

from typeclasses.economy import get_economy

PROPERTY_DEED_TRANSFER_FEE_CR = 500


def charge_property_deed_give_fee(giver, amount_cr):
    """
    Withdraw ``amount_cr`` from ``giver`` via the economy ledger.
    Returns True if ``amount_cr`` is zero or the withdrawal succeeded.
    """
    amount_cr = int(amount_cr or 0)
    if amount_cr <= 0:
        return True
    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(giver)
    econ.ensure_account(acct, opening_balance=int(giver.db.credits or 0))
    balance = econ.get_character_balance(giver)
    if balance < amount_cr:
        return False
    econ.withdraw(acct, amount_cr, memo="property deed transfer fee")
    giver.db.credits = econ.get_character_balance(giver)
    return True
