"""Fixtures compartidas de pytest."""

import pytest

from cadence.music.pattern_batch_context import reset_pattern_batch_context


@pytest.fixture(autouse=True)
def _isolate_pattern_batch_memory():
    """Evita que la memoria de combos rítmicos de un test afecte a otros."""
    reset_pattern_batch_context()
    yield
    reset_pattern_batch_context()
