"""相談窓口DB (data/consultation_offices.json) のロードと検索。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.schemas import ConsultInfo

FALLBACK_AREA_KEYWORD = "広域"


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
        """
        if keyword:
            normalized = keyword.strip()
            for office in self._offices:
                if normalized in (office.get("area"), office.get("office")):
                    return self._to_consult_info(office)
            for office in self._offices:
                municipality = office.get("municipality") or ""
                if normalized and normalized in municipality:
                    return self._to_consult_info(office)

        return self._fallback_office()

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
