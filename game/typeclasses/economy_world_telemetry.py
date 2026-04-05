"""
Periodic aggregates for the world economy web UI. O(n) tag scan here only, not per HTTP GET.
"""

from evennia import search_tag

from typeclasses.scripts import Script


class EconomyWorldTelemetry(Script):
    def at_script_creation(self):
        self.key = "economy_world_telemetry"
        self.desc = "World economy snapshot for /ui/economy-world"
        self.persistent = True
        self.interval = 60
        self.repeats = 0
        self.start_delay = False
        self.db.snapshot = {}
        self.db.snapshot_version = 1

    def at_start(self):
        self._run_snapshot()

    def at_repeat(self, **kwargs):
        self._run_snapshot()

    def _run_snapshot(self):
        from typeclasses.economy import get_economy
        from world.market_snapshot import serialize_resource_market
        from world.mining_site_metrics import site_to_dashboard_row
        from world.time import to_iso, utc_now

        now_iso = to_iso(utc_now()) or ""

        site_count = 0
        active_count = 0
        producing_count = 0
        total_cycle_cr = 0
        total_stored_cr = 0
        total_output_tons = 0.0

        for site in search_tag("mining_site", category="mining"):
            if not getattr(site.db, "is_mining_site", False):
                continue
            packed = site_to_dashboard_row(site)
            if not packed:
                continue
            row, cycle_cr, stored_cr = packed
            site_count += 1
            if row.get("active"):
                active_count += 1
            if cycle_cr > 0:
                producing_count += 1
                total_output_tons += float(row.get("estimatedOutputTons") or 0)
            total_cycle_cr += cycle_cr
            total_stored_cr += stored_cr

        econ = get_economy(create_missing=True)
        accounts = econ.db.accounts or {}
        treasury_cr = econ.get_balance(econ.get_treasury_account("alpha-prime"))
        tax_pool = int(econ.db.tax_pool or 0)
        player_mass = sum(
            int(v) for k, v in accounts.items() if str(k).startswith("player:")
        )

        from world.production_pipeline_estimate import sum_player_pipeline_breakdown_cr

        (
            char_n,
            world_stored_cr,
            world_accrual_cr,
            world_pipeline_cr,
            world_implied_cr_per_sec,
        ) = sum_player_pipeline_breakdown_cr()
        implied_cr_per_hour = int(max(0.0, world_implied_cr_per_sec) * 3600.0)

        from world.econ_automation.sim_metrics import collect_sim_metrics_snapshot

        sim_metrics = collect_sim_metrics_snapshot()

        automation_block: dict = {}
        try:
            from evennia import search_script

            found_ctrl = search_script("economy_automation_controller")
            if found_ctrl:
                c = found_ctrl[0]
                hist = list(c.db.rebalance_history or [])
                automation_block = {
                    "phase": str(c.db.phase or "stable"),
                    "globalPriceMultiplier": float(c.db.global_price_multiplier or 1.0),
                    "globalUpkeepMultiplier": float(c.db.global_upkeep_multiplier or 1.0),
                    "globalPayoutMultiplier": float(c.db.global_payout_multiplier or 1.0),
                    "recentHistory": hist[-5:],
                }
        except Exception:
            pass

        self.db.snapshot = {
            "computedAtIso": now_iso,
            "simMetrics": sim_metrics,
            "automation": automation_block,
            "worldProductionPipeline": {
                "playerCharacterCount": char_n,
                "estimatedPipelineTotalCr": world_pipeline_cr,
                "storedSitesBidCr": world_stored_cr,
                "accrualThisSlotEstimatedCr": world_accrual_cr,
                "impliedAccrualCrPerHourTotal": implied_cr_per_hour,
                "note": (
                    "Sum of per-character pipeline estimates (sites stored + in-slot accrual); "
                    "not wallet; excludes plant silo. Stored and accrual rows sum to the pipeline total."
                ),
            },
            "mining": {
                "siteCount": site_count,
                "activeSiteCount": active_count,
                "producingSiteCount": producing_count,
                "impliedCycleValueCr": total_cycle_cr,
                "storedValueBidCr": total_stored_cr,
                "impliedOutputTonsIfAllProducing": round(total_output_tons, 1),
            },
            "ledger": {
                "treasuryBalanceCr": treasury_cr,
                "taxPoolCr": tax_pool,
                "playerCreditsMassCr": player_mass,
                "accountCount": len(accounts),
            },
            "market": serialize_resource_market(),
        }
