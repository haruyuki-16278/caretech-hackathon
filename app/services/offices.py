"""相談窓口DB (data/consultation_offices.json) のロードと検索。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.schemas import ConsultInfo

FALLBACK_AREA_KEYWORD = "広域"

# 「福井県」のように市町村名の前に付く都道府県名を取り除くための接尾辞。
# 末尾がこの文字自身のみ(例:「東京都」)の場合は何も残らないため除去しない
# (=都道府県名だけの入力は市町村名なしとして扱い、フォールバックに委ねる)。
_PREFECTURE_SUFFIXES = ("都", "道", "府", "県")


def _strip_prefecture_prefix(text: str) -> str:
    """先頭付近の都道府県名を取り除いた文字列を返す(取り除けない場合は元の文字列)。"""
    for suffix in _PREFECTURE_SUFFIXES:
        idx = text.find(suffix)
        # idx より後ろに文字が残る場合のみ都道府県名とみなして取り除く。
        # 「東京都」のように末尾が接尾辞そのものである場合は対象外。
        if 0 <= idx < len(text) - 1:
            return text[idx + 1 :]
    return text


class OfficeDirectory:
    """相談窓口一覧を保持し、居住エリアから最寄りの窓口を返す。"""

    def __init__(self, offices: list[dict]):
        self._offices = offices

    @classmethod
    def load(cls, path: Path) -> "OfficeDirectory":
        if not path.exists():
            raise FileNotFoundError(f"consultation offices data not found: {path}")
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return cls(offices=data.get("offices", []))

    def find(self, keyword: Optional[str]) -> Optional[ConsultInfo]:
        """居住エリア・市町村名から最寄りの窓口を検索する。

        マッチしない場合は広域(保険者)窓口をフォールバックとして返す。
        要件上「相談カテゴリでは必ず窓口情報を掲載する」ため、最終的に
        何らかの窓口情報を返すことを優先する。

        「福井県あわら市」のように都道府県名が前置されていたり、
        「福井県坂井市丸岡町」のように住所文字列の一部として市町村・地区名が
        埋め込まれていても、できるだけ具体的な窓口を特定する。
        また、「坂井市」のように1つの市町村に複数の窓口(地区)が存在する場合は、
        地区を特定できないまま1件をランダムに選ぶのではなく、広域窓口を返しつつ
        候補となる地区名を ``note`` に明示する。
        """
        normalized = keyword.strip() if keyword else ""
        if normalized:
            candidates = self._candidate_texts(normalized)

            # 1. 完全一致(地区名 or 窓口名そのもの)。最も確実なマッチ。
            for text in candidates:
                for office in self._offices:
                    if text in (office.get("area"), office.get("office")):
                        return self._to_consult_info(office)

            # 2. 市町村名との完全一致。1市町村に複数窓口がある場合は
            #    地区を特定できないため、あいまい解決(広域+note)を行う。
            for text in candidates:
                matches = [o for o in self._offices if o.get("municipality") == text]
                if matches:
                    return self._resolve_municipality_matches(text, matches)

            # 3. 住所等の長い文字列に地区名が埋め込まれているケース。
            #    (例:「福井県坂井市丸岡町」に含まれる「丸岡」)
            for text in candidates:
                for office in self._offices:
                    area = office.get("area") or ""
                    if area and area != FALLBACK_AREA_KEYWORD and area != text and area in text:
                        return self._to_consult_info(office)

            # 4. 長い文字列に市町村名が埋め込まれているケース。
            #    地区までは特定できないため、あいまい解決を行う。
            for text in candidates:
                municipality_names = {
                    o.get("municipality")
                    for o in self._offices
                    if o.get("municipality") and o.get("municipality") != text and o.get("municipality") in text
                }
                for municipality_name in municipality_names:
                    matches = [o for o in self._offices if o.get("municipality") == municipality_name]
                    if matches:
                        return self._resolve_municipality_matches(municipality_name, matches)

        return self._fallback_office()

    @staticmethod
    def _candidate_texts(normalized: str) -> list[str]:
        """検索対象の候補文字列を返す(元の文字列 → 都道府県名を除いた文字列の順)。"""
        stripped = _strip_prefecture_prefix(normalized)
        if stripped and stripped != normalized:
            return [normalized, stripped]
        return [normalized]

    def _resolve_municipality_matches(self, municipality_name: str, matches: list[dict]) -> Optional[ConsultInfo]:
        """市町村名に一致した窓口候補から、返却する ConsultInfo を決定する。

        候補が1件のみであればそれを返す。複数件(=地区が特定できない)の場合は、
        広域窓口があればそれを返しつつ、候補地区一覧を note に明示する。
        広域窓口が見つからない場合も、先頭の候補を返しつつ同様に note を付与し、
        「複数該当したことを利用者に伝えない」状態を避ける。
        """
        if len(matches) == 1:
            return self._to_consult_info(matches[0])

        area_names = [o.get("area", "") for o in matches if o.get("area")]
        note = (
            f"{municipality_name}には複数の相談窓口があります({'・'.join(area_names)})。"
            "お住まいの地区名を教えていただくと、より詳しい窓口をご案内できます。"
        )

        broad_office = self._find_broad_office_covering(municipality_name)
        base_office = broad_office if broad_office is not None else matches[0]
        info = self._to_consult_info(base_office)
        return info.model_copy(update={"note": note})

    def _find_broad_office_covering(self, municipality_name: str) -> Optional[dict]:
        for office in self._offices:
            if office.get("area") != FALLBACK_AREA_KEYWORD:
                continue
            municipality = office.get("municipality") or ""
            if municipality_name in municipality:
                return office
        return None

    def _fallback_office(self) -> Optional[ConsultInfo]:
        for office in self._offices:
            if office.get("area") == FALLBACK_AREA_KEYWORD:
                return self._to_consult_info(office)
        if self._offices:
            return self._to_consult_info(self._offices[0])
        return None

    @staticmethod
    def _to_consult_info(office: dict) -> ConsultInfo:
        return ConsultInfo(
            municipality=office.get("municipality", ""),
            area=office.get("area", ""),
            office=office.get("office", ""),
            field=office.get("field", ""),
            address=office.get("address"),
            phone=office.get("phone"),
            fax=office.get("fax"),
        )


@lru_cache(maxsize=1)
def _cached_directory(path_str: str) -> OfficeDirectory:
    return OfficeDirectory.load(Path(path_str))


def get_office_directory() -> OfficeDirectory:
    settings = get_settings()
    return _cached_directory(str(settings.consultation_offices_path))
