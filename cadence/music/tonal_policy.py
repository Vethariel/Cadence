"""
Política de tonalidad — reduce sesgo a D minor vía mood/género/seed y contexto batch.
"""

from __future__ import annotations

import re
from typing import Literal

from cadence.music.tonal_batch_context import (
    get_batch_recent_signatures,
    record_tonal_choice,
    tonal_signature,
)

from cadence.music.scale_theory import ScaleMode, normalize_mode

Mode = ScaleMode

_KEY_RE = re.compile(
    r"\b(?:en\s+)?([A-G](?:#|b|♯|♭)?)\s*"
    r"(major|minor|maj|min|m|dorian|dorico|phrygian|frigio|frigian)\b",
    re.IGNORECASE,
)
_KEY_ONLY_RE = re.compile(
    r"\b(?:key\s*[:=]\s*)?([A-G](?:#|b|♯|♭)?)\s*(?:major|minor|maj|min|m)?\b",
    re.IGNORECASE,
)

# Pools por familia estilística (evitar un solo centro tonal)
_POOL_CHIPTUNE: list[tuple[str, Mode]] = [
    ("C", "major"), ("A", "minor"), ("E", "minor"), ("G", "major"),
]
_POOL_ORCHESTRAL: list[tuple[str, Mode]] = [
    ("F", "minor"), ("G", "minor"), ("A", "minor"), ("D", "minor"), ("E", "minor"),
]
_POOL_AMBIENT: list[tuple[str, Mode]] = [
    ("C", "minor"), ("A", "minor"), ("E", "minor"), ("F", "major"), ("D", "major"),
]
_POOL_ROCK_GAME: list[tuple[str, Mode]] = [
    ("E", "minor"), ("A", "minor"), ("G", "minor"), ("D", "major"), ("B", "minor"),
]
_POOL_CINEMATIC: list[tuple[str, Mode]] = [
    ("A", "minor"), ("D", "minor"), ("F", "minor"), ("C", "minor"), ("E", "minor"),
]
_POOL_DEFAULT: list[tuple[str, Mode]] = [
    ("C", "minor"), ("A", "minor"), ("F", "minor"), ("G", "minor"),
    ("E", "minor"), ("D", "minor"), ("B", "minor"), ("F", "major"),
    ("A", "major"), ("E", "major"),
]

_DARK_MOOD = (
    "dark", "oscuro", "aggressive", "agresiv", "ominous", "tense", "tension",
    "mister", "sinister", "grim",
)
_BRIGHT_MOOD = ("bright", "happy", "joy", "triumph", "victory", "uplift", "calm")


def _normalize_key(name: str) -> str:
    n = name.strip().replace("♯", "#").replace("♭", "b")
    if len(n) >= 2 and n[1] in "#b":
        return n[0].upper() + n[1]
    return n[0].upper()


def parse_explicit_key_mode(raw_prompt: str) -> tuple[str, Mode] | None:
    """Extrae tonalidad explícita del prompt (ej. 'D minor', 'en F# major')."""
    p = raw_prompt or ""
    m = _KEY_RE.search(p)
    if m:
        key = _normalize_key(m.group(1))
        mode_raw = m.group(2).lower()
        if mode_raw in ("minor", "min", "m"):
            mode: Mode = "minor"
        elif mode_raw in ("dorian", "dorico"):
            mode = "dorian"
        elif mode_raw in ("phrygian", "frigio", "frigian"):
            mode = "phrygian"
        else:
            mode = "major"
        return key, mode
    return None


def _tags_lower(genre_tags: list[str] | None) -> set[str]:
    if not genre_tags:
        return set()
    out: set[str] = set()
    for t in genre_tags:
        out.add(t.lower().strip())
        for part in t.lower().replace(",", " ").split():
            if part:
                out.add(part)
    return out


def _pool_for_context(
    *,
    genre_tags: list[str] | None,
    mood: str,
    use_case: str,
    raw_prompt: str,
) -> list[tuple[str, Mode]]:
    tags = _tags_lower(genre_tags)
    prompt = (raw_prompt or "").lower()
    uc = (use_case or "game").lower()

    if tags & {"chiptune", "eurobeat", "arcade", "8-bit", "8bit"} or any(
        x in prompt for x in ("chiptune", "eurobeat", "arcade")
    ):
        return list(_POOL_CHIPTUNE)
    if tags & {"ambient", "drone", "soundscape", "ethereal"} or uc == "loop":
        return list(_POOL_AMBIENT)
    if tags & {"orchestral", "symphonic", "epic", "cinematic"} or any(
        x in prompt for x in ("orquestal", "orchestral", "symphonic", "épico", "epico")
    ):
        return list(_POOL_ORCHESTRAL)
    if tags & {"rock", "metal", "techno", "industrial", "dubstep"} or any(
        x in prompt for x in ("rock", "metal", "techno")
    ):
        return list(_POOL_ROCK_GAME)
    if uc == "cutscene" or "cutscene" in prompt:
        return list(_POOL_CINEMATIC)
    return list(_POOL_DEFAULT)


def _infer_mode(
    *,
    mood: str,
    genre_tags: list[str] | None,
    use_case: str,
    seed: int,
) -> Mode:
    m = (mood or "").lower()
    if any(x in m for x in _BRIGHT_MOOD):
        return "major"
    if any(x in m for x in _DARK_MOOD):
        return "minor"
    tags = _tags_lower(genre_tags)
    if tags & {"chiptune", "eurobeat", "victory", "arcade"}:
        return "major" if seed % 3 == 0 else "minor"
    if tags & {"ambient", "dark ambient", "drone"}:
        return "minor"
    if (use_case or "").lower() == "loop":
        return "minor"
    return "minor" if seed % 5 else "major"


def _pick_from_pool(
    pool: list[tuple[str, Mode]],
    *,
    seed: int,
    raw_prompt: str,
    preferred_mode: Mode | None,
    batch_recent: list[str],
) -> tuple[str, Mode]:
    if preferred_mode:
        filtered = [(k, m) for k, m in pool if m == preferred_mode]
        if len(filtered) >= 2:
            pool = filtered

    candidates = [
        (k, m) for k, m in pool
        if tonal_signature(k, m) not in batch_recent
    ]
    if not candidates:
        candidates = list(pool)

    # Penalizar D minor si ya apareció en batch o es la opción por defecto perezosa
    if len(candidates) > 1:
        non_d = [(k, m) for k, m in candidates if not (k == "D" and m == "minor")]
        if non_d and ("D:minor" in batch_recent or seed % 4 != 0):
            candidates = non_d

    salt = abs(hash(raw_prompt)) % 97
    idx = (seed // 11 + salt) % len(candidates)
    return candidates[idx]


def select_tonal_center(
    *,
    raw_prompt: str = "",
    mood: str = "",
    genre_tags: list[str] | None = None,
    use_case: str = "game",
    energy_level: int = 3,
    seed: int = 0,
    record_batch: bool = True,
) -> tuple[str, Mode, str]:
    """
    Devuelve (key, mode, reason).
    Respeta tonalidad explícita en el prompt; si no, elige por pools + seed.
    """
    explicit = parse_explicit_key_mode(raw_prompt)
    if explicit:
        key, mode = explicit
        reason = "explicit_prompt_key"
        if record_batch:
            record_tonal_choice(key, mode)
        return key, mode, reason

    batch_recent = get_batch_recent_signatures()
    mode_hint = _infer_mode(
        mood=mood,
        genre_tags=genre_tags,
        use_case=use_case,
        seed=seed,
    )
    pool = _pool_for_context(
        genre_tags=genre_tags,
        mood=mood,
        use_case=use_case,
        raw_prompt=raw_prompt,
    )
    key, mode = _pick_from_pool(
        pool,
        seed=seed + energy_level * 3,
        raw_prompt=raw_prompt,
        preferred_mode=mode_hint,
        batch_recent=batch_recent,
    )
    reason = (
        f"policy_pool seed={seed} use_case={use_case!r} "
        f"mode_hint={mode_hint} batch_avoid={len(batch_recent)}"
    )
    if record_batch:
        record_tonal_choice(key, mode)
    return key, mode, reason


def apply_tonal_policy_to_proposal(
    proposal,
    intent,
    *,
    seed: int,
    record_batch: bool = True,
):
    """
    Ajusta key/mode del TechnicalProposal si el prompt no fija tonalidad.
    Devuelve (proposal, tonal_reason).
    """
    from cadence.schemas.song_state import TechnicalProposal, UserIntent

    if not isinstance(proposal, TechnicalProposal):
        raise TypeError("proposal debe ser TechnicalProposal")
    if not isinstance(intent, UserIntent):
        raise TypeError("intent debe ser UserIntent")

    if parse_explicit_key_mode(intent.raw_prompt):
        return proposal, "kept_llm_or_parser_explicit_key"

    key, mode, reason = select_tonal_center(
        raw_prompt=intent.raw_prompt,
        mood=intent.mood or "",
        genre_tags=proposal.genre_tags,
        use_case=intent.use_case,
        energy_level=proposal.energy_level,
        seed=seed,
        record_batch=record_batch,
    )

    if proposal.key == key and proposal.mode == mode:
        return proposal, f"{reason} (unchanged)"

    note = f"tonal_policy: {key} {mode} ({reason})"
    reasoning = f"{proposal.reasoning} | {note}".strip(" |")
    return proposal.model_copy(
        update={"key": key, "mode": mode, "reasoning": reasoning},
    ), reason
