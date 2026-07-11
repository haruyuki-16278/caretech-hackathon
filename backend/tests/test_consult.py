"""相談窓口検索(F4, F5)のテスト。"""
from app.consult import find_office, list_areas


def test_returns_office_matching_area():
    # Arrange / Act
    office = find_office("丸岡")

    # Assert
    assert office is not None
    assert office.office == "丸岡地域包括支援センター"
    assert office.phone == "0776-68-1130"


def test_falls_back_to_default_area_when_unknown():
    # 未知のエリアでも必ず窓口を返す(必須要件: 相談には必ず窓口を掲載)
    office = find_office("東京")

    assert office is not None
    assert office.area == "坂井"


def test_falls_back_when_area_empty():
    office = find_office("")

    assert office is not None
    assert office.phone


def test_all_five_centers_are_available():
    assert sorted(list_areas()) == sorted(["あわら", "三国", "丸岡", "春江", "坂井"])
