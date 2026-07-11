"""相談窓口DB(F5): data/consultation_offices.json から最寄り窓口を返す。"""
import json
from typing import Optional

from .config import OFFICES_JSON
from .schemas import ConsultInfo

with open(OFFICES_JSON, encoding="utf-8") as f:
    _DATA = json.load(f)

_OFFICES = [o for o in _DATA["offices"] if o.get("phone")]  # 連絡先のある窓口のみ
_DEFAULT_AREA = "坂井"


def find_office(area: str) -> Optional[ConsultInfo]:
    """居住エリア名に一致する地域包括支援センターを返す。

    一致しない場合は既定エリア(坂井)の窓口を返す(必ず窓口を掲載する要件のため)。
    """
    normalized = (area or "").strip()
    for office in _OFFICES:
        if office["area"] == normalized:
            return ConsultInfo(**office)
    for office in _OFFICES:
        if office["area"] == _DEFAULT_AREA:
            return ConsultInfo(**office)
    return None


def list_areas() -> list:
    return [o["area"] for o in _OFFICES]
