"""IDs canónicos, familias de patrón y aliases de compatibilidad."""

from __future__ import annotations

_VARIANT_SUFFIXES = frozenset({"a", "b", "c"})


def pattern_family(pattern_id: str) -> str:
    """techno_b → techno; offbeat_a → offbeat."""
    if not pattern_id:
        return pattern_id
    parts = pattern_id.rsplit("_", 1)
    if len(parts) == 2 and parts[1] in _VARIANT_SUFFIXES:
        return parts[0]
    return pattern_id


def resolve_pattern_id(
    pattern_id: str | None,
    aliases: dict[str, str],
    *,
    default: str,
) -> str:
    if not pattern_id:
        return default
    if pattern_id in aliases:
        return aliases[pattern_id]
    return pattern_id


def expand_family_candidates(
    base_order: list[str],
    pool: tuple[str, ...] | list[str],
) -> list[str]:
    """Incluye sub-variantes (_a/_b) de cada familia mencionada en base_order."""
    pool_list = list(pool)
    pool_set = set(pool_list)
    seen: set[str] = set()
    ordered: list[str] = []
    for pid in base_order:
        fam = pattern_family(pid)
        variants = [p for p in pool_list if p == pid or pattern_family(p) == fam]
        if not variants and pid in pool_set:
            variants = [pid]
        for v in sorted(variants):
            if v not in seen:
                seen.add(v)
                ordered.append(v)
    for p in pool_list:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return ordered
