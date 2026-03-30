# Charter Properties — Operator Guide

Charter lots are hand-authored, Tier 3 (Prime) properties in the NanoMegaPlex.
Unlike procedural exchange lots they are **never listed on the primary sovereign
exchange**.  On every server start they are automatically claimed by the
`NanoMegaPlex Real Estate` broker and held in its inventory until a staff
member explicitly releases them.

---

## Districts

| District | Zone | Typical size_units |
|---|---|---|
| Crown Atrium | residential | 7–10 |
| Sovereign Terrace | commercial | 7–10 |
| Meridian Heights | residential | 6–8 |
| Apex Row | commercial | 6–9 |
| Coreward Industrial | industrial | 9–10 |

The full lot list lives in
[`game/world/bootstrap_nmp_charter.py`](../world/bootstrap_nmp_charter.py)
(`NMP_CHARTER_CATALOGUE`).

---

## Viewing broker inventory

```
charterinventory
```

Lists every charter deed currently held by the broker with lot key, tier, zone,
size, and district.  Aliases: `charterlisting`, `charterinv`.

---

## Path 1 — Free grant to a founder or sponsor

```
grantcharter <player> = <lot_key or #claim_id>
```

- Moves the deed directly from the broker to the player's inventory.
- `sync_property_title_from_deed_location` fires: `holding.title_owner` and
  `lot.db.owner` are both updated to the player immediately.
- No credits are exchanged.
- The player receives an in-game notification and can then run `startproperty`
  to begin generating income.

**Example:**

```
grantcharter Varek = Crown Atrium Penthouse I
grantcharter Varek = #42
```

### Alternative: puppet the broker and `give`

Staff can also puppet `NanoMegaPlex Real Estate` in-game and use the standard
`give <deed> to <player>` command.  The broker is exempt from the 500 cr
transfer fee, so the deed moves at no cost.

---

## Path 2 — Paid release via secondary market

```
releasecharter <lot_key or #claim_id> = <price in cr>
```

- Lists the broker's deed on the secondary deed market (same escrow used by
  player resales).
- `title_owner` is cleared while the deed sits in escrow; `lot.db.owner`
  retains the broker as last known owner until a buyer completes purchase.
- Any player can then buy it via the web UI (secondary deed market section)
  or `buypropertydeed <claim_id>`.
- On purchase, credits go to the broker's economy account and `lot.db.owner`
  updates to the buyer.

**Example:**

```
releasecharter Crown Atrium Penthouse I = 500000
releasecharter #42 = 250000
```

---

## Adding or editing charter lots

Edit `NMP_CHARTER_CATALOGUE` in
[`game/world/bootstrap_nmp_charter.py`](../world/bootstrap_nmp_charter.py).
The bootstrap is idempotent: existing lots matched by `lot_key` are updated
in place and the grant is skipped if the broker already holds the deed.

To add a new district, add an entry to `DISTRICTS` in the same file.

**Never rename a `lot_key` after first boot** — the key is the stable identity
used by claims, holdings, and deed market listings.  Add new lots instead.

---

## Resuming normal exchange for a charter lot

There is no revert path to "unclaim" a lot back to the primary sovereign
exchange once it has been granted.  If you need to make a charter parcel
behave like a normal exchange lot:

1. Have the current holder list it on the secondary deed market
   (`listpropertydeed <price>`) or use `releasecharter`.
2. Buyers purchase through the standard secondary market flow.
