"""
Refining system — Pass 3.

Components
----------
REFINING_RECIPES   dict of output_key -> recipe definition
Refinery           Object typeclass; accepts raw ore, flora, and fauna, produces refined materials

A Refinery has two inventory dicts:
    db.input_inventory   {resource_key: float tons}  — raw ore, flora, or fauna fed in
    db.output_inventory  {product_key: float units}  — refined products ready

Workers (or commands) call refinery.process_recipe(recipe_key, batches) to
convert inputs to outputs at the defined ratio.

Economy integration:
    Refined products have a base_value_cr (per unit) stored in the recipe.
    The collectproduct command in commands/refining.py sells via grant_character_credits
    (base value only in Pass 3; Pass 4 can add market modifiers).
    CmdCollectRefined and NPC auto-collect pay miners from treasury:transfer only; the
    processing fee is retained by the treasury (no separate plant vendor payout).

Transport integration:
    CmdFeedRefinery moves raw from the Ore Receiving Bay, plant silo, room storage, or
    vehicle cargo into db.input_inventory or miner queues; use |wshared|n/|wsilo|n keywords
    for explicit plant bay vs personal silo at the station refinery. Output is collected with CmdCollectProduct.
"""

from evennia.objects.objects import DefaultObject

from .objects import ObjectParent
from typeclasses.mining import RESOURCE_CATALOG


# Fee charged by the global Processing Plant when a miner collects their
# processed output.  Applied to gross refined value at collect time.
PROCESSING_FEE_RATE = 0.10  # 10 %

# Legacy vendor ledger key (no longer credited on refined collect; fee stays with treasury).
PROCESSING_PLANT_VENDOR_ACCOUNT = "vendor:processing-plant"

# 1.0 = entire processing fee retained by treasury; miner receives gross minus fee only.
PROCESSING_FEE_TREASURY_SHARE = 1.0

# When the Processing Plant buys raw from a miner (e.g. sell commands from storage), 2% hassle fee on bid gross.
RAW_SALE_FEE_RATE = 0.02  # 2 %


def is_plant_raw_resource_key(resource_key: str) -> bool:
    """True if key is mineable ore, flora, or fauna raw accepted at the global plant."""
    from typeclasses.fauna import FAUNA_RESOURCE_CATALOG
    from typeclasses.flora import FLORA_RESOURCE_CATALOG

    return (
        resource_key in RESOURCE_CATALOG
        or resource_key in FLORA_RESOURCE_CATALOG
        or resource_key in FAUNA_RESOURCE_CATALOG
    )


def plant_raw_resource_display_name(resource_key: str) -> str:
    from typeclasses.fauna import FAUNA_RESOURCE_CATALOG
    from typeclasses.flora import FLORA_RESOURCE_CATALOG

    if resource_key in RESOURCE_CATALOG:
        return RESOURCE_CATALOG[resource_key].get("name", resource_key)
    if resource_key in FLORA_RESOURCE_CATALOG:
        return FLORA_RESOURCE_CATALOG[resource_key].get("name", resource_key)
    if resource_key in FAUNA_RESOURCE_CATALOG:
        return FAUNA_RESOURCE_CATALOG[resource_key].get("name", resource_key)
    return resource_key


def iter_plant_raw_resource_keys():
    """Stable order: mining, flora, fauna — keys accepted as plant raw (ore / flora / fauna)."""
    from typeclasses.fauna import FAUNA_RESOURCE_CATALOG
    from typeclasses.flora import FLORA_RESOURCE_CATALOG

    for k in RESOURCE_CATALOG:
        yield k
    for k in FLORA_RESOURCE_CATALOG:
        yield k
    for k in FAUNA_RESOURCE_CATALOG:
        yield k


def split_raw_sale_payout(gross_cr, fee_rate=None):
    if fee_rate is None:
        fee_rate = RAW_SALE_FEE_RATE
    gross_cr = max(0, int(gross_cr))
    fee = max(0, int(round(gross_cr * float(fee_rate))))
    net = max(0, gross_cr - fee)
    return net, fee


def settle_plant_raw_purchase_from_treasury(
    owner,
    plant_room,
    delivered: dict,
    *,
    raw_pipeline: str = "mining",
    memo: str = "Plant raw intake",
) -> int:
    """
    Treasury buys ``delivered`` {resource_key: tons} at plant bid; seller gets net after RAW_SALE_FEE.
    ``raw_pipeline`` is ``mining``, ``flora``, or ``fauna`` (hauler / intake kind).
    Returns total net credits paid. Raises ValueError if treasury balance < total net.
    """
    from typeclasses.economy import get_economy
    from typeclasses.fauna import get_fauna_commodity_bid
    from typeclasses.flora import get_flora_commodity_bid
    from typeclasses.mining import get_commodity_bid
    from world.venue_resolve import treasury_bank_id_for_object

    if not owner or not plant_room:
        return 0

    econ = get_economy(create_missing=True)
    bank_id = treasury_bank_id_for_object(plant_room)
    treasury_acct = econ.get_treasury_account(bank_id)
    miner_acct = econ.get_character_account(owner)

    econ.ensure_account(treasury_acct, opening_balance=econ.get_balance(treasury_acct))
    econ.ensure_account(miner_acct, opening_balance=int(getattr(owner.db, "credits", None) or 0))

    total_net = 0
    breakdown = []

    for resource_key, tons in (delivered or {}).items():
        t = float(tons)
        if t <= 0:
            continue
        if not is_plant_raw_resource_key(str(resource_key)):
            continue
        if raw_pipeline == "fauna":
            bid = int(get_fauna_commodity_bid(str(resource_key), location=plant_room))
        elif raw_pipeline == "flora":
            bid = int(get_flora_commodity_bid(str(resource_key), location=plant_room))
        else:
            bid = int(get_commodity_bid(str(resource_key), location=plant_room))
        gross = int(round(t * bid))
        net, fee = split_raw_sale_payout(gross)
        total_net += net
        breakdown.append(
            {
                "resource": str(resource_key),
                "tons": t,
                "gross": gross,
                "net": net,
                "fee": fee,
            }
        )

    total_net = int(total_net)
    if total_net <= 0:
        return 0

    if econ.get_balance(treasury_acct) < total_net:
        raise ValueError(
            f"treasury {treasury_acct} short: need {total_net}, have {econ.get_balance(treasury_acct)}"
        )

    total_gross = sum(int(b.get("gross") or 0) for b in breakdown)
    total_fee = sum(int(b.get("fee") or 0) for b in breakdown)

    econ.transfer(treasury_acct, miner_acct, total_net, memo=memo)
    owner.db.credits = econ.get_balance(miner_acct)
    econ.db.tax_pool = econ.get_balance(treasury_acct)
    econ.record_miner_treasury_payout(total_net, gross=total_gross, fee=total_fee)
    try:
        from world.challenges.challenge_signals import emit as _c_emit
        _c_emit(owner, "miner_payout", {"amount": total_net, "pipeline": raw_pipeline})
        _c_emit(owner, "mine_deposit" if raw_pipeline == "mining" else f"{raw_pipeline}_deposit", {})
    except Exception:
        pass

    econ.record_transaction(
        tx_type="plant_raw_intake",
        amount=total_net,
        from_account=treasury_acct,
        to_account=miner_acct,
        memo=memo,
        extra={"breakdown": breakdown, "bank_id": bank_id},
    )
    return total_net


def split_processing_fee_plant_treasury(fee_cr: int, treasury_share: float | None = None) -> tuple[int, int]:
    """
    Split integer processing fee into (plant_fee, treasury_fee) with exact conservation.
    With PROCESSING_FEE_TREASURY_SHARE = 1.0, plant_fee is always 0.
    treasury_fee is the portion retained by treasury (not paid out to the miner).
    """
    fee_cr = max(0, int(fee_cr))
    if fee_cr <= 0:
        return 0, 0
    if treasury_share is None:
        ts = float(PROCESSING_FEE_TREASURY_SHARE)
    else:
        ts = float(treasury_share)
    ts = max(0.0, min(1.0, ts))
    treasury_fee = int(round(fee_cr * ts))
    treasury_fee = max(0, min(fee_cr, treasury_fee))
    plant_fee = fee_cr - treasury_fee
    return plant_fee, treasury_fee


def compute_refined_collection_amounts(gross_cr: int, fee_rate: float) -> tuple[int, int, int]:
    """
    Match Refinery.collect_miner_output fee math exactly: fee = int(gross * fee_rate), net = gross - fee.
    Returns (gross, fee, net).
    """
    gross_cr = max(0, int(gross_cr))
    fee = int(gross_cr * float(fee_rate))
    net = gross_cr - fee
    return gross_cr, fee, net


def refined_payout_breakdown(gross_cr: int, fee_rate: float, fee_treasury_share: float | None = None) -> dict:
    """
    Full settlement breakdown for treasury-funded refined collection.
    Miner receives net; processing fee is retained by treasury (plant_fee 0).
    required_from_treasury must be available on treasury before collect_miner_output.
    """
    gross, fee, net = compute_refined_collection_amounts(gross_cr, fee_rate)
    plant_fee, treasury_fee = split_processing_fee_plant_treasury(fee, treasury_share=fee_treasury_share)
    required = net + plant_fee
    return {
        "gross": gross,
        "fee": fee,
        "net": net,
        "plant_fee": plant_fee,
        "treasury_fee": treasury_fee,
        "required_from_treasury": required,
    }


def restore_miner_output_for_payout(refinery, owner_id_str: str, products: dict) -> None:
    """Merge products back into refinery.db.miner_output after a failed treasury payout."""
    out = dict(refinery.db.miner_output or {})
    oid = str(owner_id_str)
    cur = dict(out.get(oid, {}))
    for k, v in (products or {}).items():
        cur[k] = round(float(cur.get(k, 0.0)) + float(v), 2)
    out[oid] = cur
    refinery.db.miner_output = out


def execute_refined_payout_from_treasury(
    econ,
    *,
    treasury_account: str,
    plant_vendor_account: str,
    miner_account: str,
    net: int,
    plant_fee: int,
    gross: int,
    fee: int,
    treasury_fee: int,
    memo_miner: str,
    memo_plant: str,
    owner=None,
) -> None:
    """
    Transfer only — no minting. Treasury must already have been checked >= net + plant_fee.
    With default fee split, plant_fee is 0 (only the miner is paid from treasury).
    treasury_fee is informational only (not moved).
    """
    _ = gross, fee, treasury_fee
    net = max(0, int(net))
    plant_fee = max(0, int(plant_fee))
    if net > 0:
        econ.transfer(
            treasury_account,
            miner_account,
            net,
            memo=memo_miner,
        )
    if plant_fee > 0:
        econ.transfer(
            treasury_account,
            plant_vendor_account,
            plant_fee,
            memo=memo_plant,
        )
    econ.db.tax_pool = econ.get_balance(treasury_account)
    if net > 0:
        econ.record_miner_treasury_payout(net, gross=gross, fee=fee)
        if owner is not None:
            try:
                from world.challenges.challenge_signals import emit as _c_emit
                _c_emit(owner, "miner_payout", {"amount": net, "pipeline": "mining"})
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Refining recipes
# ---------------------------------------------------------------------------

REFINING_RECIPES = {
    # Metals
    "refined_iron": {
        "name": "Refined Iron",
        "desc": "Smelted iron ingots ready for fabrication.",
        "inputs": {"iron_ore": 4.0},         # 4 t ore → 1 unit refined
        "output_units": 1,
        "base_value_cr": 520,
        "category": "refined_metal",
    },
    "refined_copper": {
        "name": "Refined Copper",
        "desc": "Pure copper cathodes for electrical components.",
        "inputs": {"copper_ore": 4.5},
        "output_units": 1,
        "base_value_cr": 900,
        "category": "refined_metal",
    },
    "refined_nickel": {
        "name": "Refined Nickel",
        "desc": "High-purity nickel pellets for alloy production.",
        "inputs": {"nickel_ore": 5.0},
        "output_units": 1,
        "base_value_cr": 1400,
        "category": "refined_metal",
    },
    "refined_titanium": {
        "name": "Refined Titanium",
        "desc": "Titanium sponge and billets for aerospace use.",
        "inputs": {"titanium_ore": 6.0},
        "output_units": 1,
        "base_value_cr": 3800,
        "category": "refined_metal",
    },
    "refined_cobalt": {
        "name": "Refined Cobalt",
        "desc": "Cobalt powder and plates for battery technology.",
        "inputs": {"cobalt_ore": 5.5},
        "output_units": 1,
        "base_value_cr": 4200,
        "category": "refined_metal",
    },
    "rare_earth_oxide": {
        "name": "Rare-Earth Oxide Mix",
        "desc": "Separated rare-earth oxides for high-tech manufacturing.",
        "inputs": {"rare_earth_concentrate": 3.0},
        "output_units": 1,
        "base_value_cr": 3800,
        "category": "refined_metal",
    },
    "platinum_bar": {
        "name": "Platinum Bar",
        "desc": "Precious platinum-group metal bar, assay-certified.",
        "inputs": {"platinum_group_ore": 8.0},
        "output_units": 1,
        "base_value_cr": 32000,
        "category": "precious_metal",
    },
    # Gem products
    "cut_opal": {
        "name": "Cut Opal",
        "desc": "Polished play-of-color opal, gem quality.",
        "inputs": {"opal_seam": 2.0},
        "output_units": 1,
        "base_value_cr": 4500,
        "category": "cut_gem",
    },
    "cut_corundum": {
        "name": "Cut Corundum",
        "desc": "Faceted sapphire/ruby corundum, jeweller's grade.",
        "inputs": {"corundum_matrix": 2.5},
        "output_units": 1,
        "base_value_cr": 6800,
        "category": "cut_gem",
    },
    "cut_emerald": {
        "name": "Cut Emerald",
        "desc": "Precision-cut emerald beryl, collector's quality.",
        "inputs": {"emerald_beryl_ore": 3.0},
        "output_units": 1,
        "base_value_cr": 9200,
        "category": "cut_gem",
    },
    "cut_diamond": {
        "name": "Cut Diamond",
        "desc": "Brilliant-cut natural diamond, certified.",
        "inputs": {"diamond_kimberlite": 4.0},
        "output_units": 1,
        "base_value_cr": 18000,
        "category": "cut_gem",
    },
    # Alloys
    "steel_alloy": {
        "name": "Steel Alloy",
        "desc": "Carbon steel alloy billet for structural applications.",
        "inputs": {"iron_ore": 3.0, "lead_zinc_ore": 1.0},
        "output_units": 1,
        "base_value_cr": 680,
        "category": "alloy",
    },
    "titanium_alloy": {
        "name": "Titanium-Aluminum Alloy",
        "desc": "Lightweight structural alloy for aerospace frames.",
        "inputs": {"titanium_ore": 3.0, "aluminum_ore": 2.0},
        "output_units": 1,
        "base_value_cr": 4800,
        "category": "alloy",
    },
    # Flora (5 t raw → 1 unit; base_value ≈ 1.1 × FLORA_RESOURCE_CATALOG base_price_cr_per_ton × 5)
    "refined_wild_harvest_biomass": {
        "name": "Refined Wild Harvest Biomass",
        "desc": "Stabilized botanical feedstock.",
        "inputs": {"wild_harvest_biomass": 5.0},
        "output_units": 1,
        "base_value_cr": 275,
        "category": "refined_flora",
    },
    "refined_structural_cane": {
        "name": "Refined Structural Cane",
        "desc": "Processed fibre stock for composites.",
        "inputs": {"structural_cane": 5.0},
        "output_units": 1,
        "base_value_cr": 358,
        "category": "refined_flora",
    },
    "refined_cellulose_pulp_bale": {
        "name": "Refined Cellulose Pulp",
        "desc": "Mill-ready pulp fraction.",
        "inputs": {"cellulose_pulp_bale": 5.0},
        "output_units": 1,
        "base_value_cr": 385,
        "category": "refined_flora",
    },
    "refined_algal_mat": {
        "name": "Refined Algal Mat",
        "desc": "Concentrated algae mass for chemistry lines.",
        "inputs": {"algal_mat": 5.0},
        "output_units": 1,
        "base_value_cr": 468,
        "category": "refined_flora",
    },
    "refined_lichen_aggregate": {
        "name": "Refined Lichen Aggregate",
        "desc": "Standardized lichen sheets for slow-release use.",
        "inputs": {"lichen_aggregate": 5.0},
        "output_units": 1,
        "base_value_cr": 523,
        "category": "refined_flora",
    },
    "refined_medicinal_sap": {
        "name": "Refined Medicinal Sap",
        "desc": "Pharma-grade sap precursor.",
        "inputs": {"medicinal_sap": 5.0},
        "output_units": 1,
        "base_value_cr": 2310,
        "category": "refined_flora",
    },
    "refined_volatile_terpene_resin": {
        "name": "Refined Terpene Resin",
        "desc": "Fractionated resin for solvents and scents.",
        "inputs": {"volatile_terpene_resin": 5.0},
        "output_units": 1,
        "base_value_cr": 3190,
        "category": "refined_flora",
    },
    "refined_spore_culture_mass": {
        "name": "Refined Spore Culture",
        "desc": "Enzyme-ready spore biomass.",
        "inputs": {"spore_culture_mass": 5.0},
        "output_units": 1,
        "base_value_cr": 3520,
        "category": "refined_flora",
    },
    "refined_xenohybrid_foliage": {
        "name": "Refined Xenohybrid Foliage",
        "desc": "Purified lab-cross metabolite feed.",
        "inputs": {"xenohybrid_foliage": 5.0},
        "output_units": 1,
        "base_value_cr": 3960,
        "category": "refined_flora",
    },
    "refined_crystalline_nectar_concentrate": {
        "name": "Refined Nectar Concentrate",
        "desc": "Crystalline floral nectar product.",
        "inputs": {"crystalline_nectar_concentrate": 5.0},
        "output_units": 1,
        "base_value_cr": 11550,
        "category": "refined_flora",
    },
    "refined_deep_root_tuber": {
        "name": "Refined Deep Root Tuber",
        "desc": "Starch fraction ready for industrial use.",
        "inputs": {"deep_root_tuber": 5.0},
        "output_units": 1,
        "base_value_cr": 605,
        "category": "refined_flora",
    },
    "refined_pollen_aggregate": {
        "name": "Refined Pollen Aggregate",
        "desc": "Protein-filtered pollen stock.",
        "inputs": {"pollen_aggregate": 5.0},
        "output_units": 1,
        "base_value_cr": 2805,
        "category": "refined_flora",
    },
    "refined_vascular_sheath_fibre": {
        "name": "Refined Vascular Sheath Fibre",
        "desc": "Textile-grade vascular bundles.",
        "inputs": {"vascular_sheath_fibre": 5.0},
        "output_units": 1,
        "base_value_cr": 660,
        "category": "refined_flora",
    },
    "refined_bioluminescent_moss": {
        "name": "Refined Bioluminescent Moss",
        "desc": "Stabilized luciferase pathway culture.",
        "inputs": {"bioluminescent_moss": 5.0},
        "output_units": 1,
        "base_value_cr": 15400,
        "category": "refined_flora",
    },
    "refined_heritage_seed_pod_lot": {
        "name": "Refined Heritage Seed Pod Lot",
        "desc": "Vault-grade certified genotype pods.",
        "inputs": {"heritage_seed_pod_lot": 5.0},
        "output_units": 1,
        "base_value_cr": 18700,
        "category": "refined_flora",
    },
    # Fauna (5 t raw → 1 unit; base_value ≈ 1.1 × FAUNA_RESOURCE_CATALOG base_price_cr_per_ton × 5)
    "refined_pelagic_protein_slurry": {
        "name": "Refined Pelagic Protein Slurry",
        "desc": "Stabilised protein feedstock from fauna harvest.",
        "inputs": {"pelagic_protein_slurry": 5.0},
        "output_units": 1,
        "base_value_cr": 286,
        "category": "refined_fauna",
    },
    "refined_chitin_microflake_lot": {
        "name": "Refined Chitin Microflake Lot",
        "desc": "Processed chitin for coatings and binders.",
        "inputs": {"chitin_microflake_lot": 5.0},
        "output_units": 1,
        "base_value_cr": 374,
        "category": "refined_fauna",
    },
    "refined_collagen_fibril_mass": {
        "name": "Refined Collagen Fibril Mass",
        "desc": "Purified collagen for gel and tissue lines.",
        "inputs": {"collagen_fibril_mass": 5.0},
        "output_units": 1,
        "base_value_cr": 407,
        "category": "refined_fauna",
    },
    "refined_keratin_fiber_bale": {
        "name": "Refined Keratin Fiber Bale",
        "desc": "Textile-grade keratin fibre stock.",
        "inputs": {"keratin_fiber_bale": 5.0},
        "output_units": 1,
        "base_value_cr": 391,
        "category": "refined_fauna",
    },
    "refined_hemolymph_serum_batch": {
        "name": "Refined Hemolymph Serum Batch",
        "desc": "Concentrated hemolymph fraction for biochemistry.",
        "inputs": {"hemolymph_serum_batch": 5.0},
        "output_units": 1,
        "base_value_cr": 484,
        "category": "refined_fauna",
    },
    "refined_exotic_enzyme_gland_paste": {
        "name": "Refined Exotic Enzyme Paste",
        "desc": "Catalysis-grade enzyme preparation.",
        "inputs": {"exotic_enzyme_gland_paste": 5.0},
        "output_units": 1,
        "base_value_cr": 2420,
        "category": "refined_fauna",
    },
    "refined_neural_lipid_extract": {
        "name": "Refined Neural Lipid Extract",
        "desc": "Pharma-grade neural lipid precursor.",
        "inputs": {"neural_lipid_extract": 5.0},
        "output_units": 1,
        "base_value_cr": 3080,
        "category": "refined_fauna",
    },
    "refined_symbiotic_microfauna_culture": {
        "name": "Refined Symbiotic Microfauna Culture",
        "desc": "Standardised culture for probiotics and remediation.",
        "inputs": {"symbiotic_microfauna_culture": 5.0},
        "output_units": 1,
        "base_value_cr": 3410,
        "category": "refined_fauna",
    },
    "refined_xenofauna_myo_bundle": {
        "name": "Refined Xenofauna Myo Bundle",
        "desc": "Purified exotic muscle protein feed.",
        "inputs": {"xenofauna_myo_bundle": 5.0},
        "output_units": 1,
        "base_value_cr": 3850,
        "category": "refined_fauna",
    },
    "refined_crystalline_venom_precipitate": {
        "name": "Refined Crystalline Venom Precipitate",
        "desc": "Research-grade venom solids.",
        "inputs": {"crystalline_venom_precipitate": 5.0},
        "output_units": 1,
        "base_value_cr": 11275,
        "category": "refined_fauna",
    },
    "refined_deep_benthic_silicate_gel": {
        "name": "Refined Deep Benthic Silicate Gel",
        "desc": "Industrial silicate matrix from abyssal fauna.",
        "inputs": {"deep_benthic_silicate_gel": 5.0},
        "output_units": 1,
        "base_value_cr": 578,
        "category": "refined_fauna",
    },
    "refined_arthropod_powder_aggregate": {
        "name": "Refined Arthropod Powder Aggregate",
        "desc": "Protein-filtered arthropod stock.",
        "inputs": {"arthropod_powder_aggregate": 5.0},
        "output_units": 1,
        "base_value_cr": 2723,
        "category": "refined_fauna",
    },
    "refined_elastic_tendon_sheath_lot": {
        "name": "Refined Elastic Tendon Sheath Lot",
        "desc": "Cable-grade elastic sheath bundles.",
        "inputs": {"elastic_tendon_sheath_lot": 5.0},
        "output_units": 1,
        "base_value_cr": 649,
        "category": "refined_fauna",
    },
    "refined_bioluminescent_scale_flake": {
        "name": "Refined Bioluminescent Scale Flake",
        "desc": "Stabilised photoprotein scale culture.",
        "inputs": {"bioluminescent_scale_flake": 5.0},
        "output_units": 1,
        "base_value_cr": 15125,
        "category": "refined_fauna",
    },
    "refined_heritage_genotype_embryo_lot": {
        "name": "Refined Heritage Genotype Embryo Lot",
        "desc": "Vault-grade certified fauna embryos.",
        "inputs": {"heritage_genotype_embryo_lot": 5.0},
        "output_units": 1,
        "base_value_cr": 18150,
        "category": "refined_fauna",
    },
    "synth_lubricant_base": {
        "name": "Synth Lubricant Base",
        "desc": "Classified blend stock; vault recipe charter and clearance required.",
        "inputs": {"iron_ore": 2.0},
        "output_units": 1,
        "base_value_cr": 400,
        "category": "synthetic",
        "requiresRecipeUnlock": True,
        "requiresLicenseKey": "arc_clearance",
        "requiresLicenseMin": 1,
    },
}


def refining_recipe_requires_player_gate(recipe: dict | None) -> bool:
    if not recipe:
        return False
    if recipe.get("requiresRecipeUnlock"):
        return True
    if str(recipe.get("requiresLicenseKey") or "").strip():
        return True
    return False


def refining_recipe_allowed_for_character(character, recipe_key: str) -> tuple[bool, str]:
    recipe = REFINING_RECIPES.get(recipe_key)
    if not recipe:
        return False, f"Unknown recipe '{recipe_key}'."
    ch = getattr(character, "challenges", None)
    if ch is None:
        if refining_recipe_requires_player_gate(recipe):
            return False, "Challenge state unavailable."
        return True, ""
    if recipe.get("requiresRecipeUnlock"):
        if not ch.has_refining_recipe_unlock(recipe_key):
            return (
                False,
                f"You have not unlocked recipe '{recipe_key}' (challenge point store).",
            )
    lk = str(recipe.get("requiresLicenseKey") or "").strip()
    if lk:
        need = int(recipe.get("requiresLicenseMin") or 1)
        if ch.license_tier(lk) < need:
            return False, "Insufficient industrial clearance for this recipe."
    return True, ""


# ---------------------------------------------------------------------------
# Refinery typeclass
# ---------------------------------------------------------------------------

class Refinery(ObjectParent, DefaultObject):
    """
    An ore processing facility.

    db.input_inventory   {resource_key: float tons}  raw ore in
    db.output_inventory  {product_key: float units}  refined goods out
    db.owner             character ref (or None for public/station facility)
    db.auto_ingest_assigned_silo  bool  legacy unused.

    Assigned plant silo ore is not auto-ingested. Owners use feedrefinery (or
    transfer_owner_plant_silo_to_miner_queue / world.plant_queue_ops) to move
    material into miner_ore_queue for attributed processing.

    Shared input_inventory is fed from receiving bay / other storage or vehicle;
    process_recipe uses the shared bin. Per-owner miner_output is collected with
    collectrefined (or NPC auto-collect for registry ids).
    """

    def at_object_creation(self):
        self.db.is_refinery = True
        self.db.owner = None
        self.db.input_inventory = {}
        self.db.output_inventory = {}
        # Per-miner queues for "process" delivery mode at the global plant.
        # keyed by str(character.id).
        self.db.miner_ore_queue = {}   # {owner_id: {resource_key: tons}}
        self.db.miner_output = {}      # {owner_id: {product_key: units}}
        self.db.auto_ingest_assigned_silo = False
        self.tags.add("refinery", category="mining")
        self.locks.add("get:false()")

    # ------------------------------------------------------------------

    def feed(self, resource_key, tons):
        """Add raw ore or flora to input inventory. Returns actual tons added."""
        if not is_plant_raw_resource_key(resource_key):
            return 0.0
        tons = round(float(tons), 2)
        if tons <= 0:
            return 0.0
        inv = self.db.input_inventory or {}
        inv[resource_key] = round(float(inv.get(resource_key, 0.0)) + tons, 2)
        self.db.input_inventory = inv
        return tons

    def enqueue_miner_ore(self, owner_id, resource_key, tons):
        """Add raw ore or flora to this refinery's attributed miner queue. Returns tons added."""
        if not is_plant_raw_resource_key(resource_key):
            return 0.0
        tons = round(float(tons), 2)
        if tons <= 0:
            return 0.0
        oid = str(owner_id)
        queues = dict(self.db.miner_ore_queue or {})
        acc = dict(queues.get(oid, {}))
        acc[resource_key] = round(float(acc.get(resource_key, 0)) + tons, 2)
        queues[oid] = acc
        self.db.miner_ore_queue = queues
        return tons

    def transfer_owner_plant_silo_to_miner_queue(self, owner, plant_room=None):
        """
        Merge this owner's tagged plant silo into miner_ore_queue, then remove only the
        queued keys from the silo. ``plant_room`` is where the tagged silo lives (ore bay
        floor); defaults to ``self.location`` when the refinery sits in the plant room.
        """
        from typeclasses.haulers import get_plant_player_storage

        room = plant_room or self.location
        if not room or not owner:
            return {}
        silo = get_plant_player_storage(room, owner)
        if not silo:
            return {}
        inv = dict(silo.db.inventory or {})
        if not inv:
            return {}

        oid = str(owner.id)
        queues = dict(self.db.miner_ore_queue or {})
        acc = dict(queues.get(oid, {}))
        moved = {}
        for res_key, tons in inv.items():
            tons = float(tons)
            if tons <= 0:
                continue
            if not is_plant_raw_resource_key(res_key):
                continue
            acc[res_key] = round(float(acc.get(res_key, 0)) + tons, 2)
            moved[res_key] = tons
        if not moved:
            return {}

        queues[oid] = acc
        self.db.miner_ore_queue = queues
        remaining = dict(inv)
        for k in moved:
            remaining.pop(k, None)
        silo.db.inventory = remaining
        return moved

    def process_recipe(self, recipe_key, batches=1, *, operator=None):
        """
        Process `batches` runs of recipe_key.

        Returns (batches_processed, message).
        Partial processing: runs as many full batches as inputs allow.

        ``operator`` — puppeting character for gated recipes; None skips gates (engine tick).
        """
        from typeclasses.commodity_demand import get_commodity_demand_engine

        demand_eng = get_commodity_demand_engine(create_missing=False)
        recipe = REFINING_RECIPES.get(recipe_key)
        if not recipe:
            return 0, f"Unknown recipe '{recipe_key}'."

        if operator is not None:
            ok, err = refining_recipe_allowed_for_character(operator, recipe_key)
            if not ok:
                return 0, err
        elif refining_recipe_requires_player_gate(recipe):
            return 0, ""

        batches = max(1, int(batches))
        inv = self.db.input_inventory or {}

        # How many full batches can we run?
        possible = batches
        for res_key, required_per_batch in recipe["inputs"].items():
            available = float(inv.get(res_key, 0.0))
            max_from_this = int(available / float(required_per_batch))
            possible = min(possible, max_from_this)

        if possible <= 0:
            needed = {
                plant_raw_resource_display_name(k): v * batches
                for k, v in recipe["inputs"].items()
            }
            return 0, (
                f"Insufficient inputs for {recipe['name']}. "
                f"Need: {', '.join(f'{v}t {k}' for k, v in needed.items())}."
            )

        # Consume inputs
        for res_key, required_per_batch in recipe["inputs"].items():
            consumed = round(float(required_per_batch) * possible, 2)
            remaining = round(float(inv.get(res_key, 0.0)) - consumed, 2)
            if remaining <= 0:
                inv.pop(res_key, None)
            else:
                inv[res_key] = remaining
        self.db.input_inventory = inv

        # Produce outputs
        out_inv = self.db.output_inventory or {}
        units_produced = recipe.get("output_units", 1) * possible
        out_inv[recipe_key] = round(float(out_inv.get(recipe_key, 0.0)) + units_produced, 2)
        self.db.output_inventory = out_inv

        if demand_eng:
            demand_eng.record_supply(recipe_key, float(units_produced))

        return possible, (
            f"Processed {possible} batch(es) of {recipe['name']}. "
            f"Produced {units_produced} unit(s)."
        )

    def collect_product(self, product_key, units=None):
        """
        Remove product(s) from output inventory.
        Returns (units_collected, base_value_cr).
        """
        out_inv = self.db.output_inventory or {}
        available = float(out_inv.get(product_key, 0.0))
        if available <= 0:
            return 0.0, 0

        if units is None:
            collected = available
        else:
            collected = round(min(float(units), available), 2)

        remaining = round(available - collected, 2)
        if remaining <= 0:
            out_inv.pop(product_key, None)
        else:
            out_inv[product_key] = remaining
        self.db.output_inventory = out_inv

        recipe = REFINING_RECIPES.get(product_key, {})
        value = int(collected * recipe.get("base_value_cr", 0))
        return collected, value

    def get_miner_output(self, owner_id):
        """Return {product_key: units} for the given owner (str id). Empty dict if none."""
        return dict((self.db.miner_output or {}).get(str(owner_id), {}))

    def get_miner_ore_queued_tons(self, owner_id):
        """Return total tons of ore queued for this miner."""
        q = (self.db.miner_ore_queue or {}).get(str(owner_id), {})
        return round(sum(float(v) for v in q.values()), 2)

    def get_miner_output_value(self, owner_id):
        """Return total credit value of miner's output at base recipe prices."""
        total = 0
        for key, units in self.get_miner_output(owner_id).items():
            recipe = REFINING_RECIPES.get(key, {})
            total += int(units * recipe.get("base_value_cr", 0))
        return total

    def get_total_miner_ore_queued_tons(self):
        """Total tons in all per-owner miner_ore_queue entries (attributed plant input)."""
        total = 0.0
        for ore_inv in (self.db.miner_ore_queue or {}).values():
            if isinstance(ore_inv, dict):
                total += sum(float(v) for v in ore_inv.values())
        return round(total, 2)

    def get_total_miner_output_value(self):
        """Gross credit value of all attributed miner_output at base recipe prices."""
        total = 0
        for owner_id in (self.db.miner_output or {}):
            total += self.get_miner_output_value(owner_id)
        return total

    def collect_miner_output(self, owner_id, fee_rate=0.0):
        """
        Remove and return all output for a miner.
        Returns (products_dict, gross_value_cr, fee_cr).
        """
        owner_id = str(owner_id)
        output = dict(self.db.miner_output or {})
        miner_out = dict(output.pop(owner_id, {}))
        if not miner_out:
            return {}, 0, 0
        self.db.miner_output = output
        gross = 0
        for key, units in miner_out.items():
            recipe = REFINING_RECIPES.get(key, {})
            gross += int(units * recipe.get("base_value_cr", 0))
        fee = int(gross * fee_rate)
        return miner_out, gross, fee

    def get_status_report(self):
        owner_str = self.db.owner.key if self.db.owner else "public facility"
        lines = [f"|wRefinery: {self.key}|n", f"  Owner: {owner_str}"]

        # Input inventory
        inv_in = self.db.input_inventory or {}
        if inv_in:
            lines.append("  Raw inputs:")
            for key in sorted(inv_in):
                tons = float(inv_in[key])
                name = plant_raw_resource_display_name(key)
                lines.append(f"    {name:<28} {tons:>8.2f} t")
        else:
            lines.append("  Raw inputs  : empty")

        # Output inventory
        inv_out = self.db.output_inventory or {}
        if inv_out:
            lines.append("  Refined outputs:")
            total_value = 0
            for key in sorted(inv_out):
                units = float(inv_out[key])
                recipe = REFINING_RECIPES.get(key, {})
                name = recipe.get("name", key)
                value = int(units * recipe.get("base_value_cr", 0))
                total_value += value
                lines.append(f"    {name:<28} {units:>8.2f} units   |y{value:>10,}|n cr")
            lines.append(f"    {'Total output value':<28} {'':>8}        |y{total_value:>10,}|n cr")
        else:
            lines.append("  Refined outputs: empty")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# RefineryEngine — global automation script
# ---------------------------------------------------------------------------

REFINERY_ENGINE_INTERVAL = 1800   # 30 min tick

# Max NPC auto-settlements per refinery per engine tick (bounded script time).
NPC_MINER_AUTO_COLLECT_MAX_PER_TICK = 2000


def _process_miner_queues(refinery):
    """
    Process per-miner ore/flora queues and write output to miner_output.
    Called each RefineryEngine tick for the global plant.
    """
    from typeclasses.commodity_demand import get_commodity_demand_engine

    demand_eng = get_commodity_demand_engine(create_missing=False)
    queues = dict(refinery.db.miner_ore_queue or {})
    output = dict(refinery.db.miner_output or {})
    changed = False

    for owner_id in list(queues.keys()):
        ore_inv = dict(queues[owner_id])
        if not ore_inv:
            del queues[owner_id]
            changed = True
            continue
        miner_out = dict(output.get(owner_id, {}))

        for recipe_key, recipe in REFINING_RECIPES.items():
            while True:
                possible = None
                for res_key, req in recipe["inputs"].items():
                    avail = float(ore_inv.get(res_key, 0.0))
                    n = int(avail / float(req))
                    possible = n if possible is None else min(possible, n)
                if not possible:
                    break
                for res_key, req in recipe["inputs"].items():
                    consumed = round(float(req) * possible, 2)
                    remaining = round(float(ore_inv.get(res_key, 0.0)) - consumed, 2)
                    if remaining <= 0:
                        ore_inv.pop(res_key, None)
                    else:
                        ore_inv[res_key] = remaining
                units = recipe.get("output_units", 1) * possible
                miner_out[recipe_key] = round(
                    float(miner_out.get(recipe_key, 0.0)) + units, 2
                )
                changed = True
                if demand_eng:
                    demand_eng.record_supply(recipe_key, float(units))

        if ore_inv:
            queues[owner_id] = ore_inv
        else:
            queues.pop(owner_id, None)
        if miner_out:
            output[owner_id] = miner_out

    if changed:
        refinery.db.miner_ore_queue = queues
        refinery.db.miner_output = output


def _auto_collect_registered_npc_miner_outputs(refinery):
    """
    Ledger-only settlement for registry NPCs: treasury pays net to player:{id};
    processing fee retained by treasury. Same rules as collectrefined.
    """
    from evennia.utils import logger

    from typeclasses.economy import get_economy
    from world.npc_miner_registry import is_registered_npc_miner_owner_id

    output = refinery.db.miner_output or {}
    if not output:
        return

    candidates = []
    for owner_id_str in output.keys():
        if not is_registered_npc_miner_owner_id(str(owner_id_str)):
            continue
        try:
            int(owner_id_str)
        except (TypeError, ValueError):
            continue
        candidates.append(str(owner_id_str))

    if not candidates:
        return

    candidates.sort()
    if len(candidates) > NPC_MINER_AUTO_COLLECT_MAX_PER_TICK:
        candidates = candidates[:NPC_MINER_AUTO_COLLECT_MAX_PER_TICK]

    econ = get_economy(create_missing=True)
    treasury_acct = econ.get_treasury_account("alpha-prime")
    plant_acct = PROCESSING_PLANT_VENDOR_ACCOUNT
    econ.ensure_account(treasury_acct, opening_balance=int(econ.db.tax_pool or 0))

    for owner_id_str in candidates:
        gross_pre = refinery.get_miner_output_value(int(owner_id_str))
        if gross_pre <= 0:
            continue

        bd_pre = refined_payout_breakdown(gross_pre, PROCESSING_FEE_RATE)
        if econ.get_balance(treasury_acct) < bd_pre["required_from_treasury"]:
            logger.log_warn(
                f"[RefineryEngine] NPC auto-collect skipped owner {owner_id_str}: "
                f"treasury short (need {bd_pre['required_from_treasury']}, "
                f"have {econ.get_balance(treasury_acct)})"
            )
            continue

        products, gross, fee = refinery.collect_miner_output(
            int(owner_id_str), fee_rate=PROCESSING_FEE_RATE
        )
        if not products:
            continue

        bd = refined_payout_breakdown(gross, PROCESSING_FEE_RATE)
        if econ.get_balance(treasury_acct) < bd["required_from_treasury"]:
            restore_miner_output_for_payout(refinery, owner_id_str, products)
            logger.log_warn(
                f"[RefineryEngine] NPC auto-collect restored owner {owner_id_str}: "
                f"treasury short after collect (need {bd['required_from_treasury']}, "
                f"have {econ.get_balance(treasury_acct)})"
            )
            continue

        owner_acct = f"player:{owner_id_str}"
        econ.ensure_account(owner_acct, opening_balance=0)

        try:
            execute_refined_payout_from_treasury(
                econ,
                treasury_account=treasury_acct,
                plant_vendor_account=plant_acct,
                miner_account=owner_acct,
                net=bd["net"],
                plant_fee=bd["plant_fee"],
                gross=gross,
                fee=fee,
                treasury_fee=bd["treasury_fee"],
                memo_miner=f"Refined output auto-collection at {refinery.key}",
                memo_plant=f"Plant fee share (NPC auto) owner {owner_id_str} at {refinery.key}",
            )
        except Exception:
            restore_miner_output_for_payout(refinery, owner_id_str, products)
            raise

        logger.log_info(
            f"[RefineryEngine] NPC auto-collect owner {owner_id_str} at {refinery.key}: "
            f"net {bd['net']} cr from treasury (gross {gross}, processing fee {fee} retained)"
        )


def _process_refinery(refinery):
    """Run pooled recipes and miner queues. Ore Receiving Bay is not auto-drained."""
    room = refinery.location
    if not room:
        return

    # Pooled input_inventory is filled only by feedrefinery / explicit code — not RefineryEngine.

    # Run all shared recipes until no more batches are possible (pooled input only)
    for recipe_key in REFINING_RECIPES:
        while True:
            batches, _ = refinery.process_recipe(recipe_key, batches=1)
            if batches == 0:
                break

    # Per-owner queues (filled via feedrefinery / transfer_owner_plant_silo_to_miner_queue)
    _process_miner_queues(refinery)

    _auto_collect_registered_npc_miner_outputs(refinery)


from .scripts import Script as _Script  # noqa: E402 — must follow Refinery definition


class RefineryEngine(_Script):
    """
    Global persistent script that processes ore and flora already in refineries.

    Every tick (30 min):
      1. Finds all Refinery objects.
      2. Runs REFINING_RECIPES on pooled input_inventory (bay is not auto-fed).
      3. Processes miner queues to miner_output.
      4. Auto-collects miner_output for ids in NpcMinerRegistryScript via treasury transfers
         (net + plant fee share from alpha-prime treasury; capped per tick).

    Ore Receiving Bay and assigned plant silos are only fed via commands / explicit code paths.
    """

    def at_script_creation(self):
        self.key = "refinery_engine"
        self.desc = "Automatically feeds and processes ore at all refineries."
        self.interval = REFINERY_ENGINE_INTERVAL
        self.persistent = True
        self.start_delay = True

    def at_repeat(self):
        from evennia import search_tag
        from evennia.utils import logger

        refineries = search_tag("refinery", category="mining")
        for refinery in refineries:
            if not refinery.is_typeclass(Refinery, exact=False):
                continue
            try:
                _process_refinery(refinery)
            except Exception as exc:
                logger.log_err(f"[RefineryEngine] Error on {refinery}: {exc}")
