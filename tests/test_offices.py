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


def test_find_strips_prefecture_prefix():
    """「福井県あわら市」のように都道府県名が前置されていても市町村名にマッチすること。"""
    directory = OfficeDirectory.load(DATA_PATH)
    result = directory.find("福井県あわら市")
    assert result is not None
    assert result.office == "あわら地域包括支援センター"


def test_find_prefecture_prefix_alone_does_not_break_matching():
    """都道府県名だけ(市町村名なし)の場合はマッチせず広域窓口にフォールバックすること。"""
    directory = OfficeDirectory.load(DATA_PATH)
    result = directory.find("東京都")
    assert result is not None
    assert result.area == "広域"


def test_find_matches_district_embedded_in_longer_address_string():
    """「福井県坂井市丸岡町」のように住所文字列の中に地区名が含まれる場合も特定できること。"""
    directory = OfficeDirectory.load(DATA_PATH)
    result = directory.find("福井県坂井市丸岡町")
    assert result is not None
    assert result.office == "丸岡地域包括支援センター"


def test_find_returns_specific_office_when_area_name_given_directly():
    directory = OfficeDirectory.load(DATA_PATH)
    result = directory.find("坂井")
    assert result is not None
    assert result.office == "坂井地域包括支援センター"


def test_find_municipality_with_multiple_offices_is_not_silently_arbitrary():
    """「坂井市」のみでは地区(三国/丸岡/春江/坂井)を特定できないため、
    広域窓口を返しつつ、候補地区を note として明示すること(サイレントに1件を選ばない)。
    """
    directory = OfficeDirectory.load(DATA_PATH)
    result = directory.find("坂井市")
    assert result is not None
    assert result.area == "広域"
    assert result.note is not None
    for expected_area in ("三国", "丸岡", "春江", "坂井"):
        assert expected_area in result.note


def test_find_prefecture_prefixed_ambiguous_municipality_also_notes_candidates():
    directory = OfficeDirectory.load(DATA_PATH)
    result = directory.find("福井県坂井市")
    assert result is not None
    assert result.area == "広域"
    assert result.note is not None
