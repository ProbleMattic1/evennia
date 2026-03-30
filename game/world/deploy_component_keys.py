"""
Shared deploy naming: append stable [owner_trunc:site_id] suffix to component keys.

Used by mining package deploy (rig/storage/hauler) and bio colony deploy
(harvester/storage/hauler) so object keys stay unique and follow one convention.
"""

from __future__ import annotations

import copy
from typing import Iterable


def deploy_instance_suffix(buyer, site) -> str:
    """
    Stable, short token for object keys: owner display key + site primary key.
    Caps length so keys stay readable; site.id guarantees uniqueness.
    """
    bk = (getattr(buyer, "key", None) or "?").strip()[:12] or "?"
    sid = getattr(site, "id", None)
    if sid is None:
        sid = 0
    return f"{bk}:{sid}"[:28]


def prepare_deploy_components(
    components: list,
    buyer,
    site,
    types_with_keys: Iterable[str],
) -> list:
    """
    Deep-copy component dicts; append ' [suffix]' to each comp['key'] for listed types.
    """
    if not components:
        return []
    out = copy.deepcopy(components)
    unique = deploy_instance_suffix(buyer, site)
    allowed = frozenset(types_with_keys)
    for c in out:
        if c.get("type") not in allowed:
            continue
        base = (c.get("key") or "").strip()
        if not base:
            continue
        c["key"] = f"{base} [{unique}]"
    return out
