"""Resource commodity board for web (bid/ask)."""


def serialize_resource_market():
    from typeclasses.mining import RESOURCE_CATALOG, get_commodity_ask, get_commodity_bid

    commodities = []
    for rk, info in RESOURCE_CATALOG.items():
        commodities.append({
            "key": rk,
            "name": info["name"],
            "category": info["category"],
            "basePriceCrPerTon": info["base_price_cr_per_ton"],
            "sellPriceCrPerTon": get_commodity_bid(rk),
            "buyPriceCrPerTon": get_commodity_ask(rk),
            "desc": info["desc"],
        })
    return commodities
