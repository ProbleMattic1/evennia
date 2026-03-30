# Cadence challenges — player and design reference

This document describes **cadence challenges** in Aurnom: what they are, how time windows and progress work, and every challenge currently defined in game data. It does **not** cover implementation details or source code.

---

## What cadence challenges are

**Cadence challenges** are time-bucketed goals tracked automatically by the game. They sit **alongside** narrative missions: missions are story-driven (rooms, NPCs, choices); cadence challenges are operational (credits, property, extraction, travel patterns) and reset or roll over on calendar boundaries.

You can see active and recent challenges on the **control surface / dashboard** when logged in. Staff can reload definitions, inspect a character’s state, or grant completions for testing.

---

## Time and windows

All cadence boundaries use **UTC**.

| Cadence | Window meaning (plain language) |
|--------|----------------------------------|
| **Daily** | One calendar day in UTC (midnight to midnight). |
| **Weekly** | ISO week (Monday-based week numbering). |
| **Monthly** | Calendar month (UTC). |
| **Quarter** | Calendar quarter (Q1–Q4, UTC). |
| **Half-year** | First or second half of the UTC calendar year. |
| **Year** | Full UTC calendar year. |

Each challenge instance is tied to a **window key** (for example a date or `YYYY-Www`). You can only **complete** a given challenge **once per window**; when the window advances, a new instance can start.

---

## How the game knows you progressed

The server records **activity signals** when you do things in the world (examples below). It also **re-evaluates** your challenges when you refresh the web dashboard, use certain API bundles, log in (including balance snapshots), or when relevant actions fire. You do not “turn in” most challenges manually; completion is detected when the rules for that window are satisfied.

**Examples of what the game notices (conceptually):**

- Moving between rooms (which **locator zone** and **venue** you are in, and which rooms you have visited).
- Vendor purchases and, when applicable, tax flowing to the treasury.
- Starting a **property operation** (income type on a holding).
- Visiting your **parcel interior** via the property travel commands.
- **Primary** deed purchase, **listing** a deed, or **secondary market** deed sale.
- **Hauler** runs completing a delivery leg (mining / flora / fauna pipelines).
- **Plant / refinery** payouts that pay your character from treasury (mining slot participation and credit movement).
- **Balance at the start of the UTC day** (snapshot), used for “net positive day” style goals.

Some counters reset **every UTC day**; others accumulate per **week** or are kept **for all time** (for example lifetime credits moved, venues ever visited).

---

## Challenge status

For each active window you may see a status such as:

| Status | Meaning |
|--------|---------|
| **In progress** | The window is open; requirements not yet met (or not yet re-checked). |
| **Complete** | Requirements for this window are satisfied. |
| **Claimed** | Completion was acknowledged (if rewards use a claim step). |
| **Expired** | The window rolled over while still in progress (no completion that window). |

---

## Fair play and limits

- Progress is **server-side**. The dashboard displays what the server has recorded.
- Telemetry lists (rooms visited today, zones, and so on) are **bounded** so logs cannot grow without limit.
- Some long-window goals use **approximate** or **proxy** checks where a perfect per-day ledger does not exist yet; those are called out under the relevant challenge where it matters for players or designers.

---

## Narrative missions and optional unlocks

Completing certain challenges can be configured to **offer narrative missions** (story opportunities) to the same character. That link is **data-driven**: only challenges whose definitions include mission unlocks will do this.

---

## Staff and maintenance

- **Reload challenge definitions** without restarting the whole game server.
- **Inspect** a character’s challenge state and key counters.
- **Grant** a completion for testing or support (respects the template and current window).

---

## Challenge catalog

Below: **ID** (internal stable name), **cadence**, **title**, **summary** from data, then **rules** in plain language (thresholds and special conditions). Challenges marked **[DEV]** are canaries for verifying hooks; you can disable them in data for a live shard.

---

### Development canaries

| ID | Cadence | Title | Summary | Rules |
|----|---------|-------|---------|-------|
| `daily.canary_zone_visit` | Daily | Canary: Zone Visit | [DEV] Verify zone telemetry. | Visit at least **1** distinct locator zone today (movement). |
| `daily.canary_vendor_purchase` | Daily | Canary: Buy Something | [DEV] Verify vendor hook. | Make at least **1** vendor purchase today. |
| `weekly.canary_treasury` | Weekly | Canary: Treasury Touch | [DEV] Verify treasury hook. | At least **1** treasury touch this week (same family of signals as tax/treasury credits). |

---

### Daily — economy and credits

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `daily.balance_net_positive` | In the Black | End the day with more credits than you started with. | Current balance **greater than** the **UTC-day opening snapshot** taken when the server refreshed your balance (e.g. login / bundle). |
| `daily.balance_after_fee` | Paid and Still Profitable | Pay a fee or tax today and still end richer than you started. | At least one **treasury-related touch** today **and** same net-positive check as *In the Black*. |
| `daily.treasury_touch` | Civic Contributor | At least one transaction flowing through treasury today. | At least **1** counted treasury touch today. |
| `daily.vendor_purchase` | Retail Therapy | At least one vendor purchase today. | At least **1** vendor sale to you today. |
| `daily.vendor_spend_cap` | Frugal Buyer | Shop lightly but still shop. | At least **1** vendor purchase today **and** total vendor spend today **≤ 1,000 cr** (from economy records for that UTC day). |
| `daily.arbitrage_note` | Market Scout | Net-positive day with shopping at two different vendors. | At least **2** distinct **vendor IDs** today **and** net-positive vs. day-open balance snapshot. |
| `daily.friday_risk` | Big Ticket | A large single purchase. | At least one **vendor purchase** today with **single transaction ≥ 500 cr**. *(Template metadata mentions a Friday theme; the server currently applies the amount rule **any UTC day**.)* |

---

### Weekly — economy

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `weekly.tax_contribution` | Treasury Week | Tax through market activity this week. | At least **100 cr** of **tax** on your vendor purchases, summed from economy records for the **current weekly window**. **Designers:** validate weekly totals in QA—ISO week window keys and timestamp matching should be checked against real ledgers. |

---

### Daily — extraction and logistics

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `daily.single_mine_deposit` | Shift Work | Mining deposit today. | At least **1** mining-side deposit event today (game counts pipeline touches). |
| `daily.mining_slot_participation` | On the Clock | Participate in a mining delivery slot today. | Currently aligned with **same signal** as *Shift Work* (plant payout / deposit participation); may be refined later for strict slot grids. |
| `daily.triple_pipeline_touch` | Full Spectrum | Mining, flora, and fauna the same day. | At least **3** distinct pipelines touched today: **mining**, **flora**, **fauna**. |
| `daily.hauler_cycle` | Autonomous Loop | A hauler run today. | At least **1** hauler **completion** event today (unload / paid run leg). |

---

### Weekly — extraction

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `weekly.hauler_throughput` | Industrial Week | Many hauler runs across zones. | At least **5** hauler completions this week **and** evidence of **≥ 2** distinct extraction-related zones over time *(implementation uses weekly totals plus zone visit history; designers should sanity-check edge cases)*. |
| `weekly.pipeline_specialist_mining` | Mining Specialist | Own an active mining site. | You **own** at least one **mining site** object in the world. |

---

### Quarter and half-year — extraction and property depth

| ID | Cadence | Title | Summary | Rules |
|----|---------|-------|---------|-------|
| `quarter.district_track_industrial` | Quarter | Industrial Colony Veteran | Hauler work tied to Industrial Colony. | You have **visited** the **industrial-colony** locator zone, **and** weekly hauler totals across the quarter meet a **minimum event count** *(implementation uses a coarse global haul sum as proxy for quarter throughput; may be tightened later)*. |
| `quarter.district_track_killstar` | Quarter | Killstar Operator | Hauler work tied to Killstar Annex. | Same pattern as Industrial, zone **killstar-annex**. |
| `quarter.district_track_meridian` | Quarter | Meridian Corridor | Hauler work tied to Meridian Shipping. | Same pattern, zone **meridian-shipping**. |
| `half_year.claim_to_skyline` | Half-year | Claim to Skyline | Operating parcel with structures. | At least one **holding** you own has an **active operation** (not paused) **and** at least **1** **structure** installed. |
| `half_year.pipeline_specialist` | Half-year | Extraction Specialist | Long-horizon mining footprint. | You **own** at least one **mining site** (same family of check as weekly mining specialist, half-year cadence). |

---

### Daily — property and realty

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `daily.property_operation_touch` | Landlord's Hours | Touch property operations today. | At least **1** **property operation start** (or equivalent signal) today. |
| `daily.visit_parcel_shell` | Home Visit | Inside your parcel interior today. | You are standing in **your** property shell root room (parcel interior tied to **your** holding). |
| `daily.deed_on_person` | Deed in Hand | Carry a deed. | At least **one property claim deed** is in **your inventory** at check time. |

---

### Weekly — property and market

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `weekly.deed_market_action` | Deed Dealer | Market activity this week. | At least **1** deed **list**, **primary purchase**, or **secondary purchase** this week *(counts deed market actions)*. |
| `weekly.primary_deed_purchase` | New Parcel | Buy from primary real estate this week. | At least one **primary-market** deed purchase recorded this week in the economy log. |
| `weekly.access_control_change` | Building a Team | Managers or tenants on a holding. | At least one **holding** has a **non-empty** managers or tenants list *(means access was configured at least once)*. |

---

### Monthly — property and tax

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `monthly.portfolio_two_zones` | Diversified Portfolio | Holdings in two zones. | Your holdings span at least **2** distinct **zone** labels (e.g. residential vs industrial). |
| `monthly.two_operation_kinds` | Mixed Income | Two operation types. | At least **2** distinct **operation kinds** across holdings, each **running** (not paused). |
| `monthly.development_not_idle` | Active Development | Development not idle. | At least one holding has **development state** other than **idle**. |
| `monthly.operation_level` | Leveled Up | Operation tier. | At least one holding has **operation level ≥ 1**. |
| `monthly.tax_contribution` | Civic Duty | Monthly tax total. | At least **100 cr** tax on your vendor purchases this **calendar month** **as recorded** in the economy log. |
| `monthly.locator_cartography` | New Ground | Discover new rooms this month. | At least **5** rooms in your **all-time first-seen** list *(without a separate monthly baseline, this effectively rewards breadth of exploration over time; designers may tighten)*. |

---

### Year — property

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `year.anniversary_deed` | Anniversary Deed | Long continuous ownership. | At least one carried deed has a **creation timestamp** at least **365 days** ago *(depends on deed object metadata being present)*. |

---

### Daily — navigation and themes

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `daily.locator_zone_bingo` | Zone Hopper | Visit several zones today. | At least **3** distinct **locator zones** today. |
| `daily.arrival_zone_visit` | Through the Gate | Arrival zone today. | **Arrival** locator zone appears in today’s zone list. |
| `daily.venue_tour` | Grand Tour | Hub, services, retail same day. | Today you have visited rooms whose zones include **core-hub**, **core-services**, and **core-retail**. |
| `daily.monday_inventory` | Monday: Take Stock | Monday inventory check. | On **Monday (UTC)**, at least **1** item in inventory. **Other days:** automatically counts as satisfied for that day. |
| `daily.thursday_social` | Thursday: Make a Deal | Thursday social / deals. | On **Thursday (UTC)**, at least **1** deed-market action **this ISO week** *(listing, primary buy, or secondary sale—used as a proxy for “social” activity)*. **Other days:** the challenge **auto-completes** for that UTC day (predicate passes without the deed check). |

---

### Year — navigation

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `year.title_odyssey_venues` | Venue Odyssey | Every venue this year. | You have visited at least one room in **every** configured **venue** in the world data. |
| `year.title_odyssey_locator_zones` | Zone Cartographer | Every known locator zone this year. | You have hit **all** locator zone IDs the challenge system treats as the full set (arrival, hubs, retail, realty, extraction districts, etc.). |

---

### Weekly — property income streak

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `weekly.property_operation_streak` | Uninterrupted Income | Operations running and earning. | At least one holding: **operation not paused**, has a **kind**, and **ledger accrued credits ≥ 1** *(approximates “income this week”; not a full seven-day snapshot history)*. |

---

### Quarter — economy and deeds

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `quarter.economy_modifier_shift` | Market Event Witness | Global economy event. | The world **global economy modifier** is at least **5%** away from baseline **1.0** *(staff-tunable economy state)*. |
| `quarter.deed_buy_hold_sell` | Property Flipper | Buy, hold, then exit. | This quarter: a **deed purchase** was recorded, you held at least **1 day**, then a **list or sell** happened *(tracked on your character for the quarter)*. |
| `quarter.multi_holding_managers` | Management Portfolio | Manager on multiple holdings. | You appear as **manager** on at least **2** distinct **holdings** (including others’ parcels if the access list names you). |

---

### Year — meta and lifetime

| ID | Title | Summary | Rules |
|----|-------|---------|-------|
| `year.almanac_twelve` | Almanac of Alpha-Prime | Twelve monthly wins in a year. | Your **challenge history** shows at least **12** distinct **monthly** window completions in the **same UTC year**. |
| `year.ledger_lifetime_milestone` | Ledger Legend | Lifetime credit movement. | **Lifetime credits moved** (vendor purchases, payouts, and related signals the server accumulates) **≥ 1,000,000**. |
| `year.oath_pacifist` | The Pacifist Oath | Voluntary year-long rule. | Your character has a **staff-set “oath active” flag** for **pacifist** and **no “violated” flag** *(requires tooling or content to set flags; otherwise cannot complete)*. |

---

## Ideas from the design plan not yet authored as JSON

The master design list included additional IDs (black-market flavor, escort, stealth, refinery diversity, guild pool, raid/boss, collection codex, prestige path, etc.) reserved for when the underlying mechanics exist or for narrative missions only. They are **not** separate rows in the current `challenges.d` files until you add them.

---

## File location (for authors)

Challenge definitions are loaded from bundled JSON under the game data tree (`challenge_templates.json` legacy path plus `challenges.d/*.json`). Reload after edits using the staff workflow described above.

---

*Document generated for design and player reference. Cadence and thresholds match the shipped template data as of authoring; tune numbers in JSON to match live economy balance.*
