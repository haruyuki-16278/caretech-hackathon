from __future__ import annotations

from pathlib import Path

from app.services.offices import OfficeDirectory

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "consultation_offices.json"


def test_load_offices_from_repository_data_file():
    directory = OfficeDirectory.load(DATA_PATH)
    result = directory.find("丸岡")
    assert result is not None
    assert result.office == "丸岡地域包括支援センター"
    assert result.phone == "0776-68-1130"


def test_find_by_municipality_substring():
    directory = OfficeDirectory.load(DATA_PATH)
    result = directory.find("あわら市")
    assert result is not None
    assert result.office == "あわら地域包括支援センター"


def test_find_falls_back_to_general_office_when_unmatched():
    directory = OfficeDirectory.load(DATA_PATH)
    result = directory.find("東京都")
    assert result is not None
    assert result.area == "広域"


def test_find_falls_back_to_general_office_when_area_is_none():
    directory = OfficeDirectory.load(DATA_PATH)
    result = directory.find(None)
    assert result is not None
    assert result.area == "広域"
