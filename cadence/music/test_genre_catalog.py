"""Tests del catálogo de géneros."""

from cadence.music.genre_catalog import (
    GENRE_CATALOG,
    all_genres,
    format_genre_catalog_for_llm,
    normalize_genre,
    normalize_genres,
)


def test_catalog_has_breadth():
    assert len(all_genres()) >= 150
    assert len(GENRE_CATALOG) >= 10


def test_normalize_aliases():
    assert normalize_genre("8bit") == "8-bit"
    assert normalize_genre("dnb") == "drum and bass"
    assert normalize_genre("boss battle") == "boss fight"
    assert normalize_genre("TECHNO") == "techno"


def test_normalize_genres_dedupes():
    tags = normalize_genres(["techno", "TECHNO", "dnb", "drum and bass"])
    assert tags == ["techno", "drum and bass"]


def test_format_catalog_for_llm():
    text = format_genre_catalog_for_llm()
    assert "CATÁLOGO DE GÉNEROS" in text
    assert "dubstep" in text
    assert "boss fight" in text


if __name__ == "__main__":
    test_catalog_has_breadth()
    test_normalize_aliases()
    test_normalize_genres_dedupes()
    test_format_catalog_for_llm()
    print("All genre_catalog tests passed.")
